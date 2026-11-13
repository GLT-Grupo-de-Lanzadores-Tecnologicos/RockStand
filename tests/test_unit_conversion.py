import pytest

from domain_models import STANDARD_GRAVITY, Unit
from services.unit_conversion import newtons_to_unit, parse_force_text, unit_to_newtons


def test_newtons_to_each_unit():
    assert newtons_to_unit(STANDARD_GRAVITY, Unit.N) == STANDARD_GRAVITY
    assert newtons_to_unit(STANDARD_GRAVITY, Unit.KGF) == pytest.approx(1.0)
    assert newtons_to_unit(STANDARD_GRAVITY, Unit.GF) == pytest.approx(1000.0)


@pytest.mark.parametrize("unit", list(Unit))
def test_conversion_round_trip(unit):
    assert unit_to_newtons(newtons_to_unit(12.5, unit), unit) == pytest.approx(12.5)


@pytest.mark.parametrize(
    "text, expected",
    [
        ("3.27", (3.27, None)),
        ("3,27 N", (3.27, Unit.N)),
        (" 0.333 kgf ", (0.333, Unit.KGF)),
        ("333gf", (333.0, Unit.GF)),
        ("-2 newtons", (-2.0, Unit.N)),
    ],
)
def test_parse_force_text_accepts_value_with_optional_unit(text, expected):
    assert parse_force_text(text) == expected


@pytest.mark.parametrize("text", ["", "abc", "3.27 lb", "1.2.3", "N"])
def test_parse_force_text_rejects_invalid_input(text):
    assert parse_force_text(text) == (None, None)
