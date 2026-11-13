from domain_models import ForceSample
from services.measurement_service import MeasurementService


def _service_with(*samples):
    service = MeasurementService()
    for t_s, force_n in samples:
        service.append(ForceSample(t_raw_s=t_s, force_raw_n=force_n))
    return service


def test_time_is_relative_to_first_sample():
    service = _service_with((5.0, 1.0), (5.5, 2.0))
    assert [sample.t_rel_s for sample in service] == [0.0, 0.5]


def test_tare_zeroes_the_latest_reading_and_accumulates():
    service = _service_with((0.0, 3.0))
    assert service.apply_tare_from_latest()
    assert service.append(ForceSample(1.0, 3.0)).force_corr_n == 0.0
    assert service.append(ForceSample(2.0, 4.0)).force_corr_n == 1.0
    assert service.apply_tare_from_latest()
    assert service.append(ForceSample(3.0, 4.0)).force_corr_n == 0.0


def test_tare_without_data_is_rejected():
    assert not MeasurementService().apply_tare_from_latest()


def test_clear_restarts_time_and_peak_but_keeps_tare():
    service = _service_with((10.0, 2.0), (11.0, 7.0))
    service.apply_tare_from_latest()
    assert service.force_max_n == 7.0

    service.clear()
    assert service.latest is None
    assert service.force_max_n == 0.0

    sample = service.append(ForceSample(20.0, 9.0))
    assert (sample.t_rel_s, sample.force_corr_n) == (0.0, 2.0)


def test_buffer_keeps_only_the_newest_points():
    service = MeasurementService(max_points=2)
    for index in range(4):
        service.append(ForceSample(float(index), 0.0))
    assert [sample.t_rel_s for sample in service] == [2.0, 3.0]
