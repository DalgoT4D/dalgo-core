# Chat with Dashboard — Accuracy Improvement Plan

## Adopting WrenAI Patterns in Dalgo's Existing LangGraph Architecture

**Date**: 2026-04-24
**Branch**: `codex/pratiksha-chat-with-dashboards-impl` (DDP_backend)
**Scope**: DDP_backend only (single service changes)

---

## 1. Problem Statement

Dalgo's current chat-with-dashboard produces lower SQL accuracy than WrenAI. Root cause analysis identifies five architectural gaps between the two systems:

| Gap | Dalgo (Current) | WrenAI (Target Pattern) |
|-----|-----------------|------------------------|
| Schema presentation | LLM discovers schema incrementally via tool calls | LLM receives pre-assembled DDL with semantic comments upfront |
| Retrieval strategy | Single flat search across 5 mixed source types, 6 results max | Two-stage: table descriptions first, then full column fetch |
| SQL generation prompt | 16 general-purpose rules in a tool-use prompt | 40+ SQL-specific rules in a dedicated generation prompt |
| SQL validation | Regex keyword checks + allowlist only | Semantic dry-run (EXPLAIN) + LLM correction loop (3 retries) |
| Few-shot learning | None | Past successful question→SQL pairs injected as examples |

---

## 2. High-Level Design

The improvements fit **inside the existing LangGraph StateGraph** without changing the graph shape. The core idea: enrich the context the LLM sees **before** the tool loop starts, and add a validation+correction step **after** SQL is generated.

### Current Flow (unchanged graph shape)

```
START → load_context → route_intent → handle_query_with_sql → compose_response → finalize → END
```

### What Changes Inside Each Node

```
load_context:
  + Build DDL schema context from allowlist + dbt metadata + warehouse columns
  + Store in state as `ddl_schema_context`

handle_query_with_sql:
  + Inject DDL schema + few-shot examples into system prompt
  + Enhanced SQL rules in system prompt
  + After tool loop: EXPLAIN validation + correction loop (up to 3 retries)

handle_follow_up_sql:
  + Same DDL injection + correction loop
```

### New Components (no new graph nodes)

```
ddpui/core/dashboard_chat/
├── context/
│   └── ddl_schema_builder.py          # NEW: Build DDL from allowlist + dbt + warehouse
├── context/
│   └── sql_few_shot_store.py          # NEW: Store/retrieve successful Q→SQL pairs
├── warehouse/
│   └── sql_guard.py                   # MODIFY: Add EXPLAIN-based semantic validation
├── agents/
│   └── prompt_template_store.py       # MODIFY: Enhanced SQL generation prompt
├── orchestration/
│   └── nodes/load_context.py          # MODIFY: Build DDL context
│   └── nodes/handle_query_with_sql.py # MODIFY: Inject DDL + few-shot + correction loop
│   └── nodes/handle_follow_up_sql.py  # MODIFY: Same injection + correction loop
│   └── llm_tools/runtime/
│       └── tool_loop_message_builder.py # MODIFY: Include DDL + few-shot in messages
```

---

## 3. Implementation Phases

### Phase 1: Pre-assembled DDL Schema Context (HIGH IMPACT)

**Goal**: Give the LLM a complete DDL representation of all allowlisted tables upfront, so it doesn't need to discover schema through tool calls.

#### 3.1.1 New File: `ddpui/core/dashboard_chat/context/ddl_schema_builder.py`

**Purpose**: Convert allowlist + dbt index + warehouse column metadata into DDL-with-comments format.

**Input**:
- `allowlist: DashboardChatAllowlist` (already built in load_context)
- `dbt_index: dict` (already built in load_context, contains columns, descriptions, relationships)
- `warehouse_tools: DashboardChatWarehouseTools` (for live column types when dbt metadata is incomplete)

**Output**: A string containing DDL statements like:

```sql
/* {"description": "Student assessment scores by school"} */
CREATE TABLE staging.assessment_scores (
  -- {"description": "Unique student identifier"}
  student_id VARCHAR,
  -- {"description": "Assessment score percentage"}
  score DOUBLE,
  -- {"description": "School where assessment was taken"}
  school_name VARCHAR
);

/* {"description": "School master data"} */
CREATE TABLE staging.schools (
  school_id VARCHAR,
  school_name VARCHAR,
  district VARCHAR,
  state VARCHAR
);
```

**Implementation approach**:

```python
"""Build DDL-with-comments schema context from dashboard allowlist and dbt metadata."""

from ddpui.core.dashboard_chat.context.dashboard_table_allowlist import DashboardChatAllowlist


class DDLSchemaBuilder:
    """Convert allowlist + dbt index into DDL-with-comments for LLM context."""

    def __init__(
        self,
        allowlist: DashboardChatAllowlist,
        dbt_index: dict,
        schema_snippets: dict | None = None,
    ):
        self.allowlist = allowlist
        self.dbt_index = dbt_index
        self.schema_snippets = schema_snippets or {}

    def build_ddl_context(self, max_tables: int | None = None) -> str:
        """Build complete DDL string for allowlisted tables.

        Prioritizes chart tables over upstream lineage tables.
        Falls back to warehouse schema snippets when dbt metadata
        lacks column info.
        """
        tables = self.allowlist.prioritized_tables(limit=max_tables)
        ddl_blocks: list[str] = []
        for table in tables:
            ddl = self._build_table_ddl(table)
            if ddl:
                ddl_blocks.append(ddl)
        return "\n\n".join(ddl_blocks)

    def _build_table_ddl(self, table_name: str) -> str | None:
        """Build one CREATE TABLE statement with embedded metadata comments."""
        # 1. Try dbt index for rich metadata (descriptions, types)
        # 2. Fall back to warehouse schema snippets for column types
        # 3. Embed descriptions as SQL comments
        # 4. Add relationship info as FOREIGN KEY comments if available
        ...
```

