# ai-xl2db

Convert a spreadsheet into one SQLite database, so that people and AI agents can query it with SQL instead of guessing at cell positions.

```bash
ai-xl2db convert budget.xlsx                 # writes budget.db, one table per sheet
ai-xl2db describe budget.db                  # tables, columns, types, and sources
ai-xl2db query budget.db "SELECT region, SUM(units) FROM sales_2026 GROUP BY region"
ai-xl2db check budget.db                    # recalculate formulas, compare with stored values
```

`query` is read-only and prints CSV, which is easy for an agent to read.

## What it does

- **One table per sheet.** Sheet names become table names, for example `Sales 2026` becomes `sales_2026`.
- **Typed columns.** Each column is an `INTEGER`, `REAL`, or `TEXT` column in a `STRICT` table, so wrong types are rejected on write. Dates are stored as ISO text.
- **Header detection.** Title rows and blank rows above and between data are skipped. The header is the first row with at least two filled cells.
- **Formulas become Python.** Each supported Excel formula is translated into a short Python script (stored in the `_formulas` table). The script rebuilds the value from the other cells. Supported: cell references and ranges, `+ - * / ^ &`, comparisons, `SUM`, `AVERAGE`, `MIN`, `MAX`, `COUNT`, `IF`, `ROUND`, `ABS`, `AND`, `OR`, and `NOT`. Anything else is recorded with the reason it is not supported.
- **Cached values.** The result stored in the file is kept in `_formulas`. `check` runs each script and compares its result with that value, and it exits with 1 on any mismatch or error.
- **Safe to run.** Before a stored script runs, it must contain only the constructs the translator produces: one `compute` function, calls to the runtime helpers, arithmetic, comparisons, and literals. Imports of anything else, `open`, `__import__`, and attribute access are refused. This guards against mistakes and edits. It is not a full sandbox.
- **Sources.** The `_sheets` table records each sheet's original title, source file, import time, and row count.
- **CSV input.** CSV files become one table. Numbers are detected, and values with leading zeros, such as postcodes, stay as text. UTF-8 and GB18030 are accepted.

## Install

```bash
pip install -e .
```

Requires Python 3.10 or newer. The only dependency is `openpyxl`.

## Limits

- Scripts are plain Python that imports `ai_xl2db.runtime`. Read them before running them, and do not run scripts from files you do not trust.
- Only the formula subset above is translated. Cross-sheet references, lookups, and whole-column ranges are not supported yet.
- If a file was saved by a program that does not store results, the cached value is empty. Open and save the file in a spreadsheet application first.
- Merged cells are read as one value in their top-left cell.
- Excel `.xls`, `.ods`, and charts are not supported yet.
- Header detection is a heuristic. Check the result with `describe`.
- Column names are cleaned to lower case with underscores, so the original names are only in the source file.

## Licence

MIT. See [LICENSE](LICENSE).
