"""Step-by-step calibration wizard for the load cell scale factor."""

from __future__ import annotations

from typing import Callable, Optional

from PyQt5.QtCore import QT_TRANSLATE_NOOP, QCoreApplication
from PyQt5.QtWidgets import (
    QDialog,
    QDialogButtonBox,
    QFormLayout,
    QGroupBox,
    QLabel,
    QLineEdit,
    QMessageBox,
    QPushButton,
    QVBoxLayout,
)

from domain_models import CalibrationInput, Unit
from services.calibration_service import compute_scale
from services.unit_conversion import newtons_to_unit, parse_force_text, unit_to_newtons

# (step title, hint shown while the step is the current one). Translated when
# shown, with the CalibrateDialog context.
STEPS = [
    (
        QT_TRANSLATE_NOOP("CalibrateDialog", "1. Enter the known value"),
        QT_TRANSLATE_NOOP(
            "CalibrateDialog",
            "Enter the value of the reference weight you will use to calibrate."
        ),
    ),
    (
        QT_TRANSLATE_NOOP("CalibrateDialog", "2. Tare with no load"),
        QT_TRANSLATE_NOOP(
            "CalibrateDialog",
            "Leave the load cell unloaded and press Tare in the main window."
        ),
    ),
    (
        QT_TRANSLATE_NOOP("CalibrateDialog", "3. Place the reference weight"),
        QT_TRANSLATE_NOOP(
            "CalibrateDialog",
            "Place the reference weight and wait for the reading to settle."
        ),
    ),
    (
        QT_TRANSLATE_NOOP("CalibrateDialog", "4. Capture the current reading"),
        QT_TRANSLATE_NOOP(
            "CalibrateDialog",
            "Press 'Capture current reading' to store the value under load."
        ),
    ),
    (
        QT_TRANSLATE_NOOP("CalibrateDialog", "5. Compute and send"),
        QT_TRANSLATE_NOOP(
            "CalibrateDialog",
            "Finish the wizard to compute the new scale factor and send it."
        ),
    ),
]
CAPTURE_STEP = 3
LAST_STEP = len(STEPS) - 1

STYLE_STEP_DONE = "color: #2e7d32;"
STYLE_STEP_CURRENT = "font-weight: 600; color: #111;"
STYLE_STEP_PENDING = "color: #666;"

KNOWN_VALUE_EXAMPLES = QT_TRANSLATE_NOOP("CalibrateDialog", "3.27, 3.27 N, 0.333 kgf or 333 gf")