**Key design decisions**:
- **Prioritize chart tables**: `allowlist.prioritized_tables()` already returns chart tables first, upstream tables second. This ensures the most relevant tables appear first in the DDL context.
- **dbt index as primary source**: The compact dbt index (built in `load_context`) already has column names, types, and descriptions. Use this first.
- **Warehouse schema as fallback**: When dbt metadata lacks column info (e.g., for sources without schema.yml docs), fall back to `schema_snippets` from the warehouse client.
- **PostgreSQL vs BigQuery**: DDL format is warehouse-agnostic — it's for LLM context, not execution. Use generic SQL types (VARCHAR, INTEGER, DOUBLE, TIMESTAMP, BOOLEAN). The `dbt_index` already stores column types from dbt, and `schema_snippets` stores types from the warehouse. Map both to generic types.
- **Size control**: Add `max_tables` parameter. Default to allowlist size (typically 5-15 tables per dashboard). If the DDL exceeds a token budget (configurable, e.g., 4000 tokens), truncate upstream tables first.

#### 3.1.2 Modify: `ddpui/core/dashboard_chat/orchestration/nodes/load_context.py`

**Change**: After building allowlist and dbt_index, also build DDL schema context.

```python
# In load_context_node(), after allowlist and dbt_index are built:

from ddpui.core.dashboard_chat.context.ddl_schema_builder import DDLSchemaBuilder

# Load schema snippets for allowlisted tables (from warehouse)
warehouse_tools = DashboardChatWarehouseTools(org=org)
schema_snippets = warehouse_tools.get_schema_snippets(
    allowlist.prioritized_tables()
)

ddl_builder = DDLSchemaBuilder(
    allowlist=allowlist,
    dbt_index=dbt_index,
    schema_snippets=schema_snippets_dict,
)
ddl_schema_context = ddl_builder.build_ddl_context()

return {
    ...existing fields...,
    "ddl_schema_context": ddl_schema_context,
    "schema_snippet_payloads": serialize_schema_snippets(schema_snippets),
}
```

**Note on warehouse type differences**: `warehouse_tools.get_schema_snippets()` already handles both PostgreSQL and BigQuery via the `Warehouse` abstract interface. The DDL builder receives normalized `DashboardChatSchemaSnippet` objects regardless of warehouse type.

#### 3.1.3 Modify: `ddpui/core/dashboard_chat/orchestration/state/graph_state.py`

**Change**: Add `ddl_schema_context` field.

```python
class DashboardChatGraphState(TypedDict, total=False):
    ...existing fields...
    ddl_schema_context: str | None  # Pre-assembled DDL for LLM context
```

#### 3.1.4 Modify: `ddpui/core/dashboard_chat/orchestration/tool_loop_message_builder.py`

**Change**: Inject DDL schema into system prompt for both new queries and follow-ups.

```python
def build_new_query_messages(llm_client, state) -> list[dict[str, Any]]:
    system_prompt = llm_client.get_prompt(DashboardChatPromptTemplateKey.NEW_QUERY_SYSTEM)

    # Inject DDL schema context
    ddl_context = state.get("ddl_schema_context") or ""
    if ddl_context:
        system_prompt += f"\n\n### DATABASE SCHEMA ###\n{ddl_context}"

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["user_query"]},
    ]
```

Same pattern for `build_follow_up_messages()`.

#### 3.1.5 Tests

**File**: `ddpui/tests/core/dashboard_chat/test_ddl_schema_builder.py`

Test cases:
1. `test_build_ddl_from_dbt_index_with_descriptions` — dbt index has full column metadata → DDL includes descriptions as comments
2. `test_build_ddl_falls_back_to_warehouse_schema` — dbt index has no columns → uses schema snippets
3. `test_build_ddl_prioritizes_chart_tables` — chart tables appear before upstream tables in DDL
4. `test_build_ddl_max_tables_limit` — respects max_tables parameter
5. `test_build_ddl_empty_allowlist` — returns empty string for no tables
6. `test_build_ddl_mixed_dbt_and_warehouse` — some tables have dbt metadata, some only warehouse schema
7. `test_build_ddl_generic_types` — warehouse-specific types (e.g., BigQuery STRING) mapped to generic SQL types
8. `test_build_ddl_with_relationships` — dbt relationships rendered as FOREIGN KEY comments
9. `test_ddl_injected_in_new_query_messages` — verify DDL appears in system prompt
10. `test_ddl_injected_in_follow_up_messages` — verify DDL appears in follow-up system prompt

**Testing pattern** (follow existing `test_runtime.py`):
```python
@pytest.mark.django_db
class TestDDLSchemaBuilder:
    def test_build_ddl_from_dbt_index_with_descriptions(self):
        allowlist = DashboardChatAllowlist(
            chart_tables={"staging.students"},
            upstream_tables=set(),
            allowed_tables={"staging.students"},
            ...
        )
        dbt_index = {
            "resources_by_unique_id": {
                "model.project.students": {
                    "table": "staging.students",
                    "columns": [
                        {"name": "student_id", "type": "VARCHAR", "description": "Unique ID"},
                        {"name": "score", "type": "DOUBLE", "description": "Test score"},
                    ],
                    "description": "Student assessment data",
                }
            }
        }
        builder = DDLSchemaBuilder(allowlist=allowlist, dbt_index=dbt_index)
        ddl = builder.build_ddl_context()

        assert "CREATE TABLE staging.students" in ddl
        assert "Unique ID" in ddl
        assert "student_id" in ddl
```

