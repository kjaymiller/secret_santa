# AGENTS.md

## Commands (via `just`)
- `just test <path>`: Run specific test (e.g., `just test tests/test_file.py`)
- `just test`: Run all tests (uses `pytest --nomigrations --reuse-db`)
- `just lint`: Run pre-commit hooks (ruff, blacken-docs, etc.)
- `just manage <cmd>`: Run Django commands (e.g., `makemigrations`, `migrate`)
- `just run <cmd>`: Run arbitrary commands in utility container

## Code Style & Standards
- **Stack:** Python 3.13+, Django 5.x.
- **Formatting:** Line length 120 chars. Use `ruff` for linting/formatting.
- **Imports:** Standard lib -> Third-party -> Local.
- **Models:** Use `uuid.uuid4()` for PKs. Define `related_name` and `Meta.ordering`.
- **Testing:** Use `pytest`. Fixtures in `conftest.py` override settings.
- **Conventions:** Follow existing patterns (e.g., `djade` for templates).
- **Environment:** All commands run in Docker. Do not run `pip`/`python` directly.
