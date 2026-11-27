# Contributing to Ragforge

Thanks for helping out. This guide covers everything you need to land your first pull request. If anything here is unclear, that's a bug: open an issue or ask in [Discussions](https://github.com/KrushanPatel/ragforge/discussions).

By taking part, you agree to follow our [Code of Conduct](CODE_OF_CONDUCT.md).

## Contents

- [Where things stand](#where-things-stand)
- [Finding something to work on](#finding-something-to-work-on)
- [Development environment](#development-environment)
- [Running checks locally](#running-checks-locally)
- [Project conventions](#project-conventions)
- [Branch naming](#branch-naming)
- [Commit messages](#commit-messages)
- [Signing off your commits (DCO)](#signing-off-your-commits-dco)
- [Pull request process](#pull-request-process)
- [Reporting bugs and security issues](#reporting-bugs-and-security-issues)

## Where things stand

Ragforge is at an early stage. The package skeleton, tooling and design docs exist, and the pipeline itself is being built task by task:

- [`docs/PRD.md`](docs/PRD.md): what we're building (requirements and design).
- [`tasks/plan.md`](tasks/plan.md): the phased implementation plan and the architecture decisions behind it.
- [`tasks/todo.md`](tasks/todo.md): each task with its acceptance criteria and the files it's likely to touch.

Much of the README describes the **planned** interface (Make targets, the API, deployment), and those sections are labelled as planned. The commands in this guide are the ones that work today.

## Finding something to work on

- **[`good first issue`](https://github.com/KrushanPatel/ragforge/labels/good%20first%20issue)**: small and self-contained, with enough context to start without asking anyone.
- **[`help wanted`](https://github.com/KrushanPatel/ragforge/labels/help%20wanted)**: bigger tasks where help is welcome.
- Tasks in [`tasks/todo.md`](tasks/todo.md) that don't have an issue yet. Open an issue first so nobody duplicates the work.

Before you start, leave a comment on the issue so it can be assigned to you. For anything bigger than a small fix, agree on the approach in the issue before you write code. It saves a rewrite.

## Development environment

### Prerequisites

- **Python 3.12 or newer.** `uv` can install it for you.
- **[uv](https://docs.astral.sh/uv/getting-started/installation/)**, which manages the virtualenv, dependencies and builds.
- Git.

### Setup

```bash
git clone https://github.com/KrushanPatel/ragforge.git   # or your fork
cd ragforge
uv sync              # creates .venv and installs runtime + dev dependencies from uv.lock
uv run ragforge      # smoke check: prints "Hello from ragforge!"
```

The first `uv sync` downloads PyTorch, which is large. On Linux and Windows the CPU-only wheels are used (see `[tool.uv.sources]` in `pyproject.toml`), so you don't need a GPU.

## Running checks locally

CI runs these same commands. Run them before you push:

```bash
uv run ruff check            # lint
uv run ruff format --check   # formatting
uv run pytest -q             # tests
uv build                     # build the sdist and wheel into dist/
```

To fix lint and formatting problems automatically:

```bash
uv run ruff check --fix && uv run ruff format
```

Ruff's configuration lives in `pyproject.toml` and is the final word on style. The repo also ships an `.editorconfig`, so most editors pick up the indentation and line-ending rules automatically.

## Project conventions

- **Use uv for everything.** Add dependencies with `uv add <pkg>` (or `uv add --dev <pkg>`), and commit `pyproject.toml` and `uv.lock` together. Never `pip install`, and never edit `uv.lock` by hand.
- **Keep torch CPU-only.** Don't add CUDA wheels or change the PyTorch index.
- **No hardcoded configuration.** URLs, hosts, ports, model names and keys go through pydantic-settings, loaded from the environment or `.env`. Never commit `.env` or any secret.
- **Tests come with changes.** New behaviour ships with pytest tests, and bug fixes ship with a regression test. Unit tests must run without external services, so mock Qdrant and the embedding model or put them behind fixtures.
- **Use type hints** on public functions, in modern syntax (`list[str]`, `X | None`).

## Branch naming

Branch from `main` and name the branch `<type>/<short-description>`, using the same types as commit messages:

```
feat/hybrid-retrieval
fix/pdf-empty-page-crash
docs/contributing-typos
test/config-override-order
chore/bump-ruff
```

If you're working from a fork, the same convention applies there.

## Commit messages

We use [Conventional Commits](https://www.conventionalcommits.org/en/v1.0.0/):

```
<type>(<optional scope>): <summary in the imperative, lowercase, no period>
```

Types: `feat`, `fix`, `docs`, `test`, `refactor`, `perf`, `chore`, `ci`, `build`. Real examples from this repo's history:

```
docs: move design spec from README into docs/PRD.md
chore: add CLAUDE.md, Claude Code skills, and ruff config
```

For a breaking change, add `!` after the type (`feat!: ...`) and a `BREAKING CHANGE:` footer.

## Signing off your commits (DCO)

We use the [Developer Certificate of Origin](https://developercertificate.org/) (DCO). Every commit must carry a `Signed-off-by` line. It certifies that you wrote the change, or otherwise have the right to submit it under the project's [Apache-2.0 license](LICENSE).

Add the line with `-s`:

```bash
git commit -s -m "fix: handle empty PDF pages"
```

It uses your `user.name` and `user.email` from git config. If you forgot to sign off:

```bash
git commit --amend -s --no-edit          # last commit only
git rebase --signoff main                # every commit on your branch
git push --force-with-lease              # update your PR branch
```

A DCO check runs on every pull request and fails if any commit is missing a sign-off. There is no CLA.

## Pull request process

1. Fork the repo (or branch, if you have write access) and create a branch as described above.
2. Make your change, with tests and doc updates.
3. Run the [checks](#running-checks-locally) locally.
4. Open a pull request against `main`. The template asks for a summary, the linked issue (`Closes #123`), the type of change and how you tested it.
5. CI must pass: `lint`, `test (3.12)`, `test (3.13)`, `build` and `dco`. If this is your first contribution, a maintainer has to approve the workflow run before CI starts.
6. Every PR needs **one approving review** from a code owner (see [`.github/CODEOWNERS`](.github/CODEOWNERS)), and every review conversation must be resolved before merge.

What to expect from review:

- A first response within **3 business days**.
- Feedback on correctness, tests, readability and fit with the plan. Small, focused PRs get reviewed fastest; split large changes where you can.
- Reply by pushing new commits rather than force-pushing, which keeps the review history easy to follow. The maintainer squash-merges, so the PR title becomes the commit message on `main`. Write it as a Conventional Commit.
- A PR with no activity for 30 days is marked stale, and closed 14 days later unless someone updates it. You're always welcome to reopen it.

## Reporting bugs and security issues

- **Bugs and feature ideas:** use the [issue forms](https://github.com/KrushanPatel/ragforge/issues/new/choose).
- **Questions:** use [Discussions → Q&A](https://github.com/KrushanPatel/ragforge/discussions/categories/q-a).
- **Security vulnerabilities:** never open a public issue. Follow [SECURITY.md](SECURITY.md).
