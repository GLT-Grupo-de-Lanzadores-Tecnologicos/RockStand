"""Force unit conversion and parsing of user-typed force values."""

from __future__ import annotations

import re
from typing import Optional

from domain_models import STANDARD_GRAVITY, Unit

_FORCE_TEXT_PATTERN = re.compile(r"([+-]?\d+(?:\.\d+)?)\s*([a-z]*)")

_UNIT_ALIASES: dict[str, Optional[Unit]] = {
    "": None,
    "n": Unit.N,
    "newton": Unit.N,
    "newtons": Unit.N,
    "kgf": Unit.KGF,
    "gf": Unit.GF,
}


def newtons_to_unit(force_n: float, unit: Unit) -> float:
    """Convert a force in newtons to ``unit``."""
    if unit == Unit.KGF:
        return force_n / STANDARD_GRAVITY
    if unit == Unit.GF:
        return force_n / STANDARD_GRAVITY * 1000.0
    return force_n


def unit_to_newtons(value: float, unit: Unit) -> float:
    """Convert a force expressed in ``unit`` to newtons."""
    if unit == Unit.KGF:
        return value * STANDARD_GRAVITY
    if unit == Unit.GF:
        return value / 1000.0 * STANDARD_GRAVITY
    return value


def parse_force_text(text: str) -> tuple[Optional[float], Optional[Unit]]:
    """Parse text such as ``"3.27"``, ``"3,27 N"``, ``"0.333 kgf"`` or ``"333gf"``.

    Returns ``(value, unit)``. ``unit`` is ``None`` when the text has no unit
    suffix; ``value`` is ``None`` when the text cannot be parsed.
    """
    normalized = text.strip().lower().replace(",", ".")
    match = _FORCE_TEXT_PATTERN.fullmatch(normalized)
    if not match:
        return None, None

    unit_text = match.group(2)
    if unit_text not in _UNIT_ALIASES:
        return None, None
    return float(match.group(1)), _UNIT_ALIASES[unit_text]
