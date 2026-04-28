# Dalgo Consulting Process — dbt Model Development

This document captures the end-to-end consulting workflow for building dbt SQL models that transform raw NGO program data into insights and metrics. It is the reference for designing agentic skills around this workflow.

---

## Overview

The consulting engagement bridges two worlds: the client's M&E (Monitoring & Evaluation) logic, and the technical dbt data model that implements it. The workflow moves through four phases — **Discovery → Framework → Data Exploration → Model Development**.

The framework and data exploration phases have a feedback loop: the framework captures business logic first, but once raw data is explored, the calculation logic may need to be revised to reflect what is actually available in the data.

There are two tracks:
- **New engagement** — full four-phase process for a new client or program
- **Modification** — lightweight track for existing clients updating or adding metrics

---

## Flowchart — New Engagement

```mermaid
flowchart TD
    A([Start Engagement]) --> B[M&E Goal Conversation]
    B --> C[Client fills Requirements Sheet]
    C --> D[Curate Metrics List]
    D --> E[Build KPI Framework Sheet v1]
    E --> F[Ingest Raw Data via Airbyte]
    F --> G[Explore Raw Table Structure]
    G --> H{KPI Framework\nrevision needed?}
    H -- Yes --> I[Revise KPI Framework Sheet]
    I --> J[Design ER Diagram]
    H -- No --> J
    J --> K[Write Staging Models]
    K --> L[dbt run — Staging]
    L --> M{Output\ncorrect?}
    M -- No --> K
    M -- Yes --> N[Write Intermediate Models]
    N --> O[dbt run — Intermediate]
    O --> P{Output\ncorrect?}
    P -- No --> N
    P -- Yes --> Q[Write Mart Models]
    Q --> R[dbt run — Marts]
    R --> S{KPIs match\nframework?}
    S -- No --> Q
    S -- Yes --> T[Generate Data Dictionary Sheet]
    T --> U([Engagement Complete])
```

## Flowchart — Modification Track

```mermaid
flowchart TD
    A([Change Request]) --> B[Identify scope:\nnew KPI / revised logic / new data source]
    B --> C[Update KPI Framework Sheet]
    C --> D{New data source?}
    D -- Yes --> E[Ingest + Explore new tables]
    E --> F[Revise KPI Framework Sheet if needed]
    F --> G[Modify or add dbt models]
    D -- No --> G
    G --> H[dbt run — affected layers only]
    H --> I{Output correct?}
    I -- No --> G
    I -- Yes --> J[Update schema.yml]
    J --> K[Update Data Dictionary Sheet]
    K --> L([Done])
```

---

## Phase 1: Discovery

**Goal:** Understand what the client is trying to measure and why, with minimal but structured client input upfront.

### Steps

1. **M&E Goal Conversation**
   - Meet with client to understand program objectives and M&E goals per program/intervention.
   - Capture: program names, reporting cadence, audience (internal vs. donor), key questions the data must answer.
   - Output: consultant fills `me_goals.md` — this stays as a lightweight MD summary.

2. **Client Fills Requirements Sheet**
   - Share the **Requirements Sheet** (Google Sheet template) with the client.
   - The client fills in their existing logical framework / logframe — what they want to measure, with what formulas, from what data sources, and with what breakdown dimensions.
   - This is the primary client input artifact for the entire engagement. Keep the form simple: one row per metric they want, with columns for calculation intent, data source, and reporting audience.
   - The consultant reviews this sheet and adds annotations in a dedicated "Consultant Notes" column.
   - This sheet is the input that feeds metric list curation in Phase 2. It does not need to be re-created — it is updated in-place as the engagement progresses.

### Artifacts

| Artifact | Format | Owner | Purpose |
|---|---|---|---|
| `me_goals.md` | Markdown | Consultant | Summary of goals conversation |
| Requirements Sheet | Google Sheet | Client (consultant annotates) | Client's intended metrics, data sources, calculation intent — primary requirements input |

---

## Phase 2: Framework

**Goal:** Translate the requirements sheet into a structured, implementation-ready KPI Framework that is ready for data engineers to build against.

**KPI Framework vs. Requirements Sheet — the distinction:**

The Requirements Sheet is written by the client in program/M&E language. It captures intent. The client does not need to know anything about databases to fill it.

The KPI Framework Sheet is built by the consultant in data/technical language. It captures implementation. It cannot be filled without knowing the actual raw table structure.

The same metric looks like this in each:

