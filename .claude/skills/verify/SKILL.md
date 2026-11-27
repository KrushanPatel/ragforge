---
name: verify
description: Run ragforge's lint, format check, and test suite to verify changes. Use after editing Python code and before declaring a task done or committing.
---

Run all checks in one Bash call from the repo root. Use `;` so every check runs even if an earlier one fails:

```bash
uv run ruff check; uv run ruff format --check; uv run pytest -q
```

Report a pass/fail line for each check. If pytest exits with code 5 (no tests collected), report "no tests yet", not a failure. For failures, show the relevant output and propose fixes. Don't apply fixes unless asked.
