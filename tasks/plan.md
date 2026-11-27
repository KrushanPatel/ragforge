# Implementation Plan: Ragforge (production RAG)

Source spec: `README.md` (Ragforge — Production-Grade Retrieval-Augmented Generation). On 2026-11-27 this replaced the earlier CLI-only ragforge v1 plan, at the user's direction.

## Overview

A production RAG system with these parts:
- **Async ingestion:** connectors → queue → parse/clean/dedup → chunk → embed → index.
- **A stateless FastAPI query service:** guardrails → rewrite → hybrid retrieval → rerank → context build → LLM gateway → output checks.
- **Built in from the start:** ACL enforcement, caching, evaluation gates, OpenTelemetry/Prometheus observability, and Docker/Helm/Terraform deployment.

The work is sliced vertically. Phase 1 delivers a thin but real path from ingestion to the `/v1/query` endpoint to evaluation, and each later phase deepens one part of that path while keeping the system working and measured.

## Architecture Decisions

These resolve the swappable choices in the README's component table. Each one needs human review; see Open Questions.

- **Stack reconciliation.** The README supersedes CLAUDE.md's "Typer CLI, Qdrant, sentence-transformers" project line. Task 1 updates CLAUDE.md and `pyproject.toml` to match. **uv stays the package manager** and `make` targets wrap `uv run …`, which satisfies both the README's `make` interface and the CLAUDE.md uv rule.
- **Package name and layout.** The README's `ragforge/` module layout (`connectors/`, `parsing/`, `chunking/`, …) lives under `src/ragforge/` so the uv build backend and the existing repo keep working. Apps go in `apps/api`, `apps/ingestion` and `apps/admin`. The project and package name is **Ragforge** (`ragforge`), decided by the user on 2026-11-27.
- **Vector store: Qdrant.** It's a README-listed option and already set up in this repo (`/qdrant-up`). Blue/green re-indexing uses Qdrant collection aliases.
- **Keyword index: OpenSearch (BM25).** The README's `make up` includes it.
- **Document store, metadata and ACLs: Postgres,** with Alembic migrations. pgvector isn't needed because Qdrant holds the vectors.
- **Queue: Redis Streams in dev** behind a `Queue` interface, with a Kafka adapter later. This saves running Kafka locally, and the README lists Redis Streams as an option.
- **Embeddings.** A provider interface with a `sentence_transformers` adapter (local, CPU-only torch per CLAUDE.md) as the dev default, plus an `openai_compatible` adapter for hosted or TEI endpoints. The model name and version are recorded on every vector.
- **LLM gateway.** A provider abstraction over OpenAI-compatible chat APIs. The **dev default is Ollama's OpenAI-compatible endpoint**, following the user's earlier choice. It handles routing, retries, fallback models and token accounting, and is built in-house rather than on LiteLLM, so there's no extra dependency until one is needed.
- **Reranker.** A sentence-transformers `CrossEncoder` adapter, with a hosted rerank adapter possible later.
- **Config.** Layered `configs/base.yaml` → `configs/<env>.yaml` → env vars, loaded through pydantic-settings using a YAML settings source. Secrets come only from env vars.
- **Auth.** OIDC JWT validation. In dev, a local signing key issues `DEV_TOKEN`.
- **Tooling additions** (via `uv add`): fastapi, uvicorn, sqlalchemy, alembic, psycopg, redis, opensearch-py, opentelemetry-*, prometheus-client, pyyaml, tiktoken (or the model tokenizer), and datasketch (MinHash). Dev tools: mypy, testcontainers, respx, plus k6 for load testing (outside Python). Each task adds only what it needs.

## Dependency Graph

```
Task 1 config/layout/Makefile ── Task 2 compose infra + FastAPI skeleton
        │
        ├── Task 3 sync ingest (parse→chunk→embed→Qdrant+Postgres)
        │       └── Task 4 /v1/query (dense retrieve + LLM gateway + citations)
        │               └── Task 5 eval harness v0 (golden set, recall@k, make eval)
        │
        ├── Ingestion: 6 parsers → 7 structure-aware chunking → 8 versioning/deletes
        │               → 9 async queue+worker → 10 clean/dedup/PII
        ├── Retrieval: 11 BM25+RRF → 12 rerank+threshold → 13 query rewrite → 14 context builder
        ├── Generation: 15 versioned prompts → 16 SSE → 17 citation validation → 18 gateway resilience
        ├── Security: 19 OIDC+rate limit → 20 ACL/tenant filters → 21 guardrails → 22 cache (needs 20)
        ├── Quality/Obs: 23 OTel tracing → 24 metrics+dashboards → 25 eval gates+judge → 26 feedback
        ├── Deploy: 27 images → 28 CI pipeline (needs 25) → 29 Helm → 30 Terraform → 31 load tests+runbooks
        └── Connectors/Admin: 32 S3 → 33 Confluence → 34 SharePoint → 35 Google Drive → 36 DB → 37 admin UI
```

Phases 2 and 3 depend only on Phase 1 and can run in parallel. Task 22 (cache) must follow Task 20 (ACLs), because caches have to be keyed by permission set.

## Task List

Full task details (acceptance criteria, verification, files) are in `tasks/todo.md`.

### Phase 1: Foundation + thin end-to-end slice
- [ ] Task 1: Project restructure, layered config, Makefile, CLAUDE.md update
- [ ] Task 2: Local infrastructure (docker-compose) + API skeleton with health probes
- [ ] Task 3: Synchronous ingest of Markdown into Qdrant + Postgres
- [ ] Task 4: `POST /v1/query`: dense retrieval + LLM gateway + cited answer
- [ ] Task 5: Evaluation harness v0 (golden set, Recall@k/MRR, `make eval`)

