import pytest

from domain_models import ForceSample
from services.measurement_service import MeasurementService
from services.zero_filter import RELEASE_FACTOR, ZeroFilter


def test_noise_around_zero_becomes_a_flat_line():
    zero_filter = ZeroFilter(threshold_n=0.05)
    noise = [0.01, -0.03, 0.049, -0.02, 0.0]
    assert [zero_filter.apply(value) for value in noise] == [0.0] * len(noise)


def test_real_loads_pass_through_unchanged():
    zero_filter = ZeroFilter(threshold_n=0.05)
    assert zero_filter.apply(12.345) == 12.345
    assert zero_filter.apply(-3.0) == -3.0


def test_hysteresis_stops_flicker_at_the_threshold():
    zero_filter = ZeroFilter(threshold_n=0.05)
    assert zero_filter.apply(0.04) == 0.0
    # Just above the threshold, but still inside the release band: stays at zero.
    assert zero_filter.apply(0.06) == 0.0
    assert zero_filter.apply(-0.07) == 0.0
    released = 0.05 * RELEASE_FACTOR + 0.01
    assert zero_filter.apply(released) == pytest.approx(released)
    # Once released, values above the threshold are shown again.
    assert zero_filter.apply(0.06) == pytest.approx(0.06)


def test_disabled_filter_keeps_the_noise():
    zero_filter = ZeroFilter(threshold_n=0.05, enabled=False)
    assert zero_filter.apply(0.01) == 0.01


def test_negative_threshold_is_treated_as_zero():
    zero_filter = ZeroFilter(threshold_n=-1.0)
    assert zero_filter.threshold_n == 0.0
    assert zero_filter.apply(0.001) == 0.001


def test_service_applies_the_filter_after_the_tare():
    service = MeasurementService(zero_filter=ZeroFilter(threshold_n=0.05))
    service.append(ForceSample(0.0, 10.0))
    assert service.apply_tare_from_latest()
    assert service.append(ForceSample(0.1, 10.03)).force_corr_n == 0.0
    assert service.append(ForceSample(0.2, 12.0)).force_corr_n == pytest.approx(2.0)


def test_tare_inside_the_zero_band_removes_the_residual_offset():
    service = MeasurementService(zero_filter=ZeroFilter(threshold_n=0.05))
    # A small offset that the filter hides from the display...
    assert service.append(ForceSample(0.0, 0.03)).force_corr_n == 0.0
    assert service.apply_tare_from_latest()
    # ...is still removed by the tare, so a real load reads exactly.
    assert service.append(ForceSample(0.1, 1.03)).force_corr_n == pytest.approx(1.0)
