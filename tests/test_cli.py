import subprocess
import sys


def _run(*args):
    return subprocess.run([sys.executable, "-m", "ai_xl2db.cli", *args], capture_output=True, text=True)


def test_convert_describe_query_round_trip(messy_xlsx, tmp_path):
    db = tmp_path / "out.db"
    assert _run("convert", str(messy_xlsx), "-o", str(db)).returncode == 0
    described = _run("describe", str(db), "--table", "sales_2026")
    assert described.returncode == 0 and "region  TEXT" in described.stdout
    queried = _run("query", str(db), "SELECT region, units FROM sales_2026 ORDER BY region")
    assert queried.returncode == 0
    assert queried.stdout.splitlines()[0] == "region,units"


def test_unsupported_input_exits_with_2(tmp_path):
    path = tmp_path / "book.ods"
    path.write_text("x")
    assert _run("convert", str(path)).returncode == 2


def test_missing_input_exits_with_1(tmp_path):
    assert _run("convert", str(tmp_path / "nope.xlsx")).returncode == 1


def test_bad_sql_exits_with_1(messy_xlsx, tmp_path):
    db = tmp_path / "out.db"
    _run("convert", str(messy_xlsx), "-o", str(db))
    result = _run("query", str(db), "SELECT * FROM no_such_table")
    assert result.returncode == 1
    assert "query failed" in result.stderr
