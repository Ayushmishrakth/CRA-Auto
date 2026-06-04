#!/usr/bin/env python3
"""
Compile uploaded CRA Excel workbooks into runtime-safe JSON registries.

The runtime engine must not read Excel files. This script is the controlled
ingestion boundary:

Excel files -> normalization -> validation -> JSON registries -> DB seeder.
"""

from __future__ import annotations

import argparse
import json
import re
import sys
from collections import Counter, defaultdict
from dataclasses import asdict, dataclass, field
from datetime import datetime, timezone
from pathlib import Path
from typing import Any
from xml.etree import ElementTree as ET
from zipfile import ZipFile


DEFAULT_SOURCES = [
    Path("/home/herb/Downloads/CRA_Parameters_PassFailCriteria 2.xlsx"),
    Path("/home/herb/Downloads/CRA parameters and how to get them(1) (1) 1.xlsx"),
]

DEFAULT_OUTPUT_DIR = Path("app/config/assessment_registry")
SPREADSHEET_NS = {"a": "http://schemas.openxmlformats.org/spreadsheetml/2006/main"}
REL_NS = {
    "r": "http://schemas.openxmlformats.org/package/2006/relationships",
    "office": "http://schemas.openxmlformats.org/officeDocument/2006/relationships",
}

SEVERITY_ORDER = {"critical": 5, "high": 4, "medium": 3, "low": 2, "info": 1}
SEVERITY_DEDUCTIONS = {"critical": 25, "high": 15, "medium": 8, "low": 3, "info": 1}
VALID_COLLECTION_METHODS = {
    "graph",
    "powershell",
    "script",
    "portal",
    "manual",
    "composite",
    "unknown",
}


@dataclass
class ValidationReport:
    errors: list[str] = field(default_factory=list)
    warnings: list[str] = field(default_factory=list)
    stats: dict[str, Any] = field(default_factory=dict)

    def error(self, message: str) -> None:
        self.errors.append(message)

    def warn(self, message: str) -> None:
        self.warnings.append(message)


def clean_text(value: Any) -> str:
    if value is None:
        return ""
    text = str(value).replace("\xa0", " ").replace("\u200b", " ")
    return re.sub(r"\s+", " ", text).strip()


def normalize_header(value: str) -> str:
    return re.sub(r"[^a-z0-9]+", "_", clean_text(value).lower()).strip("_")


def slugify(value: str) -> str:
    text = clean_text(value).lower()
    text = text.replace("&", " and ")
    text = re.sub(r"[^a-z0-9]+", "_", text)
    return re.sub(r"_+", "_", text).strip("_")


def canonical_severity(value: str) -> str:
    severity = slugify(value)
    if severity in SEVERITY_ORDER:
        return severity
    return ""


def canonical_collection_method(value: str) -> str:
    raw = clean_text(value).lower()
    if not raw:
        return "unknown"
    if "graph" in raw:
        return "graph"
    if "script" in raw or "powershell" in raw or "ps" == raw:
        return "powershell"
    if "portal" in raw or "admin center" in raw or "defender portal" in raw:
        return "portal"
    if "manual" in raw or "need to check" in raw:
        return "manual"
    return slugify(raw) if slugify(raw) in VALID_COLLECTION_METHODS else "unknown"


def infer_collector_type(collection_method: str, graph_endpoint: str, powershell_mapping: str) -> str:
    if graph_endpoint:
        return "graph"
    if powershell_mapping or collection_method in {"powershell", "script"}:
        return "powershell"
    if collection_method == "portal":
        return "portal"
    if collection_method == "manual":
        return "manual"
    return "unknown"


def infer_domain(technology: str, pillar: str) -> str:
    pillar_key = slugify(pillar)
    technology_key = slugify(technology)
    if pillar_key == "governanace":
        return "governance"
    if pillar_key and len(pillar_key) > 2 and pillar_key not in {"m365", "unclassified"}:
        return pillar_key
    if any(token in technology_key for token in ["entra", "identity", "azure_ad"]):
        return "identity_access"
    if any(token in technology_key for token in ["purview", "compliance", "dlp", "retention"]):
        return "compliance"
    if any(
        token in technology_key
        for token in ["teams", "sharepoint", "onedrive", "exchange", "mailbox", "owa", "outlook"]
    ):
        return "collaboration"
    if any(token in technology_key for token in ["license", "licensing", "sku"]):
        return "licensing"
    if any(token in technology_key for token in ["defender", "security"]):
        return "security"
    return "unclassified"


