"""Main window: live force plot, serial connection, tare, calibration and export."""

from __future__ import annotations

import math
from datetime import datetime
from typing import Optional

from PyQt5 import uic
from PyQt5.QtCore import Qt, QTimer
from PyQt5.QtGui import QPixmap
from PyQt5.QtWidgets import (
    QActionGroup,
    QApplication,
    QDialog,
    QFileDialog,
    QFrame,
    QLabel,
    QMainWindow,
    QMessageBox,
    QScrollArea,
    QSizePolicy,
)

import i18n
from app_info import APP_NAME, APP_SUBTITLE, APP_VERSION, ORGANIZATION
from domain_models import STANDARD_GRAVITY, ForceSample, LoadCellType, PlotMode, Unit
from resources import LOGO_PNG, MAIN_WINDOW_UI, resource_path
from services.measurement_service import MeasurementService
from services.serial_port_service import scan_serial_ports
from services.serial_worker import SerialThreadController
from services.txt_export_service import (
    RANGE_EXPORT_FILENAME_FORMAT,
    RECORDING_FILENAME_FORMAT,
    TXT_FILE_FILTER,
    TxtRecorder,
    ensure_txt_extension,
    export_measurements,
)
from services.unit_conversion import newtons_to_unit, unit_to_newtons
from ui.calibrate_dialog import CalibrateDialog
from ui.plot_axis import PlainNumberAxis
from ui.x_range_selection import XRangeSelectionController

PLOT_REFRESH_INTERVAL_MS = 50
PORT_SCAN_INTERVAL_MS = 2000
SLIDING_WINDOW_S = 10.0
PANEL_LOGO_SIZE_PX = 96
LONG_MESSAGE_MS = 8000
# Menu bar, status bar and layout margins around the side panel.
WINDOW_CHROME_HEIGHT_PX = 70
WINDOW_TITLE_BAR_ALLOWANCE_PX = 40

# Decimals of the zero filter threshold, per display unit.
ZERO_THRESHOLD_DECIMALS = {Unit.N: 3, Unit.KGF: 4, Unit.GF: 1}

EMPTY_TEXT = "-"


