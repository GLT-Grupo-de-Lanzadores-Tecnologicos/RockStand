from services.simple_protocol import ErrorLine, MeasurementLine, OkLine, parse_line


def test_parses_measurement_line():
    line = parse_line("12.3456\r\n")

    assert isinstance(line, MeasurementLine)
    assert line.weight_kg == 12.3456


def test_parses_ok_line():
    assert isinstance(parse_line("OK"), OkLine)


def test_parses_error_line():
    line = parse_line("ERROR:factor_invalido")

    assert isinstance(line, ErrorLine)
    assert line.message == "ERROR:factor_invalido"


def test_ignores_unknown_and_empty_lines():
    assert parse_line("FW:hx711-minimal") is None
    assert parse_line("") is None
