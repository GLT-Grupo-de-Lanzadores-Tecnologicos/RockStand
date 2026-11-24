"""Smoke tests: build the real windows offscreen and drive the main flows."""

import pytest
from PyQt5.QtWidgets import QFileDialog, QMessageBox

from domain_models import STANDARD_GRAVITY, Unit
from ui.calibrate_dialog import CalibrateDialog
from ui.main_window import MainWindow
from ui.plot_axis import PlainNumberAxis


@pytest.fixture(autouse=True)
def no_blocking_dialogs(monkeypatch):
    """Message boxes would block the test waiting for a click."""
    for name in ("information", "warning", "critical"):
        monkeypatch.setattr(QMessageBox, name, staticmethod(lambda *args, **kwargs: None))


@pytest.fixture
def window(app):
    window = MainWindow()
    window.port_timer.stop()
    yield window
    window.close()


def _save_dialog_returns(monkeypatch, path):
    monkeypatch.setattr(
        QFileDialog, "getSaveFileName", staticmethod(lambda *args, **kwargs: (str(path), ""))
    )


def test_window_shows_logo_and_english_title(window):
    assert window.windowTitle() == "RocktStand v0.3.1 - Rocket Stand Test Software"
    logo = window.verticalLayout_panel.itemAt(0).widget()
    assert not logo.pixmap().isNull()
    assert not logo.pixmap().hasAlphaChannel()


def test_measurements_update_labels_units_and_tare(window):
    window.on_measurement(0.0, 1.0, 1)
    window.on_measurement(0.1, 2.0, 2)
    assert window.lbl_force.text() == f"{2 * STANDARD_GRAVITY:.2f} N"
    assert window.lbl_time.text() == "0.10 s"

    window.rb_unit_kgf.setChecked(True)
    assert window.unit == Unit.KGF
    assert window.lbl_force.text() == "2.00 kgf"
    assert window.lbl_fmax.text() == "2.00 kgf"

    window.do_tare()
    window.on_measurement(0.2, 2.5, 3)
    assert window.lbl_force.text() == "0.50 kgf"

    window.refresh_plot()
    x_data, y_data = window.curve.getData()
    assert len(x_data) == len(y_data) == 3


def test_compression_inverts_the_sign(window):
    window.rb_measurement_compression.setChecked(True)
    window.on_measurement(0.0, 1.0, 1)
    assert window.lbl_force.text() == f"{-STANDARD_GRAVITY:.2f} N"


def test_paused_reading_ignores_measurements(window):
    window.toggle_reading()
    window.on_measurement(0.0, 1.0, 1)
    assert window.measurements.latest is None
    assert window.btn_toggle_reading.text() == "Resume reading"


def test_connection_state_follows_serial_signals(window):
    window.on_connected("COM7")
    assert window.lbl_status.text() == "Connected to COM7"
    assert window.btn_calibrate.isEnabled()

    window.on_disconnected()
    assert window.lbl_status.text() == "Disconnected"
    assert not window.btn_calibrate.isEnabled()


def test_recording_keeps_unit_and_writes_file(window, tmp_path, monkeypatch):
    record_path = tmp_path / "rec.txt"
    _save_dialog_returns(monkeypatch, record_path)

    window.start_recording()
    window.on_measurement(0.0, 1.0, 1)
    window.on_measurement(1.0, 1.0, 2)
    window.rb_unit_gf.setChecked(True)  # must be ignored while recording
    assert window.unit == Unit.N
    assert window.rb_unit_n.isChecked()
    window.stop_recording()

    lines = record_path.read_text(encoding="utf-8").splitlines()
    assert lines[2] == "# tiempo_s\tfuerza_N"
    assert len(lines) == 5


def test_range_export_writes_only_selected_points(window, tmp_path, monkeypatch):
    _save_dialog_returns(monkeypatch, tmp_path / "range")
    window.on_measurement(0.0, 1.0, 1)
    window.on_measurement(1.0, 1.0, 2)
    window.on_measurement(2.0, 1.0, 3)

    window.on_x_selection_button()
    assert window.x_selection.active
    window.x_selection.region.setRegion((0.5, 1.5))
    assert window.lbl_xrange.text() == "0.5 .. 1.5 s"

    window.on_x_selection_button()
    assert not window.x_selection.active
    exported = (tmp_path / "range.txt").read_text(encoding="utf-8").splitlines()
    assert exported[3:] == [f"1.000000\t{STANDARD_GRAVITY:.6f}"]


def test_calibration_dialog_computes_new_scale(app):
    dialog = CalibrateDialog(unit=Unit.KGF, scale_current=1000.0, reading_provider=lambda: 2.0)
    dialog.in_known.setText("1000 gf")  # 1 kgf, typed in another unit
    for _ in range(4):
        dialog._on_next()
    assert dialog._current_step == 3  # blocked: no reading captured yet

    dialog._capture_reading()
    dialog._on_next()
    assert dialog.btn_finish.isEnabled()
    dialog._on_finish()
    assert dialog.scale_new == pytest.approx(2000.0)


def test_calibration_dialog_requires_a_known_value_to_advance(app):
    dialog = CalibrateDialog(unit=Unit.N, scale_current=1000.0, reading_provider=lambda: None)
    dialog._on_next()
    assert dialog._current_step == 0


def test_axis_labels_are_plain_numbers(app):
    axis = PlainNumberAxis(orientation="left")
    assert axis.tickStrings([0, 100, 200], 1.0, 100) == ["0", "100", "200"]
    assert axis.tickStrings([0.0, 0.25, 0.5], 1.0, 0.25) == ["0", "0.25", "0.5"]


def test_calibration_reading_ignores_the_zero_filter(window):
    window.on_measurement(0.0, 0.003, 1)  # inside the zero band
    assert window.lbl_force.text() == "0.00 N"
    assert window._latest_reading_in_display_unit() == pytest.approx(0.003 * STANDARD_GRAVITY)


def test_zero_filter_flattens_noise_and_follows_the_unit(window):
    window.on_measurement(0.0, 0.001, 1)  # 0.0098 N of noise
    window.on_measurement(0.1, -0.002, 2)
    assert window.lbl_force.text() == "0.00 N"
    window.refresh_plot()
    _x_data, y_data = window.curve.getData()
    assert list(y_data) == [0.0, 0.0]

    threshold_n = window.measurements.zero_filter.threshold_n
    window.rb_unit_gf.setChecked(True)
    assert window.sb_zero_threshold.suffix() == " gf"
    assert window.sb_zero_threshold.value() == pytest.approx(
        threshold_n / STANDARD_GRAVITY * 1000, abs=0.1
    )

    window.gb_zero_filter.setChecked(False)
    assert not window.measurements.zero_filter.enabled
    window.on_measurement(0.2, 0.001, 3)
    assert window.lbl_force.text() == "1.00 gf"