def severity_weight(severity: str) -> float:
    return float(SEVERITY_ORDER.get(severity, 1))


def extract_reference_urls(*values: str) -> list[str]:
    urls: list[str] = []
    for value in values:
        urls.extend(re.findall(r"https?://[^\s),]+", value or ""))
    return sorted(set(urls))


def detect_rule_type(pass_criteria: str, fail_criteria: str) -> str:
    text = f"{pass_criteria} {fail_criteria}".lower()
    if "%" in text or "percent" in text:
        return "percentage_threshold"
    if any(token in text for token in ["enabled", "disabled", "configured", "not configured", "present"]):
        return "boolean_gate"
    if any(token in text for token in ["less than", "more than", "greater than", "count", "number of"]):
        return "count_threshold"
    if any(token in text for token in ["policy", "policies"]):
        return "policy_existence_check"
    if any(token in text for token in ["set to", "configuration", "setting"]):
        return "configuration_value_check"
    if "," in text or " and " in text or " or " in text:
        return "composite_rule"
    return "configuration_value_check"


def build_rule_expression(pass_criteria: str, fail_criteria: str) -> dict[str, Any]:
    text = f"{pass_criteria} {fail_criteria}".lower()
    percentages = [float(item) for item in re.findall(r"(\d+(?:\.\d+)?)\s*%", text)]
    counts = [float(item) for item in re.findall(r"(?:less than|more than|greater than|under|over)\s+(\d+)", text)]
    expression: dict[str, Any] = {
        "pass_criteria": pass_criteria,
        "fail_criteria": fail_criteria,
    }
    if percentages:
        expression["percentage_thresholds"] = sorted(set(percentages))
    if counts:
        expression["count_thresholds"] = sorted(set(counts))
    return expression


def col_index(cell_ref: str) -> int:
    match = re.match(r"([A-Z]+)", cell_ref)
    if not match:
        return 0
    value = 0
    for char in match.group(1):
        value = value * 26 + ord(char) - 64
    return value - 1


class XlsxReader:
    def __init__(self, path: Path):
        self.path = path

    def _shared_strings(self, archive: ZipFile) -> list[str]:
        try:
            raw = archive.read("xl/sharedStrings.xml")
        except KeyError:
            return []
        root = ET.fromstring(raw)
        shared = []
        for item in root.findall("a:si", SPREADSHEET_NS):
            shared.append("".join(text.text or "" for text in item.findall(".//a:t", SPREADSHEET_NS)))
        return shared

    def _sheet_paths(self, archive: ZipFile) -> list[tuple[str, str]]:
        workbook = ET.fromstring(archive.read("xl/workbook.xml"))
        rels = ET.fromstring(archive.read("xl/_rels/workbook.xml.rels"))
        rel_map = {rel.attrib["Id"]: rel.attrib["Target"] for rel in rels}
        sheets = []
        for sheet in workbook.findall(".//a:sheet", SPREADSHEET_NS):
            rel_id = sheet.attrib["{http://schemas.openxmlformats.org/officeDocument/2006/relationships}id"]
            target = rel_map[rel_id]
            sheet_path = target if target.startswith("xl/") else f"xl/{target.lstrip('/')}"
            sheets.append((sheet.attrib["name"], sheet_path))
        return sheets

    def _cell_value(self, cell: ET.Element, shared: list[str]) -> str:
        cell_type = cell.attrib.get("t")
        if cell_type == "inlineStr":
            return clean_text("".join(text.text or "" for text in cell.findall(".//a:t", SPREADSHEET_NS)))
        value = cell.find("a:v", SPREADSHEET_NS)
        if value is None:
            return ""
        raw = value.text or ""
        if cell_type == "s":
            return clean_text(shared[int(raw)] if raw.isdigit() and int(raw) < len(shared) else raw)
        return clean_text(raw)

    def sheets(self) -> dict[str, list[list[str]]]:
        with ZipFile(self.path) as archive:
            shared = self._shared_strings(archive)
            result: dict[str, list[list[str]]] = {}
            for sheet_name, sheet_path in self._sheet_paths(archive):
                root = ET.fromstring(archive.read(sheet_path))
                rows: list[list[str]] = []
                for row in root.findall(".//a:sheetData/a:row", SPREADSHEET_NS):
                    cells = {
                        col_index(cell.attrib.get("r", "A1")): self._cell_value(cell, shared)
                        for cell in row.findall("a:c", SPREADSHEET_NS)
                    }
                    if not cells:
                        continue
                    max_index = max(cells)
                    values = [cells.get(index, "") for index in range(max_index + 1)]
                    if any(values):
                        rows.append(values)
                result[sheet_name] = rows
            return result


