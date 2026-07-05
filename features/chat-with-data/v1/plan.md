# Chat with Data v1 — Implementation Plan

**Status:** Draft v1
**Date:** 2026-07-03
**Spec:** [../spec.md](../spec.md)

---

## 1. Overview

A natural-language-to-warehouse chat feature for NGO M&E staff. Users ask questions in plain English; the system produces narrative answers grounded in the org's warehouse data.

**Core architecture:**

- **Semantic layer** stored in Django, shaped to the [Open Semantic Interchange (OSI)](https://github.com/open-semantic-interchange/OSI) spec for portability. Source of truth for what data means in each NGO.
- **[Cube](https://cube.dev)** (OSS) as the compiler and query engine. Django generates Cube schema files deterministically from the OSI Django rows; Cube compiles semantic queries to SQL and executes against the org's warehouse. Multi-tenancy via `driverFactory` / `repositoryFactory` / `contextToAppId`.
- **LLMs at the edges only**: LLM #1 (Sonnet-class) converts a user question + retrieved context into a structured Cube semantic query JSON. LLM #2 narrates the returned rows into 1–3 sentences. LLMs never see or write SQL.
- **Retrieval** is a hybrid pipeline over `pgvector` (dense) + Postgres full-text (sparse) + a deterministic glossary lookup, followed by a hosted reranker, over per-org atomic embedding rows.
- **Streaming** to the client is via **Server-Sent Events** — phase messages during retrieval + LLM #1 + Cube; token events during LLM #2; final event carrying provenance metadata; refusal events carrying an editor deep-link.
- **Semantic-layer editor and curator queue** live in **webapp_v2**, not Django admin. Both are user-facing product surfaces.
- **Metric reuse:** the existing Dalgo `Metric` model is extended (nullable FKs) to serve as the semantic-layer measure primitive. No wrapper table.

**Services affected:**

- **DDP_backend** — extends `Metric`; adds new semantic-layer, chat, retrieval, and curator models; adds new APIs for chat orchestration, semantic-layer CRUD, retrieval, and an internal endpoint that serves Cube schema files. Adds an embedding worker (Celery).
- **Cube** — new service in the Dalgo stack (Node.js). Runs alongside Django. Reads schema and warehouse credentials from Django on demand via an authenticated internal HTTP callback.
- **webapp_v2** — new chat surface (global FAB + Explore full-page), semantic-layer editor pages, curator-queue page.
- **Not affected:** prefect-proxy, prefect-airbyte, Airbyte, warehouse contents themselves.

---

## 2. Blast radius

| Surface | Hop | Edge type | Why affected | Status | Notes |
|---|---|---|---|---|---|
| **Metric** (existing) | 1 (SemanticLayer→Metric) | reuse + extend | Adds 4 nullable fields; backfill migration wires existing rows to auto-created SemanticLayer + Dataset | **In scope (extend)** | Existing Chart/KPI/Alert consumers unaffected — new fields nullable |
| **KPI** (existing) | 0 | none | Not part of the semantic layer; no schema change | **Untouched** | Future: chat "KPI shortcut" path may reference it; not v1 |
| **Chart** (existing) | 0 | none | Continues to reference `Metric` unchanged | **Untouched** | Charts stay chart-shaped |
| **Alert** (existing) | 0 | none | Continues to reference `Metric` / `KPI` unchanged | **Untouched** | |
| **Org / OrgUser** | 1 | reference | SemanticLayer, ChatSession, CuratorTask all FK to Org | **In scope (read-only)** | |
| **OrgWarehouseConfig** (existing) | 1 | read | Cube's `driverFactory` reads warehouse credentials via internal API | **In scope (read-only)** | Existing model, new consumer |
| **dbt project artefacts** | 1 | read at bootstrap | Auto-populates Dataset / Field / Relationship rows from `manifest.json` | **In scope (read-only)** | One-shot per NGO onboarding + refresh on demand |
| **Warehouse (Postgres / BigQuery)** | 1 | query-from | Cube executes SQL on the org's warehouse | **In scope** | Same auth path Charts/KPIs use today |
| **webapp_v2 nav / layout** | UI | new surface | Global FAB visible on every page; new Explore chat; new editor + curator queue routes | **In scope** | |
| **Explore page** (existing) | UI | new surface | Full-page chat added; existing schema browser preserved | **In scope** | Two views on Explore: chat + schema browser |

### v2 debt documented from this table

- Chart-aware and dashboard-aware chat — feeds page context into the LLM prompt.
- KPI shortcut path — chat serves a KPI's precomputed number when the resolved semantic query matches a KPI definition.
- User-facing "edit the resolved query" UX (v1: corrections happen through the curator queue).
- Multiple semantic layers per org.
- Semantic-layer version history and rollback.

---

## 3. High-Level Design (HLD)

### 3.1 System architecture

```
┌─────────────────────────── webapp_v2 ────────────────────────────┐
│                                                                   │
│  Global FAB (every page) ──── Right-side chat drawer              │
│  Explore page ──────────────── Full-page chat                     │
│  /semantic-layer/* ─────────── Editor pages                       │
│  /curator-queue ────────────── Queue page                         │
│                     │                                              │
└─────────────────────┼──────────────────────────────────────────────┘
                      │  HTTP (JSON) + SSE stream
┌─────────────────────┼──────── DDP_backend (Django) ───────────────┐
│                     │                                              │
│  Chat API                                                          │
│   • POST /api/chat/sessions/                                       │
│   • POST /api/chat/messages/  (SSE stream response)                │
│   • POST /api/chat/messages/{id}/feedback/                         │
│   • POST /api/chat/messages/{id}/retry/                            │
│                                                                    │
│  Semantic Layer API                                                │
│   • POST /api/semantic-layer/bootstrap/  (from dbt manifest)       │
│   • CRUD /api/semantic-layer/{datasets,fields,relationships,       │
│           metrics,glossary,qa-examples}/                           │
│   • POST /api/semantic-layer/turn-on/                              │
│   • GET  /api/semantic-layer/coverage/                             │
│                                                                    │
│  Curator API                                                       │
│   • GET  /api/curator/tasks/                                       │
│   • POST /api/curator/tasks/{id}/resolve/                          │
│                                                                    │
│  Internal API (Cube-facing, JWT-signed)                            │
│   • GET  /internal/cube-schema/{org_id}/                           │
│   • GET  /internal/warehouse-config/{org_id}/                      │
│                                                                    │
│  Services:                                                         │
│   ChatOrchestrator      (retrieve → LLM #1 → validate → Cube →     │
│                          LLM #2, all streamed via SSE)             │
│   SemanticLayerService  (CRUD, version bump, sync trigger)         │
│   DbtBootstrapService   (manifest.json → OSI Django rows)          │
│   CubeSchemaGenerator   (OSI Django rows → Cube JS strings)        │
│   EmbeddingGenerator    (OSI Django rows → SemanticEntityEmbedding)│
│   RetrievalService      (hybrid dense + sparse + glossary + graph) │
│   SemanticQueryValidator (validate LLM #1 JSON against schema)     │
│   CuratorService                                                   │
│                                                                    │
│  Postgres:                                                         │
│   ~13 new tables + 4 fields added to existing Metric               │
│   pgvector extension enabled                                       │
│                                                                    │
│  Celery worker:                                                    │
│   • embed_semantic_entities (on semantic-layer save, incremental)  │
│                                                                    │
└──────────┬─────────────────────────────────┬───────────────────────┘
           │                                 │
           │ (LLM #1, LLM #2)                │ (schema files, warehouse creds)
           ▼                                 ▼
┌─────────────────────┐            ┌──────────────────────────────┐
│ Anthropic / OpenAI  │            │ Cube (Node.js service)        │
│ - LLM #1: JSON      │            │                              │
│ - LLM #2: streamed  │            │  driverFactory ─── warehouse │
│         narration   │            │  repositoryFactory ── schema │
└─────────────────────┘            │  contextToAppId ─── cache    │
                                   │                              │
                                   │  Compiles semantic query →   │
                                   │  SQL, executes on warehouse  │
                                   └──────────────┬───────────────┘
                                                  │
                                                  ▼
                                    ┌──────────────────────────┐
                                    │ NGO warehouse            │
                                    │ (Postgres or BigQuery)   │
                                    └──────────────────────────┘
```

### 3.2 Data flow — a single question, end-to-end

```
1. User sends question ─────────────► POST /api/chat/messages/
                                       │
                                       │ SSE stream opens
                                       ▼
2. ChatOrchestrator.retrieve()
   - embed question (OpenAI/Voyage)
   - pgvector dense top-30
   - Postgres FTS sparse top-30
   - RRF fuse → top-30
   - Cohere Rerank → top-8
   - graph expand (join hop-1, columns)
   - QA retrieval (dense-only, top-5)
   - glossary lookup (deterministic)
                                       │
                     [emit: phase "Reading your question…"]
                                       ▼
3. Prompt assembly (deterministic template)
                     [emit: phase "Looking for {domain} data…"]
                                       ▼
4. LLM #1 — semantic query generation
   - Anthropic tool_use / OpenAI structured output
   - schema forces valid JSON
                                       │
                                       ▼
5. SemanticQueryValidator
   - all measures/dims/filters exist in this org's SemanticLayer?
   - dims valid for measure (fanout check)?
   - if invalid: repair loop, max 2 retries, then refuse
   - if refuse: [emit: refuse {reason, fix_url}] and stop
                                       │
                     [emit: phase "Running query on your warehouse…"]
                                       ▼
6. Cube.query(semantic_query, jwt={org_id, sl_version})
   - Cube compiles JSON → SQL
   - driverFactory picks warehouse
   - executes
                                       │
                                       ▼
7. LLM #2 — narration
   - question + rows + provenance
   - streams via SDK
                                       │
                     [emit: token, token, token…]
                                       ▼
8. Persist ChatMessage row (question, retrieved_entities,
   resolved_semantic_query, cube_sql, result_rows_top_n,
   narration, latency, tokens, models used)
                                       │
                     [emit: done {message_id, provenance}]
```

### 3.3 Data flow — semantic-layer save → Cube reload

```
1. User saves an edit in the editor (e.g. adds a Metric)
                                       │
                                       ▼
2. SemanticLayerService.save()
   - persist row(s)
   - create SemanticLayerVersion (version++)
   - CubeSchemaGenerator.generate() → GeneratedCubeSchema (Cube JS strings)
   - EmbeddingGenerator.enqueue() → Celery task per affected entity
                                       │
                                       ▼
3. Return to editor; UI shows "saved, version {N}"
                                       │
                                       ▼
4. On next chat query:
   - Django mints JWT with {org_id, sl_version: N}
   - Cube's contextToAppId = f"org_{org_id}_v{N}"
   - Cube cache miss → calls /internal/cube-schema/{org_id}/
   - Django returns latest GeneratedCubeSchema.files
   - Cube compiles fresh, caches under new app_id
```

### 3.4 Data flow — refusal → editor → retry

```
1. Chat streams [refuse {reason: "no measure for 'attendance'",
                        fix_url: "/semantic-layer/metrics/new?
                                   suggested_name=attendance_count&
                                   from_chat_message_id={id}"}]
                                       │
                                       ▼
2. CuratorTask row created (kind=refusal, triggered_by=chat_message)
                                       │
                                       ▼
3. User clicks "Fix this" → deep-links to editor
                                       │
                                       ▼
4. User adds the measure, saves (see § 3.3)
                                       │
                                       ▼
5. User clicks "Retry" on the same chat message
   POST /api/chat/messages/{id}/retry/
                                       │
                                       ▼
6. Orchestrator re-runs with updated semantic layer version
   New ChatMessage row (linked to the retried one)
```

### 3.5 New API endpoints

| Method | Path | Permission | Purpose |
|---|---|---|---|
| POST | `/api/chat/sessions/` | `can_use_chat` | Create session |
| GET | `/api/chat/sessions/` | `can_use_chat` | List sessions for current user |
| GET | `/api/chat/sessions/{id}/` | `can_use_chat` | Session + messages |
| POST | `/api/chat/messages/` | `can_use_chat` | Ask question; returns SSE stream |
| POST | `/api/chat/messages/{id}/feedback/` | `can_use_chat` | Thumbs up / down + optional comment |
| POST | `/api/chat/messages/{id}/retry/` | `can_use_chat` | Re-run with current semantic layer |
| POST | `/api/semantic-layer/bootstrap/` | `can_edit_semantic_layer` | Import from dbt manifest (multipart or manifest URL) |
| GET | `/api/semantic-layer/` | `can_view_semantic_layer` | Overview + coverage % |
| CRUD | `/api/semantic-layer/datasets/` | `can_edit_semantic_layer` | Dataset CRUD |
| CRUD | `/api/semantic-layer/fields/` | `can_edit_semantic_layer` | Field CRUD |
| CRUD | `/api/semantic-layer/relationships/` | `can_edit_semantic_layer` | Relationship CRUD |
| CRUD | `/api/semantic-layer/metrics/` | `can_edit_semantic_layer` | Metric CRUD (backed by existing Metric model) |
| CRUD | `/api/semantic-layer/glossary/` | `can_edit_semantic_layer` | Glossary CRUD |
| CRUD | `/api/semantic-layer/qa-examples/` | `can_edit_semantic_layer` | QA examples CRUD |
| POST | `/api/semantic-layer/turn-on/` | `can_edit_semantic_layer` | Toggle chat on for the org (gated by MV bar) |
| GET | `/api/semantic-layer/coverage/` | `can_view_semantic_layer` | Completeness stats |
| GET | `/api/curator/tasks/` | `can_edit_semantic_layer` | Curator queue, paginated, sorted by frequency |
| POST | `/api/curator/tasks/{id}/resolve/` | `can_edit_semantic_layer` | Mark resolved or won't-fix |

**Internal endpoints (Cube-facing, JWT-signed with shared secret):**

| Method | Path | Purpose |
|---|---|---|
| GET | `/internal/cube-schema/{org_id}/` | Returns `GeneratedCubeSchema.files` for `repositoryFactory` |
| GET | `/internal/warehouse-config/{org_id}/` | Returns warehouse creds for `driverFactory` |

### 3.6 Key design decisions

| Decision | Choice | Rationale |
|---|---|---|
| Semantic-layer interchange format | [OSI](https://github.com/open-semantic-interchange/OSI) v0.1.1 | Portability across future tools (Cube, MetricFlow, hosted engines) — the model swap should be a converter change, not a rewrite. See memory `prefer-standard-oss-infra` |
| Semantic-layer runtime | Cube (OSS) | Battle-tested SQL compilation with correct joins/aggregations/multi-dialect; native multi-tenancy; REST API matches our semantic-query shape exactly; saves us weeks of writing a compiler |
| Cube ↔ Django integration | `repositoryFactory` HTTP callback to Django `/internal/cube-schema/` | No shared filesystem; Django is single source of truth; Cube is derivable |
| Multi-tenancy | `driverFactory` + `repositoryFactory` + `contextToAppId` off JWT `{org_id, sl_version}` | Standard Cube multi-tenancy. Cache keys **must** include `org_id` — validated by a cross-tenant integration test |
| LLM placement | Question → JSON (LLM), JSON → SQL (Cube, deterministic), Rows → narrative (LLM) | LLM only ever picks from constrained enums; never writes SQL. Removes the biggest hallucination class |
| Semantic-query output constraint | Anthropic `tool_use` / OpenAI structured output with JSON schema | Guarantees structural validity; frees us to validate only semantic conformance |
| Validation failure | Repair loop (max 2 retries) with allowed-value hints, then refuse | Escapes silent guesses; every un-repaired refusal becomes a CuratorTask |
| Answer-side hallucination | System prompt forbids trend/comparison claims not in rows; provenance visible on demand | Reduces narration hallucination; explicit source line on every answer |
| Metric | Reuse existing `DDP_backend/ddpui/models/metric.py::Metric`, add 4 nullable fields | Prevents drift between Charts/KPIs/Chat definitions of the same number; existing Metrics chat-queryable on day 1 |
| Grain / kind / PII flags | `Metric.custom_extensions.dalgo.*` and `Dataset.custom_extensions.dalgo.*` JSONFields | OSI-compliant extension mechanism; namespaced under `dalgo.*`; doesn't collide with future OSI core fields |
| Retrieval channels | Dense (pgvector, hybrid HNSW) + Sparse (Postgres FTS) + Glossary (deterministic) | Each catches things the others miss; RRF fusion is standard and needs no score normalisation |
| Reranker | Cohere Rerank (hosted, ~$0.001/1000 pairs) | Zero infra; move to self-hosted `bge-reranker-large` if cost or residency demands. Skip reranker entirely in v1 if too complex; add if precision is poor |
| Embedding model | `text-embedding-3-small` (OpenAI) or `voyage-3-lite` — final call during build | Cost/quality sweet spot; ~1536 dims; pgvector handles it fine |
| Vector store | pgvector in Dalgo's Postgres | ~15–25K rows total at 20 NGOs; trivial. No new infra |
| Embedding recomputation | Celery worker, incremental (only rows whose `embedding_text` changed) | On semantic-layer save. Content-hash gate |
| QA examples index | Same `SemanticEntityEmbedding` table, `entity_kind=qa_example`, queried dense-only | Retrieval sees them alongside entities. Thumbs-up promotes real Q&As into the index |
| Streaming | Server-Sent Events (not WebSockets) | One-way; simpler; native `EventSource`; matches our need |
| Streaming shape | Phase events (backend-generated human strings) + token events (LLM stream) + done/refuse | See § 3.7 |
| Semantic-layer version | Monotonic counter (`SemanticLayerVersion.version`), not a full snapshot | v1 doesn't need rollback. Cache-bust marker only |
| Semantic-layer editor location | webapp_v2 | Per memory `no-django-admin-for-user-facing-tools` — Django admin is off-limits for user-facing tools |
| Curator queue location | webapp_v2 | Same reason |
| Auto-bootstrap trust | Auto-draft everything possible from dbt manifest, `Metric`, `Chart`, `KPI` catalogs; every draft flagged "needs review" | Human confirms before entities count toward coverage; nothing goes live without review |
| Chat turn-on gate | MV bar (≥1 Dataset w/ grain+kind, ≥1 Metric, ≥5 QA examples, all PII columns tagged) | Below gate: chat is disabled entirely. Prevents "on but bad" |
| Refuse over guess | Every unknown measure/dim/filter, every below-threshold retrieval confidence → refuse | Silent wrong answers destroy trust faster than refusals |
| SQL fallback | **None** | Ad-hoc LLM SQL against raw tables would violate the accuracy promise |
| PII policy | Single boolean column tag; Cube masks or excludes at query time | v1 minimal; full policy engine deferred |

### 3.7 SSE event schema

```
event: phase       data: {phase: "understanding"|"finding_data"|"querying"|"answering",
                          text: string}

event: token       data: {text: string}   # narration tokens as they stream

event: done        data: {message_id: int,
                          semantic_query: object,
                          cube_sql: string,
                          tables: string[],
                          filters: object,
                          row_count: int}

event: refuse      data: {reason: string,
                          fix_url: string,
                          curator_task_id: int}

event: error       data: {code: string, message: string}
```

Content-Type: `text/event-stream`. Uvicorn already supports this via async generators from Django Ninja routes.

---

## 4. Low-Level Design (LLD)

### 4.1 Data model

Thirteen new tables plus four added fields on existing `Metric`. `pgvector` extension enabled on Dalgo's Postgres.

#### Group A — Semantic layer (OSI-shaped)

```python
# ddpui/models/semantic_layer.py

class SemanticLayer(models.Model):
    org = models.OneToOneField("Org", on_delete=models.CASCADE, related_name="semantic_layer")
    name = models.CharField(max_length=200, default="default")
    description = models.TextField(blank=True)
    ai_context = models.JSONField(default=dict)         # {instructions, synonyms, examples}
    custom_extensions = models.JSONField(default=list)  # OSI vendor extensions
    is_chat_enabled = models.BooleanField(default=False)  # MV-bar gate
    updated_at = models.DateTimeField(auto_now=True)


class Dataset(models.Model):
    semantic_layer = models.ForeignKey(SemanticLayer, on_delete=models.CASCADE, related_name="datasets")
    name = models.CharField(max_length=200)              # e.g., "Trainings"
    source = models.CharField(max_length=500)            # "warehouse.schema.table"
    primary_key = models.JSONField(default=list)
    unique_keys = models.JSONField(default=list)
    description = models.TextField(blank=True)
    ai_context = models.JSONField(default=dict)
    custom_extensions = models.JSONField(default=list)   # dalgo.grain, dalgo.kind (fact/dim/bridge), dalgo.pii_columns
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        unique_together = [("semantic_layer", "name")]


class Field(models.Model):
    dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="fields")
    name = models.CharField(max_length=200)
    expression = models.JSONField()                      # OSI-style: {dialects: [{dialect, expression}]}
    data_type = models.CharField(max_length=50)
    role = models.CharField(max_length=30)               # dimension | measure_input | pk | fk | timestamp | metadata
    is_time = models.BooleanField(default=False)
    description = models.TextField(blank=True)
    ai_context = models.JSONField(default=dict)          # synonyms, sample values, filter phrasings
    custom_extensions = models.JSONField(default=list)   # dalgo.pii

    class Meta:
        unique_together = [("dataset", "name")]


class Relationship(models.Model):
    semantic_layer = models.ForeignKey(SemanticLayer, on_delete=models.CASCADE, related_name="relationships")
    name = models.CharField(max_length=200)
    from_dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="rels_out")
    to_dataset = models.ForeignKey(Dataset, on_delete=models.CASCADE, related_name="rels_in")
    from_columns = models.JSONField()                    # ["beneficiary_id"]
    to_columns = models.JSONField()                      # ["beneficiary_id"]
    ai_context = models.JSONField(default=dict)
    custom_extensions = models.JSONField(default=list)   # dalgo.cardinality, dalgo.is_default_join


class GlossaryTerm(models.Model):
    semantic_layer = models.ForeignKey(SemanticLayer, on_delete=models.CASCADE, related_name="glossary_terms")
    term = models.CharField(max_length=200)              # "women"
    synonyms = models.JSONField(default=list)            # ["female", "girls"]
    resolves_to = models.JSONField()                     # {filter: {member, operator, values}} OR {measure: "..."}
    applies_when = models.TextField(blank=True)
```

#### Extension to existing `Metric` (in `DDP_backend/ddpui/models/metric.py`)

```python
# Add these 4 nullable fields to the existing Metric class:
class Metric(models.Model):
    # ... existing fields unchanged ...
    semantic_layer = models.ForeignKey(
        "SemanticLayer", null=True, blank=True, on_delete=models.SET_NULL, related_name="metrics"
    )
    anchor_dataset = models.ForeignKey(
        "Dataset", null=True, blank=True, on_delete=models.SET_NULL, related_name="metrics"
    )
    ai_context = models.JSONField(default=dict)
    custom_extensions = models.JSONField(default=list)   # dalgo.format, dalgo.linked_kpi_ids
```

#### Group B — Cube sync

```python
# ddpui/models/semantic_layer.py (continued)

class SemanticLayerVersion(models.Model):
    semantic_layer = models.ForeignKey(SemanticLayer, on_delete=models.CASCADE, related_name="versions")
    version = models.IntegerField()                      # monotonic per SemanticLayer
    created_at = models.DateTimeField(auto_now_add=True)
    created_by = models.ForeignKey("OrgUser", null=True, on_delete=models.SET_NULL)
    change_summary = models.TextField(blank=True)

    class Meta:
        unique_together = [("semantic_layer", "version")]


class GeneratedCubeSchema(models.Model):
    version = models.OneToOneField(SemanticLayerVersion, on_delete=models.CASCADE, related_name="cube_schema")
    files = models.JSONField()                           # {"trainings.js": "cube('Trainings', {...})", ...}
    generated_at = models.DateTimeField(auto_now_add=True)
```

#### Group C — Chat runtime

```python
# ddpui/models/chat.py

class ChatSession(models.Model):
    org = models.ForeignKey("Org", on_delete=models.CASCADE, related_name="chat_sessions")
    user = models.ForeignKey("OrgUser", on_delete=models.CASCADE, related_name="chat_sessions")
    title = models.CharField(max_length=500, blank=True)  # auto-generated from first question
    started_at = models.DateTimeField(auto_now_add=True)
    last_message_at = models.DateTimeField(auto_now_add=True)


class ChatMessage(models.Model):
    session = models.ForeignKey(ChatSession, on_delete=models.CASCADE, related_name="messages")
    role = models.CharField(max_length=20)                # user | assistant | system
    question = models.TextField(blank=True)               # user role only

    # Full trace — for provenance UI + eval + debugging
    retrieved_entities = models.JSONField(null=True)
    resolved_semantic_query = models.JSONField(null=True)
    cube_sql = models.TextField(blank=True)
    result_rows_sample = models.JSONField(null=True)      # top-N rows for audit
    row_count = models.IntegerField(null=True)
    narration = models.TextField(blank=True)              # assistant role only

    # Outcomes
    refused_reason = models.CharField(max_length=500, blank=True)
    retried_from = models.ForeignKey(
        "self", null=True, blank=True, on_delete=models.SET_NULL, related_name="retries"
    )

    # Metadata
    latency_ms = models.IntegerField(null=True)
    semantic_query_llm = models.CharField(max_length=100, blank=True)
    narration_llm = models.CharField(max_length=100, blank=True)
    input_tokens = models.IntegerField(null=True)
    output_tokens = models.IntegerField(null=True)
    semantic_layer_version = models.IntegerField(null=True)  # which version served this answer
    created_at = models.DateTimeField(auto_now_add=True)


class Feedback(models.Model):
    message = models.ForeignKey(ChatMessage, on_delete=models.CASCADE, related_name="feedback")
    signal = models.CharField(max_length=20)              # thumbs_up | thumbs_down
    comment = models.TextField(blank=True)
    created_by = models.ForeignKey("OrgUser", on_delete=models.CASCADE)
    created_at = models.DateTimeField(auto_now_add=True)
```

#### Group D — Retrieval

```python
# ddpui/models/retrieval.py
from pgvector.django import VectorField, HnswIndex
from django.contrib.postgres.search import SearchVectorField
from django.contrib.postgres.indexes import GinIndex

class SemanticEntityEmbedding(models.Model):
    """One row per retrievable entity. entity_kind in
       {dataset, measure, field, relationship, glossary, qa_example}."""
    semantic_layer = models.ForeignKey(
        "SemanticLayer", on_delete=models.CASCADE, related_name="embeddings"
    )
    entity_kind = models.CharField(max_length=30)
    entity_ref = models.JSONField()                       # {kind, id, name} — points back to Group A row

    embedding_text = models.TextField()                   # the natural-language doc that was embedded
    embedding_text_hash = models.CharField(max_length=64) # to skip re-embedding unchanged rows
    embedding = VectorField(dimensions=1536)
    fts_vector = SearchVectorField(null=True)             # Postgres full-text (sparse)

    embedding_model = models.CharField(max_length=100)    # "text-embedding-3-small" — for cache invalidation
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        indexes = [
            HnswIndex(name="sem_emb_hnsw", fields=["embedding"],
                      m=16, ef_construction=64, opclasses=["vector_cosine_ops"]),
            GinIndex(fields=["fts_vector"]),
            models.Index(fields=["semantic_layer", "entity_kind"]),
        ]


class QAExample(models.Model):
    """Question → semantic query pair. Also gets a SemanticEntityEmbedding row
       (kind=qa_example) for retrieval as a few-shot exemplar."""
    semantic_layer = models.ForeignKey(
        "SemanticLayer", on_delete=models.CASCADE, related_name="qa_examples"
    )
    question = models.TextField()
    semantic_query = models.JSONField()                   # the Cube query JSON
    verified_by = models.ForeignKey("OrgUser", null=True, on_delete=models.SET_NULL)
    verified_at = models.DateTimeField(null=True)
    source = models.CharField(max_length=30)              # seeded | promoted_from_feedback | curator_added
    created_at = models.DateTimeField(auto_now_add=True)
```

#### Group E — Curator queue

```python
# ddpui/models/curator.py

class CuratorTask(models.Model):
    org = models.ForeignKey("Org", on_delete=models.CASCADE, related_name="curator_tasks")
    triggered_by_message = models.ForeignKey(
        "ChatMessage", null=True, blank=True, on_delete=models.SET_NULL, related_name="curator_tasks"
    )
    kind = models.CharField(max_length=30)                # refusal | thumbs_down | ambiguous
    description = models.TextField()                     # human-readable
    question_fingerprint = models.CharField(max_length=64, db_index=True)  # for frequency roll-up
    status = models.CharField(max_length=20, default="open")  # open | in_progress | resolved | wont_fix
    resolution_notes = models.TextField(blank=True)
    resolved_by = models.ForeignKey("OrgUser", null=True, blank=True, on_delete=models.SET_NULL)
    created_at = models.DateTimeField(auto_now_add=True)
    resolved_at = models.DateTimeField(null=True, blank=True)
```

Curator queue ordering (list endpoint) groups by `question_fingerprint`, counts open tasks per fingerprint, and sorts descending. That's the "asked 14 times this week" effect without a separate rollup table.

### 4.2 Cube integration

Cube runs as a new service defined in `dalgo_dev.config.js`.

**`cube.js`** (Cube service config, checked in under a new top-level `cube/` directory):

```javascript
const jwt = require("jsonwebtoken");
const fetch = require("node-fetch");

const DALGO_INTERNAL_URL = process.env.DALGO_INTERNAL_URL;  // http://ddp_backend:8002
const DALGO_INTERNAL_JWT_SECRET = process.env.DALGO_INTERNAL_JWT_SECRET;

module.exports = {
  contextToAppId: ({ securityContext }) =>
    `org_${securityContext.org_id}_v${securityContext.sl_version}`,

  contextToOrchestratorId: ({ securityContext }) =>
    `org_${securityContext.org_id}`,

  repositoryFactory: ({ securityContext }) => ({
    dataSchemaFiles: async () => {
      const token = jwt.sign(
        { org_id: securityContext.org_id, purpose: "cube-schema" },
        DALGO_INTERNAL_JWT_SECRET,
        { expiresIn: "1m" }
      );
      const r = await fetch(
        `${DALGO_INTERNAL_URL}/internal/cube-schema/${securityContext.org_id}/`,
        { headers: { Authorization: `Bearer ${token}` } }
      );
      const { files } = await r.json();
      return Object.entries(files).map(([fileName, content]) => ({ fileName, content }));
    },
  }),

  driverFactory: async ({ securityContext }) => {
    const token = jwt.sign(
      { org_id: securityContext.org_id, purpose: "warehouse-config" },
      DALGO_INTERNAL_JWT_SECRET,
      { expiresIn: "1m" }
    );
    const r = await fetch(
      `${DALGO_INTERNAL_URL}/internal/warehouse-config/${securityContext.org_id}/`,
      { headers: { Authorization: `Bearer ${token}` } }
    );
    const cfg = await r.json();
    if (cfg.type === "bigquery") {
      return {
        type: "bigquery",
        projectId: cfg.gcp_project,
        credentials: cfg.service_account_json,
      };
    }
    return {
      type: "postgres",
      host: cfg.host, port: cfg.port,
      database: cfg.db, user: cfg.user, password: cfg.password,
      ssl: cfg.ssl,
    };
  },
};
```

**Django-side JWT minting** — Django signs a short-lived JWT with `{org_id, sl_version, user_id}` when calling Cube's REST API. Cube verifies with the shared secret. This is separate from the JWT Django uses for its own API auth.

### 4.3 Semantic-layer authoring

#### 4.3.1 dbt bootstrap converter

`ddpui/services/semantic_layer/dbt_bootstrap.py`

Takes a dbt `manifest.json` (uploaded or fetched from an S3 URL). For each model:

1. Create `Dataset` row (name from model name, source from `database.schema.alias`, description from `schema.yml`, `custom_extensions.dalgo.kind` auto-guessed from name prefix / column patterns, `custom_extensions.dalgo.grain = ""` (human fills in), `is_reviewed=false`).
2. Create `Field` rows for each column (name, type, description, `role` auto-guessed).
3. If `unique` tests exist → populate `primary_key`.
4. If `relationships` tests exist → create `Relationship` rows.
5. Populate `ai_context.examples` from an LLM auto-suggestion pass (offline, batch, cached).

Existing `Metric` rows for the org get their `semantic_layer` and `anchor_dataset` fields backfilled from `schema_name` + `table_name`.

Existing `Chart` rows are inspected for referenced tables/columns → those Datasets and Fields get tagged `custom_extensions.dalgo.used_by_chart = true` so the editor prioritizes them.

Existing `KPI` rows → their linked Metric gets `custom_extensions.dalgo.linked_kpi_ids` populated.

#### 4.3.2 OSI → Cube schema generator

`ddpui/services/semantic_layer/cube_schema_generator.py`

Pure string templating. For each `Dataset`:

```python
def dataset_to_cube_js(dataset: Dataset) -> str:
    return f"""
cube('{cube_name(dataset)}', {{
  sql_table: `{dataset.source}`,
  {render_primary_key(dataset)}
  measures: {{
    {render_measures(dataset.metrics.all())}
  }},
  dimensions: {{
    {render_dimensions(dataset.fields.all())}
  }},
  joins: {{
    {render_joins(dataset.rels_out.filter(semantic_layer=dataset.semantic_layer))}
  }}
}});
"""
```

Runs on every semantic-layer save. Output persisted in `GeneratedCubeSchema.files` (dict of `filename → JS string`) so `repositoryFactory` can serve it fast.

No LLM in this generator.

#### 4.3.3 OSI → embedding docs generator

`ddpui/services/semantic_layer/embedding_docs.py`

For each entity, generates a natural-language doc (§ retrieval design earlier). Includes `Sample questions this X answers:` block populated from `ai_context.examples`. Runs on semantic-layer save; each doc hashed to skip unchanged rows.

Docs are handed to the embedding worker (§ 4.4.1).

#### 4.3.4 Editor pages (webapp_v2)

New routes under `/semantic-layer/`:

- `/semantic-layer/` — org overview: coverage %, per-Dataset traffic-light readiness, chat on/off toggle
- `/semantic-layer/datasets/` — filtered list, search
- `/semantic-layer/datasets/{id}/` — batch-editable detail
- `/semantic-layer/relationships/` — visual join graph editor (React Flow or similar)
- `/semantic-layer/metrics/` — Metric list (backed by existing `/api/metrics/` extended)
- `/semantic-layer/metrics/new` — measure wizard
- `/semantic-layer/glossary/` — glossary table editor
- `/semantic-layer/qa-examples/` — seeded QA editor + import from feedback
- `/curator-queue/` — task list, sortable, resolvable

State: Zustand store for the current SemanticLayer draft (paged fetches, optimistic updates).

### 4.4 Retrieval

#### 4.4.1 Embedding worker

Celery task `embed_semantic_entities(semantic_layer_id, entity_kinds=None)`.

- Enqueued from `SemanticLayerService.save()` after `EmbeddingDocsGenerator.run()`.
- Iterates entities of the given kinds, compares `embedding_text_hash` to stored value, skips unchanged.
- Batches calls to the embedding provider (100 per request).
- Updates `SemanticEntityEmbedding.embedding` and `fts_vector` (via Postgres `to_tsvector`).

Embedding provider: **`text-embedding-3-small`** (OpenAI) or **`voyage-3-lite`** — final call during build; both give 1536-dim vectors and behave similarly. Voyage cheaper; OpenAI simpler auth for Dalgo's stack today. Wrap behind an interface so it's swappable.

#### 4.4.2 Retrieval pipeline

`ddpui/services/chat/retrieval.py`

```python
class RetrievalService:
    def retrieve(self, semantic_layer_id: int, question: str) -> RetrievalContext:
        question_norm = normalize(question)
        q_vec = self.embed_provider.embed_one(question_norm)

        # Channel A: dense (pgvector)
        dense = SemanticEntityEmbedding.objects.filter(
            semantic_layer_id=semantic_layer_id
        ).exclude(entity_kind="qa_example").order_by(
            L2Distance("embedding", q_vec)
        )[:30]

        # Channel B: sparse (Postgres FTS)
        tsq = to_tsquery_from_question(question_norm)
        sparse = SemanticEntityEmbedding.objects.filter(
            semantic_layer_id=semantic_layer_id,
            fts_vector=tsq,
        ).exclude(entity_kind="qa_example").order_by("-rank")[:30]

        # RRF fuse
        fused = reciprocal_rank_fusion(dense, sparse, k=60)[:30]

        # Rerank (Cohere) — optional in v1
        top8 = self.reranker.rerank(question_norm, fused, top_k=8) if self.reranker else fused[:8]

        # Graph expansion (1-hop joins + columns)
        expanded = self.graph_expand(top8)

        # QA retrieval — separate dense-only sub-query
        qa_examples = SemanticEntityEmbedding.objects.filter(
            semantic_layer_id=semantic_layer_id,
            entity_kind="qa_example",
        ).order_by(L2Distance("embedding", q_vec))[:5]

        # Glossary — deterministic term lookup
        glossary_hits = self.glossary_lookup(semantic_layer_id, question_norm)

        return RetrievalContext(
            entities=expanded, qa_examples=qa_examples, glossary_hits=glossary_hits,
            top_entity_score=fused[0].score if fused else 0.0
        )
```

Reranker: Cohere Rerank API. Wrap behind an interface. If not enabled, skip (fused top-8).

Confidence threshold: if `top_entity_score < 0.35` (tunable), retrieval flags low-confidence → orchestrator can choose to refuse pre-emptively.

#### 4.4.3 Prompt assembly

`ddpui/services/chat/prompt.py` — deterministic template functions. Sections:

1. System prompt (role, output schema, refuse rule, no-invent rule).
2. Schema block: retrieved entities formatted as compact YAML-like strings.
3. Glossary block: matched terms.
4. Examples block: retrieved QA pairs (3–5).
5. Question.
6. Output tool schema (Anthropic `tool_use` or OpenAI JSON mode).

Token budget: ~6–8K input tokens per call. Kept small by tight entity slicing.

### 4.5 LLM orchestrator

`ddpui/services/chat/orchestrator.py`

```python
class ChatOrchestrator:
    async def stream_answer(self, message: ChatMessage) -> AsyncIterator[SSEEvent]:
        yield phase("understanding", "Reading your question…")

        ctx = self.retrieval.retrieve(sl_id, message.question)
        message.retrieved_entities = ctx.summary_for_persistence()

        yield phase("finding_data", f"Looking for {ctx.domain_hint} data…")

        prompt = self.prompt_builder.build(message.question, ctx)
        for attempt in range(3):  # 1 primary + 2 repair
            sq = await self.semantic_query_llm.emit_json(prompt)
            err = self.validator.validate(sq, sl_id)
            if not err:
                break
            prompt = self.prompt_builder.add_repair(prompt, err)
        else:
            yield refuse("Couldn't map your question to a valid query.", fix_url=...)
            return

        if sq.get("refuse"):
            yield refuse(sq["reason"], fix_url=build_fix_url(sq, message.id))
            return

        yield phase("querying", "Running query on your warehouse…")

        rows = await self.cube.query(sq, jwt_for(sl_id))

        yield phase("answering", "")

        message.resolved_semantic_query = sq
        message.cube_sql = rows.compiled_sql

        async for tok in self.narration_llm.stream(message.question, sq, rows):
            yield token(tok)

        message.narration = self.narration_llm.final_text
        message.save()
        yield done(message)
```

### 4.6 SSE endpoint

Django Ninja route returning `StreamingHttpResponse`:

```python
@router.post("/chat/messages/")
async def create_message(request, payload: MessageIn):
    session = ...
    msg = ChatMessage.objects.create(session=session, role="user", question=payload.question)

    async def event_stream():
        async for event in ChatOrchestrator().stream_answer(msg):
            yield event.to_sse()

    return StreamingHttpResponse(event_stream(), content_type="text/event-stream")
```

Frontend uses `EventSource` and a Zustand chat store to render phases (replace-in-place) and tokens (append to current message).

### 4.7 Chat surface (webapp_v2)

- **`<ChatFAB>`** — mounted at app root; shows/hides based on `useSemanticLayer().isChatEnabled`.
- **`<ChatDrawer>`** — right-side drawer, session picker + transcript + input.
- **`<ChatMessage>`** — narration + collapsed provenance card + feedback buttons + retry action.
- **`<ProvenanceCard>`** — expandable: measure, tables, filters, time range, SQL (copy button).
- **`<RefusalMessage>`** — reason + "Fix this" deep-link button + optional context.
- **Explore page**: existing schema browser as one tab, new `<ChatFullPage>` as another tab.

### 4.8 Curator queue page

`/curator-queue/` — sortable list, filter by kind (refusal / thumbs_down), resolve or won't-fix inline, deep-link into the same focused editor views used from chat.

---

## 5. Migration

### 5.1 Migrations (Django)

Ordered:

1. Add 4 nullable fields to `Metric`.
2. Create Group A tables (SemanticLayer, Dataset, Field, Relationship, GlossaryTerm).
3. Create Group B tables.
4. Create Group C tables.
5. Enable `pgvector` extension; create Group D tables + HNSW index.
6. Create Group E tables.

### 5.2 Data backfill

For each existing Org:

1. Create one `SemanticLayer` (auto).
2. For every unique `(schema_name, table_name)` referenced by existing `Metric` rows: create a `Dataset` (source populated, `is_reviewed=false`).
3. Link `Metric.semantic_layer` and `Metric.anchor_dataset`.
4. Do **not** flip `is_chat_enabled=true` — chat stays off until an onboarding pass raises coverage above the MV bar.

### 5.3 New dev-config service

Add `cube` to `dalgo_dev.config.js` — a Node.js process running Cube. Env vars: `DALGO_INTERNAL_URL`, `DALGO_INTERNAL_JWT_SECRET`, `CUBEJS_API_SECRET`.

---

## 6. Rollout

- **Cohort 1** (2–3 partner NGOs with reasonable dbt hygiene and existing Metrics/KPIs). Dalgo staff runs the full onboarding (§ spec 4.3). Ship to production with a per-org feature flag `chat_with_data_enabled`. Success metric: 50+ chat questions/week/org within 4 weeks, thumbs-up rate >70%.
- **Cohort 2** (partner NGOs with less-documented dbt). Tests the auto-bootstrap + refusal-driven curation on weaker inputs. Expect lower initial accuracy; expect higher curator queue turnover.
- **General availability** after both cohorts show sustained curator-queue-turnover ≥ opens per week for 4 consecutive weeks per org.
- **Chat is off by default per org.** `is_chat_enabled=false` on `SemanticLayer` creation. Flipping to `true` requires the MV bar (§ 5.3 of the plan? No — of the spec).

---

## 7. Open questions

1. **Cube + BigQuery multi-tenant with per-org service accounts** — Cube's BigQuery driver was designed for single-tenant deploys. Need a 1-day spike: two mock BigQuery orgs, verify `driverFactory` swaps credentials cleanly under concurrent queries and there's no cross-tenant caching. **Do this before merging § 4.2.**
2. **Reranker in v1: ship with or without?** Cohere Rerank adds ~50–100ms latency and one more vendor dependency. Alternative: ship without in v1, add if precision measurably suffers. Decision: start without; add if eval < 80%.
3. **Embedding provider**: `text-embedding-3-small` vs `voyage-3-lite`. Voyage is ~30% cheaper and comparable quality on similar tasks. Cost impact at 20 orgs is small either way. Decision: OpenAI for v1 (simpler auth story alongside LLM calls), swap if cost becomes a factor.
4. **Confidence threshold for pre-emptive refusal** (`top_entity_score < X`) — X to be tuned on the eval set, not guessed. Start at 0.35, adjust from first cohort's data.
5. **LLM #1 model choice**: Sonnet 4.6 as default. Haiku 4.5 is cheap and fast but likely misses on constrained JSON with novel schema; verify with an eval before switching down.
6. **PII masking policy in Cube** — do we mask PII columns unconditionally, or expose them to specific roles? V1 answer: PII columns excluded from LLM prompt entirely (don't retrieve them into schema block). Cube can still query them for aggregations if the measure needs them, but the columns aren't dimensions in the semantic layer. Formalize this in the embedding-doc generator.
7. **Follow-up-in-session state**: does the orchestrator carry prior turn's resolved semantic query into the next turn's prompt, or is each turn independent + retrieval-only? V1: pass prior turn's resolved query as an extra context block ("Previous question resolved to: {sq}") for at most 2 turns. Skip fancier dialogue state.
8. **Curator-queue frequency roll-up**: fingerprint by exact-question-hash is too tight; fingerprint by embedding cluster is fancy. V1: hash of `(normalized_question_stem)`. Good enough.

---

## 8. Testing

- **Unit tests** for converters: dbt manifest → OSI, OSI → Cube JS, OSI → embedding doc. Golden inputs, golden outputs.
- **Unit tests** for `SemanticQueryValidator`.
- **Integration test** for `driverFactory` / `repositoryFactory` cross-tenant isolation. Two mock orgs, verify no cross-leakage in schema OR data OR cache.
- **Retrieval quality tests**: seed a small semantic layer + 20 golden Q→expected-top-8 entities. Assert top-8 recall on the eval set. Fails PR if regression.
- **End-to-end eval harness**: golden Q→A pairs per test org. Runs full pipeline (retrieve → LLM #1 → validate → Cube → LLM #2). Metrics: semantic-query exact-match rate, row-set match rate, refusal precision. Runs on CI for changes to prompts, retrieval code, embedding docs, or model versions.
- **UI tests**: playwright for FAB open, message send, SSE stream consumption, refusal → "Fix this" navigation, provenance card expand.

---

## 9. Milestones

1. **M1 — Data model & migrations** (~1 week). All tables, `pgvector` enabled, Metric extension migration + backfill on staging.
2. **M2 — Semantic layer authoring backend** (~1 week). CRUD APIs, dbt bootstrap, OSI → Cube generator, embedding doc generator, embedding worker.
3. **M3 — Cube service integration** (~1 week). Cube in dev config, `driverFactory` + `repositoryFactory` wired, cross-tenant isolation test green. **Depends on M1.**
4. **M4 — Retrieval + LLM orchestrator** (~1.5 weeks). Retrieval service, prompt builder, semantic-query LLM call, validator, repair loop, narration LLM, Cube call. Command-line testable before SSE. **Depends on M2, M3.**
5. **M5 — SSE endpoint + frontend chat surface** (~1.5 weeks). Streaming endpoint, `<ChatFAB>`, `<ChatDrawer>`, `<ChatFullPage>` on Explore, provenance card, refusal UX. **Depends on M4.**
6. **M6 — Semantic layer editor UI** (~2 weeks). All editor pages in webapp_v2. **Depends on M2.**
7. **M7 — Curator queue** (~0.5 weeks). Queue page + resolve flow. **Depends on M5, M6.**
8. **M8 — Eval harness + first NGO onboarding** (~1 week). Golden set, CI integration, first partner NGO onboarded end-to-end.

Total: ~9.5 engineering weeks with parallelism (M4 and M6 can run partly in parallel after M2). Realistic calendar: 12 weeks with rollout overhead.

---

*Feedback? Comment on this doc or ping the eng lead. Spec: [../spec.md](../spec.md).*
