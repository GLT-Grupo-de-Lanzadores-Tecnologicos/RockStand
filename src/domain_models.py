"""Domain types shared by the services and the UI. No Qt or serial imports here."""

from __future__ import annotations

from dataclasses import dataclass
from enum import Enum
from typing import Optional

# Standard gravity, used to convert between newtons and kgf / gf.
STANDARD_GRAVITY = 9.80665

# A captured calibration reading below this magnitude is treated as "no load".
CALIBRATION_MIN_READING = 1e-9

# A new scale factor may differ from the current one by at most this ratio
# (in either direction). Larger jumps almost always mean a wrong unit or tare.
MAX_ALLOWED_SCALE_RATIO = 50.0


class Unit(str, Enum):
    """Force units available for display and export."""

    N = "N"
    KGF = "kgf"
    GF = "gf"


class PlotMode(str, Enum):
    """How the live plot follows incoming data."""

    ACCUMULATED = "accumulated"  # show everything in the buffer
    SLIDING = "sliding"  # show only the last few seconds
    PAUSED = "paused"  # freeze the plot (data keeps being stored)


class LoadCellType(str, Enum):
    """Mounting of the load cell; compression readings are sign-inverted."""

    TENSION = "tension"
    COMPRESSION = "compression"


@dataclass(frozen=True)
class ForceSample:
    """A sample as received: session time and force before tare."""

    t_raw_s: float
    force_raw_n: float


@dataclass(frozen=True)
class CorrectedSample:
    """A stored sample: time relative to the first sample, force after tare."""

    t_rel_s: float
    force_corr_n: float


@dataclass(frozen=True)
class CalibrationInput:
    """Data needed to compute a new firmware scale factor.

    ``captured_reading`` and ``known_value`` must be in the same unit.
    """

    scale_current: float
    captured_reading: float
    known_value: float


@dataclass(frozen=True)
class CalibrationResult:
    """Either a new scale factor or a user-facing error message."""

    scale_new: Optional[float] = None
    error: Optional[str] = None
