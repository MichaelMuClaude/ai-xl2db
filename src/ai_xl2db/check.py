"""Recalculate the translated formulas in a database and compare with the cached values."""

import math
import sqlite3
from dataclasses import dataclass
from pathlib import Path

from ai_xl2db import runtime, safe
from ai_xl2db.store import FORMULAS_TABLE, DatabaseError


@dataclass
class Check:
    table: str
    spreadsheet_row: int
    column: str
    formula: str
    result: str
    cached: str | None
    status: str  # "match", "mismatch", "no cached value", or "error"
    message: str = ""


def _same(result: object, cached: str) -> bool:
    try:
        return math.isclose(float(result), float(cached), rel_tol=1e-9, abs_tol=1e-9)
    except (TypeError, ValueError):
        return runtime._text(result) == cached


def check_database(db_path: Path) -> list[Check]:
    uri = Path(db_path).resolve().as_uri() + "?mode=ro"
    conn = sqlite3.connect(uri, uri=True)
    try:
        rows = conn.execute(
            f"SELECT table_name, spreadsheet_row, column_name, formula, python_script, cached_value "
            f"FROM {FORMULAS_TABLE} WHERE python_script IS NOT NULL ORDER BY table_name, spreadsheet_row"
        ).fetchall()
    except sqlite3.OperationalError as exc:
        raise DatabaseError(
            f"{db_path.name} has no formula table in the current format; convert the workbook again ({exc})"
        ) from exc
    finally:
        conn.close()

    sheets: dict[str, runtime.SheetData] = {}
    checks = []
    for table, row, column, formula, script, cached in rows:
        if table not in sheets:
            sheets[table] = runtime.load_sheet(db_path, table)
        try:
            value = safe.run(script, sheets[table])
        except Exception as exc:  # report any failure against the formula, do not stop the run
            checks.append(Check(table, row, column, formula, "", cached, "error", str(exc)))
            continue
        result = runtime._text(value)
        if cached is None:
            status = "no cached value"
        elif _same(value, cached):
            status = "match"
        else:
            status = "mismatch"
        checks.append(Check(table, row, column, formula, result, cached, status))
    return checks
