"""In-memory measurement session: buffering, relative time, tare and peak force."""

from __future__ import annotations

from collections import deque
from typing import Iterator, Optional

from domain_models import CorrectedSample, ForceSample

DEFAULT_MAX_POINTS = 4000


class MeasurementService:
    """Stores the most recent samples of a session, already tare-corrected.

    Forces are always kept in newtons; unit conversion is a display concern.
    The buffer is bounded, so very long sessions keep only the newest points
    (a recording to file is not affected by this limit).
    """

    def __init__(self, max_points: int = DEFAULT_MAX_POINTS):
        self._samples: deque[CorrectedSample] = deque(maxlen=max_points)
        self._time_origin_s: Optional[float] = None
        self._tare_offset_n = 0.0
        self._force_max_n = 0.0

    def append(self, sample: ForceSample) -> CorrectedSample:
        """Store a raw sample and return it with relative time and tare applied."""
        if self._time_origin_s is None:
            self._time_origin_s = sample.t_raw_s

        corrected = CorrectedSample(
            t_rel_s=sample.t_raw_s - self._time_origin_s,
            force_corr_n=sample.force_raw_n - self._tare_offset_n,
        )
        self._samples.append(corrected)
        self._force_max_n = max(self._force_max_n, corrected.force_corr_n)
        return corrected

    def apply_tare_from_latest(self) -> bool:
        """Make the latest reading the new zero. Returns False if there is no data."""
        latest = self.latest
        if latest is None:
            return False
        self._tare_offset_n += latest.force_corr_n
        return True

    def clear(self) -> None:
        """Drop all samples and restart time and peak tracking. Tare is kept."""
        self._samples.clear()
        self._time_origin_s = None
        self._force_max_n = 0.0

    @property
    def latest(self) -> Optional[CorrectedSample]:
        return self._samples[-1] if self._samples else None

    @property
    def force_max_n(self) -> float:
        """Peak corrected force since the last clear (never below zero)."""
        return self._force_max_n

    def __iter__(self) -> Iterator[CorrectedSample]:
        return iter(self._samples)