class CalibrateDialog(QDialog):
    """Guides the user through a single-point calibration.

    ``reading_provider`` returns the latest reading in ``unit`` (or ``None``
    if no measurement has arrived yet). After the dialog is accepted,
    ``scale_new`` holds the factor to send to the firmware.
    """

    def __init__(
        self,
        unit: Unit,
        scale_current: float,
        reading_provider: Callable[[], Optional[float]],
        parent=None,
    ):
        super().__init__(parent)
        self.setWindowTitle(self.tr("Calibration wizard"))
        self.setModal(True)

        self.unit = unit
        self.scale_current = scale_current
        self.scale_new: Optional[float] = None
        self._reading_provider = reading_provider
        self._reading: Optional[float] = None
        self._current_step = 0

        self._build_ui()
        self._refresh_step_ui()

    def _build_ui(self) -> None:
        root = QVBoxLayout(self)

        self.lbl_reading = QLabel("-")
        self.in_known = QLineEdit()
        self.in_known.setPlaceholderText(self.tr("E.g. {0}").format(self.tr(KNOWN_VALUE_EXAMPLES)))
        self.in_known.textChanged.connect(self._refresh_step_ui)
        self.btn_capture = QPushButton(self.tr("Capture current reading"))
        self.btn_capture.clicked.connect(self._capture_reading)

        form = QFormLayout()
        form.addRow(self.tr("Current scale factor"), QLabel(f"{self.scale_current:.5f}"))
        form.addRow(self.tr("Captured reading ({0})").format(self.unit.value), self.lbl_reading)
        form.addRow(self.tr("Known value ({0})").format(self.unit.value), self.in_known)
        form.addRow("", self.btn_capture)
        root.addLayout(form)

        steps_box = QGroupBox(self.tr("Steps"))
        steps_layout = QVBoxLayout(steps_box)
        self.step_labels: list[QLabel] = []
        for title, _hint in STEPS:
            label = QLabel(self.tr(title))
            label.setWordWrap(True)
            self.step_labels.append(label)
            steps_layout.addWidget(label)
        root.addWidget(steps_box)

        self.lbl_step_hint = QLabel()
        self.lbl_step_hint.setWordWrap(True)
        root.addWidget(self.lbl_step_hint)

        self.btn_next = QPushButton(self.tr("Next"))
        self.btn_next.clicked.connect(self._on_next)
        root.addWidget(self.btn_next)

        buttons = QDialogButtonBox(QDialogButtonBox.Ok | QDialogButtonBox.Cancel)
        self.btn_finish = buttons.button(QDialogButtonBox.Ok)
        self.btn_finish.setText(self.tr("Compute and send"))
        buttons.accepted.connect(self._on_finish)
        buttons.rejected.connect(self.reject)
        root.addWidget(buttons)

    def _known_value(self) -> Optional[float]:
        """The typed known value converted to the dialog unit, or ``None``.

        A value typed without a unit suffix is taken to be in the dialog unit.
        """
        value, typed_unit = parse_force_text(self.in_known.text())
        if value is None:
            return None
        if typed_unit is None or typed_unit == self.unit:
            return value
        return newtons_to_unit(unit_to_newtons(value, typed_unit), self.unit)

    def _is_known_value_valid(self) -> bool:
        return bool(self._known_value())  # rejects both None and 0

    def _refresh_step_ui(self) -> None:
        for index, label in enumerate(self.step_labels):
            if index < self._current_step:
                label.setStyleSheet(STYLE_STEP_DONE)
            elif index == self._current_step:
                label.setStyleSheet(STYLE_STEP_CURRENT)
            else:
                label.setStyleSheet(STYLE_STEP_PENDING)
        self.lbl_step_hint.setText(self.tr(STEPS[self._current_step][1]))

        is_last = self._current_step >= LAST_STEP
        self.btn_capture.setEnabled(self._current_step >= CAPTURE_STEP)
        self.btn_next.setVisible(not is_last)
        self.btn_finish.setEnabled(
            is_last and self._reading is not None and self._is_known_value_valid()
        )

    def _capture_reading(self) -> None:
        reading = self._reading_provider()
        if reading is None:
            QMessageBox.warning(
                self, self.tr("No data"), self.tr("There is no reading to capture yet.")
            )
            return
        self._reading = reading
        self.lbl_reading.setText(f"{reading:.4f}")
        self._refresh_step_ui()

    def _on_next(self) -> None:
        if self._current_step == 0 and not self._is_known_value_valid():
            QMessageBox.warning(
                self,
                self.tr("Invalid value"),
                self.tr("Enter a valid, non-zero known value (e.g. {0}).").format(
                    self.tr(KNOWN_VALUE_EXAMPLES)
                ),
            )
            return

        if self._current_step == CAPTURE_STEP and self._reading is None:
            QMessageBox.warning(
                self,
                self.tr("Missing reading"),
                self.tr("Capture a reading with the reference weight in place first."),
            )
            return

        if self._current_step < LAST_STEP:
            self._current_step += 1
            self._refresh_step_ui()

    def _on_finish(self) -> None:
        known_value = self._known_value()
        if self._reading is None or not known_value:
            return  # the button is disabled in this state; kept as a guard

        result = compute_scale(
            CalibrationInput(
                scale_current=self.scale_current,
                captured_reading=self._reading,
                known_value=known_value,
            )
        )
        if result.error:
            QMessageBox.warning(
                self,
                self.tr("Calibration out of range"),
                self.tr("{0} Check the unit, the tare and the captured reading.").format(
                    QCoreApplication.translate("CalibrationService", result.error)
                ),
            )
            return

        self.scale_new = result.scale_new
        self.accept()
