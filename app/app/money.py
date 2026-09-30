from __future__ import annotations

import re
from typing import Any

_NUM = re.compile(
    r"(?P<sym>\$|CAD|cdn)?\s*(?P<num>[\d]{1,3}(?:,\d{3})+|\d+)(?:\.(?P<dec>\d+))?\s*(?P<scale>billion|milliard|million|millions|M|B)?",
    re.I,
)


def parse_amount(raw: Any) -> float | None:
    if raw is None or raw == "":
        return None
    if isinstance(raw, (int, float)):
        return float(raw)
    text = str(raw).strip().replace("\xa0", " ")
    try:
        return float(text.replace(",", "").replace("$", "").replace("CAD", "").strip())
    except ValueError:
        pass
    m = _NUM.search(text)
    if not m:
        return None
    num = float((m.group("num") or "0").replace(",", ""))
    if m.group("dec"):
        num = float(f"{int(num)}.{m.group('dec')}")
    scale = (m.group("scale") or "").lower()
    if scale in {"billion", "milliard", "b"}:
        num *= 1_000_000_000
    elif scale in {"million", "millions", "m"}:
        num *= 1_000_000
    return num


def format_cad(amount: float | None) -> str | None:
    if amount is None:
        return None
    if amount >= 1_000_000_000:
        return f"${amount / 1_000_000_000:.2f} billion"
    if amount >= 1_000_000:
        return f"${amount / 1_000_000:.2f} million"
    return f"${amount:,.2f}"