| | Requirements Sheet (client fills) | KPI Framework Sheet (consultant builds) |
|---|---|---|
| What it says | "% of female beneficiaries who completed the full training cycle — completions divided by enrolled, by gender, monthly, for donor report" | `COUNT(DISTINCT beneficiary_id WHERE gender='F' AND sessions_attended >= required_sessions) / COUNT(DISTINCT beneficiary_id WHERE gender='F')` — from `kobo_training_responses` joined to `enrollment_master` on `beneficiary_id`, filter `program_id = 'prog_x'`, grain: monthly per program, mart: `fct_training_completion` |
| Who can fill it | The M&E manager | The consultant (after data exploration) |
| When it locks | After requirements review | After data exploration |

They are separate sheets because they have different audiences (client vs. data team) and different lifecycles (Requirements locks early; KPI Framework stays live through data exploration).

### Steps

3. **Curate Metrics List**
   - Read the Requirements Sheet and enumerate all KPIs that need to be tracked.
   - Deduplicate, consolidate overlapping metrics, and flag anything ambiguous for client clarification.
   - This list becomes the rows of the KPI Framework Sheet.

4. **Build the KPI Framework Sheet**
   - One row per KPI. Columns:
     - **KPI name** — human-readable label
     - **Requirements alignment** — which row in the Requirements Sheet this maps to
     - **Definition** — plain English definition of what is being measured
     - **Calculation logic** — formula or aggregation (e.g., `COUNT(DISTINCT beneficiary_id) WHERE activity_type = 'training'`)
     - **Data source(s)** — which raw table(s) feed it (filled in/confirmed after data exploration)
     - **Filters / conditions** — time ranges, cohort conditions, exclusions
     - **Granularity** — per-beneficiary / per-location / per-period
     - **Mart model** — which `fct_` or `dim_` model will expose this metric
     - **Status** — draft / confirmed / revised
   - At this stage, Data Source and Mart Model columns may be partially filled — they are completed and locked after data exploration.

### Artifacts

| Artifact | Format | Owner | Purpose |
|---|---|---|---|
| KPI Framework Sheet | Google Sheet | Consultant | Technical spec for every metric: definition, calculation logic, sources, granularity. Living document through data exploration. |

---

## Phase 3: Data Exploration

**Goal:** Understand the actual shape of the raw data before designing models. Validate and revise the KPI Framework against what is actually in the data.

### Steps

5. **Ingest Raw Data**
   - Data sources (KoboToolbox, Google Sheets, ODK, CRMs, etc.) ingested via Airbyte into raw tables in the warehouse.
   - Confirm all sources listed in the KPI Framework are available.

6. **Explore Raw Table Structure**
   - For each raw table, query to understand:
     - Column names and data types
     - Null rates and cardinality for key columns
     - Sample rows
     - Join keys (IDs linking tables)
     - Date/time fields and formats
     - Anomalies, duplicates, encoding issues

7. **Revise KPI Framework Sheet (if needed)**
   - After exploring raw tables, revisit each KPI row in the Framework Sheet.
   - Update if data structure, quality, or available fields differ from assumptions:
     - Calculation logic (e.g., assumed a direct field but need a derived one)
     - Data source mapping (e.g., missing join key, alternate path needed)
     - Filters/conditions (e.g., status field has unexpected values)
   - Mark revised rows as "Revised" in the Status column. The post-exploration version is the binding reference for model development.

8. **Design ER Diagram**
   - Start from the standard NGO entity pattern (beneficiary → program enrollment → activity → outcome) and adapt to this program.
   - Document: entities and grain, relationships and cardinalities, which raw tables map to which entities, join paths needed for each metric.

### Artifacts

| Artifact | Format | Owner | Purpose |
|---|---|---|---|
| `table_profiles.md` | Markdown | Consultant | Per-table structure notes from exploration |
| `er_diagram.md` / `.png` | Markdown / Image | Consultant | Entity-relationship diagram |
| KPI Framework Sheet | Google Sheet | Consultant | Updated with confirmed data sources and revised calculation logic |

---

## Phase 4: Model Development (dbt Medallion Architecture)

**Goal:** Build, run, verify, and iterate dbt models layer by layer.

The models follow a **staging → intermediate → mart** medallion pattern. Each layer is written and verified before proceeding to the next.

### Layer 1: Staging (`stg_`)

- One model per raw source table.
- Responsibilities: rename columns, cast data types, deduplicate, handle nulls. No business logic.
- For nested/JSON data: decide which fields to extract, how to handle arrays, consistent naming conventions.
- **Run & verify:** row counts match source, no unexpected nulls in key columns, data types correct.

### Layer 2: Intermediate (`int_`)

