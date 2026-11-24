"""Dead-band filter that turns the noise around zero into a flat line."""

from __future__ import annotations

# Default threshold in newtons (about 5 gf). The HX711 firmware averages
# 3 samples per reading, which still leaves a few gf of noise with no load.
DEFAULT_ZERO_THRESHOLD_N = 0.05

# Once the output is held at zero, the reading must exceed the threshold by
# this factor to be released. The hysteresis stops noise that straddles the
# threshold from flickering between 0 and +/- threshold.
RELEASE_FACTOR = 2.0


class ZeroFilter:
    """Replaces readings near zero with exactly ``0.0``.

    A reading enters the zero band when ``|force| < threshold_n`` and leaves it
    only when ``|force| > threshold_n * RELEASE_FACTOR``. Readings outside the
    band are passed through unchanged (no offset is subtracted), so real loads
    keep their exact value.
    """

    def __init__(self, threshold_n: float = DEFAULT_ZERO_THRESHOLD_N, enabled: bool = True):
        self.threshold_n = threshold_n
        self.enabled = enabled
        self._holding_zero = False

    @property
    def threshold_n(self) -> float:
        return self._threshold_n

    @threshold_n.setter
    def threshold_n(self, value: float) -> None:
        self._threshold_n = max(0.0, float(value))

    def apply(self, force_n: float) -> float:
        if not self.enabled or self._threshold_n <= 0.0:
            self._holding_zero = False
            return force_n

        limit = self._threshold_n * RELEASE_FACTOR if self._holding_zero else self._threshold_n
        if self._holding_zero:
            self._holding_zero = abs(force_n) <= limit
        else:
            self._holding_zero = abs(force_n) < limit
        return 0.0 if self._holding_zero else force_n

    def reset(self) -> None:
        self._holding_zero = False
