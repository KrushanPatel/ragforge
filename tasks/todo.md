# Ragforge — Task List

Plan: `tasks/plan.md`. Spec: `docs/PRD.md` + `README.md`.

Split tasks use letter suffixes (0a/0b, 1a/1b, 2a/2b, 30a–30c); numbering is otherwise stable.

**Standard verification for every task:** `/verify` (`uv run ruff check; uv run ruff format --check; uv run pytest -q`). Once Task 1b lands, `make lint test` also runs mypy. Following CLAUDE.md, each task starts with a short plan and waits for approval before code is written. Run the code-reviewer agent at each checkpoint.

---

## Phase 0: Five-minute first run (embedded mode)

Source: `docs/ideas/five-minute-first-run.md`. This phase ships first: a developer clones the repo and gets cited passages over their own docs in under 5 minutes, with no Docker and no API key. The production stack (Tasks 1a onward) follows unchanged and reuses the interfaces built here.

### Task 0a: `ragforge index` + `ragforge ask` with retrieval-only output
**Description:** Replace the placeholder `main()` with a Typer app that has two commands. `ragforge index <path>` reads Markdown and plain-text files, splits them with a fixed-size splitter that keeps line numbers, embeds the chunks with a small CPU sentence-transformers model, and stores them in Qdrant local mode under `.ragforge/`. `ragforge ask <path> "<question>"` indexes the path if it isn't indexed yet, then prints the top passages, ranked, each cited as `path:line`. Embedding and search go through an `Embedder` and a `Retriever` interface that the production stack (Tasks 3–4) reuses. Add a minimal pydantic-settings `Settings` (env vars only) for the model name, the index directory and `top_k`. Task 1a layers YAML on top of it later.
**Acceptance criteria:**
- [ ] `uv run ragforge ask ./docs "…"` prints ranked passages with `path:line` citations, and no server, Docker or API key is needed
- [ ] Running `ragforge index` twice on unchanged files doesn't duplicate points, and `.ragforge/` is gitignored
- [ ] Code specific to embedded mode is under 150 lines; everything else sits behind the shared `Embedder`/`Retriever` interfaces
**Verification:** `/verify` (one smoke test: a tiny fixture corpus, a fake embedder and Qdrant local mode in a temp dir); manual check: `uv run ragforge ask ./docs "How is config loaded?"` returns a relevant passage
**Dependencies:** None. Settle Open Question 9 (default model) in this task's plan.
**Files:** `src/ragforge/__init__.py`, `src/ragforge/config.py`, `src/ragforge/{chunking,embeddings,retrieval}/…`, `tests/unit/test_embedded.py` + `tests/fixtures/corpus/`, `.gitignore`
**Scope:** M

### Task 0b: Optional cited LLM answer + README quickstart
**Description:** When an OpenAI-compatible endpoint is set through `Settings` (base URL, model, and an optional key from env), `ragforge ask` also writes a short answer that cites the retrieved passages by `path:line`. Without it, the output stays retrieval-only and says how to turn answers on. Use a thin httpx client, not a full gateway: Task 4's LLM gateway replaces it later. Put an embedded-mode quickstart at the top of the README (clone → `uv sync` → `uv run ragforge ask`), with a terminal GIF or asciinema recording, and link to the production stack below it.
**Acceptance criteria:**
- [ ] With the endpoint set, the answer cites only passages that were retrieved; without it, output is unchanged from 0a
- [ ] A failing or unreachable endpoint prints a one-line error and still shows the passages, with no stack trace
- [ ] The README opens with the embedded quickstart and recording, and the production stack is one link away
**Verification:** `/verify` (client tested with `httpx.MockTransport`, so no new dependency); manual check: run against a local Ollama endpoint, then again with the endpoint unset
**Dependencies:** Task 0a
**Files:** `src/ragforge/generation/llm.py`, `src/ragforge/__init__.py`, `src/ragforge/config.py`, `README.md`, `tests/unit/test_ask_llm.py`
**Scope:** S–M

## Checkpoint 0: After Tasks 0a–0b
- [ ] `/verify` passes
- [ ] **Cold start fits in 5 minutes:** time `git clone && uv sync && uv run ragforge ask ./docs "…"` on a clean machine and record the time here. If it's over 5 minutes, revisit direction C (ONNX embeddings) in the idea doc
- [ ] **Retrieval-only output is useful:** for 5 realistic questions over this repo's docs, the top 3 passages answer each one
- [ ] **No split codebase:** embedded-only code is under 150 lines
- [ ] Human review before the README change goes out. The post-launch check (stars and clones 2 weeks after posting the demo) is tracked in the idea doc, not here

---

## Phase 1: Foundation + thin end-to-end slice

### Task 1a: Layout + layered config
**Description:** Create the README module layout under `src/ragforge/` and the `apps/`, `configs/`, `prompts/`, `evals/`, `deploy/`, `tests/{unit,integration,load}` directories. Extend Task 0a's `Settings` into a layered config: `configs/base.yaml` → `<env>.yaml` → env vars, typed with pydantic-settings, with secrets taken only from env and `RAG_ENV` selecting the environment. Add `.env.example`.
**Acceptance criteria:**
- [ ] `Settings.load()` merges base → env YAML → env vars, and tests prove the override order
- [ ] A secret key in YAML is rejected at load time
- [ ] `.env.example` lists every env var the config reads, with no real values
**Verification:** `/verify`; `RAG_ENV=staging uv run python -c "…Settings.load()"` shows staging values
**Dependencies:** Checkpoint 0 (Task 0b). `ragforge ask` keeps working with no YAML files present
**Files:** `src/ragforge/config.py`, `configs/*.yaml`, `.env.example`, `tests/unit/test_config.py`
**Scope:** S–M