- Join and reshape staging models into business entities.
- Responsibilities: joins across staging models, cohort construction, derived fields (age from DOB, duration from start/end), light aggregations.
- **Run & verify:** validate join cardinalities, check for fan-out or row loss, spot-check derived fields.

### Layer 3: Mart (`fct_` / `dim_`)

- Final models exposing metrics and dimensions for reporting.
- Responsibilities: metric calculations per KPI Framework (aggregations, filters, period logic), dimension tables.
- **Run & verify:** compare computed metric values against manually calculated spot checks, validate against KPI Framework definitions.

### Development Loop (per layer)

```
write model → dbt run → inspect output in warehouse → correct logic → dbt run → confirm → proceed
```

### Data Dictionary (Final Deliverable)

At the end of model development, generate a **Data Dictionary Sheet** (Google Sheet) for the client. This is a structured reference of every table and column in the final dbt models.

Columns:
- **Schema** — `staging` / `intermediate` / `marts`
- **Table name** — full dbt model name
- **Column name**
- **Data type**
- **Description** — plain English definition (pulled from `schema.yml` descriptions)
- **Example value** (optional)
- **Source** — raw table/column it originates from (for staging models)
- **KPI** — which KPI this column feeds (for mart models)

This sheet, alongside the dbt lineage and auto-generated dbt docs, is the handoff artifact to the client's data team.

### Artifacts

| Artifact | Format | Owner | Purpose |
|---|---|---|---|
| `models/staging/stg_*.sql` | SQL | Engineer | Staging models |
| `models/intermediate/int_*.sql` | SQL | Engineer | Intermediate models |
| `models/marts/fct_*.sql`, `dim_*.sql` | SQL | Engineer | Mart models |
| `models/schema.yml` | YAML | Engineer | Column descriptions and dbt tests |
| dbt docs site | Generated | Engineer | Auto-generated lineage and documentation |
| Data Dictionary Sheet | Google Sheet | Engineer → Client | All tables and columns with definitions — client-facing handoff artifact |

---

## Full Artifact Map

```
workdocs/consulting/{engagement}/
├── discovery/
│   └── me_goals.md
├── data_exploration/
│   ├── table_profiles.md
│   └── er_diagram.md
└── models/                        ← or inside the dbt project repo
    ├── staging/
    ├── intermediate/
    └── marts/

Google Sheets (linked from workdocs, not stored as files):
├── Requirements Sheet             ← client-filled, consultant-annotated
├── KPI Framework Sheet            ← consultant-built technical spec
└── Data Dictionary Sheet          ← generated at engagement close
```

---

## Modification Track (Existing Clients)

For clients already live on Dalgo who want to add or change metrics — no full re-engagement needed.

**Entry point:** A change request describing what needs to change (new KPI, revised formula, new data source, new breakdown dimension).

**Steps:**
1. Open the existing KPI Framework Sheet for the client.
2. Add new rows or mark existing rows for revision. Update calculation logic, filters, or source columns as needed.
3. If the change involves a new data source: ingest via Airbyte, explore the new tables, update table_profiles.md, update the ER diagram if relationships change.
4. Identify the affected dbt model layers. Only rewrite or modify the models that are impacted — do not rebuild the full model set.
5. Run dbt for affected models only. Verify output.
6. Update `schema.yml` for any new or modified columns.
7. Update the Data Dictionary Sheet to reflect added/changed tables and columns.

**Artifacts updated (not recreated):**
- KPI Framework Sheet — revised rows marked with date and change reason
- Data Dictionary Sheet — updated columns/tables
- Affected SQL models and schema.yml only

---

## Key Principles

- **Requirements Sheet drives scope:** The client fills this once at the start and it is the input to the KPI Framework. Avoid scope creep by requiring changes to go through an explicit update to the Framework Sheet.
- **KPI Framework is the technical contract:** Every dbt model traces back to a row in the KPI Framework Sheet. No model is written without a corresponding KPI definition.
- **KPI Framework is living until data exploration is complete:** Business intent is captured upfront, but calculation logic is confirmed only after raw tables are explored. Post-exploration version is binding.
- **Data Dictionary is a client deliverable:** Not just internal documentation — it is the handoff artifact that lets the client's team understand and maintain their data independently.
- **Modification track is the default for live clients:** Once a client is set up, almost all work flows through the modification track. Avoid re-running the full process unless the program structure has fundamentally changed.
- **Layer-by-layer verification:** Models are run and validated at each layer boundary before the next layer is written.
- **NGO data quality is often poor:** Paper-to-digital conversion, inconsistent enumerators, mid-program schema changes. The staging layer must be defensive; document assumptions explicitly in table_profiles.md and schema.yml.
