from domain_models import CalibrationInput
from services.calibration_service import compute_scale


def test_calibration_uses_hx711_scale_relation():
    result = compute_scale(
        CalibrationInput(scale_current=1000.0, captured_reading=20.0, known_value=10.0)
    )

    assert result.error is None
    assert result.scale_new == 2000.0


def test_calibration_allows_large_single_step_correction_when_within_safety_ratio():
    result = compute_scale(
        CalibrationInput(scale_current=1000.0, captured_reading=5.0, known_value=100.0)
    )

    assert result.error is None
    assert result.scale_new == 50.0


def test_calibration_rejects_extreme_total_change_ratio():
    result = compute_scale(
        CalibrationInput(scale_current=1000.0, captured_reading=0.01, known_value=100.0)
    )

    assert result.scale_new is None
    assert result.error is not None


def test_calibration_rejects_zero_known_value_and_zero_reading():
    assert compute_scale(CalibrationInput(1000.0, 5.0, 0.0)).error is not None
    assert compute_scale(CalibrationInput(1000.0, 0.0, 5.0)).error is not None
