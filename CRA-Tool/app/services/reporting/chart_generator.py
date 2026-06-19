from __future__ import annotations

from io import BytesIO
from typing import Any

import matplotlib

matplotlib.use("Agg")
import matplotlib.pyplot as plt


def _items(data: Any) -> list[tuple[str, float]]:
    if isinstance(data, dict):
        return [(str(key), float(value or 0)) for key, value in data.items()]
    if isinstance(data, list):
        rows = []
        for item in data:
            if isinstance(item, dict):
                rows.append((str(item.get("name") or item.get("label") or ""), float(item.get("value") or 0)))
        return rows
    return []


def _figure_to_png(fig) -> BytesIO:
    output = BytesIO()
    fig.savefig(output, format="png", dpi=140, bbox_inches="tight", facecolor="white")
    plt.close(fig)
    output.seek(0)
    return output


def _pie_chart(data: Any, title: str, colors: list[str] | None = None) -> BytesIO:
    rows = [(label, value) for label, value in _items(data) if value > 0]
    if not rows:
        rows = [("No data", 1)]
    labels, values = zip(*rows)
    fig, ax = plt.subplots(figsize=(5, 3.5))
    ax.pie(values, labels=labels, autopct="%1.0f%%", startangle=90, colors=colors)
    ax.set_title(title, fontsize=11, fontweight="bold")
    return _figure_to_png(fig)


def _bar_chart(data: Any, title: str, color: str = "#3B82F6") -> BytesIO:
    rows = [(label, value) for label, value in _items(data) if label]
    if not rows:
        rows = [("No data", 0)]
    labels, values = zip(*rows)
    fig, ax = plt.subplots(figsize=(6, 3))
    bars = ax.barh(range(len(labels)), values, color=color)
    ax.set_yticks(range(len(labels)))
    ax.set_yticklabels(labels, fontsize=8)
    ax.invert_yaxis()
    ax.bar_label(bars, padding=3, fontsize=8)
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return _figure_to_png(fig)


def generate_severity_pie_chart(severity_distribution: Any) -> BytesIO:
    return _pie_chart(
        severity_distribution,
        "Findings by Severity",
        ["#DC2626", "#EA580C", "#D97706", "#65A30D", "#3B82F6"],
    )


def generate_pass_fail_chart(pass_count: int, fail_count: int) -> BytesIO:
    return _pie_chart(
        {"Pass": pass_count, "Fail": fail_count},
        "Pass vs Fail",
        ["#16A34A", "#DC2626"],
    )


def generate_service_chart(service_distribution: Any) -> BytesIO:
    return _bar_chart(service_distribution, "Results by Service", "#1E3A5F")


def generate_pillar_chart(pillar_distribution: Any) -> BytesIO:
    return _bar_chart(pillar_distribution, "Findings by Pillar", "#3B82F6")


def generate_risk_category_chart(risk_category_distribution: Any) -> BytesIO:
    return _pie_chart(
        risk_category_distribution,
        "Risk Category",
        ["#DC2626", "#EA580C", "#D97706", "#65A30D", "#3B82F6"],
    )


def generate_donut_chart(active: int, total: int, title: str, size: tuple[float, float] = (2.5, 2.5)) -> BytesIO:
    active = max(float(active or 0), 0.0)
    total = max(float(total or 0), 0.0)
    pct = (active / total * 100) if total > 0 else 0
    fill_color = "#27AE60" if pct > 0 else "#CCCCCC"
    fig, ax = plt.subplots(figsize=size)
    ax.pie(
        [pct, max(0, 100 - pct)],
        colors=[fill_color, "#E8E8E8"],
        startangle=90,
        wedgeprops={"width": 0.35, "edgecolor": "white", "linewidth": 2},
    )
    ax.text(0, 0, f"{pct:.0f}%", ha="center", va="center", fontsize=16, fontweight="bold")
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.set_aspect("equal")
    ax.set_axis_off()
    return _figure_to_png(fig)


def generate_pie_chart(data_dict: Any, title: str, size: tuple[float, float] = (3.5, 3.0)) -> BytesIO:
    rows = [(label, value) for label, value in _items(data_dict) if value > 0]
    if not rows:
        rows = [("No data", 1)]
    labels, values = zip(*rows)
    fig, ax = plt.subplots(figsize=size)
    wedges, _texts, autotexts = ax.pie(values, labels=None, autopct="%1.0f%%", startangle=90)
    for text in autotexts:
        text.set_fontsize(8)
        text.set_fontweight("bold")
    ax.set_title(title, fontsize=11, fontweight="bold")
    ax.legend(
        wedges,
        [f"{label}; {int(value)}" for label, value in zip(labels, values)],
        loc="lower center",
        bbox_to_anchor=(0.5, -0.18),
        ncol=2,
        fontsize=7,
        frameon=False,
    )
    return _figure_to_png(fig)


def generate_bar_chart(fields_dict: Any, total: int, title: str, size: tuple[float, float] = (3.5, 2.8)) -> BytesIO:
    rows = [(label, value) for label, value in _items(fields_dict) if label]
    if not rows:
        rows = [("No data", 0)]
    labels, present = zip(*rows)
    total = max(int(total or max(present, default=0) or 0), 0)
    missing = [max(total - int(value), 0) for value in present]
    x = range(len(labels))
    fig, ax = plt.subplots(figsize=size)
    ax.bar(x, missing, color="#E53935", label="Not Added")
    ax.bar(x, present, bottom=missing, color="#43A047", label="Added")
    ax.set_xticks(list(x))
    ax.set_xticklabels([label.replace(" ", "\n") for label in labels], fontsize=7)
    ax.set_title(title, fontsize=10, fontweight="bold")
    ax.legend(fontsize=7, frameon=False)
    ax.spines["top"].set_visible(False)
    ax.spines["right"].set_visible(False)
    return _figure_to_png(fig)
