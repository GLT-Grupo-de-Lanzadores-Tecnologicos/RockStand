from services.serial_port_service import scan_serial_ports


class _DummyPort:
    def __init__(self, device):
        self.device = device


def test_scan_serial_ports_returns_sorted_unique_devices():
    result = scan_serial_ports(
        comports_factory=lambda: [
            _DummyPort("COM10"),
            _DummyPort("COM3"),
            _DummyPort("COM1"),
            _DummyPort("COM3"),
            _DummyPort(""),
        ]
    )

    assert result.error_message is None
    assert result.ports == ["COM1", "COM3", "COM10"]


def test_scan_serial_ports_reports_missing_pyserial():
    def missing_serial():
        exc = ModuleNotFoundError("No module named 'serial'")
        exc.name = "serial"
        raise exc

    result = scan_serial_ports(comports_factory=missing_serial)

    assert result.ports == []
    assert result.error_message == "Cannot list ports: pyserial is not installed in this environment."
