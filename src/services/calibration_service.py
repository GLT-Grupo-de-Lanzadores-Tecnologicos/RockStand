"""Computation of a new HX711 scale factor from a known reference load."""

from __future__ import annotations

import math

from domain_models import (
    CALIBRATION_MIN_READING,
    MAX_ALLOWED_SCALE_RATIO,
    CalibrationInput,
    CalibrationResult,
)


def QT_TRANSLATE_NOOP(_context: str, text: str) -> str:
    """Mark a message for Qt Linguist (pylupdate5) without importing Qt here.

    The UI translates ``CalibrationResult.error`` with the same context.
    """
    return text



def compute_scale(data: CalibrationInput) -> CalibrationResult:
    """Return the scale factor that makes the reading match the known load.

    The HX711 library divides raw counts by the scale factor, so::

        scale_new = scale_current * (captured_reading / known_value)

    The result is rejected when an input is unusable or when the factor would
    change by more than ``MAX_ALLOWED_SCALE_RATIO``.
    """
    if data.known_value == 0:
        return CalibrationResult(error=QT_TRANSLATE_NOOP("CalibrationService", "The known value must be non-zero."))

    if abs(data.captured_reading) < CALIBRATION_MIN_READING:
        return CalibrationResult(error=QT_TRANSLATE_NOOP("CalibrationService", "The captured reading is almost zero."))

    if data.scale_current == 0:
        return CalibrationResult(error=QT_TRANSLATE_NOOP("CalibrationService", "The current scale factor cannot be zero."))

    scale_new = data.scale_current * (data.captured_reading / data.known_value)
    if not math.isfinite(scale_new):
        return CalibrationResult(error=QT_TRANSLATE_NOOP("CalibrationService", "The new scale factor is not a valid number."))

    change_ratio = abs(scale_new / data.scale_current)
    if not (1 / MAX_ALLOWED_SCALE_RATIO <= change_ratio <= MAX_ALLOWED_SCALE_RATIO):
        return CalibrationResult(
            error=QT_TRANSLATE_NOOP(
                "CalibrationService", "The new scale factor differs too much from the current one."
            )
        )

    return CalibrationResult(scale_new=scale_new)