### Task 1b: Tooling (Makefile, mypy, pre-commit) + CLAUDE.md update
**Description:** Add a Makefile whose targets wrap `uv run` (`install`, `lint`, `test`, plus stubs for the rest), mypy configured in `pyproject.toml`, and `.pre-commit-config.yaml`. Update CLAUDE.md: the project line and stack match the Ragforge decisions, it points to `docs/PRD.md` (spec) and `tasks/` (plan), and the uv and CPU-only torch rules are kept.
**Acceptance criteria:**
- [ ] `make install lint test` work; `make lint` runs ruff + mypy
- [ ] `pre-commit run --all-files` passes
- [ ] The CI `lint` job also runs mypy, so type errors block merges
- [ ] CLAUDE.md reflects the new stack, points to `docs/PRD.md` and `tasks/`, and keeps the uv rule
**Verification:** `/verify`; `make lint test` clean
**Dependencies:** Task 1a
**Files:** `Makefile`, `pyproject.toml`, `.pre-commit-config.yaml`, `CLAUDE.md`, `.github/workflows/ci.yml`
**Scope:** S

## Checkpoint 1a: After Tasks 1a–1b
- [ ] `/verify` + `make lint test` pass (ruff + mypy)
- [ ] CLAUDE.md diff reviewed by the human

### Task 2a: Local infrastructure (docker-compose) + Postgres schema
**Description:** Add `docker-compose.yml` with a `core` profile (Qdrant, Postgres, Redis, OpenSearch) and an `obs` profile (Jaeger, Prometheus, Grafana), with `make up`/`make down`. Add the initial Alembic setup for the Postgres document store.
**Acceptance criteria:**
- [ ] `make up` brings up the core services healthy; `make down` stops them without deleting volumes
- [ ] `alembic upgrade head` creates the `documents` and `chunks` metadata tables
- [ ] Service URLs come from config (Task 1a), not hardcoded
**Verification:** `/verify`; manual check: `make up`, `docker compose ps` all healthy, `alembic upgrade head` then `alembic downgrade base` both succeed
**Dependencies:** Task 1b
**Files:** `docker-compose.yml`, `src/ragforge/storage/db.py`, `migrations/`, `Makefile`
**Scope:** M

### Task 2b: API skeleton with health probes
**Description:** Add a FastAPI app in `apps/api` with `/healthz` (liveness) and `/readyz` (pings each configured dependency), plus `make api` (uvicorn with reload).
**Acceptance criteria:**
- [ ] `/healthz` returns 200 whenever the process is up
- [ ] `/readyz` returns 503 naming the failing dependency when one is down, and 200 when all are up
- [ ] `make api` serves the app with OpenAPI docs at `/docs`
**Verification:** `/verify` (readyz tested with fakes); manual check: `make up && make api`, `curl localhost:8000/readyz`, then stop Redis and see a 503
**Dependencies:** Task 2a
**Files:** `apps/api/main.py`, `Makefile`, `tests/unit/test_health.py`
**Scope:** S

## Checkpoint 1b: After Tasks 2a–2b
- [ ] `/verify` + `make lint test` pass
- [ ] `make up` → `make api` → `curl /readyz` returns 200
- [ ] Human review of config layout and compose services before ingest work

### Task 3: Synchronous ingest of Markdown into Qdrant + Postgres
**Description:** Build the first full write path. `make ingest SOURCE=./samples/docs` (a Typer CLI) parses Markdown, runs recursive token chunking, embeds through the provider interface (sentence-transformers adapter), upserts into Qdrant with payload `{doc_id, version, chunk_index, text, source_uri, embed_model, embed_model_version}`, and writes document and chunk metadata to Postgres. Add a `samples/docs` corpus.
**Acceptance criteria:**
- [ ] Ingesting `samples/docs` stores matching chunk counts in Qdrant and Postgres
- [ ] Every Qdrant point records the embedding model name and version; the collection's vector size comes from the model
- [ ] Re-running the ingest creates no duplicates (deterministic IDs: `hash(source_id, version, chunk_index)`)
**Verification:** `/verify` (chunker unit tests; pipeline test with in-memory Qdrant, a fake embedder and SQLite or testcontainers Postgres); manual check: `make up && make ingest SOURCE=./samples/docs`, then compare counts
**Dependencies:** Task 2b
**Files:** `src/ragforge/{parsing,chunking,embeddings,storage}/…`, `apps/ingestion/cli.py`, `samples/docs/`, `tests/unit/…`, `tests/integration/test_ingest.py`
**Scope:** M

### Task 4: `POST /v1/query`: dense retrieval + LLM gateway + cited answer
**Description:** `/v1/query` embeds the query, runs a dense Qdrant search, builds the context with `[doc:ID#chunk:N]` source IDs, calls the LLM gateway (OpenAI-compatible client; dev target is Ollama), and returns the README response shape (`answer`, `citations`, `trace_id`, `usage`, `latency_ms`). Requests and responses are Pydantic-validated. Auth is not added yet (Task 19).
**Acceptance criteria:**
- [ ] The response matches the README schema (contract test) and the OpenAPI docs are served at `/docs`
- [ ] The answer cites sources that exist in the retrieved context
- [ ] An LLM failure returns a structured 502/503, not a stack trace
**Verification:** `/verify` (gateway tested with respx-mocked OpenAI-compatible responses; endpoint tested with fakes); manual check: ingest the samples, then run the README's `curl` against Ollama
**Dependencies:** Task 3
**Files:** `src/ragforge/{retrieval,generation}/…`, `apps/api/routes/query.py`, `apps/api/schemas.py`, `tests/unit/…`
**Scope:** M

