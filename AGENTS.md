# AGENTS.md — guide for AI agents contributing to ai-xl2db

This file is for AI coding agents that read, test, or change this project. The human-facing rules are in [CONTRIBUTING.md](CONTRIBUTING.md).

## What this project is

`ai-xl2db` converts a spreadsheet into one SQLite file and provides read-only SQL access to it. The goal is a file that an AI agent can understand: typed columns, recorded formulas, and recorded sources.

## Promises to keep

1. **No data loss.** Every non-empty cell in a detected table ends up in the database. Dropping blank rows is allowed; dropping values is not.
2. **Strict types.** Tables are created with `STRICT`. Never weaken this.
3. **Read-only queries.** `query` opens the database read-only. Do not add a write path to it.
4. **Safe identifiers.** Table and column names are generated from `naming.py`. Do not put raw user text into SQL identifiers.
5. **Stable CLI.** Keep `convert`, `describe`, and `query`, their flags, and the exit codes (0 success, 1 failure, 2 unsupported input).
6. **Stored scripts run only through `safe.run`.** Never call `exec` on a script from the database directly, and widen `safe.py`'s allow-list only with a test that shows why it is needed.
7. **Formulas become Python scripts.** Only translate what `formula.py` supports. Anything else must be recorded with a reason in `note`, never guessed. Generated scripts must compile and must only import from `ai_xl2db.runtime`.

## Layout

```
src/ai_xl2db/
  cli.py      commands and exit codes
  reader.py   .xlsx and .csv reading, header detection, formula capture
  infer.py    column types and value conversion
  naming.py   safe table and column names
  formula.py  Excel formula -> Python expression (supported subset only)
  runtime.py  functions the generated scripts call, and load_sheet()
  store.py    writing, describing, and querying the SQLite file
  safe.py     validates a stored script before it runs; the only place scripts are executed
  check.py    recalculates translated formulas and compares them with stored values
tests/        pytest suite; conftest.py builds a messy workbook for the tests
```

## Setup and checks

```bash
python3 -m venv ~/.venvs/ai-xl2db-dev
~/.venvs/ai-xl2db-dev/bin/pip install -e ".[dev]"
~/.venvs/ai-xl2db-dev/bin/python -m pytest -q
```

Tests must create their own workbooks. Do not commit real spreadsheets.

## Rules for changes

- One change per pull request, with a test for each behaviour change.
- Check any new header-detection or type rule against the messy fixture in `tests/conftest.py`.
- Keep the Python floor at 3.10. The only runtime dependency is `openpyxl`; do not add others without discussion.

## Security

Do not report vulnerabilities in a public issue. Use a private security advisory on GitHub.
