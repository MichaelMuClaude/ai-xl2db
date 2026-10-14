import datetime

from ai_xl2db import infer


def test_column_type_choices():
    assert infer.column_type([1, 2, None]) == infer.INTEGER
    assert infer.column_type([1, 2.5]) == infer.REAL
    assert infer.column_type([1, "n/a"]) == infer.TEXT
    assert infer.column_type([True, False]) == infer.INTEGER
    assert infer.column_type([None, None]) == infer.TEXT


def test_dates_are_stored_as_iso_text():
    assert infer.to_storage(datetime.date(2026, 1, 5), infer.TEXT) == "2026-01-05"
    assert infer.to_storage(datetime.datetime(2026, 1, 5, 14, 30), infer.TEXT) == "2026-01-05 14:30:00"
    assert infer.to_storage(datetime.datetime(2026, 1, 5), infer.TEXT) == "2026-01-05"


def test_whole_floats_in_text_columns_lose_the_decimal_point():
    assert infer.to_storage(12.0, infer.TEXT) == "12"
    assert infer.to_storage(12.5, infer.TEXT) == "12.5"
