# RagForge

[![CI](https://github.com/KrushanPatel/ragforge/actions/workflows/ci.yml/badge.svg)](https://github.com/KrushanPatel/ragforge/actions/workflows/ci.yml)
[![License: MIT](https://img.shields.io/badge/License-MIT-blue.svg)](LICENSE)

Production-grade RAG, built step by step. Fully self-hosted (Ollama + Qdrant + sentence-transformers).

> **Status:** early development (phase 1: core ingestion pipeline). APIs will change.

## Quick start

```bash
git clone https://github.com/KrushanPatel/ragforge.git
cd ragforge
python -m venv .venv && source .venv/bin/activate
pip install -e ".[dev]"
cp .env.example .env
```

You'll need [Ollama](https://ollama.com) running locally with the configured model (`ollama pull llama3.1:8b`).

## Configuration

All settings can be overridden through environment variables or `.env` using the `RAG_` prefix. See [`.env.example`](.env.example) and `src/ragforge/config.py`.

## Contributing

Contributions are welcome! Please read [CONTRIBUTING.md](CONTRIBUTING.md) and our [Code of Conduct](CODE_OF_CONDUCT.md). To report a security issue, see [SECURITY.md](SECURITY.md).

## License

[MIT](LICENSE)
