"""Write spreadsheets to a SQLite database and read it back."""

import csv
import datetime
import sqlite3
import sys
from pathlib import Path

from ai_xl2db import infer, naming
from ai_xl2db.reader import Sheet

SHEETS_TABLE = "_sheets"
FORMULAS_TABLE = "_formulas"


class DatabaseError(RuntimeError):
    """A database operation failed. The message is meant for the user."""


def write_database(db_path: Path, sheets: list[Sheet], source: str, force: bool = False) -> None:
    if db_path.exists():
        if not force:
            raise DatabaseError(f"{db_path} already exists (use --force to replace it)")
        db_path.unlink()
    db_path.parent.mkdir(parents=True, exist_ok=True)

    conn = sqlite3.connect(db_path)
    try:
        conn.execute(
            f"CREATE TABLE {SHEETS_TABLE} ("
            "table_name TEXT PRIMARY KEY, sheet_title TEXT NOT NULL, source TEXT NOT NULL, "
            "imported_at TEXT NOT NULL, row_count INTEGER NOT NULL) STRICT"
        )
        conn.execute(
            f"CREATE TABLE {FORMULAS_TABLE} ("
            "table_name TEXT NOT NULL, spreadsheet_row INTEGER NOT NULL, "
            "column_name TEXT NOT NULL, formula TEXT NOT NULL) STRICT"
        )
        taken = {SHEETS_TABLE, FORMULAS_TABLE}
        imported_at = datetime.datetime.now().isoformat(timespec="seconds")

        for sheet in sheets:
            table = naming.table_name(sheet.title, taken)
            columns = naming.column_names(sheet.header)
            types = [infer.column_type([row[i] for row in sheet.rows]) for i in range(len(columns))]
            definitions = ", ".join(f'"{name}" {sql_type}' for name, sql_type in zip(columns, types))
            conn.execute(f'CREATE TABLE "{table}" ({definitions}) STRICT')

            placeholders = ", ".join("?" for _ in columns)
            conn.executemany(
                f'INSERT INTO "{table}" VALUES ({placeholders})',
                (
                    [infer.to_storage(value, sql_type) for value, sql_type in zip(row, types)]
                    for row in sheet.rows
                ),
            )
            conn.execute(
                f"INSERT INTO {SHEETS_TABLE} VALUES (?, ?, ?, ?, ?)",
                (table, sheet.title, source, imported_at, len(sheet.rows)),
            )
            for (row_index, col_index), formula in sheet.formulas.items():
                conn.execute(
                    f"INSERT INTO {FORMULAS_TABLE} VALUES (?, ?, ?, ?)",
                    (table, sheet.row_numbers[row_index], columns[col_index], formula),
                )
        conn.commit()
    finally:
        conn.close()


def _open_read_only(db_path: Path) -> sqlite3.Connection:
    if not db_path.is_file():
        raise DatabaseError(f"no such database: {db_path}")
    uri = db_path.resolve().as_uri() + "?mode=ro"
    return sqlite3.connect(uri, uri=True)


def _data_tables(conn: sqlite3.Connection) -> list[tuple[str, str, str, str, int]]:
    try:
        return conn.execute(
            f"SELECT table_name, sheet_title, source, imported_at, row_count FROM {SHEETS_TABLE} "
            "ORDER BY table_name"
        ).fetchall()
    except sqlite3.OperationalError:
        return []


def describe(db_path: Path, table: str | None = None) -> str:
    conn = _open_read_only(db_path)
    try:
        tables = _data_tables(conn)
        if table is not None:
            tables = [t for t in tables if t[0] == table]
            if not tables:
                raise DatabaseError(f"no table named {table!r} in {db_path.name}")
        lines = []
        for name, title, source, imported_at, row_count in tables:
            lines.append(f"{name}  (sheet {title!r} from {source}, {row_count} rows, imported {imported_at})")
            for _cid, col, sql_type, *_ in conn.execute(f'PRAGMA table_info("{name}")'):
                lines.append(f"    {col}  {sql_type}")
            formulas = conn.execute(
                f"SELECT COUNT(*) FROM {FORMULAS_TABLE} WHERE table_name = ?", (name,)
            ).fetchone()[0]
            if formulas:
                lines.append(f"    ({formulas} cells had formulas; see {FORMULAS_TABLE})")
            lines.append("")
        if not lines:
            lines.append("no data tables found")
        return "\n".join(lines).rstrip() + "\n"
    finally:
        conn.close()


def query(db_path: Path, sql: str, out=sys.stdout) -> None:
    conn = _open_read_only(db_path)
    try:
        try:
            cursor = conn.execute(sql)
        except sqlite3.Error as exc:
            raise DatabaseError(f"query failed: {exc}") from exc
        writer = csv.writer(out)
        if cursor.description:
            writer.writerow([column[0] for column in cursor.description])
            writer.writerows(cursor.fetchall())
    finally:
        conn.close()