### Task 5: Evaluation harness v0 (golden set, Recall@k/MRR, `make eval`)
**Description:** Add `evals/datasets/golden_v1.jsonl` (about 30 question/answer/source triples over `samples/docs`), `evals/metrics/` (Recall@k, MRR, nDCG) and `evals/run_eval.py`, which writes a JSON + Markdown report. Add `make eval DATASET=… [INDEX=…]`. This puts measurement in place before anything is tuned. **Gate:** the golden set should be built over the real first corpus named in `docs/PRD.md` → Product Context → *Data and domain* (Open Question 5). If that is still TBD, build `golden_v1` over `samples/docs`, mark it `provisional: true` in the dataset header, and replace it before Task 25 enforces gates.
**Acceptance criteria:**
- [ ] `make eval` prints Recall@10, MRR and nDCG and writes `evals/reports/<timestamp>.{json,md}`
- [ ] The metric functions have unit tests against hand-computed cases
- [ ] Two reports can be diffed (`run_eval.py --compare A B`)
**Verification:** `/verify`; manual check: `make eval DATASET=evals/datasets/golden_v1.jsonl` gives a baseline report; record the baseline in the plan
**Dependencies:** Task 4; PRD Product Context *Data and domain* filled (Open Question 5), or the provisional fallback above
**Files:** `evals/run_eval.py`, `evals/metrics/*.py`, `evals/datasets/golden_v1.jsonl`, `Makefile`, `tests/unit/test_metrics.py`
**Scope:** M

## Checkpoint 1: After Tasks 1a–5
- [ ] `/verify` + `make lint test` pass
- [ ] `make up` → `make ingest` → `curl /v1/query` → `make eval` works end to end
- [ ] Baseline eval report saved
- [ ] code-reviewer agent run; human review of the Architecture Decisions + Open Questions before Phase 2

---

## Phase 2: Production ingestion

### Task 6: Layout-aware parsers (PDF, DOCX, HTML; tables as Markdown)
**Description:** Add a parser interface returning structured elements (heading, paragraph, list, table, code) with page and section info. Implement PDF (pypdf; OCR fallback behind an optional extra), DOCX (python-docx) and HTML (boilerplate/navigation stripped). Tables are serialized to Markdown.
**Acceptance criteria:**
- [ ] Each format yields headings, lists and tables in document order; tables come out as valid Markdown
- [ ] Scanned PDF pages are detected; without OCR installed they're skipped with a warning, and with it they go through OCR
- [ ] Corrupt or encrypted files fail that document only, with a recorded reason
**Verification:** `/verify` (fixture docs in `tests/fixtures/`); manual check: parse representative real documents and inspect the output
**Dependencies:** Checkpoint 1
**Files:** `src/ragforge/parsing/{base,pdf,docx,html,ocr}.py`, `tests/unit/parsing/`, `tests/fixtures/`
**Scope:** M

### Task 7: Structure-aware, token-based chunking with heading paths
**Description:** Add the `structure_aware` (default), `recursive` and `parent_child` strategies, sized in tokens (`chunk_size_tokens`, `chunk_overlap_tokens`, `min_chunk_tokens`). Prepend the `Title > Section > Subsection` heading path before embedding. Never split tables or code blocks. `semantic` is left as a follow-up.
**Acceptance criteria:**
- [ ] No chunk splits a table row or code block (property-style tests)
- [ ] The heading path is present in the embedded text and in the payload
- [ ] The strategy is selected by config, and the eval report records which one ran
**Verification:** `/verify`; `make eval` comparing structure-aware with recursive, with the report attached to the checkpoint
**Dependencies:** Task 6
**Files:** `src/ragforge/chunking/{structure,recursive,parent_child,tokenize}.py`, `tests/unit/chunking/`
**Scope:** M

### Task 8: Document versioning, deterministic IDs, update/delete propagation
**Description:** Add a document version model in Postgres. An update writes the new version first, then deletes the old one (never a window with zero results). A delete writes a tombstone and propagates to Qdrant and Postgres (OpenSearch and the cache join in later tasks via the same interface). Add a reconciliation command that detects drift between the stores.
**Acceptance criteria:**
- [ ] During an update, a concurrent query always returns either the old or the new version, never neither (test with an interleaved fake)
- [ ] A delete removes the document from every registered store; reconciliation reports zero drift afterwards
- [ ] Re-ingesting an unchanged document is a no-op (content hash)
**Verification:** `/verify` + integration test on testcontainers
**Dependencies:** Task 7
**Files:** `src/ragforge/storage/{versions,stores,reconcile}.py`, `migrations/`, `tests/integration/test_versioning.py`
**Scope:** M

## Checkpoint 2a: After Tasks 6–8
- [ ] `/verify` + `make lint test` pass
- [ ] Re-ingesting an unchanged corpus is a no-op; an edited doc replaces only its chunks
- [ ] Human review before continuing

