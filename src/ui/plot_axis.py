"""Plot axis that always prints plain decimal numbers."""

from __future__ import annotations

import math

import pyqtgraph as pg

MAX_DECIMALS = 6


class PlainNumberAxis(pg.AxisItem):
    """Axis whose tick labels never use scientific notation or SI prefixes."""

    def tickStrings(self, values, scale, spacing):
        if not math.isfinite(scale):
            scale = 1.0

        # Show one more decimal than the tick spacing needs.
        scaled_spacing = abs((spacing or 0.0) * scale)
        if math.isfinite(scaled_spacing) and scaled_spacing > 0:
            decimals = int(math.ceil(-math.log10(scaled_spacing))) + 1
            decimals = min(MAX_DECIMALS, max(0, decimals))
        else:
            decimals = 2

        return [self._format_tick(value * scale, decimals) for value in values]

    @staticmethod
    def _format_tick(value: float, decimals: int) -> str:
        if not math.isfinite(value):
            return ""
        if abs(value) < 10 ** (-(decimals + 1)):
            value = 0.0  # avoid printing "-0"
        text = f"{value:.{decimals}f}"
        if "." in text:
            text = text.rstrip("0").rstrip(".")
        return text or "0"