---

### Phase 2: Enhanced SQL Generation Prompt (HIGH IMPACT)

**Goal**: Replace the 16-rule general prompt with a comprehensive SQL-specific prompt (40+ rules).

#### 3.2.1 Modify: `ddpui/core/dashboard_chat/agents/prompt_template_store.py`

**Change**: Rewrite `PROTOTYPE_NEW_QUERY_SYSTEM_PROMPT` with WrenAI-inspired SQL rules.

The new prompt should include these rule categories:

**Structural rules**:
- Always use CTEs (WITH clauses) instead of subqueries for readability
- Every CTE must be referenced in the final query
- Always qualify column names with table aliases in JOINs
- Use explicit JOIN syntax, never comma-separated FROM
- Always include a GROUP BY when using aggregate functions

**Data handling rules**:
- Use LOWER() for case-insensitive text comparisons
- Use COALESCE() to handle NULL values in comparisons
- For date/time filtering, use date functions, not string comparisons
- When counting entities, use COUNT(DISTINCT identifier) not COUNT(*)
- For percentage calculations, cast numerator to FLOAT/DOUBLE before division
- Never use HAVING without GROUP BY

**Safety rules**:
- Always include LIMIT (max 200)
- Only SELECT queries allowed
- Only reference tables from the provided DATABASE SCHEMA section
- Never fabricate table or column names not in the schema

**Output rules**:
- When proposing SQL, immediately call run_sql_query — do not ask for confirmation
- Only call get_distinct_values for columns you plan to filter in WHERE clauses
- Use the EXACT schema-qualified table names from the schema

**Warehouse compatibility** (both PostgreSQL and BigQuery):
- Use standard SQL syntax that works across dialects
- For string concatenation, use `CONCAT()` not `||` (BigQuery compatibility)
- For date extraction, use `EXTRACT(YEAR FROM col)` syntax
- Avoid PostgreSQL-specific functions like `TO_CHAR`; use `CAST` instead
- Avoid BigQuery-specific backtick quoting in the generated SQL — the system handles quoting

```python
PROTOTYPE_NEW_QUERY_SYSTEM_PROMPT = """You are a data analysis assistant with access to tools and a pre-loaded database schema. Your job is to answer data questions accurately using SQL.

### IMPORTANT WORKFLOW ###
1. Review the DATABASE SCHEMA section below — it contains all accessible tables and columns
2. Use chart metadata from retrieve_docs to understand which tables are relevant
3. Call get_distinct_values ONLY for columns you will filter in WHERE clauses
4. Write and execute SQL immediately via run_sql_query — never ask for confirmation

### SQL RULES ###

## Structure
1. Use CTEs (WITH clauses) instead of subqueries
2. Every CTE must be referenced in the final SELECT
3. Always qualify column names with table aliases when using JOINs
4. Use explicit JOIN ... ON syntax, never comma-separated FROM
5. Always include GROUP BY when using aggregate functions
6. Use table aliases for readability (e.g., FROM staging.students AS s)

## Data Handling
7. Use LOWER(column) for case-insensitive text comparisons
8. Use COALESCE(column, default) to handle NULLs in comparisons
9. For date filtering, use EXTRACT() or date functions, not string comparison
10. For counting entities, use COUNT(DISTINCT identifier_column), not COUNT(*)
11. For percentages, CAST numerator to FLOAT before division
12. Never use HAVING without GROUP BY
13. Use CAST() for type conversions, not dialect-specific functions
14. For string concatenation use CONCAT(), not ||
15. For rounding, use ROUND(value, decimal_places)
16. When ordering by aggregates, repeat the expression or use a CTE

## Safety
17. Always include LIMIT (maximum 200 rows)
18. Only write SELECT queries — no INSERT, UPDATE, DELETE, DROP
19. Only reference tables listed in DATABASE SCHEMA — never guess table names
20. Only reference columns listed in the schema for each table
21. Never fabricate column names — if unsure, call get_schema_snippets first

## Tools
22. Call retrieve_docs first to find relevant charts and context
23. Use chart metadata (preferred_table, metric_columns, dimension_columns) to guide queries
24. Call get_distinct_values before using WHERE on text columns — required
25. Call get_schema_snippets only for tables not already in DATABASE SCHEMA
26. Call list_tables_by_keyword only if no relevant table is found in the schema
27. After writing SQL, always call run_sql_query immediately
28. If run_sql_query returns an error, fix the SQL and retry — do not give up

## Query Patterns
29. For "top N" questions: ORDER BY metric DESC LIMIT N
30. For "trend over time": GROUP BY time_period ORDER BY time_period
31. For "comparison": GROUP BY dimension with appropriate aggregates
32. For "changes": Compare values across time periods using self-joins or window functions
33. For geographic questions: Use the most specific location column available, note any substitution
34. For "breakdown by X": GROUP BY X with metrics
35. If a requested column is missing, use the closest available alternative and note it

## Response
36. Stay within the current dashboard scope — do not suggest other dashboards
37. Use the EXACT schema-qualified table names from the schema or tools
38. Prefer simpler queries when possible — avoid unnecessary joins
39. When multiple approaches exist, prefer the one using fewer tables

### SQL EXAMPLES ###
{few_shot_examples}

Available tools:
- retrieve_docs: Find relevant charts, datasets, context, or dbt models
- search_dbt_models: Search for dbt models by keyword
- get_dbt_model_info: Get detailed info about a specific dbt model
- get_schema_snippets: Get column names and types for tables
- get_distinct_values: Get actual values in a column (required before WHERE on text)
- check_table_row_count: Check if a table has data before querying
- run_sql_query: Execute a read-only SQL query
- list_tables_by_keyword: Find tables by name or column keyword"""
```