### Task 9: Async ingestion: queue + worker + `/v1/documents` endpoints
**Description:** Add a `Queue` interface with a Redis Streams adapter. `DocumentEvent{source_id, uri, version, acl, op}`. Add `make worker` (consumer group, retries with backoff, a dead-letter stream) and the endpoints `POST /v1/documents`, `DELETE /v1/documents/{id}` and `GET /v1/documents/{id}/status`.
**Acceptance criteria:**
- [ ] Pushing a document via the API makes it searchable once the worker processes it; status moves queued → processing → indexed or failed
- [ ] A poison message lands in the DLQ after N retries without blocking the stream
- [ ] `make ingest` now publishes events (the sync path is kept behind `--sync` for dev)
**Verification:** `/verify` + an integration test (Redis testcontainer) covering push → index → query → delete
**Dependencies:** Task 8
**Files:** `src/ragforge/queue/{base,redis_streams}.py`, `apps/ingestion/worker.py`, `apps/api/routes/documents.py`, `tests/integration/test_async_ingest.py`
**Scope:** M

### Task 10: Cleaning, near-duplicate detection, PII redaction at ingest
**Description:** The cleaner normalizes whitespace and Unicode, strips repeated headers and footers, and detects language. MinHash near-duplicate detection (threshold from config) drops chunks that are near-duplicates. A pattern-based PII detector (email, phone, card numbers, plus an extension hook) redacts where policy requires.
**Acceptance criteria:**
- [ ] Repeated page headers and footers are removed from parsed PDFs
- [ ] Near-duplicate chunks above the threshold are dropped and counted in the ingest report
- [ ] With `pii_redaction: true`, the seeded PII in the fixtures never reaches Qdrant or Postgres
**Verification:** `/verify`; `make eval` shows no regression from Task 7's report
**Dependencies:** Task 9
**Files:** `src/ragforge/ingestion/{clean,dedup}.py`, `src/ragforge/guardrails/pii.py`, `tests/unit/…`
**Scope:** M

## Checkpoint 2: After Tasks 6–10
- [ ] `/verify` + integration suite pass
- [ ] Mixed-format corpus ingested via the API; update and delete propagate
- [ ] Eval: no regression vs. baseline (report attached)
- [ ] code-reviewer agent run; human review

---

## Phase 3: Retrieval quality

