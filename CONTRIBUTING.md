# Contributing to RagForge

Thanks for your interest in contributing! RagForge is built step by step, and contributions of all sizes are welcome: bug reports, docs fixes, tests, and features.

## Ground rules

- Be respectful. This project follows the [Code of Conduct](CODE_OF_CONDUCT.md).
- For anything bigger than a small fix, **open an issue first** so we can agree on the approach before you write code.
- Keep pull requests focused: one logical change per PR.

## Development setup

Requirements: [uv](https://docs.astral.sh/uv/getting-started/installation/), and for end-to-end runs, [Ollama](https://ollama.com) running locally. uv installs the right Python version for you (see `.python-version`).

```bash
git clone https://github.com/<your-username>/ragforge.git
cd ragforge
uv sync                          # creates .venv and installs the project + dev tools
cp .env.example .env             # adjust settings if needed
```

### Managing dependencies

- Add a runtime dependency: `uv add <package>`
- Add a dev-only dependency: `uv add --dev <package>`
- Commit both `pyproject.toml` and `uv.lock` together. Never edit `uv.lock` by hand.

## Before you open a PR

Run the same checks CI runs:

```bash
uv run ruff check .
uv run ruff format --check .
uv run pytest
```

`uv run ruff format .` and `uv run ruff check --fix .` will fix most style issues automatically.

## Making changes

1. Fork the repo and create a branch from `main`:
   `git checkout -b feat/short-description`
2. Make your change and add or update tests in `tests/`.
3. Update `README.md` or docstrings if behaviour changes.
4. Commit using [Conventional Commits](https://www.conventionalcommits.org/) style, e.g.
   - `feat(ingestion): add HTML loader`
   - `fix(loaders): skip empty PDF pages`
   - `docs: clarify Ollama setup`
5. Push and open a pull request against `main`, filling in the PR template.

## Code style

- Formatting and linting: [ruff](https://docs.astral.sh/ruff/) (config in `pyproject.toml`, line length 100).
- Type hints on public functions.
- Configuration goes through `ragforge.config.Settings` (env vars prefixed `RAG_`), not hard-coded values.
- Keep heavy imports (e.g. `pypdf`, `docx`, model libraries) lazy where practical so the CLI stays fast.

## Reporting bugs and requesting features

Use the [issue templates](https://github.com/KrushanPatel/ragforge/issues/new/choose). For security issues, **do not open a public issue**. See [SECURITY.md](SECURITY.md).

## License

By contributing, you agree that your contributions will be licensed under the [MIT License](LICENSE).