def row_to_record(headers: list[str], row: list[str]) -> dict[str, str]:
    return {
        normalize_header(header): clean_text(row[index] if index < len(row) else "")
        for index, header in enumerate(headers)
        if clean_text(header)
    }


def extract_records(source: Path, report: ValidationReport) -> list[dict[str, Any]]:
    reader = XlsxReader(source)
    records: list[dict[str, Any]] = []
    for sheet_name, rows in reader.sheets().items():
        if not rows:
            continue
        header = [normalize_header(value) for value in rows[0]]
        has_parameter_header = "parameter_name" in header
        if has_parameter_header:
            raw_headers = rows[0]
            data_rows = rows[1:]
            for row_number, row in enumerate(data_rows, start=2):
                record = row_to_record(raw_headers, row)
                if not record.get("parameter_name"):
                    continue
                record["_source_file"] = source.name
                record["_source_sheet"] = sheet_name
                record["_source_row"] = row_number
                records.append(record)
        else:
            # Some sheets are value-only mappings: parameter, pillar, status, severity, technology.
            for row_number, row in enumerate(rows, start=1):
                if len(row) < 4 or not clean_text(row[0]) or clean_text(row[0]).lower() == "parameter name":
                    continue
                record = {
                    "parameter_name": clean_text(row[0]),
                    "pillar": clean_text(row[1] if len(row) > 1 else ""),
                    "expected_status": clean_text(row[2] if len(row) > 2 else ""),
                    "severity": clean_text(row[3] if len(row) > 3 else ""),
                    "technology": clean_text(row[4] if len(row) > 4 else ""),
                    "_source_file": source.name,
                    "_source_sheet": sheet_name,
                    "_source_row": row_number,
                }
                records.append(record)
    if not records:
        report.warn(f"No parameter records extracted from {source}")
    return records


def merge_records(records: list[dict[str, Any]], report: ValidationReport) -> dict[str, dict[str, Any]]:
    merged: dict[str, dict[str, Any]] = {}
    display_names: dict[str, set[str]] = defaultdict(set)
    for record in records:
        name = record.get("parameter_name", "")
        key = slugify(name)
        if not key:
            report.warn(f"Skipped row without parameter name: {record.get('_source_file')}:{record.get('_source_row')}")
            continue
        if key not in merged:
            merged[key] = {
                "parameter_key": key,
                "display_name": name,
                "technology": "",
                "domain": "",
                "category": "",
                "severity": "",
                "collection_method": "unknown",
                "collector_type": "unknown",
                "graph_endpoint": "",
                "powershell_mapping": "",
                "portal_mapping": "",
                "pass_criteria": "",
                "fail_criteria": "",
                "warning_threshold": "",
                "expected_output": "",
                "copilot_relevance": "",
                "scoring_weight": None,
                "copilot_blocker": False,
                "source_refs": [],
            }
        item = merged[key]
        display_names[key].add(name)
        source_ref = {
            "file": record.get("_source_file"),
            "sheet": record.get("_source_sheet"),
            "row": record.get("_source_row"),
        }
        if source_ref not in item["source_refs"]:
            item["source_refs"].append(source_ref)

        technology = record.get("technology") or record.get("script_portal") or ""
        pillar = record.get("pillar") or ""
        how_to_check = record.get("how_to_check") or ""
        script_portal = record.get("script_portal") or record.get("script_portal_") or ""
        severity = canonical_severity(record.get("risk_severity") or record.get("severity") or item["severity"])
        collection_method = canonical_collection_method(script_portal or how_to_check or item["collection_method"])

        item["technology"] = item["technology"] or clean_text(technology)
        item["domain"] = item["domain"] or infer_domain(technology, pillar)
        item["category"] = item["category"] or clean_text(pillar) or clean_text(technology) or "Unclassified"
        item["severity"] = item["severity"] or severity
        item["collection_method"] = item["collection_method"] if item["collection_method"] != "unknown" else collection_method
        item["pass_criteria"] = item["pass_criteria"] or clean_text(record.get("pass", ""))
        item["fail_criteria"] = item["fail_criteria"] or clean_text(record.get("fail", ""))
        item["expected_output"] = item["expected_output"] or clean_text(record.get("output", ""))
        item["copilot_relevance"] = item["copilot_relevance"] or clean_text(record.get("copilot_relation", ""))
        item["portal_mapping"] = item["portal_mapping"] or how_to_check
        item["graph_endpoint"] = item["graph_endpoint"] or clean_text(record.get("graph_endpoint", ""))
        item["powershell_mapping"] = item["powershell_mapping"] or (
            item["display_name"] if collection_method == "powershell" else ""
        )

    for key, names in display_names.items():
        if len(names) > 1:
            report.warn(f"Parameter key {key!r} merged display name variants: {sorted(names)}")
    return merged