### Task 11: BM25 via OpenSearch + hybrid retrieval with RRF
**Description:** Index chunks into OpenSearch at ingest (joining Task 8's store interface). Add a sparse retriever and a hybrid retriever (dense ∥ sparse, run concurrently), fused with RRF (`rrf_k`). `retrieval.mode` is `dense`, `sparse` or `hybrid`.
**Acceptance criteria:**
- [ ] Exact-term queries (codes, IDs) that dense search misses are found in hybrid mode (adversarial eval items)
- [ ] The RRF implementation matches hand-computed fusion in unit tests
- [ ] Deletes and updates propagate to OpenSearch (the reconciliation check covers it)
**Verification:** `/verify`; `make eval` with dense vs. hybrid in the report
**Dependencies:** Checkpoint 2
**Files:** `src/ragforge/retrieval/{sparse,hybrid,fusion}.py`, `src/ragforge/storage/opensearch.py`, `tests/…`
**Scope:** M

### Task 12: Cross-encoder reranking + relevance threshold ("not found")
**Description:** Add a reranker interface with a sentence-transformers CrossEncoder adapter. Retrieve wide (`dense_top_k`/`sparse_top_k`) and rerank narrow (`top_n`). When nothing clears `min_relevance_score`, return a graceful "not found" answer without calling the LLM.
**Acceptance criteria:**
- [ ] The rerank step is toggled by config and its latency is recorded
- [ ] Unanswerable eval questions return "not found" and the LLM is not called
- [ ] Eval shows the precision change with reranking vs. without
**Verification:** `/verify`; `make eval` (hybrid vs. hybrid + rerank)
**Dependencies:** Task 11
**Files:** `src/ragforge/reranking/{base,cross_encoder}.py`, `src/ragforge/retrieval/pipeline.py`, `tests/…`
**Scope:** S–M

## Checkpoint 3a: After Tasks 11–12
- [ ] `/verify` + `make lint test` pass
- [ ] Eval report shows the hybrid + rerank delta over dense-only
- [ ] Human review before continuing

### Task 13: Query understanding: condensation, multi-query, HyDE
**Description:** Store conversation history by `conversation_id` (Redis). Condense follow-up questions into standalone queries, expand into N paraphrases with results fused, and add HyDE as an option. All of these use the LLM gateway and can be toggled by config.
**Acceptance criteria:**
- [ ] A follow-up ("what about monthly?") with `conversation_id` retrieves the same documents as the equivalent standalone question
- [ ] Multi-query results are deduplicated and fused with RRF
- [ ] Each technique is eval-reported on/off
**Verification:** `/verify` (LLM mocked); `make eval` with a conversational subset added to the golden set
**Dependencies:** Task 12
**Files:** `src/ragforge/retrieval/query_rewrite.py`, `src/ragforge/storage/conversations.py`, `evals/datasets/…`
**Scope:** M

### Task 14: Context builder: token budget, ordering, MMR, source IDs
**Description:** Enforce `max_context_tokens`, truncating by passage and never mid-sentence. Use "lost in the middle" ordering (strongest passages at the start and end), optional MMR diversity, and `[doc:ID#chunk:N]` labels.
**Acceptance criteria:**
- [ ] The context never exceeds the budget (property test)
- [ ] The ordering puts the top-2 passages at the start and end
- [ ] MMR reduces near-duplicate passages in the fixtures
**Verification:** `/verify`; `make eval`
**Dependencies:** Task 12
**Files:** `src/ragforge/generation/context.py`, `tests/unit/test_context.py`
**Scope:** S

## Checkpoint 3: After Tasks 11–14
- [ ] Eval report: dense → hybrid → +rerank → +rewrite, with Recall@10 and context precision
- [ ] code-reviewer agent run; human picks default retrieval settings from the evidence

---

## Phase 4: Generation hardening

### Task 15: Versioned YAML prompts, with the version recorded per request
**Description:** Load prompts from `prompts/*.vN.yaml` (with a changelog) and port the PRD's `answer_with_citations` prompt as v1. Hard-coded prompts are not allowed (a test enforces it). The active prompt version is returned in the response metadata and attached to logs.
**Acceptance criteria:**
- [ ] The prompt is selected by `generation.prompt_template`, and missing variables fail at startup
- [ ] The prompt version appears in the response metadata and logs
- [ ] A test fails if application code contains prompt literals (allowlisted module only)
**Verification:** `/verify`; `make eval` records the prompt version
**Dependencies:** Checkpoint 3
**Files:** `prompts/answer_with_citations.v1.yaml`, `prompts/CHANGELOG.md`, `src/ragforge/generation/prompts.py`, `tests/…`
**Scope:** S

### Task 16: SSE streaming for `/v1/query`
**Description:** `stream: true` returns Server-Sent Events: token deltas, then a final event with citations, usage and trace_id. Client disconnects cancel the upstream LLM call.
**Acceptance criteria:**
- [ ] The final SSE event matches the non-streaming response schema
- [ ] Time to first token is measured
- [ ] A client disconnect cancels the gateway request (test with a fake)
**Verification:** `/verify`; manual check: `curl -N` with `"stream": true` against Ollama
**Dependencies:** Task 15
**Files:** `apps/api/routes/query.py`, `src/ragforge/generation/gateway.py`, `tests/…`
**Scope:** S–M

## Checkpoint 4a: After Tasks 15–16
- [ ] `/verify` + `make lint test` pass
- [ ] `/v1/query` streams tokens over SSE; prompt version appears in the response metadata
- [ ] Human review before continuing

### Task 17: Citation validation + optional groundedness check
**Description:** After generation, every cited ID must exist in the supplied context; invalid citations are stripped or flagged according to config. If `require_citations` is set and the answer has no valid citations, it falls back to "not found". Add an optional sampled groundedness check using an LLM judge.
**Acceptance criteria:**
- [ ] Hallucinated citation IDs never appear in `citations` (unit tests with crafted outputs)
- [ ] The `require_citations` fallback works
- [ ] The groundedness check can be sampled (0–100%) and runs asynchronously so it doesn't block the response
**Verification:** `/verify`; eval adds a citation accuracy metric
**Dependencies:** Task 15
**Files:** `src/ragforge/generation/{citations,groundedness}.py`, `evals/metrics/citations.py`, `tests/…`
**Scope:** S–M

### Task 18: Gateway resilience: timeouts, retries, circuit breaker, fallback, routing, budgets
**Description:** The LLM gateway gets per-call timeouts, retries with jittered backoff, a circuit breaker per model, failover from `model` to `fallback_model`, simple routing (a cheap model for short or FAQ-like queries) and token counting with per-tenant budgets. The embedding calls get the same retry and backoff.
**Acceptance criteria:**
- [ ] When the primary provider fails (simulated), responses come from the fallback model, and the response metadata names it
- [ ] The breaker opens after N failures and half-opens after the cooldown (tests with a fake clock)
- [ ] A tenant over budget gets a 429 with a clear error
**Verification:** `/verify` (respx fault injection)
**Dependencies:** Task 16
**Files:** `src/ragforge/generation/{gateway,routing,budget,breaker}.py`, `tests/unit/…`
**Scope:** M

## Checkpoint 4: After Tasks 15–18
- [ ] Streaming + validated citations work; provider-outage fallback demonstrated
- [ ] code-reviewer agent run; human review

---

## Phase 5: Security

### Task 19: OIDC authentication + per-tenant rate limiting
**Description:** Validate JWTs against `OIDC_ISSUER`/`OIDC_AUDIENCE` (with JWKS caching), resolve the user's principals and tenant, and add `make dev-token` for local use. Add a Redis-backed rate limiter per tenant/user. Every `/v1/*` route requires auth; health and metrics routes don't.
**Acceptance criteria:**
- [ ] Missing, expired or wrong-audience tokens get a 401; valid tokens populate the request principal
- [ ] Rate limiting returns 429 with `Retry-After`
- [ ] The README's quickstart `curl` with `$DEV_TOKEN` works
**Verification:** `/verify` (tokens signed by a test key)
**Dependencies:** Checkpoint 4
**Files:** `src/ragforge/security/{auth,ratelimit}.py`, `apps/api/deps.py`, `tests/…`
**Scope:** M

### Task 20: Document ACLs + tenant isolation enforced inside retrieval
**Description:** Connectors and the API supply ACL principals and `tenant_id` per document, stored on every chunk (Qdrant payload, OpenSearch fields, Postgres). A single retrieval chokepoint adds mandatory tenant and ACL pre-filters to both the dense and sparse queries. ACL changes arrive as ingestion events.
**Acceptance criteria:**
- [ ] For every role in the fixture ACL model, queries never return unauthorized chunks (leakage suite)
- [ ] No retrieval path can bypass the chokepoint (an architecture test: the store clients are only importable inside it)
- [ ] An ACL update event changes visibility without a re-embed
**Verification:** `/verify` + an integration leakage suite on testcontainers
**Dependencies:** Task 19
**Files:** `src/ragforge/security/{acl,tenancy}.py`, `src/ragforge/retrieval/chokepoint.py`, `tests/security/test_acl_leakage.py`
**Scope:** M

## Checkpoint 5a: After Tasks 19–20
- [ ] `/verify` + `make lint test` pass
- [ ] ACL leakage suite green for every role
- [ ] Human review before continuing

### Task 21: Guardrails: prompt-injection detection, untrusted-context wrapping, output moderation
**Description:** Add an input classifier (heuristics plus an optional model) that flags or blocks injection attempts according to config. Retrieved content is wrapped and labeled as untrusted in the prompt. The output filter blocks policy violations, PII leakage, and untrusted links or images that could exfiltrate data.
**Acceptance criteria:**
- [ ] The injection suite (adversarial set) is flagged at ≥ the configured threshold, and flagged requests are logged
- [ ] Context passages are always wrapped in untrusted delimiters (prompt render test)
- [ ] Output containing seeded PII or exfiltration markdown links is blocked or sanitized
**Verification:** `/verify`; adversarial eval subset
**Dependencies:** Task 20
**Files:** `src/ragforge/guardrails/{injection,moderation,output}.py`, `evals/datasets/adversarial_v1.jsonl`, `tests/…`
**Scope:** M

### Task 22: Exact + semantic cache keyed by permission set, with invalidation
**Description:** Add a Redis exact-match cache (TTL) and a semantic cache (similarity ≥ threshold). Both are keyed by tenant plus a permission-set hash. When a document is updated, cached entries that cited it are invalidated.
**Acceptance criteria:**
- [ ] Users with different permission sets never share cache entries (included in the leakage suite)
- [ ] Updating or deleting a cited document invalidates the dependent entries
- [ ] Cache hit and miss are recorded on the response metadata
**Verification:** `/verify` + leakage suite re-run including the cache
**Dependencies:** Task 20 (must come after the ACLs)
**Files:** `src/ragforge/cache/{exact,semantic,invalidation}.py`, `tests/security/test_cache_leakage.py`
**Scope:** M

## Checkpoint 5: After Tasks 19–22
- [ ] The ACL and cache leakage suites pass for every role
- [ ] security-auditor agent review of auth, ACL and guardrails; human review

---

## Phase 6: Observability + evaluation maturity

### Task 23: OpenTelemetry tracing + structured logging
**Description:** Add spans `auth → guardrails.input → query.rewrite → retrieve.dense → retrieve.sparse → fuse → rerank → context.build → llm.generate → guardrails.output`, with attributes for prompt version, model, chunk IDs and scores, tokens, cache hit and tenant (never raw PII). Add JSON structured logs carrying trace_id, the OTLP exporter, and Jaeger in the `obs` profile. Ingestion workers get the same treatment.
**Acceptance criteria:**
- [ ] One `/v1/query` produces a trace containing every span above
- [ ] The response `trace_id` matches the exported trace
- [ ] A log-scrubbing test proves seeded PII never appears in logs or span attributes
**Verification:** `/verify` (in-memory span exporter); manual check: the trace appears in Jaeger
**Dependencies:** Checkpoint 5
**Files:** `src/ragforge/observability/{tracing,logging}.py`, wiring across the pipeline, `tests/…`
**Scope:** M

### Task 24: Prometheus metrics + Grafana dashboards as code
**Description:** Add the PRD's metrics table (`rag_request_latency_seconds`, `rag_time_to_first_token_seconds`, `rag_llm_errors_total`, `rag_no_context_found_total`, `rag_cache_hit_ratio`, `rag_tokens_total{type,model,tenant}`, `rag_ingestion_lag_seconds`, `rag_feedback_negative_ratio`) on `/metrics`, plus Grafana dashboards and alert rules in `deploy/grafana/`.
**Acceptance criteria:**
- [ ] All listed metrics are exported with the documented labels
- [ ] Dashboards load provisioned in local Grafana
- [ ] The alert rules encode the PRD's example thresholds
**Verification:** `/verify`; manual check: `make up --profile obs` and the dashboards show live traffic
**Dependencies:** Task 23
**Files:** `src/ragforge/observability/metrics.py`, `deploy/grafana/{dashboards,alerts}/`, `docker-compose.yml`
**Scope:** M

## Checkpoint 6a: After Tasks 23–24
- [ ] `/verify` + `make lint test` pass
- [ ] Grafana dashboards render from code; one trace shows the query spans
- [ ] Human review before continuing

### Task 25: Full eval suite: adversarial set, LLM-as-judge, CI regression gates
**Description:** Add generation metrics (faithfulness, answer relevance, correctness, citation accuracy, refusal accuracy) via an LLM judge, and safety metrics (injection resistance). Add `evals/gates.yaml` using the README's thresholds and `max_regression` against the stored baseline; `make eval` exits non-zero on a regression. Grow the golden set toward 200+ triples, reviewed by a human.
**Acceptance criteria:**
- [ ] `make eval` exits non-zero when any gate fails or regresses beyond `max_regression`
- [ ] The judge prompts are versioned, and judge scores are spot-checked against human labels on a sample
- [ ] Reports include latency and cost per query
**Verification:** `/verify`; deliberately degrade a setting and confirm the gate fails
**Dependencies:** Task 24 (and the eval metrics from Tasks 5 and 17)
**Files:** `evals/metrics/{judge,safety}.py`, `evals/gates.yaml`, `evals/datasets/*`, `evals/run_eval.py`
**Scope:** M

### Task 26: `/v1/feedback` linked to traces
**Description:** `POST /v1/feedback {trace_id, rating, comment}` is stored in Postgres and linked to the trace. Negative feedback is exportable as candidates for the golden set (with anonymization).
**Acceptance criteria:**
- [ ] Feedback is retrievable by trace_id; an unknown trace_id gives a 404
- [ ] `rag_feedback_negative_ratio` updates
- [ ] The export command produces anonymized golden-set candidates
**Verification:** `/verify`
**Dependencies:** Task 23
**Files:** `apps/api/routes/feedback.py`, `src/ragforge/storage/feedback.py`, `migrations/`, `tests/…`
**Scope:** S

## Checkpoint 6: After Tasks 23–26
- [ ] One trace shows every span; dashboards are live; `make eval` enforces gates.yaml
- [ ] code-reviewer agent run; human review of the golden-set quality

---

## Phase 7: Deployment

### Task 27: Production Docker images (multi-stage, non-root, scanned)
**Description:** Add Dockerfiles for api, worker and admin in `deploy/docker/`, built with uv in a multi-stage build, with CPU-only torch, a non-root user, and base images pinned by digest. `make build` builds and tags with the git SHA.
**Acceptance criteria:**
- [ ] The images run as non-root and pass a vulnerability scan (Trivy) with no critical findings
- [ ] Each image starts and passes `/healthz` in compose
- [ ] Image size is recorded; the torch wheel is CPU-only
**Verification:** `make build`; `docker run` smoke test; Trivy scan
**Dependencies:** Checkpoint 6
**Files:** `deploy/docker/{api,worker,admin}.Dockerfile`, `.dockerignore`, `Makefile`
**Scope:** S–M

### Task 28: CI pipeline (lint, type-check, tests, integration, eval gates, security scans)
**Description:** GitHub Actions following the README's pipeline. On PRs: lint, mypy, unit tests, integration tests (compose or testcontainers), offline eval against the gates, and SAST, dependency and image scans. On merge: build and sign images, deploy to staging, then smoke tests, full eval and a load test.
**Acceptance criteria:**
- [ ] A PR that regresses an eval gate fails CI (demonstrated on a throwaway branch)
- [ ] Images are signed (cosign) and pushed with the SHA tag on merge
- [ ] The pipeline runs in a reasonable time (target under 20 minutes for PRs)
**Verification:** a CI run on a test PR
**Dependencies:** Tasks 25, 27
**Files:** `.github/workflows/{pr,main}.yml`
**Scope:** M

## Checkpoint 7a: After Tasks 27–28
- [ ] `/verify` + `make lint test` pass
- [ ] CI green on a PR (lint, types, tests, scans)
- [ ] Human review before continuing

### Task 29: Helm chart (HPA, KEDA, PDBs, probes, NetworkPolicies)
**Description:** `deploy/helm/ragforge` contains: the api Deployment (HPA, at least 3 replicas, spread across zones), the ingestion worker (KEDA on queue lag, scale to zero), optional reranker and embedder workloads, PDBs, resource requests and limits, probes, NetworkPolicies that restrict egress, and values files for dev, staging and prod.
**Acceptance criteria:**
- [ ] `helm lint` and `helm template` pass for every values file
- [ ] The chart installs on a local kind cluster and `/readyz` passes
- [ ] NetworkPolicies block egress to anything not on the allow-list (tested on kind)
**Verification:** `helm lint`; kind install smoke test
**Dependencies:** Task 27
**Files:** `deploy/helm/ragforge/**`
**Scope:** M

## Checkpoint 7b: After Task 29
- [ ] `/verify` + `make lint test` pass
- [ ] Helm chart installs on a local kind cluster; probes go green
- [ ] Human review before cloud infrastructure

### Task 30a: Terraform — network + Kubernetes cluster
**Description:** `deploy/terraform/modules/{network,cluster}` and the staging stack wiring for them. **Blocked on Open Question 2 (which cloud).**
**Acceptance criteria:**
- [ ] `terraform validate` and `plan` succeed for staging
- [ ] Cluster is private by default with node pools sized from variables
- [ ] tflint/checkov report no high findings
**Verification:** `terraform plan` on staging; tflint/checkov scan
**Dependencies:** Task 29, Open Question 2
**Files:** `deploy/terraform/modules/network/**`, `deploy/terraform/modules/cluster/**`, `deploy/terraform/envs/staging/main.tf`
**Scope:** M

### Task 30b: Terraform — data services (Postgres, Redis, vector store)
**Description:** Modules for managed Postgres, Redis and the vector store (managed Qdrant or a cluster deployment), wired into staging.
**Acceptance criteria:**
- [ ] `terraform plan` for staging includes all three, in private subnets only
- [ ] Backups and encryption at rest are enabled
- [ ] Connection details are written to the secrets manager, not to state outputs
**Verification:** `terraform plan` on staging; checkov scan
**Dependencies:** Task 30a
**Files:** `deploy/terraform/modules/{postgres,redis,vectorstore}/**`, `deploy/terraform/envs/staging/main.tf`
**Scope:** M

### Task 30c: Terraform — secrets, IAM + staging composition
**Description:** Secrets manager and IAM modules (workload identity for the api and worker), the per-environment stacks, and docs for creating staging from scratch.
**Acceptance criteria:**
- [ ] All secrets come from the secrets manager; nothing sensitive lives in state outputs
- [ ] Workloads use least-privilege identities, with no static keys
- [ ] Staging is created from scratch with no console steps (documented)
**Verification:** `terraform plan`/`apply` on staging; checkov scan
**Dependencies:** Task 30b
**Files:** `deploy/terraform/modules/{secrets,iam}/**`, `deploy/terraform/envs/*/`, `docs/runbooks/terraform-bootstrap.md`
**Scope:** M

## Checkpoint 7c: After Tasks 30a–30c
- [ ] Staging created from scratch with `terraform apply`; checkov clean
- [ ] Human review of IAM and network exposure

### Task 31: Load tests (k6) + runbooks + blue/green reindex commands
**Description:** Add k6 scripts in `tests/load/` and `make load-test`. Add `make reindex TARGET_INDEX=… EMBED_MODEL=…`, `make promote-index` (an atomic Qdrant alias swap; OpenSearch alias too) with the old index kept 7 days for rollback. Add `docs/runbooks/` for each README operations scenario.
**Acceptance criteria:**
- [ ] The load test reports p50/p95/p99 and error rate at the target RPS; staging passes at 2× peak
- [ ] Reindex → eval → promote → rollback works on a staging-like setup
- [ ] Every row of the PRD's runbook table has a runbook document
**Verification:** `make load-test` against staging; reindex rehearsal
**Dependencies:** Task 28
**Files:** `tests/load/*.js`, `src/ragforge/storage/reindex.py`, `Makefile`, `docs/runbooks/*.md`
**Scope:** M

## Checkpoint 7: After Tasks 27–31 (incl. 30a–30c)
- [ ] Staging deployed via CI; load test at 2× peak passes; reindex rehearsed
- [ ] Human review before connectors

---

## Phase 8: Connectors + admin

Each connector emits `DocumentEvent`s with ACLs, supports incremental sync (CDC or webhooks where available, scheduled diffing otherwise) and delete propagation, and has contract tests against recorded responses. Live tests are opt-in.

### Task 32: S3 connector
**Acceptance criteria:**
- [ ] Incremental sync detects new, changed and deleted objects (ETag/version)
- [ ] Bucket or prefix ACL mapping to principals is configurable
- [ ] Contract tests pass using moto or recorded responses
**Verification:** `/verify`; manual sync of a test bucket | **Dependencies:** Checkpoint 7 | **Files:** `src/ragforge/connectors/s3.py`, tests | **Scope:** S–M

### Task 33: Confluence connector
**Acceptance criteria:**
- [ ] Spaces and pages are synced incrementally (via `lastModified`/webhooks) with page restrictions mapped to ACLs
- [ ] Deleted or archived pages produce delete events
- [ ] Contract tests pass using recorded API responses
**Verification:** `/verify`; manual sync of a test space | **Dependencies:** Task 32 (shared connector framework) | **Files:** `src/ragforge/connectors/confluence.py`, tests | **Scope:** M

### Task 34: SharePoint connector
**Acceptance criteria:** Graph delta-query sync; site and item permissions mapped to ACLs; deletes propagate; contract tests pass
**Verification:** `/verify` | **Dependencies:** Task 32 | **Files:** `src/ragforge/connectors/sharepoint.py`, tests | **Scope:** M

## Checkpoint 8a: After Tasks 32–34
- [ ] `/verify` + `make lint test` pass
- [ ] S3, Confluence and SharePoint connectors pass contract tests
- [ ] Human review before continuing

### Task 35: Google Drive connector
**Acceptance criteria:** Changes API sync; sharing permissions mapped to ACLs; Google Docs exported to parseable formats; contract tests pass
**Verification:** `/verify` | **Dependencies:** Task 32 | **Files:** `src/ragforge/connectors/gdrive.py`, tests | **Scope:** M

### Task 36: Database connector
**Acceptance criteria:** Configurable query and row-to-document mapping; incremental sync on an updated_at or CDC column; row-level ACL mapping; contract tests on a Postgres testcontainer
**Verification:** `/verify` | **Dependencies:** Task 32 | **Files:** `src/ragforge/connectors/database.py`, tests | **Scope:** S–M

### Task 37: Admin UI (index management + feedback review)
**Acceptance criteria:**
- [ ] View ingestion status and failures, trigger re-sync and reindex/promote
- [ ] Review negative-feedback traces and send them to the golden set
- [ ] Admin-role auth is required (OIDC), and actions are audit-logged
**Verification:** `/verify`; manual walkthrough | **Dependencies:** Tasks 26, 31; Open Question 7 (UI stack) | **Files:** `apps/admin/**` | **Scope:** M–L (split once the stack is chosen)

## Checkpoint 8: Complete
- [ ] Every item in the PRD's Production Readiness Checklist verified or explicitly deferred
- [ ] security-auditor + code-reviewer agents run on the full system
- [ ] Human sign-off
