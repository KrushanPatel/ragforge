# Implementation Plan: Ragforge (production RAG)

Source spec: `docs/PRD.md` (requirements and design) and `README.md` (overview, layout, config, API, deployment). On 2026-11-27 this replaced the earlier CLI-only ragforge v1 plan, at the user's direction.

## Overview

A production RAG system with these parts:
- **Async ingestion:** connectors → queue → parse/clean/dedup → chunk → embed → index.
- **A stateless FastAPI query service:** guardrails → rewrite → hybrid retrieval → rerank → context build → LLM gateway → output checks.
- **Built in from the start:** ACL enforcement, caching, evaluation gates, OpenTelemetry/Prometheus observability, and Docker/Helm/Terraform deployment.

The work is sliced vertically. Phase 1 delivers a thin but real path from ingestion to the `/v1/query` endpoint to evaluation, and each later phase deepens one part of that path while keeping the system working and measured.

## Architecture Decisions

These resolve the swappable choices in the PRD's component table. Each one needs human review; see Open Questions.

- **Stack reconciliation.** The README supersedes CLAUDE.md's "Typer CLI, Qdrant, sentence-transformers" project line. Task 1 updates CLAUDE.md and `pyproject.toml` to match. **uv stays the package manager** and `make` targets wrap `uv run …`, which satisfies both the README's `make` interface and the CLAUDE.md uv rule.
- **Package name and layout.** The README's `ragforge/` module layout (`connectors/`, `parsing/`, `chunking/`, …) lives under `src/ragforge/` so the uv build backend and the existing repo keep working. Apps go in `apps/api`, `apps/ingestion` and `apps/admin`. The project and package name is **Ragforge** (`ragforge`), decided by the user on 2026-11-27.
- **Vector store: Qdrant.** It's a PRD-listed option and already set up in this repo (`/qdrant-up`). Blue/green re-indexing uses Qdrant collection aliases.
- **Keyword index: OpenSearch (BM25).** The README's `make up` includes it.
- **Document store, metadata and ACLs: Postgres,** with Alembic migrations. pgvector isn't needed because Qdrant holds the vectors.
- **Queue: Redis Streams in dev** behind a `Queue` interface, with a Kafka adapter later. This saves running Kafka locally, and the PRD lists Redis Streams as an option.
- **Embeddings.** A provider interface with a `sentence_transformers` adapter (local, CPU-only torch per CLAUDE.md) as the dev default, plus an `openai_compatible` adapter for hosted or TEI endpoints. The model name and version are recorded on every vector.
- **LLM gateway.** A provider abstraction over OpenAI-compatible chat APIs. The **dev default is Ollama's OpenAI-compatible endpoint**, following the user's earlier choice. It handles routing, retries, fallback models and token accounting, and is built in-house rather than on LiteLLM, so there's no extra dependency until one is needed.
- **Reranker.** A sentence-transformers `CrossEncoder` adapter, with a hosted rerank adapter possible later.
- **Config.** Layered `configs/base.yaml` → `configs/<env>.yaml` → env vars, loaded through pydantic-settings using a YAML settings source. Secrets come only from env vars.
- **Auth.** OIDC JWT validation. In dev, a local signing key issues `DEV_TOKEN`.
- **Tooling additions** (via `uv add`): fastapi, uvicorn, sqlalchemy, alembic, psycopg, redis, opensearch-py, opentelemetry-*, prometheus-client, pyyaml, tiktoken (or the model tokenizer), and datasketch (MinHash). Dev tools: mypy, testcontainers, respx, plus k6 for load testing (outside Python). Each task adds only what it needs.

## Dependency Graph

```
Task 1a layout/config → 1b tooling/CLAUDE.md → 2a compose+schema → 2b API skeleton
        │
        ├── Task 3 sync ingest (parse→chunk→embed→Qdrant+Postgres)
        │       └── Task 4 /v1/query (dense retrieve + LLM gateway + citations)
        │               └── Task 5 eval harness v0 (golden set, recall@k, make eval) ⟵ gate: PRD Product Context (data/domain)
        │
        ├── Ingestion: 6 parsers → 7 structure-aware chunking → 8 versioning/deletes
        │               → 9 async queue+worker → 10 clean/dedup/PII
        ├── Retrieval: 11 BM25+RRF → 12 rerank+threshold → 13 query rewrite → 14 context builder
        ├── Generation: 15 versioned prompts → 16 SSE → 17 citation validation → 18 gateway resilience
        ├── Security: 19 OIDC+rate limit → 20 ACL/tenant filters → 21 guardrails → 22 cache (needs 20)
        ├── Quality/Obs: 23 OTel tracing → 24 metrics+dashboards → 25 eval gates+judge → 26 feedback
        ├── Deploy: 27 images → 28 CI pipeline (needs 25) → 29 Helm → 30a network/cluster → 30b data services
        │           → 30c secrets/IAM/staging → 31 load tests+runbooks
        └── Connectors/Admin: 32 S3 → 33 Confluence → 34 SharePoint → 35 Google Drive → 36 DB → 37 admin UI
```

