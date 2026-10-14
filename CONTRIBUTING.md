# Contributing to ai-xl2db

Humans and AI agents are both welcome. The detailed rules for agents are in [AGENTS.md](AGENTS.md).

- Keep every value. Dropping blank rows is fine; losing data is not.
- Keep queries read-only, and keep the database types strict.
- Add a test for each change. Build any spreadsheet in the test itself, and do not commit real data.

```bash
python3 -m venv ~/.venvs/ai-xl2db-dev
~/.venvs/ai-xl2db-dev/bin/pip install -e ".[dev]"
~/.venvs/ai-xl2db-dev/bin/python -m pytest -q
```

Describe what changed, why, and which tests you ran. If an AI agent helped, say so and name the tool and model.

By contributing, you agree that your contribution is released under the MIT licence in [LICENSE](LICENSE).
