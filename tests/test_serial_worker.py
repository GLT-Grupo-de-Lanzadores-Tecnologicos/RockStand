"""Run the real worker thread against a fake serial port that mimics the firmware."""

import sys
import time
import types

import pytest

from services import serial_worker
from services.serial_worker import SerialThreadController


class FakeFirmwarePort:
    """Answers G / F: / R / S the way the Arduino sketch does."""

    instances = []

    def __init__(self, port, baud, timeout=None, write_timeout=None):
        if port == "BAD":
            raise OSError("port not found")
        self.replies = []
        self.received = []
        self.closed = False
        FakeFirmwarePort.instances.append(self)

    def reset_input_buffer(self):
        pass

    def reset_output_buffer(self):
        pass

    def write(self, data):
        command = data.decode("ascii").strip()
        self.received.append(command)
        if command == "G":
            self.replies.append(b"1.5000\r\n")
        elif command == "F:0.00000":
            self.replies.append(b"ERROR:factor_invalido\r\n")
        else:
            self.replies.append(b"OK\r\n")

    def readline(self):
        if self.replies:
            return self.replies.pop(0)
        time.sleep(0.001)
        return b""

    def close(self):
        self.closed = True


@pytest.fixture
def controller(app, monkeypatch):
    monkeypatch.setitem(sys.modules, "serial", types.SimpleNamespace(Serial=FakeFirmwarePort))
    monkeypatch.setattr(serial_worker, "BOARD_RESET_DELAY_S", 0.0)
    monkeypatch.setattr(serial_worker, "POLL_INTERVAL_S", 0.005)
    FakeFirmwarePort.instances.clear()

    controller = SerialThreadController()
    controller.events = []
    for name in ("connected", "disconnected", "warning", "error", "scale_updated"):
        getattr(controller, name).connect(
            lambda *args, name=name: controller.events.append((name, *args))
        )
    controller.measurement_received.connect(
        lambda t_s, weight_kg, seq: controller.events.append(("measurement", weight_kg, seq))
    )

    def wait_for(predicate, timeout_s=3.0):
        deadline = time.monotonic() + timeout_s
        while time.monotonic() < deadline:
            app.processEvents()
            if predicate():
                return True
            time.sleep(0.005)
        return False

    controller.wait_for = wait_for
    controller.has = lambda name: any(event[0] == name for event in controller.events)
    yield controller
    controller.disconnect(wait=True)
    app.processEvents()


def test_worker_polls_sets_scale_and_disconnects(controller):
    controller.connect("COM_FAKE", 115200)
    assert controller.wait_for(lambda: controller.has("measurement"))
    assert ("connected", "COM_FAKE") in controller.events
    assert ("measurement", 1.5, 1) in controller.events

    controller.set_scale(1234.5)
    assert controller.wait_for(lambda: controller.has("scale_updated"))
    assert controller.current_scale_factor == 1234.5

    controller.set_scale(0.0)
    assert controller.wait_for(lambda: controller.has("warning"))
    assert controller.current_scale_factor == 1234.5

    controller.set_recording_indicator(True)
    port = FakeFirmwarePort.instances[0]
    assert controller.wait_for(lambda: "R" in port.received)
    assert "F:1234.50000" in port.received

    controller.disconnect()
    assert controller.wait_for(lambda: not controller.is_connected())
    assert controller.has("disconnected")
    assert port.closed
    assert not controller.has("error")


def test_worker_reports_port_that_cannot_be_opened(controller):
    controller.connect("BAD", 115200)
    assert controller.wait_for(lambda: not controller.is_connected())
    assert controller.has("error")
    assert not controller.has("connected")