def finalize_parameter(item: dict[str, Any], report: ValidationReport) -> dict[str, Any]:
    if not item["severity"]:
        report.error(f"{item['parameter_key']}: missing severity")
        item["severity"] = "info"
    if not item["domain"] or item["domain"] == "unclassified":
        report.error(f"{item['parameter_key']}: missing or unclassified domain")
    if item["scoring_weight"] is None:
        item["scoring_weight"] = severity_weight(item["severity"])
    item["collector_type"] = infer_collector_type(
        item["collection_method"], item["graph_endpoint"], item["powershell_mapping"]
    )
    item["copilot_blocker"] = item["severity"] == "critical" or "block" in item["copilot_relevance"].lower()
    return item


def build_registries(records: list[dict[str, Any]]) -> tuple[dict[str, Any], ValidationReport]:
    report = ValidationReport()
    raw_keys = [slugify(record.get("parameter_name", "")) for record in records if record.get("parameter_name")]
    duplicates = {key: count for key, count in Counter(raw_keys).items() if count > 1}
    report.stats["duplicate_rows_by_parameter_key"] = duplicates

    merged = merge_records(records, report)
    parameters = [finalize_parameter(item, report) for item in merged.values()]
    parameters.sort(key=lambda item: (item["domain"], item["display_name"]))

    seen = set()
    for parameter in parameters:
        key = parameter["parameter_key"]
        if key in seen:
            report.error(f"Duplicate parameter key after merge: {key}")
        seen.add(key)
        if parameter["scoring_weight"] < 0:
            report.error(f"{key}: invalid negative scoring weight")
        if parameter["collector_type"] == "unknown":
            report.warn(f"{key}: collector mapping is unknown")
        if parameter["collector_type"] == "graph" and not parameter["graph_endpoint"]:
            report.error(f"{key}: graph collector missing Graph endpoint")
        if parameter["collection_method"] not in VALID_COLLECTION_METHODS:
            report.error(f"{key}: invalid collection method {parameter['collection_method']}")

    rules = []
    recommendations = []
    collectors = []
    for parameter in parameters:
        key = parameter["parameter_key"]
        rule_type = detect_rule_type(parameter["pass_criteria"], parameter["fail_criteria"])
        rule = {
            "parameter_key": key,
            "rule_type": rule_type,
            "severity": parameter["severity"],
            "copilot_blocking": parameter["copilot_blocker"],
            "scoring_weight": parameter["scoring_weight"],
            "expression": build_rule_expression(parameter["pass_criteria"], parameter["fail_criteria"]),
        }
        rules.append(rule)

        recommendation = {
            "parameter_key": key,
            "title": f"Remediate {parameter['display_name']}",
            "severity": parameter["severity"],
            "impact": parameter["copilot_relevance"],
            "remediation_steps": [
                parameter["pass_criteria"] or "Configure this control to meet the uploaded CRA pass criteria."
            ],
            "copilot_impact": parameter["copilot_relevance"],
            "priority": SEVERITY_ORDER.get(parameter["severity"], 1),
            "reference_urls": extract_reference_urls(
                parameter["portal_mapping"],
                parameter["copilot_relevance"],
                parameter["pass_criteria"],
                parameter["fail_criteria"],
            ),
        }
        if not recommendation["impact"]:
            report.warn(f"{key}: recommendation impact is missing")
        recommendations.append(recommendation)

        collectors.append(
            {
                "parameter_key": key,
                "collector_name": f"{parameter['collector_type']}.{key}",
                "collector_type": parameter["collector_type"],
                "collection_method": parameter["collection_method"],
                "graph_endpoint": parameter["graph_endpoint"],
                "powershell_script": parameter["powershell_mapping"],
                "portal_mapping": parameter["portal_mapping"],
                "parser_mapping": {
                    "expected_output": parameter["expected_output"],
                    "value_field": "value",
                    "status_field": "status",
                },
                "throttling_strategy": {
                    "retry_after_header": parameter["collector_type"] == "graph",
                    "max_retries": 3,
                    "backoff_seconds": [2, 5, 15],
                },
            }
        )

    domain_counter = Counter(parameter["domain"] for parameter in parameters)
    total = sum(domain_counter.values()) or 1
    scoring = {
        "domain_weights": {
            domain: round(count / total, 4)
            for domain, count in sorted(domain_counter.items())
        },
        "severity_deductions": SEVERITY_DEDUCTIONS,
        "score_normalization": {
            "minimum": 0,
            "maximum": 100,
            "method": "weighted_domain_average_with_severity_deductions",
        },
        "blocker_logic": {
            "critical_copilot_blockers_cap_score_at": 59,
            "copilot_blocker_field": "copilot_blocker",
        },
    }

    report.stats.update(
        {
            "parameters": len(parameters),
            "rules": len(rules),
            "recommendations": len(recommendations),
            "collectors": len(collectors),
            "domains": dict(domain_counter),
            "collector_types": dict(Counter(item["collector_type"] for item in parameters)),
            "generated_at": datetime.now(timezone.utc).isoformat(),
        }
    )

    registries = {
        "parameters": parameters,
        "rules": rules,
        "recommendations": recommendations,
        "collectors": collectors,
        "scoring": scoring,
    }
    return registries, report


