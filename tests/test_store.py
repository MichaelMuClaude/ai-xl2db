import sqlite3

import pytest

from ai_xl2db import reader, store


def _build(messy_xlsx, db):
    store.write_database(db, reader.read_xlsx(messy_xlsx), source=messy_xlsx.name)


def test_each_sheet_becomes_a_strict_table(messy_xlsx, tmp_path):
    db = tmp_path / "out.db"
    _build(messy_xlsx, db)
    conn = sqlite3.connect(db)
    names = {r[0] for r in conn.execute("SELECT name FROM sqlite_master WHERE type='table'")}
    assert {"sales_2026", "sheet_2nd_sheet", "_sheets", "_formulas"} <= names
    assert conn.execute("SELECT COUNT(*) FROM sales_2026").fetchone()[0] == 4
    conn.close()


def test_column_types_follow_the_data(messy_xlsx, tmp_path):
    db = tmp_path / "out.db"
    _build(messy_xlsx, db)
    text = store.describe(db)
    assert "units  INTEGER" in text
    assert "price  TEXT" in text  # mixed numbers and "n/a"
    assert "date  TEXT" in text


def test_strict_tables_reject_wrong_types(messy_xlsx, tmp_path):
    db = tmp_path / "out.db"
    _build(messy_xlsx, db)
    conn = sqlite3.connect(db)
    with pytest.raises(sqlite3.Error):
        conn.execute("INSERT INTO sales_2026 (region, units) VALUES ('X', 'many')")
    conn.close()


def test_formulas_are_recorded_with_spreadsheet_row_numbers(messy_xlsx, tmp_path):
    db = tmp_path / "out.db"
    _build(messy_xlsx, db)
    out = tmp_path / "rows.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        store.query(db, "SELECT table_name, spreadsheet_row, column_name, formula FROM _formulas", out=f)
    assert "sales_2026,8,units,=SUM(B4:B6)" in out.read_text(encoding="utf-8")


def test_query_is_read_only(messy_xlsx, tmp_path):
    db = tmp_path / "out.db"
    _build(messy_xlsx, db)
    with pytest.raises(store.DatabaseError):
        store.query(db, "DELETE FROM sales_2026")


def test_existing_database_is_not_overwritten_without_force(messy_xlsx, tmp_path):
    db = tmp_path / "out.db"
    _build(messy_xlsx, db)
    with pytest.raises(store.DatabaseError, match="--force"):
        _build(messy_xlsx, db)
    store.write_database(db, reader.read_xlsx(messy_xlsx), source="again", force=True)


def test_missing_database_gives_a_clear_error(tmp_path):
    with pytest.raises(store.DatabaseError, match="no such database"):
        store.describe(tmp_path / "nope.db")


def test_chinese_text_survives_the_round_trip(messy_xlsx, tmp_path):
    db = tmp_path / "out.db"
    _build(messy_xlsx, db)
    out = tmp_path / "zh.csv"
    with out.open("w", encoding="utf-8", newline="") as f:
        store.query(db, "SELECT note FROM \"sheet_2nd_sheet\"", out=f)
    assert "中文备注" in out.read_text(encoding="utf-8")


def test_formulas_are_stored_as_python_scripts(messy_xlsx, tmp_path):
    db = tmp_path / "out.db"
    _build(messy_xlsx, db)
    conn = sqlite3.connect(db)
    script, note = conn.execute(
        "SELECT python_script, note FROM _formulas WHERE table_name = 'sales_2026'"
    ).fetchone()
    conn.close()
    assert note is None
    assert "return SUM(rng(sheet, 'units', 4, 6))" in script


def test_stored_script_gives_the_same_total_as_the_spreadsheet_formula(messy_xlsx, tmp_path):
    from ai_xl2db import runtime

    db = tmp_path / "out.db"
    _build(messy_xlsx, db)
    conn = sqlite3.connect(db)
    script = conn.execute("SELECT python_script FROM _formulas WHERE table_name = 'sales_2026'").fetchone()[0]
    conn.close()
    namespace: dict = {}
    exec(script, namespace)  # test-only: runs the script we generated above
    data = runtime.load_sheet(db, "sales_2026")
    # Excel =SUM(B4:B6) over North 10, South 20, and a blank row
    assert namespace["compute"](data) == 30


def test_unsupported_formula_is_recorded_with_a_note(tmp_path):
    import openpyxl

    wb = openpyxl.Workbook()
    ws = wb.active
    ws.title = "Lookup"
    ws.append(["Key", "Value"])
    ws.append(["a", 1])
    ws.append(["b", "=VLOOKUP(A2,A1:B2,2,FALSE)"])
    path = tmp_path / "lookup.xlsx"
    wb.save(path)
    db = tmp_path / "lookup.db"
    store.write_database(db, reader.read_xlsx(path), source=path.name)
    conn = sqlite3.connect(db)
    script, note = conn.execute("SELECT python_script, note FROM _formulas").fetchone()
    conn.close()
    assert script is None
    assert "not supported" in note