**Note**: The `{few_shot_examples}` placeholder will be filled at runtime (Phase 4).

#### 3.2.2 Modify: `ddpui/core/dashboard_chat/agents/prompt_template_store.py` (follow-up prompt)

Update `PROTOTYPE_FOLLOW_UP_SYSTEM_PROMPT` with the same SQL rules section, plus follow-up-specific instructions.

#### 3.2.3 Tests

**File**: `ddpui/tests/core/dashboard_chat/test_prompt_templates.py`

Test cases:
1. `test_new_query_prompt_contains_sql_rules` — verify key rules are present
2. `test_new_query_prompt_contains_few_shot_placeholder` — verify `{few_shot_examples}` placeholder exists
3. `test_follow_up_prompt_contains_sql_rules` — verify follow-up has same rules
4. `test_db_backed_prompt_overrides_default` — verify DB-stored prompt takes precedence
5. `test_default_prompt_used_when_no_db_entry` — verify fallback works

---

### Phase 3: SQL Dry-Run Validation + Correction Loop (HIGH IMPACT)

**Goal**: Before returning SQL results, validate the SQL semantically via EXPLAIN, and if it fails, feed the error back to the LLM for correction (up to 3 retries).

#### 3.3.1 Modify: `ddpui/core/dashboard_chat/warehouse/warehouse_access_tools.py`

**Add method**: `explain_sql(sql: str) -> dict`

```python
def explain_sql(self, sql: str) -> dict:
    """Run EXPLAIN on SQL to validate it semantically without executing.

    Returns:
        {"valid": True} on success.
        {"valid": False, "error": "error message"} on failure.

    Works for both PostgreSQL (EXPLAIN) and BigQuery (dry_run via query job config).
    """
    try:
        wtype = self.warehouse_client.get_wtype()
        if wtype == "bigquery":
            # BigQuery: use dry_run job config
            # The BigQuery client supports dry_run which validates
            # without executing and returns bytes processed
            from google.cloud import bigquery as bq
            client = self.warehouse_client.client  # underlying BQ client
            job_config = bq.QueryJobConfig(dry_run=True, use_query_cache=False)
            client.query(sql, job_config=job_config)
            return {"valid": True}
        else:
            # PostgreSQL: use EXPLAIN (no ANALYZE — don't execute)
            self.warehouse_client.execute(f"EXPLAIN {sql}")
            return {"valid": True}
    except Exception as e:
        return {"valid": False, "error": str(e)}
```

**Important BigQuery note**: The BigQuery SQLAlchemy driver may not expose `dry_run` directly. Alternative approach — wrap the SQL in a `SELECT * FROM (original_sql) WHERE FALSE` to get schema validation without returning rows. This works on both PostgreSQL and BigQuery:

```python
def explain_sql(self, sql: str) -> dict:
    """Validate SQL semantically without executing by wrapping in a no-row query."""
    validation_sql = f"SELECT * FROM ({sql}) AS _validation_check WHERE FALSE"
    try:
        self.warehouse_client.execute(validation_sql)
        return {"valid": True}
    except Exception as e:
        return {"valid": False, "error": str(e)}
```

This approach is **warehouse-agnostic** — works on both PostgreSQL and BigQuery without needing dialect-specific EXPLAIN syntax or BigQuery dry_run API access.

#### 3.3.2 Modify: `ddpui/core/dashboard_chat/orchestration/llm_tools/implementations/sql_execution_tools.py`

**Add**: SQL correction loop after validation failure.

The correction loop wraps the existing `handle_run_sql_query_tool` logic:

```python
MAX_SQL_CORRECTION_RETRIES = 3

def handle_run_sql_query_tool(
    warehouse_tools_factory, runtime_config, args, state, turn_context
):
    sql = (args.get("sql") or "").strip()
    if not sql:
        return {"error": "No SQL provided", "success": False}

    # Existing validation: allowlist, distinct values, sql_guard...
    validation_result = _validate_sql(sql, state, turn_context, ...)

    if not validation_result.is_valid:
        return {"error": ..., "success": False}

    # NEW: Semantic validation via EXPLAIN / dry-run
    warehouse_tools = get_turn_warehouse_tools(warehouse_tools_factory, turn_context, state)
    explain_result = warehouse_tools.explain_sql(validation_result.sanitized_sql)

    if not explain_result["valid"]:
        # Return error to the LLM with the specific database error
        # The tool loop will naturally retry — the LLM sees the error
        # in the tool result and generates corrected SQL
        return {
            "success": False,
            "error": f"SQL validation failed: {explain_result['error']}",
            "sql_used": validation_result.sanitized_sql,
            "hint": "Fix the SQL based on the error message and try again.",
        }

    # Existing execution logic...
    rows = warehouse_tools.execute_sql(validation_result.sanitized_sql)
    ...
```

