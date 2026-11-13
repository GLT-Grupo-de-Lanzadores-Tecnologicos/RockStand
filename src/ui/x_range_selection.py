"""Selection of a time range on the plot, used to export part of a session."""

from __future__ import annotations

from typing import Sequence

import pyqtgraph as pg
from PyQt5.QtWidgets import QLabel, QPushButton

SELECT_TEXT = "Select X range"
EXPORT_TEXT = "Export selected range"
EMPTY_TEXT = "-"

# Fraction of the recorded time span initially covered by the selection band.
INITIAL_SPAN_FRACTION = 0.25


class XRangeSelectionController:
    """Drives the draggable band on the plot and the widgets that describe it.

    While the selection is active, ``btn_primary`` becomes the export button
    and ``btn_cancel`` is shown.
    """

    def __init__(
        self,
        plot: pg.PlotWidget,
        lbl_xrange: QLabel,
        lbl_xdelta: QLabel,
        btn_primary: QPushButton,
        btn_cancel: QPushButton,
    ):
        self.lbl_xrange = lbl_xrange
        self.lbl_xdelta = lbl_xdelta
        self.btn_primary = btn_primary
        self.btn_cancel = btn_cancel
        self.active = False

        self.region = pg.LinearRegionItem()
        self.region.setZValue(10)
        self.region.hide()
        self.region.sigRegionChanged.connect(self.update_labels)
        plot.addItem(self.region)

    def activate(self, times: Sequence[float]) -> None:
        self.active = True
        self.region.show()
        self.btn_primary.setText(EXPORT_TEXT)
        self.btn_cancel.show()
        self.ensure_initialized(times)
        self.update_labels()

    def deactivate(self) -> None:
        self.active = False
        self.region.hide()
        self.btn_primary.setText(SELECT_TEXT)
        self.btn_cancel.hide()
        self.lbl_xrange.setText(EMPTY_TEXT)
        self.lbl_xdelta.setText(EMPTY_TEXT)

    def ensure_initialized(self, times: Sequence[float]) -> None:
        """Place the band over the last part of the data if it is still empty."""
        if len(times) < 2:
            return

        x0, x1 = self.region.getRegion()
        if abs(x1 - x0) > 1e-12:
            return  # the user (or a previous call) already placed it

        t_min, t_max = times[0], times[-1]
        span = max(t_max - t_min, 0.001)
        self.region.setRegion((t_max - span * INITIAL_SPAN_FRACTION, t_max))

    def reset_region(self) -> None:
        self.region.setRegion((0, 0))

    def selected_range(self) -> tuple[float, float]:
        x0, x1 = self.region.getRegion()
        return min(x0, x1), max(x0, x1)

    def update_labels(self) -> None:
        if not self.active:
            return
        x_min, x_max = self.selected_range()
        self.lbl_xrange.setText(f"{x_min:.1f} .. {x_max:.1f} s")
        self.lbl_xdelta.setText(f"{x_max - x_min:.1f} s")
