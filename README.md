# ai-xl2db

Convert a spreadsheet into one SQLite database, so that people and AI agents can query it with SQL instead of guessing at cell positions.

```bash
ai-xl2db convert budget.xlsx                 # writes budget.db, one table per sheet
ai-xl2db describe budget.db                  # tables, columns, types, and sources
ai-xl2db query budget.db "SELECT region, SUM(units) FROM sales_2026 GROUP BY region"
```

`query` is read-only and prints CSV, which is easy for an agent to read.

## What it does

- **One table per sheet.** Sheet names become table names, for example `Sales 2026` becomes `sales_2026`.
- **Typed columns.** Each column is an `INTEGER`, `REAL`, or `TEXT` column in a `STRICT` table, so wrong types are rejected on write. Dates are stored as ISO text.
- **Header detection.** Title rows and blank rows above and between data are skipped. The header is the first row with at least two filled cells.
- **Formulas.** Each formula is recorded in a `_formulas` table with its spreadsheet row and column, so an agent can see how a value was calculated. The value is stored as it appears in the file.
- **Sources.** The `_sheets` table records each sheet's original title, source file, import time, and row count.
- **CSV input.** CSV files become one table. Numbers are detected, and values with leading zeros, such as postcodes, stay as text. UTF-8 and GB18030 are accepted.

## Install

```bash
pip install -e .
```

Requires Python 3.10 or newer. The only dependency is `openpyxl`.

## Limits

- Formulas are not calculated. If a file was saved by a program that does not store results, the value is empty. Open and save the file in a spreadsheet application first.
- Merged cells are read as one value in their top-left cell.
- Excel `.xls`, `.ods`, and charts are not supported yet.
- Header detection is a heuristic. Check the result with `describe`.
- Column names are cleaned to lower case with underscores, so the original names are only in the source file.

## Licence

MIT. See [LICENSE](LICENSE).
