import argparse
import sys
from pathlib import Path

from ai_xl2db import __version__
from ai_xl2db import store
from ai_xl2db.reader import SUPPORTED_EXTENSIONS, read_spreadsheet


def _convert(args: argparse.Namespace) -> int:
    source = Path(args.input)
    if not source.is_file():
        print(f"error: no such file: {source}", file=sys.stderr)
        return 1
    if source.suffix.lower() not in SUPPORTED_EXTENSIONS:
        print(f"error: unsupported file type: {source.suffix or 'no extension'} "
              f"(supported: {', '.join(sorted(SUPPORTED_EXTENSIONS))})", file=sys.stderr)
        return 2

    output = Path(args.output) if args.output else source.with_suffix(".db")
    try:
        sheets = read_spreadsheet(source)
        if not sheets:
            print("error: no data found in the file", file=sys.stderr)
            return 1
        store.write_database(output, sheets, source=source.name, force=args.force)
    except (store.DatabaseError, ValueError) as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1

    for sheet in sheets:
        print(f"imported sheet {sheet.title!r}: {len(sheet.rows)} rows, {len(sheet.header)} columns")
    print(f"wrote {output}")
    return 0


def _describe(args: argparse.Namespace) -> int:
    try:
        print(store.describe(Path(args.database), args.table), end="")
    except store.DatabaseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def _query(args: argparse.Namespace) -> int:
    try:
        store.query(Path(args.database), args.sql)
    except store.DatabaseError as exc:
        print(f"error: {exc}", file=sys.stderr)
        return 1
    return 0


def main() -> None:
    parser = argparse.ArgumentParser(
        prog="ai-xl2db",
        description="Convert spreadsheets (.xlsx, .csv) into a single SQLite database that people and AI can query",
    )
    parser.add_argument("--version", action="version", version=__version__)
    subparsers = parser.add_subparsers(dest="command", required=True)

    convert = subparsers.add_parser("convert", help="Convert a spreadsheet to a SQLite database")
    convert.add_argument("input", help="Path to a .xlsx or .csv file")
    convert.add_argument("-o", "--output", help="Output .db path (default: same name, .db extension)")
    convert.add_argument("--force", action="store_true", help="Replace the output file if it exists")
    convert.set_defaults(func=_convert)

    describe = subparsers.add_parser("describe", help="Show the tables, columns, and sources in a database")
    describe.add_argument("database", help="Path to a .db file")
    describe.add_argument("--table", help="Only describe this table")
    describe.set_defaults(func=_describe)

    query = subparsers.add_parser("query", help="Run a read-only SQL query and print CSV")
    query.add_argument("database", help="Path to a .db file")
    query.add_argument("sql", help="A SQL statement, for example: SELECT * FROM sales LIMIT 5")
    query.set_defaults(func=_query)

    args = parser.parse_args()
    sys.exit(args.func(args))


if __name__ == "__main__":
    main()
