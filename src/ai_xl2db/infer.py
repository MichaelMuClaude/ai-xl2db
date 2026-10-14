"""Choose a SQLite column type for a list of values."""

import datetime

INTEGER = "INTEGER"
REAL = "REAL"
TEXT = "TEXT"


def column_type(values: list[object]) -> str:
    present = [v for v in values if v is not None]
    if not present:
        return TEXT
    if all(isinstance(v, bool) for v in present):
        return INTEGER
    if all(isinstance(v, int) and not isinstance(v, bool) for v in present):
        return INTEGER
    if all(isinstance(v, (int, float)) and not isinstance(v, bool) for v in present):
        return REAL
    return TEXT


def to_storage(value: object, sql_type: str) -> object:
    """Convert a spreadsheet value to the Python value stored in a column of ``sql_type``."""
    if value is None:
        return None
    if sql_type == INTEGER:
        return int(value)
    if sql_type == REAL:
        return float(value)
    if isinstance(value, datetime.datetime):
        if value.time() == datetime.time(0, 0):
            return value.date().isoformat()
        return value.isoformat(sep=" ", timespec="seconds")
    if isinstance(value, datetime.date):
        return value.isoformat()
    if isinstance(value, datetime.time):
        return value.isoformat(timespec="seconds")
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)