### Checkpoint 1: `make up` → `make ingest` → `curl /v1/query` → `make eval` works end to end

### Phase 2: Production ingestion
- [ ] Task 6: Layout-aware parsers (PDF, DOCX, HTML; tables as Markdown)
- [ ] Task 7: Structure-aware, token-based chunking with heading paths
- [ ] Task 8: Document versioning, deterministic IDs, update/delete propagation
- [ ] Task 9: Async ingestion: queue + worker + `/v1/documents` endpoints
- [ ] Task 10: Cleaning, near-duplicate detection, PII redaction at ingest

### Checkpoint 2: incremental ingest via the API; eval shows no regression

### Phase 3: Retrieval quality
- [ ] Task 11: BM25 via OpenSearch + hybrid retrieval with RRF
- [ ] Task 12: Cross-encoder reranking + relevance threshold ("not found")
- [ ] Task 13: Query understanding: condensation, multi-query, HyDE
- [ ] Task 14: Context builder: token budget, ordering, MMR, source IDs

### Checkpoint 3: eval report shows the gain from hybrid + rerank over dense-only

### Phase 4: Generation hardening
- [ ] Task 15: Versioned YAML prompts, with the version recorded per request
- [ ] Task 16: SSE streaming for `/v1/query`
- [ ] Task 17: Citation validation + optional groundedness check
- [ ] Task 18: Gateway resilience: timeouts, retries, circuit breaker, fallback, routing, budgets

### Checkpoint 4: streaming, validated citations; provider-outage fallback demonstrated

### Phase 5: Security
- [ ] Task 19: OIDC authentication + per-tenant rate limiting
- [ ] Task 20: Document ACLs + tenant isolation enforced inside retrieval
- [ ] Task 21: Guardrails: prompt-injection detection, untrusted-context wrapping, output moderation
- [ ] Task 22: Exact + semantic cache keyed by permission set, with invalidation

### Checkpoint 5: ACL leakage suite passes for every role, including via cache

### Phase 6: Observability + evaluation maturity
- [ ] Task 23: OpenTelemetry tracing + structured logging
- [ ] Task 24: Prometheus metrics + Grafana dashboards as code
- [ ] Task 25: Full eval suite: adversarial set, LLM-as-judge, CI regression gates
- [ ] Task 26: `/v1/feedback` linked to traces

### Checkpoint 6: one trace shows every pipeline span; `make eval` enforces gates.yaml

### Phase 7: Deployment
- [ ] Task 27: Production Docker images (multi-stage, non-root, scanned)
- [ ] Task 28: CI pipeline (lint, type-check, tests, integration, eval gates, security scans)
- [ ] Task 29: Helm chart (HPA, KEDA, PDBs, probes, NetworkPolicies)
- [ ] Task 30: Terraform infrastructure
- [ ] Task 31: Load tests (k6) + runbooks + blue/green reindex commands

### Checkpoint 7: staging deploy via CI; load test at 2× target peak passes

### Phase 8: Connectors + admin
- [ ] Task 32: S3 connector
- [ ] Task 33: Confluence connector
- [ ] Task 34: SharePoint connector
- [ ] Task 35: Google Drive connector
- [ ] Task 36: Database connector
- [ ] Task 37: Admin UI (index management + feedback review)

### Checkpoint 8: Production Readiness Checklist (README) reviewed item by item

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Scope is very large (37 tasks) and later phases drift from early decisions | High | Checkpoint reviews after every phase; ADRs in `docs/adr/` for each Architecture Decision above |
| Running many services locally (Qdrant, Postgres, OpenSearch, Redis, Jaeger, Grafana) is heavy on the dev machine | Med | Compose profiles (`core` and `obs`); unit tests use fakes; testcontainers only in integration tests |
| ACL leaks through cache or reranker | High | Single retrieval chokepoint (Task 20) built before the cache (Task 22); leakage suite per role in CI |
| Eval gates are meaningless with a tiny golden set | High | Start with ~30 hand-written triples in Task 5 and grow toward 200+ before gates are enforced in Task 25; the human reviews the dataset |
| Local CPU models (Ollama, cross-encoder) are slow, so latency SLOs look bad in dev | Med | Latency gates apply only in staging; dev evals measure quality only |
| Stack change conflicts with CLAUDE.md and the `/qdrant-up` skill | Med | Task 1 updates CLAUDE.md; Qdrant is kept so the skill stays valid |
| Embedding model change needs a full re-index | Med | Qdrant aliases for blue/green (Task 31); model and version stored on every point (Task 3) |
| Connector APIs (Confluence, SharePoint, Drive) need credentials and test tenants | Med | Contract tests against recorded responses (VCR/respx); live tests are opt-in |

## Open Questions

1. ~~**Package name.**~~ Resolved: **Ragforge** (`ragforge`).
2. **Cloud for Terraform and Helm values:** AWS, GCP or Azure? This blocks Task 30 and the managed-service choices (SQS vs Kafka, secrets manager).
3. **Queue in production:** Kafka (README default) or a managed alternative? Dev uses Redis Streams either way.
4. **LLM in staging/prod:** hosted provider or self-hosted? Dev uses Ollama, as you chose earlier.
5. **Golden dataset:** which documents and domain? The README examples are billing/refund policies. Who reviews the Q&A triples?
6. **Git workflow:** the README says feature branch + PR with code-owner approval, but your saved preference is to commit to `main`. Which applies here?
7. **Admin UI stack** (Task 37): server-rendered FastAPI templates or a separate frontend?
