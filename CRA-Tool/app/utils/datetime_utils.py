from __future__ import annotations

import re
from datetime import datetime


_GRAPH_FRACTION_RE = re.compile(r"^(?P<prefix>.+?\.)(?P<fraction>\d{1,})(?P<suffix>Z|[+-]\d{2}:\d{2})?$")


def parse_graph_datetime(value: str | None) -> datetime | None:
    """Parse Microsoft Graph datetime strings, including 7-digit fractions."""

    if value is None:
        return None
    text = str(value).strip()
    if not text:
        return None

    if text.endswith("Z"):
        text = f"{text[:-1]}+00:00"

    match = _GRAPH_FRACTION_RE.match(text)
    if match:
        fraction = match.group("fraction")
        suffix = match.group("suffix") or ""
        if suffix == "Z":
            suffix = "+00:00"
        text = f"{match.group('prefix')}{fraction[:6].ljust(6, '0')}{suffix}"

    return datetime.fromisoformat(text)
