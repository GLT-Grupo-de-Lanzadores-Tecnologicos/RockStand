from datetime import datetime
from io import StringIO

from services.txt_export_service import (
    TxtRecorder,
    ensure_txt_extension,
    format_txt_measurement_line,
    write_txt_header,
)

EXPECTED_HEADER = [
    "# fecha y hora = 13/03/2026 12:46",
    "# g local =      9.8066500 m/s2",
    "# tiempo_s\tfuerza_kgf",
]


def test_write_txt_header_uses_time_and_force_columns():
    output = StringIO()

    write_txt_header(output, datetime(2026, 3, 13, 12, 46), 9.80665, "kgf")

    assert output.getvalue().splitlines() == EXPECTED_HEADER


def test_measurement_line_uses_tab_separator():
    assert format_txt_measurement_line(1.25, 3.5) == "1.250000\t3.500000\n"


def test_ensure_txt_extension():
    assert ensure_txt_extension("run") == "run.txt"
    assert ensure_txt_extension("run.TXT") == "run.TXT"


def test_recorder_writes_header_and_rows(tmp_path):
    path = tmp_path / "session.txt"
    recorder = TxtRecorder()

    recorder.start(str(path), datetime(2026, 3, 13, 12, 46), "kgf")
    assert recorder.is_recording
    recorder.write(0.5, 1.25)
    recorder.stop()

    assert not recorder.is_recording
    assert path.read_text(encoding="utf-8").splitlines() == EXPECTED_HEADER + [
        "0.500000\t1.250000"
    ]
