"""In-memory measurement session: buffering, relative time, tare and peak force."""

from __future__ import annotations

from collections import deque
from typing import Iterator, Optional

from domain_models import CorrectedSample, ForceSample
from services.zero_filter import ZeroFilter

DEFAULT_MAX_POINTS = 4000


class MeasurementService:
    """Stores the most recent samples of a session, already tare-corrected.

    Forces are always kept in newtons; unit conversion is a display concern.
    After the tare, ``zero_filter`` flattens the noise around zero; the tare
    itself always uses the unfiltered reading.
    The buffer is bounded, so very long sessions keep only the newest points
    (a recording to file is not affected by this limit).
    """

    def __init__(self, max_points: int = DEFAULT_MAX_POINTS, zero_filter: Optional[ZeroFilter] = None):
        self._samples: deque[CorrectedSample] = deque(maxlen=max_points)
        self.zero_filter = zero_filter if zero_filter is not None else ZeroFilter()
        self._latest_unfiltered_n: Optional[float] = None
        self._time_origin_s: Optional[float] = None
        self._tare_offset_n = 0.0
        self._force_max_n = 0.0

    def append(self, sample: ForceSample) -> CorrectedSample:
        """Store a raw sample and return it with relative time and tare applied."""
        if self._time_origin_s is None:
            self._time_origin_s = sample.t_raw_s

        unfiltered_n = sample.force_raw_n - self._tare_offset_n
        self._latest_unfiltered_n = unfiltered_n
        corrected = CorrectedSample(
            t_rel_s=sample.t_raw_s - self._time_origin_s,
            force_corr_n=self.zero_filter.apply(unfiltered_n),
        )
        self._samples.append(corrected)
        self._force_max_n = max(self._force_max_n, corrected.force_corr_n)
        return corrected

    def apply_tare_from_latest(self) -> bool:
        """Make the latest reading the new zero. Returns False if there is no data."""
        if self.latest is None or self._latest_unfiltered_n is None:
            return False
        # The unfiltered value, so a residual offset inside the zero band is
        # also removed.
        self._tare_offset_n += self._latest_unfiltered_n
        self._latest_unfiltered_n = 0.0
        self.zero_filter.reset()
        return True

    def clear(self) -> None:
        """Drop all samples and restart time and peak tracking. Tare is kept."""
        self._samples.clear()
        self._time_origin_s = None
        self._latest_unfiltered_n = None
        self._force_max_n = 0.0
        self.zero_filter.reset()

    @property
    def latest(self) -> Optional[CorrectedSample]:
        return self._samples[-1] if self._samples else None

    @property
    def latest_unfiltered_n(self) -> Optional[float]:
        """Latest tare-corrected force before the zero filter (for calibration)."""
        return self._latest_unfiltered_n

    @property
    def force_max_n(self) -> float:
        """Peak corrected force since the last clear (never below zero)."""
        return self._force_max_n

    def __iter__(self) -> Iterator[CorrectedSample]:
        return iter(self._samples)
