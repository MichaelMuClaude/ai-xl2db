---
name: ai-xl2db
description: Convert a spreadsheet (.xlsx or .csv) into a single SQLite database, then query it with read-only SQL. Use when a spreadsheet needs to be searched, filtered, or summarised, or when several sheets must be joined.
---

# ai-xl2db

## What it does

Turns each sheet into a table in one `.db` file, with typed columns and a record of formulas and sources.

## Commands

```bash
ai-xl2db convert book.xlsx                    # writes book.db
ai-xl2db convert book.xlsx -o out/book.db --force
ai-xl2db describe book.db                     # all tables and their columns
ai-xl2db describe book.db --table sales_2026  # one table
ai-xl2db query book.db "SELECT region, units FROM sales_2026 WHERE units > 10"
```

- `query` is read-only. It refuses any statement that writes. Output is CSV on stdout.
- Start with `describe` to see the table and column names before writing a query.

## Reading the result

- Table names are the sheet names in lower case with underscores. Column names are the header cells cleaned the same way. `column_N` means the header was blank.
- The `_sheets` table shows each sheet's original title and source file.
- The `_formulas` table lists each formula by table, spreadsheet row, and column. `python_script` is a Python script that recomputes the value. `cached_value` is the result stored in the file. `note` says why a formula could not be translated.

## Limits

- Only a subset of Excel functions is translated. Cross-sheet references, lookups, and whole-column ranges are not supported.
- Scripts run with `ai_xl2db.runtime`. Read a script before running it.
- Title rows and blank rows are skipped. If a table is missing rows, check the source file.
- `.xls`, `.ods`, and charts are not supported.