**Key insight**: The existing tool loop already supports retries naturally. When `run_sql_query` returns an error, the LLM sees it and generates corrected SQL in the next tool loop iteration. The 15-turn limit provides an implicit retry budget. We don't need to add a separate correction loop — the existing tool loop IS the correction loop. The EXPLAIN step just catches errors earlier (before execution) and provides better error messages.

**However**, to make the correction more focused (like WrenAI's dedicated correction prompt), we can add the DDL schema context to the error message:

```python
if not explain_result["valid"]:
    ddl_context = state.get("ddl_schema_context") or ""
    return {
        "success": False,
        "error": (
            f"SQL validation failed: {explain_result['error']}\n\n"
            f"Review the DATABASE SCHEMA and fix the query:\n{ddl_context[:2000]}"
        ),
        "sql_used": validation_result.sanitized_sql,
    }
```

#### 3.3.3 Tests

**File**: `ddpui/tests/core/dashboard_chat/test_sql_dry_run.py`

Test cases:
1. `test_explain_sql_valid_query_postgres` — valid SQL returns `{"valid": True}`
2. `test_explain_sql_invalid_column_postgres` — invalid column returns error
3. `test_explain_sql_valid_query_bigquery` — same for BigQuery
4. `test_explain_sql_invalid_table_bigquery` — same for BigQuery
5. `test_explain_sql_fallback_on_exception` — unexpected errors return `{"valid": False}`
6. `test_tool_loop_retries_after_explain_failure` — LLM receives error and generates corrected SQL
7. `test_explain_runs_before_execution` — EXPLAIN is called before execute_sql

**Testing approach for warehouse-agnostic EXPLAIN**:

```python
class FakeWarehouseClient:
    """Stub that simulates both PG and BQ behavior."""

    def __init__(self, wtype="postgres", fail_explains=None):
        self.wtype = wtype
        self.fail_explains = fail_explains or set()

    def get_wtype(self):
        return self.wtype

    def execute(self, sql):
        # If the SQL references a table in fail_explains, raise
        for pattern in self.fail_explains:
            if pattern in sql:
                raise Exception(f'column "nonexistent" does not exist')
        return []
```

---

### Phase 4: Few-Shot Examples from Past Successful Queries (HIGH IMPACT)

**Goal**: Store successful question→SQL pairs and retrieve similar ones as few-shot examples at query time.

#### 3.4.1 New File: `ddpui/core/dashboard_chat/context/sql_few_shot_store.py`

**Purpose**: Manage a per-org Chroma collection of successful Q→SQL pairs.

```python
"""Store and retrieve successful question→SQL pairs for few-shot prompting."""

from ddpui.core.dashboard_chat.vector.org_vector_store import OrgVectorStore
from ddpui.core.dashboard_chat.vector.vector_documents import DashboardChatVectorDocument


SQL_PAIRS_SOURCE_TYPE = "sql_pairs"
DEFAULT_FEW_SHOT_LIMIT = 3
SIMILARITY_THRESHOLD = 0.7


class SqlFewShotStore:
    """Manage question→SQL pairs in the org vector collection."""

    def __init__(self, vector_store: OrgVectorStore):
        self.vector_store = vector_store

    def store_successful_pair(
        self,
        org_id: int,
        question: str,
        sql: str,
        dashboard_id: int | None = None,
        collection_name: str | None = None,
    ) -> str:
        """Store a thumbs-up question→SQL pair."""
        doc = DashboardChatVectorDocument(
            org_id=org_id,
            source_type=SQL_PAIRS_SOURCE_TYPE,
            source_identifier=f"sql_pair:{hash(question + sql)}",
            content=question,
            dashboard_id=dashboard_id,
            title=question[:100],
            chunk_index=0,
        )
        # Store SQL in metadata (not in content, which is used for embedding)
        self.vector_store.upsert_documents(
            org_id, [doc], collection_name=collection_name,
            extra_metadata={"sql": sql},
        )
        return doc.document_id

    def retrieve_similar_pairs(
        self,
        org_id: int,
        query: str,
        limit: int = DEFAULT_FEW_SHOT_LIMIT,
        collection_name: str | None = None,
    ) -> list[dict]:
        """Retrieve similar past Q→SQL pairs for few-shot injection."""
        results = self.vector_store.query(
            org_id,
            query_text=query,
            n_results=limit,
            source_types=[SQL_PAIRS_SOURCE_TYPE],
            collection_name=collection_name,
        )
        pairs = []
        for doc in results:
            sql = doc.get("metadata", {}).get("sql")
            if sql:
                pairs.append({
                    "question": doc.get("content", ""),
                    "sql": sql,
                })
        return pairs
```

**Design decisions**:
- **Embedding the question, not the SQL**: The question text is embedded and stored as document content. The SQL is stored in metadata. This way, similarity search matches questions, not SQL syntax.
- **Per-org isolation**: Uses existing org-scoped vector collections. SQL pairs live alongside other document types with `source_type=sql_pairs`.
- **Trigger**: Pairs are stored when a user gives thumbs-up feedback on an assistant message that contains SQL.

#### 3.4.2 New Source Type: `ddpui/core/dashboard_chat/vector/vector_documents.py`

**Change**: Add `SQL_PAIRS` to source types.

```python
class DashboardChatSourceType(str, Enum):
    ORG_CONTEXT = "org_context"
    DASHBOARD_CONTEXT = "dashboard_context"
    DASHBOARD_EXPORT = "dashboard_export"
    DBT_MANIFEST = "dbt_manifest"
    DBT_CATALOG = "dbt_catalog"
    SQL_PAIRS = "sql_pairs"  # NEW
```

#### 3.4.3 Modify: Feedback Handler

When a user gives `thumbs_up` feedback on a message with SQL, store the Q→SQL pair.

**File to modify**: Find the existing feedback endpoint (likely in `ddpui/api/` or `ddpui/websockets/dashboard_chat_consumer.py`).

```python
# In the feedback handler:
if feedback == DashboardChatMessageFeedback.THUMBS_UP:
    payload = message.payload or {}
    sql = payload.get("sql")
    if sql:
        few_shot_store = SqlFewShotStore(vector_store=OrgVectorStore())
        few_shot_store.store_successful_pair(
            org_id=session.org_id,
            question=user_message.content,
            sql=sql,
            dashboard_id=session.dashboard_id,
        )
```

#### 3.4.4 Modify: `ddpui/core/dashboard_chat/orchestration/tool_loop_message_builder.py`

**Change**: Retrieve and inject few-shot examples into the system prompt.

```python
def build_new_query_messages(llm_client, state, vector_store=None) -> list[dict[str, Any]]:
    system_prompt = llm_client.get_prompt(DashboardChatPromptTemplateKey.NEW_QUERY_SYSTEM)

    # Inject DDL schema context
    ddl_context = state.get("ddl_schema_context") or ""
    if ddl_context:
        system_prompt += f"\n\n### DATABASE SCHEMA ###\n{ddl_context}"

    # Inject few-shot examples
    few_shot_text = ""
    if vector_store:
        few_shot_store = SqlFewShotStore(vector_store=vector_store)
        pairs = few_shot_store.retrieve_similar_pairs(
            org_id=state["org_id"],
            query=state["user_query"],
            collection_name=state.get("vector_collection_name"),
        )
        if pairs:
            examples = []
            for pair in pairs:
                examples.append(f"Question: {pair['question']}\nSQL: {pair['sql']}")
            few_shot_text = "\n\n".join(examples)

    system_prompt = system_prompt.replace("{few_shot_examples}", few_shot_text or "No examples available yet.")

    return [
        {"role": "system", "content": system_prompt},
        {"role": "user", "content": state["user_query"]},
    ]
```

#### 3.4.5 Tests

**File**: `ddpui/tests/core/dashboard_chat/test_sql_few_shot_store.py`

Test cases:
1. `test_store_and_retrieve_pair` — store a pair, retrieve it by similar question
2. `test_retrieve_returns_empty_for_no_matches` — no stored pairs → empty list
3. `test_retrieve_limit_respected` — only returns requested number of pairs
4. `test_pair_stored_on_thumbs_up_feedback` — feedback handler triggers storage
5. `test_pair_not_stored_on_thumbs_down` — negative feedback doesn't store
6. `test_pair_not_stored_without_sql` — context-only answers don't store
7. `test_few_shot_injected_in_system_prompt` — verify examples appear in prompt
8. `test_few_shot_placeholder_replaced_when_no_pairs` — placeholder replaced with fallback text

---

### Phase 5: Two-Stage Retrieval (HIGH IMPACT)

**Goal**: Replace flat vector search with two-stage retrieval: (1) find relevant tables, (2) fetch full schema for those tables.

#### 3.5.1 Modify: `ddpui/core/dashboard_chat/orchestration/llm_tools/implementations/vector_retrieval_tool.py`

**Change**: When retrieving dbt/dataset documents, use two-stage approach.

**Current**: Single flat search across mixed source types with limit=6.

**New**:
1. First retrieve from a "table descriptions" subset (just table name + description + column list) to identify relevant tables
2. Then deterministically fetch full schema for those tables from dbt_index

Since we already have DDL schema context injected in the prompt (Phase 1), the retrieval tool becomes less critical for schema discovery. The main value of retrieval shifts to:
- Finding relevant **charts** (which tables are used in the dashboard's visualizations)
- Finding relevant **context** (org/dashboard markdown docs)
- Finding **dbt model descriptions** (business context beyond column types)

**Implementation**:

```python
def handle_retrieve_docs_tool(vector_store, source_config, runtime_config, args, state, turn_context):
    # ... existing argument parsing ...

    # For dbt_model/dataset type requests, also search table descriptions
    # from the dbt_index deterministically
    if "dataset" in requested_types or "dbt_model" in requested_types:
        dbt_index = state.get("dbt_index") or {}
        resources = dbt_index.get("resources_by_unique_id", {})
        query_lower = query.lower()

        # Deterministic table matching from dbt index
        matching_resources = []
        for uid, resource in resources.items():
            name = (resource.get("name") or "").lower()
            desc = (resource.get("description") or "").lower()
            table = (resource.get("table") or "").lower()
            if query_lower in name or query_lower in desc or query_lower in table:
                matching_resources.append(resource)

        # Include these as additional context in the response
        if matching_resources:
            for resource in matching_resources[:5]:
                deterministic_docs.append({
                    "type": "dbt_model",
                    "source": "dbt_index",
                    "table": resource.get("table"),
                    "description": resource.get("description"),
                    "columns": [c["name"] for c in resource.get("columns", [])[:20]],
                })

    # Still do vector search for fuzzy matching
    # ... existing vector retrieval code ...
```

This is a lighter change since Phase 1 already provides the full DDL schema. The two-stage retrieval here is additive — deterministic dbt index lookup + existing vector search.

#### 3.5.2 Tests

Add to existing `test_runtime.py` or create `test_two_stage_retrieval.py`:

1. `test_retrieve_docs_includes_dbt_index_matches` — keyword match against dbt index returns results
2. `test_retrieve_docs_dbt_index_plus_vector_deduped` — no duplicates between deterministic and vector results
3. `test_retrieve_docs_dbt_index_empty_when_no_match` — no false positives from deterministic search

---

## 4. Data Model Changes

### New State Field

Add to `DashboardChatGraphState`:
```python
ddl_schema_context: str | None  # Pre-assembled DDL for LLM context
```

### New Source Type

Add to `DashboardChatSourceType`:
```python
SQL_PAIRS = "sql_pairs"
```

### No New Django Models Required

- SQL pairs are stored in Chroma (vector DB), not PostgreSQL
- The existing `DashboardChatMessage.feedback` field already tracks thumbs up/down
- The existing `DashboardChatMessage.payload` already stores SQL

### No Database Migrations Required

---

## 5. Configuration Changes

### New Environment Variables

```bash
# DDL Schema Context
AI_DASHBOARD_CHAT_DDL_MAX_TABLES=20          # Max tables in DDL context (default: 20)
AI_DASHBOARD_CHAT_DDL_MAX_TOKENS=4000        # Approximate token budget for DDL (default: 4000)

# Few-Shot Examples
AI_DASHBOARD_CHAT_FEW_SHOT_LIMIT=3           # Max few-shot examples to inject (default: 3)

# SQL Correction
AI_DASHBOARD_CHAT_SQL_EXPLAIN_ENABLED=true   # Enable EXPLAIN-based validation (default: true)
```

### Modify: `ddpui/core/dashboard_chat/config.py`

Add to `DashboardChatRuntimeConfig`:
```python
ddl_max_tables: int = 20
ddl_max_tokens: int = 4000
few_shot_limit: int = 3
sql_explain_enabled: bool = True
```

---

## 6. Warehouse Compatibility Matrix

Every change must work for both PostgreSQL and BigQuery:

| Change | PostgreSQL | BigQuery | Notes |
|--------|-----------|----------|-------|
| DDL schema builder | Generic SQL types | Generic SQL types | DDL is for LLM context, not execution |
| SQL prompt rules | Standard SQL | Standard SQL | Avoids dialect-specific functions |
| EXPLAIN validation | `EXPLAIN sql` | `SELECT * FROM (sql) WHERE FALSE` | Use warehouse-agnostic wrapper approach |
| Few-shot storage | Chroma (same) | Chroma (same) | Vector DB is warehouse-independent |
| Schema snippets | `get_table_columns()` | `get_table_columns()` | Already abstracted via Warehouse interface |

**The warehouse-agnostic EXPLAIN approach** (`SELECT * FROM (sql) WHERE FALSE`) is the recommended implementation because:
1. Works identically on both PostgreSQL and BigQuery
2. Validates column existence, type compatibility, and JOIN correctness
3. Returns no rows (fast)
4. Uses the existing `warehouse_client.execute()` interface
5. No need for dialect-specific code paths

---

## 7. Rollout Strategy

### Feature Flags

All changes are behind existing `AI_DASHBOARD_CHAT` feature flag. New env vars provide fine-grained control:
- `AI_DASHBOARD_CHAT_SQL_EXPLAIN_ENABLED=false` to disable EXPLAIN validation
- `AI_DASHBOARD_CHAT_DDL_MAX_TABLES=0` to disable DDL injection
- `AI_DASHBOARD_CHAT_FEW_SHOT_LIMIT=0` to disable few-shot examples

### Implementation Order

```
Phase 1: DDL Schema Context ──────────────── (highest impact, foundation for other phases)
    │
    ├── Phase 2: Enhanced SQL Prompt ──────── (depends on Phase 1 for {few_shot_examples} placeholder)
    │
    ├── Phase 3: EXPLAIN Validation ───────── (independent, can parallelize with Phase 2)
    │
    └── Phase 4: Few-Shot Examples ────────── (depends on Phase 2 for prompt placeholder)
         │
         └── Phase 5: Two-Stage Retrieval ─── (independent, can come last since Phase 1 reduces retrieval dependency)
```

**Recommended order**: Phase 1 → Phase 2 → Phase 3 → Phase 4 → Phase 5

Each phase is independently deployable and testable. If any phase causes regressions, it can be disabled via env vars without rolling back other phases.

---

## 8. Testing Strategy

### Unit Tests (per phase)

Each phase section above includes specific test cases. All tests follow patterns from existing `test_runtime.py`:
- Use `FakeWarehouseTools`, `FakeDashboardChatVectorStore`, and LLM stubs
- Use `@pytest.mark.django_db` for DB-dependent tests
- Use `build_runtime_state()` and `build_turn_context()` helpers
- Run with: `uv run pytest ddpui/tests/core/dashboard_chat/ -v`

### Integration Tests

After all phases are deployed:

1. **End-to-end with PostgreSQL warehouse**:
   - Connect to a test PostgreSQL database with known schema
   - Ask questions, verify SQL is valid and returns correct results
   - Verify EXPLAIN validation catches invalid SQL before execution

2. **End-to-end with BigQuery warehouse**:
   - Same tests against a BigQuery dataset
   - Verify `SELECT * FROM (sql) WHERE FALSE` validation works
   - Verify DDL builder produces correct types from BigQuery schema

3. **Regression test via evals framework**:
   - Run existing `evals-chat-with-dashboard` against the golden dataset
   - Compare scores before and after changes
   - Key metrics: SQL Correctness, Table Selection, Answer Quality

### Evaluation Benchmarking

Use the existing `evals-chat-with-dashboard/` framework:

```bash
cd evals-chat-with-dashboard
# Run against local environment
uv run python evals.py

# Compare results
# Before: results/eval_before.json
# After:  results/eval_after.json
```

**Success criteria**:
- SQL Correctness score improves by ≥ 0.1 (10%) on the golden dataset
- Table Selection score maintains or improves
- No regression in Intent Correctness
- Response Latency stays under 40s threshold (EXPLAIN adds ~100-500ms)

---

## 9. Risks and Mitigations

| Risk | Impact | Mitigation |
|------|--------|------------|
| DDL context makes prompts too long (token overflow) | LLM truncates or errors | `ddl_max_tokens` config limits size; truncate upstream tables first |
| EXPLAIN adds latency to every SQL query | Higher response times | ~100-500ms per EXPLAIN; negligible vs. 10-30s total turn time |
| EXPLAIN may reject valid SQL (false positives) | Good SQL rejected | If EXPLAIN fails, fall through to execute anyway (with warning) |
| Few-shot examples from one dashboard mislead another | Wrong SQL patterns | Filter by org_id; pairs carry dashboard context; low similarity threshold |
| Enhanced prompt is too long for small models | Token budget exceeded | Use gpt-4o-mini's 128k context; DDL + prompt + few-shot fits easily |
| BigQuery EXPLAIN equivalent may behave differently | PG/BQ parity issues | Use `SELECT * FROM (sql) WHERE FALSE` — identical behavior on both |

---

## 10. Files Changed Summary

### New Files
| File | Purpose |
|------|---------|
| `ddpui/core/dashboard_chat/context/ddl_schema_builder.py` | Build DDL from allowlist + dbt + warehouse |
| `ddpui/core/dashboard_chat/context/sql_few_shot_store.py` | Store/retrieve Q→SQL pairs |
| `ddpui/tests/core/dashboard_chat/test_ddl_schema_builder.py` | DDL builder tests |
| `ddpui/tests/core/dashboard_chat/test_sql_few_shot_store.py` | Few-shot store tests |
| `ddpui/tests/core/dashboard_chat/test_sql_dry_run.py` | EXPLAIN validation tests |
| `ddpui/tests/core/dashboard_chat/test_prompt_templates.py` | Enhanced prompt tests |

### Modified Files
| File | Change |
|------|--------|
| `orchestration/state/graph_state.py` | Add `ddl_schema_context` field |
| `orchestration/nodes/load_context.py` | Build DDL context during bootstrap |
| `orchestration/tool_loop_message_builder.py` | Inject DDL + few-shot into messages |
| `orchestration/nodes/handle_query_with_sql.py` | Pass vector_store to message builder |
| `orchestration/nodes/handle_follow_up_sql.py` | Same DDL injection |
| `agents/prompt_template_store.py` | Enhanced SQL generation prompt |
| `warehouse/warehouse_access_tools.py` | Add `explain_sql()` method |
| `orchestration/llm_tools/implementations/sql_execution_tools.py` | Add EXPLAIN before execution |
| `orchestration/llm_tools/implementations/vector_retrieval_tool.py` | Add deterministic dbt index lookup |
| `vector/vector_documents.py` | Add `SQL_PAIRS` source type |
| `config.py` | Add DDL, few-shot, EXPLAIN config |

---

## 11. Confidence Score

**7/10** for one-pass implementation success.

**Rationale**:
- (+) All changes are within a single service (DDP_backend)
- (+) No new Django migrations needed
- (+) No new microservices or infrastructure
- (+) Existing test patterns are well-established and can be followed
- (+) Each phase is independently deployable with feature flags
- (+) Warehouse abstraction already handles PG/BQ differences
- (-) The `explain_sql` method needs validation on real BigQuery connections
- (-) Few-shot store requires modifying the feedback handler (location needs to be confirmed at implementation time)
- (-) Prompt engineering is inherently iterative — the enhanced prompt may need tuning after eval runs
- (-) The `upsert_documents` call for SQL pairs may need `extra_metadata` support added to `OrgVectorStore` (storing SQL in Chroma metadata)

---

## 12. References

- **WrenAI source**: https://github.com/Canner/WrenAI
  - SQL generation pipeline: `wren-ai-service/src/pipelines/generation/sql_generation.py`
  - DDL chunking: `wren-ai-service/src/pipelines/indexing/db_schema.py`
  - Table description retrieval: `wren-ai-service/src/pipelines/indexing/table_description.py`
  - SQL correction: `wren-ai-service/src/pipelines/generation/sql_correction.py`
  - SQL pairs indexing: `wren-ai-service/src/pipelines/indexing/sql_pairs.py`
- **Dalgo dashboard chat CLAUDE.md**: `DDP_backend/ddpui/core/dashboard_chat/CLAUDE.md`
- **Dalgo evals framework**: `evals-chat-with-dashboard/`
- **LangGraph docs**: https://langchain-ai.github.io/langgraph/
- **Chroma docs**: https://docs.trychroma.com/
