"""TXT export: file format helpers and the live session recorder.

The header keys and column names are kept in Spanish on purpose: they are the
data format already used by existing measurement files and analysis scripts.
"""

from __future__ import annotations

from datetime import datetime
from typing import Iterable, Optional, TextIO

from domain_models import STANDARD_GRAVITY

TXT_FILE_FILTER = "TXT (*.txt)"
RECORDING_FILENAME_FORMAT = "log_%Y_%m_%d__%Hh_%Mmin.txt"
RANGE_EXPORT_FILENAME_FORMAT = "medicion_rango_%Y_%m_%d__%Hh_%Mmin.txt"


def write_txt_header(
    file_obj: TextIO,
    timestamp: datetime,
    g_value: float,
    unit_label: str,
) -> None:
    file_obj.write(f"# fecha y hora = {timestamp.strftime('%d/%m/%Y %H:%M')}\n")
    file_obj.write(f"# g local = {g_value:14.7f} m/s2\n")
    file_obj.write(f"# tiempo_s\tfuerza_{unit_label}\n")


def format_txt_measurement_line(t_value_s: float, force_display: float) -> str:
    return f"{t_value_s:.6f}\t{force_display:.6f}\n"


def ensure_txt_extension(path: str) -> str:
    return path if path.lower().endswith(".txt") else path + ".txt"


def export_measurements(
    path: str,
    timestamp: datetime,
    unit_label: str,
    rows: Iterable[tuple[float, float]],
) -> None:
    """Write a complete TXT file (header plus rows)."""
    with open(path, "w", newline="", encoding="utf-8") as file_obj:
        write_txt_header(file_obj, timestamp, STANDARD_GRAVITY, unit_label)
        for t_value_s, force_display in rows:
            file_obj.write(format_txt_measurement_line(t_value_s, force_display))


class TxtRecorder:
    """Appends samples to a TXT file while a recording is active.

    Every line is flushed, so a crash during a test loses at most one sample.
    """

    def __init__(self):
        self._file: Optional[TextIO] = None

    @property
    def is_recording(self) -> bool:
        return self._file is not None

    def start(self, path: str, timestamp: datetime, unit_label: str) -> None:
        """Create the file and write its header. Raises ``OSError`` on failure."""
        self.stop()
        self._file = open(path, "w", newline="", encoding="utf-8")
        write_txt_header(self._file, timestamp, STANDARD_GRAVITY, unit_label)
        self._file.flush()

    def write(self, t_value_s: float, force_display: float) -> None:
        if self._file is None:
            return
        self._file.write(format_txt_measurement_line(t_value_s, force_display))
        self._file.flush()

    def stop(self) -> None:
        """Close the file. Safe to call when not recording."""
        file_obj, self._file = self._file, None
        if file_obj is not None:
            file_obj.close()
