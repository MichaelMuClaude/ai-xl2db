import pytest

from ai_xl2db import runtime
from ai_xl2db.runtime import SheetData


def sheet():
    return SheetData(rows={4: {"units": 10}, 5: {"units": 20}, 6: {"units": None}, 7: {"units": 5}})


def test_sum_ignores_blanks_and_text():
    data = SheetData(rows={1: {"x": 2}, 2: {"x": "n/a"}, 3: {"x": None}, 4: {"x": 3}})
    assert runtime.SUM(runtime.rng(data, "x", 1, 4)) == 5


def test_blank_cell_counts_as_zero_in_arithmetic():
    assert runtime.cell(sheet(), "units", 6) == 0


def test_average_of_nothing_is_an_error():
    with pytest.raises(ValueError, match="DIV/0"):
        runtime.AVERAGE([None, None])


def test_round_is_half_away_from_zero_like_excel():
    assert runtime.ROUND(2.5, 0) == 3
    assert runtime.ROUND(-2.5, 0) == -3
    assert runtime.ROUND(1.2345, 2) == 1.23


def test_concat_shows_whole_numbers_without_decimal_point():
    assert runtime.concat(12.0, "x") == "12x"
    assert runtime.concat(None, "y") == "y"


def test_logical_functions():
    assert runtime.IF(True, "a", "b") == "a"
    assert runtime.IF(False, "a") is False
    assert runtime.AND(True, 1) is True
    assert runtime.OR(False, 0) is False