Phases 2 and 3 depend only on Phase 1 (Checkpoint 1) and can run in parallel. Task 22 (cache) must follow Task 20 (ACLs), because caches have to be keyed by permission set.

## Task List

Full task details (acceptance criteria, verification, files) are in `tasks/todo.md`.

Split tasks use letter suffixes (1a/1b, 2a/2b, 30a–30c); numbering is otherwise stable. A checkpoint follows every 2–3 tasks.

### Phase 1: Foundation + thin end-to-end slice
- [ ] Task 1a: Layout + layered config
- [ ] Task 1b: Tooling (Makefile, mypy, pre-commit) + CLAUDE.md update
- [ ] Checkpoint 1a: `make lint test` green; CLAUDE.md reviewed
- [ ] Task 2a: Local infrastructure (docker-compose) + Postgres schema
- [ ] Task 2b: API skeleton with health probes
- [ ] Checkpoint 1b: `make up` → `make api` → `/readyz` 200
- [ ] Task 3: Synchronous ingest of Markdown into Qdrant + Postgres
- [ ] Task 4: `POST /v1/query`: dense retrieval + LLM gateway + cited answer
- [ ] Task 5: Evaluation harness v0 (golden set, Recall@k/MRR, `make eval`). Gate: PRD Product Context *Data and domain*, else a provisional set over `samples/docs`
- [ ] **Checkpoint 1:** `make up` → `make ingest` → `curl /v1/query` → `make eval` works end to end

### Phase 2: Production ingestion
- [ ] Task 6: Layout-aware parsers (PDF, DOCX, HTML; tables as Markdown)
- [ ] Task 7: Structure-aware, token-based chunking with heading paths
- [ ] Task 8: Document versioning, deterministic IDs, update/delete propagation
- [ ] Checkpoint 2a: re-ingest is idempotent
- [ ] Task 9: Async ingestion: queue + worker + `/v1/documents` endpoints
- [ ] Task 10: Cleaning, near-duplicate detection, PII redaction at ingest
- [ ] **Checkpoint 2:** incremental ingest via the API; eval shows no regression

### Phase 3: Retrieval quality
- [ ] Task 11: BM25 via OpenSearch + hybrid retrieval with RRF
- [ ] Task 12: Cross-encoder reranking + relevance threshold ("not found")
- [ ] Checkpoint 3a: eval shows the hybrid + rerank delta
- [ ] Task 13: Query understanding: condensation, multi-query, HyDE
- [ ] Task 14: Context builder: token budget, ordering, MMR, source IDs
- [ ] **Checkpoint 3:** eval report shows the gain over dense-only

### Phase 4: Generation hardening
- [ ] Task 15: Versioned YAML prompts, with the version recorded per request
- [ ] Task 16: SSE streaming for `/v1/query`
- [ ] Checkpoint 4a: streaming works; prompt version in metadata
- [ ] Task 17: Citation validation + optional groundedness check
- [ ] Task 18: Gateway resilience: timeouts, retries, circuit breaker, fallback, routing, budgets
- [ ] **Checkpoint 4:** validated citations; provider-outage fallback demonstrated

### Phase 5: Security
- [ ] Task 19: OIDC authentication + per-tenant rate limiting
- [ ] Task 20: Document ACLs + tenant isolation enforced inside retrieval
- [ ] Checkpoint 5a: ACL leakage suite green
- [ ] Task 21: Guardrails: prompt-injection detection, untrusted-context wrapping, output moderation
- [ ] Task 22: Exact + semantic cache keyed by permission set, with invalidation
- [ ] **Checkpoint 5:** ACL leakage suite passes for every role, including via cache

