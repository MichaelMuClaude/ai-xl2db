import sqlite3
import subprocess
import sys

import pytest

from ai_xl2db import check, reader, runtime, safe, store


@pytest.fixture
def built_db(messy_xlsx, tmp_path):
    db = tmp_path / "out.db"
    store.write_database(db, reader.read_xlsx(messy_xlsx), source=messy_xlsx.name)
    return db


def _set_cached(db, value):
    conn = sqlite3.connect(db)
    conn.execute("UPDATE _formulas SET cached_value = ? WHERE table_name = 'sales_2026'", (value,))
    conn.commit()
    conn.close()


def test_formula_without_cached_value_is_reported_as_such(built_db):
    [result] = check.check_database(built_db)
    assert result.result == "30"
    assert result.status == "no cached value"


def test_matching_cached_value(built_db):
    _set_cached(built_db, "30")
    [result] = check.check_database(built_db)
    assert result.status == "match"


def test_numbers_compare_as_numbers(built_db):
    _set_cached(built_db, "30.0")
    [result] = check.check_database(built_db)
    assert result.status == "match"


def test_mismatched_cached_value(built_db):
    _set_cached(built_db, "31")
    [result] = check.check_database(built_db)
    assert result.status == "mismatch"


def test_cli_exit_codes(built_db):
    run = lambda *a: subprocess.run([sys.executable, "-m", "ai_xl2db.cli", *a], capture_output=True, text=True)
    assert run("check", str(built_db)).returncode == 0  # no cached value is not a failure
    _set_cached(built_db, "99")
    assert run("check", str(built_db)).returncode == 1


def test_database_from_an_older_format_gives_a_clear_message(tmp_path):
    db = tmp_path / "old.db"
    conn = sqlite3.connect(db)
    conn.execute("CREATE TABLE _formulas (table_name TEXT, spreadsheet_row INTEGER, column_name TEXT, formula TEXT)")
    conn.commit()
    conn.close()
    with pytest.raises(store.DatabaseError, match="convert the workbook again"):
        check.check_database(db)


SAFE = "from ai_xl2db.runtime import SUM, rng\n\ndef compute(sheet):\n    return SUM(rng(sheet, 'units', 1, 3))\n"


def test_generated_style_script_is_accepted():
    safe.validate(SAFE)


@pytest.mark.parametrize(
    "source, reason",
    [
        ("import os\ndef compute(sheet):\n    return 1\n", "scripts may only import"),
        ("def compute(sheet):\n    return __import__('os')\n", "not allowed"),
        ("def compute(sheet):\n    return open('x')\n", "not allowed"),
        ("def compute(sheet):\n    return sheet.__class__\n", "not allowed"),
        ("def compute(sheet):\n    return [x for x in sheet]\n", "not allowed"),
        ("def other(sheet):\n    return 1\n", "exactly one function"),
        ("def compute(sheet):\n    return SUM(1)\n", "called without being imported"),
        ("from ai_xl2db.runtime import SUM\ndef compute(sheet):\n    return SUM(1)\nprint(1)\n", "not allowed"),
    ],
)
def test_suspicious_scripts_are_refused(source, reason):
    with pytest.raises(ValueError, match=reason):
        safe.validate(source)


def test_run_returns_the_computed_value():
    data = runtime.SheetData(rows={1: {"units": 2}, 2: {"units": 3}, 3: {"units": None}})
    assert safe.run(SAFE, data) == 5


def test_a_refused_script_is_reported_as_an_error(built_db):
    conn = sqlite3.connect(built_db)
    conn.execute("UPDATE _formulas SET python_script = ?", ("import os\ndef compute(sheet):\n    return 1\n",))
    conn.commit()
    conn.close()
    [result] = check.check_database(built_db)
    assert result.status == "error"
    assert "may only import" in result.message