def write_json(path: Path, payload: Any) -> None:
    path.parent.mkdir(parents=True, exist_ok=True)
    path.write_text(json.dumps(payload, indent=2, sort_keys=True) + "\n", encoding="utf-8")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(description="Compile CRA Excel workbooks into JSON registries.")
    parser.add_argument("--source", action="append", type=Path, help="Excel workbook path. Can be passed multiple times.")
    parser.add_argument("--output-dir", type=Path, default=DEFAULT_OUTPUT_DIR)
    parser.add_argument("--strict", action="store_true", help="Exit non-zero when validation errors are detected.")
    args = parser.parse_args(argv)

    sources = args.source or [path for path in DEFAULT_SOURCES if path.exists()]
    missing = [str(path) for path in (args.source or DEFAULT_SOURCES) if not path.exists()]
    if missing:
        print(f"Missing source files: {missing}", file=sys.stderr)
        return 2
    if not sources:
        print("No source workbooks found.", file=sys.stderr)
        return 2

    extraction_report = ValidationReport()
    records: list[dict[str, Any]] = []
    for source in sources:
        records.extend(extract_records(source, extraction_report))

    registries, report = build_registries(records)
    report.errors.extend(extraction_report.errors)
    report.warnings.extend(extraction_report.warnings)
    report.stats["source_files"] = [str(path) for path in sources]
    report.stats["source_records"] = len(records)

    for name, payload in registries.items():
        write_json(args.output_dir / f"{name}.json", payload)
    write_json(args.output_dir / "validation_report.json", asdict(report))

    print(json.dumps(asdict(report), indent=2, sort_keys=True))
    if args.strict and report.errors:
        return 1
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