class MainWindow(QMainWindow):
    """Wires the widgets from ``main_window.ui`` to the services."""

    def __init__(self):
        super().__init__()
        uic.loadUi(resource_path(MAIN_WINDOW_UI), self)
        self.setWindowTitle(f"{APP_NAME} v{APP_VERSION} - {APP_SUBTITLE}")

        self._init_state()
        self._init_serial()
        self._setup_plot()
        self._setup_panel()
        self._setup_language_menu()
        self._connect_signals()
        self._setup_timers()
        self.refresh_ports()

    # ---- setup -----------------------------------------------------------

    def _init_state(self) -> None:
        self.unit = Unit.N
        self.plot_mode = PlotMode.ACCUMULATED
        self.load_cell_type = LoadCellType.BENDING
        self.measurements = MeasurementService()
        self.recorder = TxtRecorder()
        self.is_reading_active = True

        self.available_ports: list[str] = []
        self.port_scan_error: Optional[str] = None
        self.showing_port_error = False
        self.pending_port: Optional[str] = None
        self.connected_port: Optional[str] = None

    def _init_serial(self) -> None:
        self.serial = SerialThreadController()
        self.serial.connected.connect(self.on_connected)
        self.serial.disconnected.connect(self.on_disconnected)
        self.serial.warning.connect(self.on_warning)
        self.serial.error.connect(self.on_error)
        self.serial.measurement_received.connect(self.on_measurement)
        self.serial.scale_updated.connect(self.on_scale_updated)

    def _setup_plot(self) -> None:
        self.plot = self.widget_graph
        self.plot.plotItem.setAxisItems({"left": PlainNumberAxis(orientation="left")})
        self.plot.setTitle(self.tr("Force vs Time"))
        self.plot.setLabel("bottom", self.tr("Time"), units="s")
        self.plot.getAxis("left").enableAutoSIPrefix(False)
        self._update_force_axis_label()
        self.curve = self.plot.plot([], [])

        self.x_selection = XRangeSelectionController(
            plot=self.plot,
            lbl_xrange=self.lbl_xrange,
            lbl_xdelta=self.lbl_xdelta,
            btn_primary=self.btn_x_select,
            btn_cancel=self.btn_x_cancel,
        )

    def _setup_panel(self) -> None:
        logo = QLabel()
        logo.setPixmap(
            QPixmap(resource_path(LOGO_PNG)).scaled(
                PANEL_LOGO_SIZE_PX, PANEL_LOGO_SIZE_PX, Qt.KeepAspectRatio, Qt.SmoothTransformation
            )
        )
        logo.setAlignment(Qt.AlignCenter)
        logo.setToolTip(ORGANIZATION)
        self.verticalLayout_panel.insertWidget(0, logo)

        self.btn_x_cancel.hide()
        self._set_x_range_rows_visible(False)
        self._sync_settings_controls()
        self._sync_zero_filter_controls()

        # Long status texts must not widen the panel; fix it at its natural width.
        self.lbl_status.setSizePolicy(QSizePolicy.Ignored, QSizePolicy.Preferred)
        self.widget_panel.setSizePolicy(QSizePolicy.Fixed, QSizePolicy.Expanding)
        panel_size = self.widget_panel.sizeHint()
        self.widget_panel.setFixedWidth(panel_size.width())
        self._make_panel_scrollable(panel_size.width())
        self._fit_height_to_panel(panel_size.height())

    def _make_panel_scrollable(self, panel_width: int) -> None:
        """Let the panel scroll so the window also fits on small laptop screens."""
        scroll_area = QScrollArea()
        scroll_area.setFrameShape(QFrame.NoFrame)
        scroll_area.setWidgetResizable(True)
        scroll_area.setHorizontalScrollBarPolicy(Qt.ScrollBarAlwaysOff)
        scroll_bar_width = scroll_area.verticalScrollBar().sizeHint().width()
        scroll_area.setFixedWidth(panel_width + scroll_bar_width)
        self.horizontalLayout_main.replaceWidget(self.widget_panel, scroll_area)
        scroll_area.setWidget(self.widget_panel)

    def _fit_height_to_panel(self, panel_height: int) -> None:
        """Open tall enough to show the whole panel, if the screen allows it."""
        wanted = panel_height + WINDOW_CHROME_HEIGHT_PX
        available = QApplication.primaryScreen().availableGeometry().height()
        available -= WINDOW_TITLE_BAR_ALLOWANCE_PX
        self.resize(self.width(), max(self.height(), min(wanted, available)))

    def _setup_language_menu(self) -> None:
        """Check the language in use; a new choice applies on the next start."""
        self.language_actions = {"en": self.action_lang_en, "es": self.action_lang_es}
        group = QActionGroup(self)
        group.setExclusive(True)
        for action in self.language_actions.values():
            group.addAction(action)
        self._sync_language_menu()

    def _connect_signals(self) -> None:
        self.btn_refresh_ports.clicked.connect(self.refresh_ports)
        self.btn_connect.clicked.connect(self.connect_serial)
        self.btn_disconnect.clicked.connect(self.disconnect_serial)
        self.btn_calibrate.clicked.connect(self.open_calibrate)

        for radio_button in (
            self.rb_unit_n,
            self.rb_unit_kgf,
            self.rb_unit_gf,
            self.rb_plot_accumulated,
            self.rb_plot_sliding,
            self.rb_plot_paused,
            self.rb_measurement_bending,
            self.rb_measurement_compression,
        ):
            radio_button.toggled.connect(self._on_settings_changed)

        self.gb_zero_filter.toggled.connect(self._on_zero_filter_changed)
        self.sb_zero_threshold.valueChanged.connect(self._on_zero_filter_changed)

        for code, action in self.language_actions.items():
            action.triggered.connect(lambda _checked, code=code: self.change_language(code))

        self.btn_clear.clicked.connect(self.clear_plot)
        self.btn_tare.clicked.connect(self.do_tare)
        self.btn_x_select.clicked.connect(self.on_x_selection_button)
        self.btn_x_cancel.clicked.connect(self.cancel_x_selection)
        self.btn_toggle_reading.clicked.connect(self.toggle_reading)
        self.btn_rec_start.clicked.connect(self.start_recording)
        self.btn_rec_stop.clicked.connect(self.stop_recording)

    def _setup_timers(self) -> None:
        self.plot_timer = QTimer(self)
        self.plot_timer.setInterval(PLOT_REFRESH_INTERVAL_MS)
        self.plot_timer.timeout.connect(self.refresh_plot)
        self.plot_timer.start()

        self.port_timer = QTimer(self)
        self.port_timer.setInterval(PORT_SCAN_INTERVAL_MS)
        self.port_timer.timeout.connect(self.refresh_ports)
        self.port_timer.start()

    # ---- small helpers ---------------------------------------------------

    def _show_message(self, message: str, timeout_ms: int = 5000) -> None:
        self.statusBar().showMessage(message, timeout_ms)

    def _to_display_unit(self, force_n: float) -> float:
        return newtons_to_unit(force_n, self.unit)

    def _format_force(self, force_n: float) -> str:
        return f"{self._to_display_unit(force_n):.2f} {self.unit.value}"

    def _update_force_axis_label(self) -> None:
        self.plot.setLabel("left", self.tr("Force ({0})").format(self.unit.value))

    def _sample_times(self) -> list[float]:
        return [sample.t_rel_s for sample in self.measurements]

    def _set_x_range_rows_visible(self, visible: bool) -> None:
        for widget in (self.label_xrange, self.lbl_xrange, self.label_xdelta, self.lbl_xdelta):
            widget.setVisible(visible)

    def _set_reading_active(self, active: bool) -> None:
        self.is_reading_active = active
        self.btn_toggle_reading.setText(
            self.tr("Pause reading") if active else self.tr("Resume reading")
        )

    def _set_status(self, text: str, port_error: bool = False) -> None:
        self.lbl_status.setText(text)
        self.showing_port_error = port_error

    def _show_connected_state(self) -> None:
        if self.connected_port:
            self._set_status(self.tr("Connected to {0}").format(self.connected_port))
        else:
            self._set_status(self.tr("Connected"))
        self.btn_connect.setEnabled(False)
        self.btn_refresh_ports.setEnabled(False)
        self.btn_disconnect.setEnabled(True)
        self.btn_calibrate.setEnabled(True)
        self.btn_toggle_reading.setEnabled(True)

    def _show_disconnected_state(self) -> None:
        self.btn_connect.setEnabled(True)
        self.btn_refresh_ports.setEnabled(True)
        self.btn_disconnect.setEnabled(False)
        self.btn_calibrate.setEnabled(False)
        self.btn_toggle_reading.setEnabled(False)
        self._set_reading_active(True)

    # ---- serial ports and connection ---------------------------------------

    def refresh_ports(self) -> None:
        """Re-scan the serial ports, keeping the current selection if possible."""
        selected = self.cb_ports.currentText()
        scan = scan_serial_ports()

        if scan.error_message and scan.error_message != self.port_scan_error:
            self._show_message(scan.error_message, LONG_MESSAGE_MS)
        self.available_ports = scan.ports
        self.port_scan_error = scan.error_message

        self.cb_ports.blockSignals(True)
        self.cb_ports.clear()
        if scan.ports:
            self.cb_ports.addItems(scan.ports)
        elif scan.error_message:
            self.cb_ports.addItem(self.tr("(error listing ports)"))
        else:
            self.cb_ports.addItem(self.tr("(no ports)"))
        if selected in scan.ports:
            self.cb_ports.setCurrentText(selected)
        self.cb_ports.blockSignals(False)

        if not self.serial.is_connected():
            self.btn_connect.setEnabled(bool(scan.ports))
            if scan.error_message:
                self._set_status(self.tr("Port error"), port_error=True)
            elif self.showing_port_error:
                self._set_status(self.tr("Disconnected"))

    def connect_serial(self) -> None:
        port = self.cb_ports.currentText().strip()
        if port not in self.available_ports:
            QMessageBox.warning(
                self,
                self.tr("Serial ports"),
                self.port_scan_error or self.tr("No serial ports are available."),
            )
            return

        if self.serial.is_connected():
            self.connected_port = self.connected_port or port
            self._show_connected_state()
            self.on_warning(self.tr("A connection is already active."))
            return

        self.pending_port = port
        self.connected_port = None
        self.btn_connect.setEnabled(False)
        self.btn_refresh_ports.setEnabled(False)
        self.btn_disconnect.setEnabled(True)
        self._set_status(self.tr("Connecting..."))
        self.statusBar().clearMessage()
        self.serial.connect(port, int(self.cb_baud.currentText()))

    def disconnect_serial(self) -> None:
        # The status label changes when the worker confirms (on_disconnected).
        self.serial.disconnect()
        self._show_disconnected_state()

    def on_connected(self, port: str) -> None:
        self.connected_port = port
        self._show_connected_state()

    def on_disconnected(self) -> None:
        self.pending_port = None
        self.connected_port = None
        self._set_status(self.tr("Disconnected"))
        self._show_disconnected_state()

    def on_error(self, message: str) -> None:
        self.pending_port = None
        self.connected_port = None
        self._set_status(self.tr("Error"))
        self._show_disconnected_state()
        self._show_message(message)
        QMessageBox.critical(self, self.tr("Serial error"), message)

    def on_warning(self, message: str) -> None:
        if self.serial.is_connected() and self.connected_port:
            self._show_connected_state()
        self._show_message(message, LONG_MESSAGE_MS)

    def on_scale_updated(self, factor: float) -> None:
        self._show_message(self.tr("Firmware scale factor updated to {0}").format(f"{factor:.5f}"))

    # ---- measurements ----------------------------------------------------

    def on_measurement(self, t_s: float, weight_kg: float, _sequence: int) -> None:
        if not self.is_reading_active:
            return

        force_n = weight_kg * STANDARD_GRAVITY
        if self.load_cell_type == LoadCellType.COMPRESSION:
            force_n = -force_n

        sample = self.measurements.append(ForceSample(t_raw_s=t_s, force_raw_n=force_n))
        self.lbl_time.setText(f"{sample.t_rel_s:.2f} s")
        self.lbl_force.setText(self._format_force(sample.force_corr_n))
        self.lbl_fmax.setText(self._format_force(self.measurements.force_max_n))

        if self.recorder.is_recording:
            try:
                self.recorder.write(sample.t_rel_s, self._to_display_unit(sample.force_corr_n))
            except Exception as exc:
                self.stop_recording()
                QMessageBox.critical(
                    self,
                    self.tr("Recording"),
                    self.tr("Error writing the recording file:\n{0}").format(exc),
                )
                return

        if self.x_selection.active:
            self.x_selection.ensure_initialized(self._sample_times())

    def refresh_plot(self) -> None:
        if self.plot_mode == PlotMode.PAUSED:
            return

        points = [
            (sample.t_rel_s, sample.force_corr_n)
            for sample in self.measurements
            if math.isfinite(sample.t_rel_s) and math.isfinite(sample.force_corr_n)
        ]
        if len(points) < 2:
            self.curve.setData([], [])
            return

        if self.plot_mode == PlotMode.SLIDING:
            window_start = points[-1][0] - SLIDING_WINDOW_S
            points = [point for point in points if point[0] >= window_start]

        self.curve.setData(
            [t_value for t_value, _ in points],
            [self._to_display_unit(force_n) for _, force_n in points],
        )

    def _reset_session_view(self) -> None:
        self.measurements.clear()
        if self.x_selection.active:
            self.x_selection.reset_region()
        for label in (self.lbl_time, self.lbl_force, self.lbl_fmax, self.lbl_xrange, self.lbl_xdelta):
            label.setText(EMPTY_TEXT)
        self.refresh_plot()

    def clear_plot(self) -> None:
        if self.recorder.is_recording:
            QMessageBox.warning(
                self, self.tr("Recording active"), self.tr("Cannot clear while recording.")
            )
            return
        self._reset_session_view()

    def do_tare(self) -> None:
        if not self.measurements.apply_tare_from_latest():
            QMessageBox.information(self, self.tr("Tare"), self.tr("No measurements have arrived yet."))
            return
        self._show_message(self.tr("Software tare applied"))
        QMessageBox.information(self, self.tr("Tare"), self.tr("Software tare applied."))

    def toggle_reading(self) -> None:
        self._set_reading_active(not self.is_reading_active)
        self._show_message(
            self.tr("Reading resumed") if self.is_reading_active else self.tr("Reading paused")
        )

    # ---- settings panel --------------------------------------------------

    def _on_settings_changed(self) -> None:
        if self.recorder.is_recording:
            # Unit and sign must stay fixed within one recording file.
            self._sync_settings_controls()
            return

        if self.rb_unit_n.isChecked():
            self.unit = Unit.N
        elif self.rb_unit_kgf.isChecked():
            self.unit = Unit.KGF
        elif self.rb_unit_gf.isChecked():
            self.unit = Unit.GF

        if self.rb_plot_accumulated.isChecked():
            self.plot_mode = PlotMode.ACCUMULATED
        elif self.rb_plot_sliding.isChecked():
            self.plot_mode = PlotMode.SLIDING
        elif self.rb_plot_paused.isChecked():
            self.plot_mode = PlotMode.PAUSED

        if self.rb_measurement_bending.isChecked():
            self.load_cell_type = LoadCellType.BENDING
        elif self.rb_measurement_compression.isChecked():
            self.load_cell_type = LoadCellType.COMPRESSION

        self._update_force_axis_label()
        self._sync_zero_filter_controls()
        latest = self.measurements.latest
        if latest is not None:
            self.lbl_force.setText(self._format_force(latest.force_corr_n))
        self.lbl_fmax.setText(self._format_force(self.measurements.force_max_n))
        self.refresh_plot()

    def _sync_settings_controls(self) -> None:
        """Make the radio buttons reflect the current settings."""
        self.rb_unit_n.setChecked(self.unit == Unit.N)
        self.rb_unit_kgf.setChecked(self.unit == Unit.KGF)
        self.rb_unit_gf.setChecked(self.unit == Unit.GF)
        self.rb_plot_accumulated.setChecked(self.plot_mode == PlotMode.ACCUMULATED)
        self.rb_plot_sliding.setChecked(self.plot_mode == PlotMode.SLIDING)
        self.rb_plot_paused.setChecked(self.plot_mode == PlotMode.PAUSED)
        self.rb_measurement_bending.setChecked(self.load_cell_type == LoadCellType.BENDING)
        self.rb_measurement_compression.setChecked(
            self.load_cell_type == LoadCellType.COMPRESSION
        )

    # ---- zero filter -----------------------------------------------------

    def _sync_zero_filter_controls(self) -> None:
        """Show the zero filter settings in the current display unit."""
        zero_filter = self.measurements.zero_filter
        for widget in (self.gb_zero_filter, self.sb_zero_threshold):
            widget.blockSignals(True)
        self.gb_zero_filter.setChecked(zero_filter.enabled)
        self.sb_zero_threshold.setDecimals(ZERO_THRESHOLD_DECIMALS[self.unit])
        self.sb_zero_threshold.setSingleStep(10 ** -(ZERO_THRESHOLD_DECIMALS[self.unit] - 1))
        self.sb_zero_threshold.setSuffix(f" {self.unit.value}")
        self.sb_zero_threshold.setValue(self._to_display_unit(zero_filter.threshold_n))
        for widget in (self.gb_zero_filter, self.sb_zero_threshold):
            widget.blockSignals(False)

    def _on_zero_filter_changed(self) -> None:
        zero_filter = self.measurements.zero_filter
        zero_filter.enabled = self.gb_zero_filter.isChecked()
        zero_filter.threshold_n = unit_to_newtons(self.sb_zero_threshold.value(), self.unit)
        zero_filter.reset()

    # ---- language --------------------------------------------------------

    def _sync_language_menu(self) -> None:
        """Check the saved choice (it may not be loaded yet, see change_language)."""
        selected = i18n.saved_language() or i18n.active_language()
        for code, action in self.language_actions.items():
            action.setChecked(code == selected)

    def change_language(self, code: str) -> None:
        i18n.save_language(code)
        self._sync_language_menu()
        if code == i18n.active_language():
            return
        QMessageBox.information(
            self,
            # Shown in both languages: the new one is not loaded until restart.
            "Language / Idioma",
            "The new language will be used the next time RocktStand starts.\n"
            "El nuevo idioma se usará la próxima vez que se inicie RocktStand.",
        )

    # ---- calibration -----------------------------------------------------

    def _latest_reading_in_display_unit(self) -> Optional[float]:
        # Unfiltered: with a wrong scale factor the reference weight may read
        # inside the zero band, and the wizard needs its real value.
        reading_n = self.measurements.latest_unfiltered_n
        return None if reading_n is None else self._to_display_unit(reading_n)

    def open_calibrate(self) -> None:
        dialog = CalibrateDialog(
            unit=self.unit,
            scale_current=self.serial.current_scale_factor,
            reading_provider=self._latest_reading_in_display_unit,
            parent=self,
        )
        if dialog.exec_() == QDialog.Accepted and dialog.scale_new is not None:
            self.serial.set_scale(dialog.scale_new)
            self._show_message(
                self.tr("Sending new scale factor to the firmware: {0}").format(
                    f"{dialog.scale_new:.5f}"
                )
            )

    # ---- X range selection and export --------------------------------------

    def on_x_selection_button(self) -> None:
        """The same button starts the selection and then exports it."""
        if self.x_selection.active:
            self.export_selected_range()
            return
        self._set_x_range_rows_visible(True)
        self.x_selection.activate(self._sample_times())

    def cancel_x_selection(self) -> None:
        self.x_selection.deactivate()
        self._set_x_range_rows_visible(False)

    def export_selected_range(self) -> None:
        title = self.tr("Export range")
        if self.measurements.latest is None:
            QMessageBox.information(self, title, self.tr("There is no data to export."))
            return

        x_min, x_max = self.x_selection.selected_range()
        rows = [
            (sample.t_rel_s, self._to_display_unit(sample.force_corr_n))
            for sample in self.measurements
            if x_min <= sample.t_rel_s <= x_max
        ]
        if not rows:
            QMessageBox.information(
                self, title, self.tr("There are no points inside the selected range.")
            )
            return

        timestamp = datetime.now()
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save selected range"),
            timestamp.strftime(RANGE_EXPORT_FILENAME_FORMAT),
            TXT_FILE_FILTER,
        )
        if not path:
            return

        try:
            export_measurements(ensure_txt_extension(path), timestamp, self.unit.value, rows)
        except Exception as exc:
            QMessageBox.critical(self, title, self.tr("Could not save the file:\n{0}").format(exc))
            return
        QMessageBox.information(self, title, self.tr("Exported {0} points.").format(len(rows)))
        self.cancel_x_selection()

    # ---- recording -------------------------------------------------------

    def start_recording(self) -> None:
        """Start a new session (time restarts at zero) and record it to a file."""
        if self.recorder.is_recording:
            return

        timestamp = datetime.now()
        path, _ = QFileDialog.getSaveFileName(
            self,
            self.tr("Save measurement"),
            timestamp.strftime(RECORDING_FILENAME_FORMAT),
            TXT_FILE_FILTER,
        )
        if not path:
            return

        try:
            self.recorder.start(ensure_txt_extension(path), timestamp, self.unit.value)
        except Exception as exc:
            QMessageBox.critical(
                self, self.tr("Recording"), self.tr("Could not open the file:\n{0}").format(exc)
            )
            return

        self._reset_session_view()
        self.lbl_time.setText("0.00 s")
        self.lbl_fmax.setText(self._format_force(0.0))
        self.btn_rec_start.setEnabled(False)
        self.btn_rec_stop.setEnabled(True)
        self.serial.set_recording_indicator(True)

    def stop_recording(self) -> None:
        if not self.recorder.is_recording:
            return
        self.btn_rec_start.setEnabled(True)
        self.btn_rec_stop.setEnabled(False)
        self.serial.set_recording_indicator(False)
        try:
            self.recorder.stop()
        except OSError as exc:
            QMessageBox.critical(
                self,
                self.tr("Recording"),
                self.tr("Error closing the recording file:\n{0}").format(exc),
            )

    # ---- window ----------------------------------------------------------

    def closeEvent(self, event) -> None:
        self.stop_recording()
        self.serial.disconnect(wait=True)
        super().closeEvent(event)
