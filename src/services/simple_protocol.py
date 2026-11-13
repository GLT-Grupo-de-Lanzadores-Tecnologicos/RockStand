"""Parser for the line-based ASCII protocol of the HX711 firmware.

The firmware answers every command with exactly one line:

* a decimal number  -> a measurement, in kilograms-force
* ``OK``            -> the command was accepted
* ``ERROR:<reason>``-> the command was rejected
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Optional, Union


@dataclass(frozen=True)
class MeasurementLine:
    weight_kg: float


@dataclass(frozen=True)
class OkLine:
    pass


@dataclass(frozen=True)
class ErrorLine:
    message: str


ParsedLine = Union[MeasurementLine, OkLine, ErrorLine]


def parse_line(line: str) -> Optional[ParsedLine]:
    """Parse one line received from the firmware; unknown lines give ``None``."""
    text = line.strip()
    if not text:
        return None

    if text == "OK":
        return OkLine()

    if text.startswith("ERROR"):
        return ErrorLine(message=text)

    try:
        return MeasurementLine(weight_kg=float(text))
    except ValueError:
        return None
