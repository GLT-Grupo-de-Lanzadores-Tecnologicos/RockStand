"""The Spanish translation loads and covers every string of the interface."""

import xml.etree.ElementTree as ET
from pathlib import Path

import pytest

import i18n
from domain_models import Unit
from ui.calibrate_dialog import CalibrateDialog
from ui.main_window import MainWindow

TS_FILE = Path(__file__).resolve().parent.parent / "src" / "translations" / "rocktstand_es.ts"


@pytest.fixture
def spanish(app):
    assert i18n.install_translators(app, "es")
    yield
    i18n.install_translators(app, "en")


def test_spanish_ts_file_has_no_unfinished_entries():
    messages = list(ET.parse(TS_FILE).getroot().iter("message"))
    assert messages
    for message in messages:
        translation = message.find("translation")
        assert translation.get("type") is None, message.find("source").text
        assert translation.text, message.find("source").text


def test_window_in_spanish(spanish):
    assert i18n.active_language() == "es"
    window = MainWindow()
    window.port_timer.stop()
    try:
        assert window.rb_measurement_bending.text() == "Flexión"
        assert window.gb_zero_filter.title() == "Filtro de cero"
        assert window.btn_x_select.text() == "Seleccionar rango X"
        assert window.menu_language.title() == "Idioma"

        window.on_connected("COM7")
        assert window.lbl_status.text() == "Conectado a COM7"
        window.on_disconnected()
        assert window.lbl_status.text() == "Desconectado"
        window.on_x_selection_button()
        assert window.btn_x_select.text() == "Exportar rango seleccionado"
    finally:
        window.close()


def test_calibration_dialog_in_spanish(spanish, monkeypatch):
    shown = []
    monkeypatch.setattr(
        "ui.calibrate_dialog.QMessageBox.warning",
        lambda _parent, title, text: shown.append((title, text)),
    )
    dialog = CalibrateDialog(unit=Unit.N, scale_current=1000.0, reading_provider=lambda: 1e-12)
    assert dialog.windowTitle() == "Asistente de calibración"
    assert dialog.step_labels[0].text() == "1. Ingresar el valor conocido"
    assert "333 gf" in dialog.in_known.placeholderText()
    assert " o " in dialog.in_known.placeholderText()

    dialog.in_known.setText("5")
    for _ in range(3):
        dialog._on_next()
    dialog._capture_reading()
    dialog._on_next()
    dialog._on_finish()
    assert shown[-1] == (
        "Calibración fuera de rango",
        "La lectura capturada es casi cero. Revise la unidad, la tara y la lectura capturada.",
    )


def test_english_has_no_translator(app):
    assert i18n.install_translators(app, "en")
    assert i18n.active_language() == "en"
    window = MainWindow()
    window.port_timer.stop()
    try:
        assert window.rb_measurement_bending.text() == "Bending"
    finally:
        window.close()
