# CLAUDE.md

This file provides guidance to Claude Code (claude.ai/code) when working with code in this repository.

## Project
ragforge: a production-grade RAG pipeline (Typer CLI, Qdrant, sentence-transformers), built step by step.

## Tooling
- Use uv for everything: `uv run <cmd>`, `uv add <pkg>`, `uv add --dev <pkg>`. Never use `pip install`, and don't hand-edit `uv.lock`.
- torch comes from the CPU-only PyTorch index (`[tool.uv.sources]` in pyproject.toml). Don't add CUDA wheels.
- Run `/verify` (lint, format check, tests) before finishing a task. Auto-fix: `uv run ruff check --fix && uv run ruff format`.

## Local services & config
- Qdrant runs in Docker at `http://localhost:6333`. The canonical container setup lives in `.claude/skills/qdrant-up/SKILL.md`. If Qdrant is down, ask the user to run `/qdrant-up`.
- Config goes through pydantic-settings from `.env`. Don't hardcode URLs or keys.

## Workflow
- Propose a short plan before implementing each step or feature, and wait for approval before writing code.
- Commits follow Conventional Commits.
