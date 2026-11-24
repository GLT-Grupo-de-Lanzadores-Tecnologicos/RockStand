"""Serial acquisition: a polling worker thread and its Qt-facing controller.

Protocol summary (see ``docs/serial_protocol.md``): the PC sends ``G`` to
request one measurement, ``F:<factor>`` to set the HX711 scale factor and
``R`` / ``S`` to switch the "recording" LED on and off.
"""

from __future__ import annotations

import time
from collections import deque
from typing import Optional

from PyQt5.QtCore import QObject, Qt, QThread, pyqtSignal

from services.simple_protocol import ErrorLine, MeasurementLine, OkLine, parse_line

# Must match the factor compiled into the firmware (``factorEscala``).
DEFAULT_SCALE_FACTOR = 43943.025

POLL_INTERVAL_S = 0.1
READ_TIMEOUT_S = 0.05
WRITE_TIMEOUT_S = 0.2
# Opening the port resets most Arduino boards; wait for the bootloader.
BOARD_RESET_DELAY_S = 1.0
DISCONNECT_WAIT_MS = 2000


class SerialWorker(QObject):
    """Polls the firmware for measurements. Lives in its own ``QThread``."""

    # (seconds since the connection was opened, weight in kgf, sequence number)
    measurement_received = pyqtSignal(float, float, int)
    scale_updated = pyqtSignal(float)
    connected = pyqtSignal(str)
    disconnected = pyqtSignal()
    warning = pyqtSignal(str)
    error = pyqtSignal(str)
    finished = pyqtSignal()

    def __init__(
        self,
        port: str,
        baud: int = 115200,
        initial_scale_factor: float = DEFAULT_SCALE_FACTOR,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self.port = port
        self.baud = baud
        self.current_scale_factor = initial_scale_factor
        self._running = False
        self._serial = None
        # Commands queued from the GUI thread: (payload, scale factor or None).
        self._pending_writes: deque[tuple[str, Optional[float]]] = deque()
        # Scale factor sent to the firmware and not yet acknowledged.
        self._unconfirmed_scale: Optional[float] = None

    # ---- called from the GUI thread -------------------------------------

    def request_set_scale(self, factor: float) -> None:
        self._pending_writes.append((f"F:{factor:.5f}\n", factor))

    def request_recording_state(self, recording_active: bool) -> None:
        self._pending_writes.append(("R\n" if recording_active else "S\n", None))

    def stop(self) -> None:
        self._running = False

    # ---- runs in the worker thread --------------------------------------

    def run(self) -> None:
        """Open the port and poll until ``stop()`` is called or an error occurs."""
        self._running = True
        if not self._open_port():
            self._running = False
            self.finished.emit()
            return

        try:
            self._poll_loop()
        except Exception as exc:
            self.error.emit(self.tr("Serial read error: {0}").format(exc))

        self._close_port()
        self.disconnected.emit()
        self.finished.emit()

    def _open_port(self) -> bool:
        try:
            import serial

            self._serial = serial.Serial(
                self.port, self.baud, timeout=READ_TIMEOUT_S, write_timeout=WRITE_TIMEOUT_S
            )
            time.sleep(BOARD_RESET_DELAY_S)
            self._serial.reset_input_buffer()
            self._serial.reset_output_buffer()
        except Exception as exc:
            self.error.emit(self.tr("Could not open {0}: {1}").format(self.port, exc))
            return False

        self.connected.emit(self.port)
        return True

    def _close_port(self) -> None:
        try:
            if self._serial:
                self._serial.close()
        except Exception:
            pass

    def _poll_loop(self) -> None:
        sequence = 0
        session_start = time.perf_counter()
        next_poll_at = session_start

        while self._running:
            if self._pending_writes:
                payload, scale_factor = self._pending_writes.popleft()
                self._send(payload)
                if scale_factor is not None:
                    self._unconfirmed_scale = scale_factor
                continue

            # While a scale change awaits its OK, stop polling so the next
            # line received is unambiguously the answer to that command.
            now = time.perf_counter()
            if self._unconfirmed_scale is None and now >= next_poll_at:
                self._send("G\n")
                next_poll_at = now + POLL_INTERVAL_S

            raw_line = self._serial.readline()
            if not raw_line:
                continue

            parsed = parse_line(raw_line.decode("ascii", errors="ignore"))
            if isinstance(parsed, MeasurementLine):
                sequence += 1
                self.measurement_received.emit(
                    time.perf_counter() - session_start, parsed.weight_kg, sequence
                )
            elif isinstance(parsed, OkLine):
                self._on_ok()
            elif isinstance(parsed, ErrorLine):
                self._on_firmware_error(parsed.message)

    def _on_ok(self) -> None:
        if self._unconfirmed_scale is None:
            return
        self.current_scale_factor = self._unconfirmed_scale
        self._unconfirmed_scale = None
        self.scale_updated.emit(self.current_scale_factor)

    def _on_firmware_error(self, message: str) -> None:
        if self._unconfirmed_scale is None:
            self.warning.emit(message)
            return
        rejected_factor = self._unconfirmed_scale
        self._unconfirmed_scale = None
        self.warning.emit(
            self.tr("Firmware rejected F:{0} -> {1}").format(f"{rejected_factor:.5f}", message)
        )

    def _send(self, payload: str) -> None:
        if self._serial is not None:
            self._serial.write(payload.encode("ascii", errors="ignore"))


class SerialThreadController(QObject):
    """Owns the worker thread and re-emits its signals on the GUI thread."""

    measurement_received = pyqtSignal(float, float, int)
    scale_updated = pyqtSignal(float)
    connected = pyqtSignal(str)
    disconnected = pyqtSignal()
    warning = pyqtSignal(str)
    error = pyqtSignal(str)

    def __init__(
        self,
        initial_scale_factor: float = DEFAULT_SCALE_FACTOR,
        parent: Optional[QObject] = None,
    ):
        super().__init__(parent)
        self._thread: Optional[QThread] = None
        self._worker: Optional[SerialWorker] = None
        self.current_scale_factor = initial_scale_factor

    def is_connected(self) -> bool:
        """True from ``connect()`` until the worker thread has fully stopped."""
        return self._thread is not None

    def connect(self, port: str, baud: int) -> None:
        if self._thread is not None:
            self.warning.emit(self.tr("A connection is already active."))
            return

        thread = QThread()
        worker = SerialWorker(port, baud, initial_scale_factor=self.current_scale_factor)
        worker.moveToThread(thread)

        thread.started.connect(worker.run)
        worker.measurement_received.connect(self.measurement_received)
        worker.scale_updated.connect(self._on_scale_updated)
        worker.connected.connect(self.connected)
        worker.disconnected.connect(self.disconnected)
        worker.warning.connect(self.warning)
        worker.error.connect(self.error)
        # Direct: quit() is thread-safe and must not wait for the GUI event loop.
        worker.finished.connect(thread.quit, Qt.DirectConnection)
        worker.finished.connect(worker.deleteLater)
        thread.finished.connect(thread.deleteLater)
        thread.finished.connect(self._on_thread_finished)

        self._thread = thread
        self._worker = worker
        thread.start()

    def disconnect(self, wait: bool = False) -> None:
        """Ask the worker to stop; with ``wait`` block briefly until it has."""
        if self._worker:
            self._worker.stop()
        if wait and self._thread is not None:
            self._thread.wait(DISCONNECT_WAIT_MS)

    def set_scale(self, factor: float) -> None:
        if self._worker:
            self._worker.request_set_scale(factor)
        else:
            self.warning.emit(self.tr("There is no active connection to send the scale factor to."))

    def set_recording_indicator(self, recording_active: bool) -> None:
        if self._worker:
            self._worker.request_recording_state(recording_active)

    def _on_thread_finished(self) -> None:
        self._thread = None
        self._worker = None

    def _on_scale_updated(self, factor: float) -> None:
        self.current_scale_factor = factor
        self.scale_updated.emit(factor)