### Phase 6: Observability + evaluation maturity
- [ ] Task 23: OpenTelemetry tracing + structured logging
- [ ] Task 24: Prometheus metrics + Grafana dashboards as code
- [ ] Checkpoint 6a: dashboards render; trace shows query spans
- [ ] Task 25: Full eval suite: adversarial set, LLM-as-judge, CI regression gates
- [ ] Task 26: `/v1/feedback` linked to traces
- [ ] **Checkpoint 6:** one trace shows every pipeline span; `make eval` enforces gates.yaml

### Phase 7: Deployment
- [ ] Task 27: Production Docker images (multi-stage, non-root, scanned)
- [ ] Task 28: CI pipeline (lint, type-check, tests, integration, eval gates, security scans)
- [ ] Checkpoint 7a: CI green on a PR
- [ ] Task 29: Helm chart (HPA, KEDA, PDBs, probes, NetworkPolicies)
- [ ] Checkpoint 7b: chart installs on local kind
- [ ] Task 30a: Terraform: network + Kubernetes cluster
- [ ] Task 30b: Terraform: data services (Postgres, Redis, vector store)
- [ ] Task 30c: Terraform: secrets, IAM + staging composition
- [ ] Checkpoint 7c: staging created from scratch
- [ ] Task 31: Load tests (k6) + runbooks + blue/green reindex commands
- [ ] **Checkpoint 7:** staging deploy via CI; load test at 2× target peak passes

### Phase 8: Connectors + admin
- [ ] Task 32: S3 connector
- [ ] Task 33: Confluence connector
- [ ] Task 34: SharePoint connector
- [ ] Checkpoint 8a: three connectors contract-tested
- [ ] Task 35: Google Drive connector
- [ ] Task 36: Database connector
- [ ] Task 37: Admin UI (index management + feedback review)
- [ ] **Checkpoint 8:** Production Readiness Checklist (PRD) reviewed item by item

## Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| Scope is very large (37 tasks) and later phases drift from early decisions | High | Checkpoint reviews after every phase; ADRs in [`docs/adr/`](../docs/adr/) for each Architecture Decision above |
| Running many services locally (Qdrant, Postgres, OpenSearch, Redis, Jaeger, Grafana) is heavy on the dev machine | Med | Compose profiles (`core` and `obs`); unit tests use fakes; testcontainers only in integration tests |
| ACL leaks through cache or reranker | High | Single retrieval chokepoint (Task 20) built before the cache (Task 22); leakage suite per role in CI |
| Eval gates are meaningless with a tiny golden set | High | Start with ~30 hand-written triples in Task 5 and grow toward 200+ before gates are enforced in Task 25; the human reviews the dataset |
| Local CPU models (Ollama, cross-encoder) are slow, so latency SLOs look bad in dev | Med | Latency gates apply only in staging; dev evals measure quality only |
| Stack change conflicts with CLAUDE.md and the `/qdrant-up` skill | Med | Task 1 updates CLAUDE.md; Qdrant is kept so the skill stays valid |
| Embedding model change needs a full re-index | Med | Qdrant aliases for blue/green (Task 31); model and version stored on every point (Task 3) |
| Connector APIs (Confluence, SharePoint, Drive) need credentials and test tenants | Med | Contract tests against recorded responses (VCR/respx); live tests are opt-in |

## Open Questions

1. ~~**Package name.**~~ Resolved: **Ragforge** (`ragforge`).
2. **Cloud for Terraform and Helm values:** AWS, GCP or Azure? This blocks Tasks 30a–30c and the managed-service choices (SQS vs Kafka, secrets manager).
3. **Queue in production:** Kafka (PRD default) or a managed alternative? Dev uses Redis Streams either way.
4. **LLM in staging/prod:** hosted provider or self-hosted? Dev uses Ollama, as you chose earlier.
5. **Golden dataset** (fills `docs/PRD.md` → Product Context → *Data and domain*; gates Task 5): which documents and domain? The spec examples are billing/refund policies. Who reviews the Q&A triples?
6. ~~**Git workflow.**~~ **Resolved (2026-11-27):** feature branch + PR for everyone. Branches are named `<type>/<desc>`, commits are signed off (DCO), and merging needs CI plus a code-owner approval. See `CONTRIBUTING.md`.
7. **Admin UI stack** (Task 37): server-rendered FastAPI templates or a separate frontend?
8. **Rest of the PRD's Product Context:** who the users are, which team owns the system, the success metrics, and the non-goals for the first release.
