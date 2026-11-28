# Ragforge: five-minute first run

## Problem statement

How might we let an experienced RAG developer go from finding the repo to getting a cited answer over their own docs in under 5 minutes, with no Docker and no API key, so they try and star it?

## Recommended direction

Add a `ragforge ask <path> "<question>"` command in embedded mode:

- Indexing uses Qdrant local mode (stored under `.ragforge/`) and a small CPU sentence-transformers model, through the same embedder and retriever interfaces as the production stack.
- Without an LLM it prints ranked passages with file and line citations. When an OpenAI-compatible endpoint is set in the environment, it also writes a short cited answer.

This becomes the exit of a new **Task 0**, the first thing in Phase 1 to ship. The production stack (Tasks 2a through 5) follows unchanged, and the README shows embedded mode first and links straight to the production stack. All contributor recruiting stops until this exists.

The bet: experienced developers decide from the README and one terminal run. A repo they can try in 5 minutes is worth more than a better architecture they can't try.

### Directions considered

- **A. Embedded mode (chosen).** No server, no Docker, runs from a clone with `uv run`.
- **B. One-command Docker demo.** This is Checkpoint 1 as planned. Pulling 4 images and an Ollama model takes 10 minutes or more, and every RAG repo has a docker-compose file. It stays as the production path, not the headline.
- **C. A torch-free path so `uvx` works from PyPI.** ONNX embeddings (for example fastembed). It breaks the sentence-transformers and CPU-torch decision and adds a second embedding backend. Revisit it once A shows people want it.

## Key assumptions to validate

- [ ] **Cold start fits in 5 minutes.** Time a fresh `git clone && uv sync && uv run ragforge ask ./docs "…"` on a clean machine. torch CPU plus a MiniLM-class model is about 300 MB. If it doesn't fit, look at C.
- [ ] **Retrieval-only output is useful without an LLM.** Run it over this repo's own docs and check that the top 3 passages answer 5 realistic questions.
- [ ] **The demo drives stars.** Post it once (Show HN, r/LocalLLaMA or similar) with an asciinema/GIF in the README. Track stars and clones in the 2 weeks after.
- [ ] **Embedded mode doesn't split the codebase.** Under 150 lines of code specific to embedded mode, with everything else shared with the production pipeline.

## MVP scope

**In:**

- `ragforge ask` and `ragforge index`.
- Markdown and plain text only, chunked with a fixed-size splitter.
- Dense retrieval only.
- Citations as `path:line`.
- An optional OpenAI-compatible LLM, configured through pydantic-settings.
- A README section at the top, with a terminal GIF.
- One smoke test that uses a tiny fixture corpus and a mocked embedder.

**Out:**

- PDF and HTML.
- Hybrid search and reranking.
- The server and API.
- Persistence beyond the local Qdrant directory.
- Auth and multi-user support.

## Not doing (and why)

- **Contributor recruiting, community building, more issues:** adoption comes first. The current setup is enough.
- **Publishing to PyPI or `uvx`:** `[tool.uv.sources]` is ignored in published packages, so installs would pull the default CUDA torch build, which is several GB. Revisit after the demo works.
- **Docker demo as the headline:** it's slow to start and doesn't stand out. It stays as the production path.
- **Hybrid, reranking and eval in the demo:** they belong to Phases 3 and 6. Adding them makes the demo slow and complicated.
- **A hosted demo:** it doesn't fit 2 hours a week of maintainer time.

## Open questions

- Which default model? `all-MiniLM-L6-v2` (fast, older) or `bge-small-en-v1.5` (better, similar size)?
- ~~Does Task 0 come before Task 1a, or reuse 1a's config layer?~~ Resolved (2026-11-28): Task 0 comes first with a minimal env-only `Settings`, and Task 1a layers YAML onto it. See Tasks 0a and 0b in `tasks/todo.md`.
- Is a published blog post or HN post part of the plan, or just the README?

## Context

- Decided on 2026-11-27 in an idea-refine session.
- Goal: real adoption, measured in users and stars after 3 months.
- Target: experienced RAG developers.
- Maintainer time: under 2 hours a week.
