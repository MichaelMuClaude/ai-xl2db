"""Functions used by the Python scripts generated from Excel formulas.

A script receives a SheetData object and returns the value of one cell.
"""

import sqlite3
from dataclasses import dataclass, field
from decimal import ROUND_HALF_UP, Decimal
from pathlib import Path


@dataclass
class SheetData:
    """Rows of one table, keyed by spreadsheet row number, then by column name."""

    rows: dict[int, dict[str, object]] = field(default_factory=dict)

    def value(self, column: str, row: int) -> object:
        return self.rows.get(row, {}).get(column)


def _numbers(args) -> list[float]:
    numbers = []
    for arg in args:
        items = arg if isinstance(arg, list) else [arg]
        for item in items:
            if isinstance(item, bool) or item is None:
                continue
            if isinstance(item, (int, float)):
                numbers.append(item)
    return numbers


def cell(sheet: SheetData, column: str, row: int) -> object:
    """A single cell. Blank cells count as 0, as they do in arithmetic in a spreadsheet."""
    value = sheet.value(column, row)
    return 0 if value is None else value


def rng(sheet: SheetData, column: str, first: int, last: int) -> list[object]:
    """Values in a column from one spreadsheet row to another, inclusive. Blanks are None."""
    return [sheet.value(column, row) for row in range(first, last + 1)]


def SUM(*args) -> float:
    return sum(_numbers(args))


def AVERAGE(*args) -> float:
    numbers = _numbers(args)
    if not numbers:
        raise ValueError("#DIV/0!")
    return sum(numbers) / len(numbers)


def MIN(*args) -> float:
    numbers = _numbers(args)
    return min(numbers) if numbers else 0


def MAX(*args) -> float:
    numbers = _numbers(args)
    return max(numbers) if numbers else 0


def COUNT(*args) -> int:
    return len(_numbers(args))


def IF(condition, when_true, when_false=False):
    return when_true if condition else when_false


def ROUND(number, digits=0) -> float:
    quantum = Decimal(1).scaleb(-int(digits))
    return float(Decimal(str(number)).quantize(quantum, rounding=ROUND_HALF_UP))


def ABS(number) -> float:
    return abs(number)


def AND(*args) -> bool:
    return all(bool(v) for arg in args for v in (arg if isinstance(arg, list) else [arg]) if v is not None)


def OR(*args) -> bool:
    return any(bool(v) for arg in args for v in (arg if isinstance(arg, list) else [arg]) if v is not None)


def NOT(value) -> bool:
    return not bool(value)


def _text(value: object) -> str:
    if value is None:
        return ""
    if isinstance(value, bool):
        return "TRUE" if value else "FALSE"
    if isinstance(value, float) and value.is_integer():
        return str(int(value))
    return str(value)


def concat(left, right) -> str:
    return _text(left) + _text(right)


def load_sheet(db_path: Path, table: str) -> SheetData:
    """Read one data table back, with each row keyed by its original spreadsheet row number."""
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        columns = [info[1] for info in conn.execute(f'PRAGMA table_info("{table}")')]
        query = (
            f'SELECT r.spreadsheet_row, {", ".join(f"d.\"{c}\"" for c in columns)} '
            f'FROM _rows r JOIN "{table}" d ON d.rowid = r.position '
            "WHERE r.table_name = ? ORDER BY r.position"
        )
        data = SheetData()
        for record in conn.execute(query, (table,)):
            data.rows[record[0]] = dict(zip(columns, record[1:]))
        return data
    finally:
        conn.close()
