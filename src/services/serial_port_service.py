"""Enumeration of the serial ports available on this machine."""

from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional

from PyQt5.QtCore import QCoreApplication

ComportsFactory = Callable[[], Iterable[object]]


@dataclass(frozen=True)
class SerialPortScanResult:
    """Port names found, or an error message explaining why none were listed."""

    ports: list[str]
    error_message: Optional[str] = None


def scan_serial_ports(comports_factory: Optional[ComportsFactory] = None) -> SerialPortScanResult:
    """List serial port names, de-duplicated and in natural order (COM3 < COM10).

    ``comports_factory`` lets tests replace pyserial. This function never
    raises: failures are reported through ``error_message``.
    """
    try:
        if comports_factory is None:
            # Imported lazily so a missing pyserial becomes a readable message.
            from serial.tools.list_ports import comports as comports_factory

        names = {str(getattr(port, "device", "") or "").strip() for port in comports_factory()}
        names.discard("")
        return SerialPortScanResult(ports=sorted(names, key=lambda name: (len(name), name)))
    except ModuleNotFoundError as exc:
        if exc.name == "serial":
            message = QCoreApplication.translate(
                "SerialPortService",
                "Cannot list ports: pyserial is not installed in this environment."
            )
        else:
            message = QCoreApplication.translate(
                "SerialPortService", "Cannot list ports: required module '{0}' is missing."
            ).format(exc.name)
        return SerialPortScanResult(ports=[], error_message=message)
    except Exception as exc:
        message = QCoreApplication.translate(
            "SerialPortService", "Cannot list serial ports: {0}"
        ).format(exc)
        return SerialPortScanResult(ports=[], error_message=message)
