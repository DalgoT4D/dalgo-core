# Spec: Chat with Data

## 1. Problem & opportunity

M&E and program staff at NGOs need answers from their data. Today the surface is dashboards — but that requires an analyst to have pre-built a chart for every question worth asking. Questions outside the pre-built set die on the vine, or turn into ticket-based back-and-forths with the data team.

**Chat with data** lets non-technical users ask questions in natural language and get narrative answers grounded in their warehouse. Instead of "which chart shows this?", the question is answered directly.

The bar for a v1 that earns trust:

- **Correct joins, aggregations, and filters** — the SQL that runs must be right, not "usually right"
- **Non-technical UX** — narrative answers with numbers, not tables of raw rows
- **Honest about limits** — when the system doesn't know how to answer, it must refuse cleanly rather than guess
- **Reasoning visible on demand** — users can see how an answer was derived without SQL noise up front

Chat is not competing with dashboards. Dashboards remain the "at-a-glance" surface. Chat is the "answer to the question I just thought of" surface.

## 2. Vocabulary & scope boundary

- **Chat surface** — the UI where a user asks a question. Two shells in v1: a floating action button (FAB) available on every page of Dalgo, and a full-page view on the Explore page.
- **Semantic layer** — the per-org description of what data means: which tables exist, what measures they support, how tables join, what business terms map to which columns. Answers depend entirely on the quality of this layer.
- **Measure** — a named, correctly-defined calculation ("training_count = count of distinct training events"). Reuses Dalgo's existing Metric primitive.
- **Semantic-layer editor** — the Dalgo product surface where staff and NGO data leads curate the semantic layer.
- **Refusal** — a first-class outcome when the system doesn't have enough definition to answer safely. Not an error state; a normal path with a clear "extend the layer" affordance.
- **Provenance card** — the expandable panel on each answer showing which measure, tables, filters, and time range produced it.
- **Curator queue** — the list of refusals and thumbs-down items that need human review to grow the semantic layer over time.

**Out-of-scope concepts called out here:**

- **Chart-aware or dashboard-aware chat** — in v1, chat does not know what the user is currently viewing. The user's question stands alone. Contextual chat is a future spec.
- **SQL fallback** — when the semantic layer can't answer, chat does not fall back to ad-hoc LLM SQL against raw tables. Refusal is the path.
- **Agentic multi-step reasoning** — no "think, act, observe, revise" loops. One retrieval, one interpretation, one answer.
- **Delivery outside Dalgo** — no chat via Slack, WhatsApp, or email in v1. The surface is the Dalgo web product.
- **Cross-org queries** — chat operates strictly within one NGO's data.
- **Editing history / undo of the semantic layer** — the editor is edit-in-place in v1.
- **Rich PII policy engine** — a single boolean tag per column is enough for v1; column-level access-control policies are a separate concern.

## 3. Users & primary use cases

- **M&E / program manager (Priya persona)** — asks day-to-day questions of the data ("how many women were trained last quarter", "which state had the most trainings"), reads narrative answers, occasionally expands the provenance card, gives thumbs-up / thumbs-down feedback.
- **NGO data lead** — curates the semantic layer for their organisation: reviews auto-generated definitions, corrects grain/join errors, adds business glossary terms, adds seed question-answer examples. Also works the curator queue when chat refuses questions.
- **Dalgo onboarding staff** — bootstraps the semantic layer for a new NGO from the NGO's dbt project, existing Charts, and existing KPIs. Sets the minimum-viable bar and turns chat on for the org. Later works the curator queue alongside the NGO.
- **NGO analyst / dbt author** — not a direct user of chat, but their dbt project descriptions, tests, and models feed the auto-bootstrap. Good dbt hygiene lifts chat accuracy for free.

## 4. User flows

Text walk-throughs; no wireframes.

### 4.1 Ask a question and get an answer

1. From any Dalgo page, the user clicks the chat FAB (or opens the full Explore chat).
2. The user types a question in plain English: "how many women were trained in Maharashtra last quarter?"
3. Chat streams a short "thinking" trail — human-readable phases like *Reading your question…*, *Looking for training and beneficiary data…*, *Running query on your warehouse…* — while the answer is being resolved. Phases replace in place; the user sees the current step.
4. The narrative answer streams in token-by-token. Example: *"47 women were trained in Maharashtra in Q2 2025 (Apr–Jun)."*
5. Underneath the answer, a collapsed provenance card is available: "How did I get this?" Expanded, it shows the measure used, tables involved, filters applied, and time range.
6. The user can give a thumbs-up or thumbs-down on the answer, optionally with a comment.
7. The user can ask a follow-up ("break that down by district"); chat treats this as a continuation of the same session and reuses context.

### 4.2 Chat refuses because the semantic layer doesn't cover the question

1. User asks: *"how many grant disbursements did we make this year?"*
2. Chat streams thinking phases, then instead of an answer, streams a **refusal event** with a human explanation: *"I don't see a measure for 'grant disbursements' in your data. Would you like to add one?"*
3. A **Fix this** button deep-links into the semantic-layer editor, pre-scoped to what was missing.
4. The refusal is silently added to the curator queue with the original question attached.
5. The user (or someone with editor access) resolves the gap by defining the measure, saves, returns to chat, clicks **Retry** on the same message. Chat re-runs the question against the updated layer and answers.

### 4.3 Bootstrap the semantic layer for a new NGO

1. Dalgo staff opens the semantic-layer editor for an NGO that's newly onboarded.
2. Editor auto-populates by reading (in this order): the NGO's dbt manifest, existing Dalgo Metrics, existing Dalgo Charts, existing Dalgo KPIs, warehouse table catalog as fallback. Every table auto-drafted has "needs review" status.
3. Editor filters out staging and intermediate tables by default. Staff sees a shortlist of ~20–30 analytics-relevant tables.
4. For each table on the shortlist, staff confirms four things: grain, kind (fact / dim / bridge), primary key, primary time column (facts only). Batch review UI allows approving multiple auto-drafts in one action.
5. Staff reviews the auto-drafted join graph and adds joins that dbt tests didn't declare.
6. Staff transcribes ~15–20 measures from the NGO's existing funder reports and dashboards. Existing Metrics come in for free.
7. Staff adds a ~30-term business glossary (e.g. "women" → gender = F filter on the beneficiary table).
8. Staff seeds ~20 example question-answer pairs — real questions the NGO asks, resolved to the correct measure / dimensions / filters.
9. Staff marks columns containing personal information as PII.
10. When the minimum-viable bar is met (see § 5.3), the editor lets staff turn chat on for the org. Below the bar, chat stays off — the FAB is hidden and the Explore chat is disabled.

### 4.4 Edit the semantic layer inline from a refusal

1. From a chat refusal, user clicks **Fix this**.
2. Editor opens on a focused view: "You need to define a measure for 'grant disbursements'." Suggested table (from retrieval), suggested aggregation type, suggested column pre-filled where possible.
3. User confirms or edits, saves.
4. User returns to the chat message and clicks **Retry**. The new version of the semantic layer is used automatically (no page reload).

### 4.5 Work the curator queue

1. From the semantic-layer editor's home screen, user opens the curator queue.
2. Queue shows a list of items: chat refusals and thumbs-down answers, sorted by frequency ("this question or its variants was asked 14 times this week").
3. Clicking an item opens the same focused editor view as 4.4, with the original question and the retrieval trail visible.
4. User resolves the gap: adds a measure, adds a join, adds a glossary term, or marks the item "won't fix" with a note.
5. Resolved items disappear from the queue. The next time a similar question is asked, chat answers it.

### 4.6 Follow-up questions within a session

1. After receiving an answer to a first question, the user asks a follow-up in the same chat panel.
2. Chat treats follow-ups as continuations. "Break that down by state" reuses the prior question's resolved measure, dimensions, filters, and time range; layers on the new dimension.
3. Each turn is answered on its own and adds to the visible transcript. Provenance is per-turn, not per-session.

### 4.7 Provide feedback on an answer

1. Every answer has thumbs-up / thumbs-down buttons.
2. Thumbs-up: silently logged; the resolved question-and-answer pair enters the curated example bank and improves retrieval for similar future questions.
3. Thumbs-down: opens a small comment field, then routes the item to the curator queue.
4. No edit-the-resolved-query UX for the user in v1 — corrections happen via the curator queue.

## 5. Functional requirements

### 5.1 Chat surface

- **Global FAB.** Bottom-right of every page in the Dalgo product. Opens a right-side drawer with the chat conversation.
- **Full-page chat on Explore.** A dedicated Explore experience with a larger conversation area for longer sessions.
- Both surfaces speak to the same session store; a conversation started in the FAB can be resumed on Explore and vice versa.
- The chat prompt is generic: *"Ask a question about your data"*. It does not claim awareness of the page the user is on, because in v1 it isn't aware.

### 5.2 Question, answer, refusal

- Users type a natural-language question. No prescribed grammar, no query builder.
- Answers are 1–3 short sentences of narrative including the numbers, not raw tables. Every answer includes a compact provenance card that expands on demand.
- Answers stream in — first token visible within ~2 seconds under normal conditions; total answer typically within ~10 seconds.
- While streaming, chat shows brief "thinking" phase messages that update in place (never a spinner with no content).
- **Refusals are first-class.** When the semantic layer cannot support the question, chat produces a refusal message explaining what's missing and offering a **Fix this** deep link into the editor. Refusals never fall back to guessed answers.
- Every answer or refusal is a thumbs-up-able / thumbs-down-able event.

### 5.3 Minimum-viable bar to turn chat on for an org

Chat is disabled for an org until the semantic layer meets a minimum coverage bar:

- At least one analytics table has grain and kind confirmed
- At least one measure defined (or lifted from an existing Metric)
- At least 5 seed question-answer examples
- All columns containing personal information tagged as PII

Below this bar, the chat surface is hidden. Above it, chat is available but expected to refuse frequently until the semantic layer grows.

### 5.4 Semantic-layer authoring UX

- Lives in the Dalgo product (webapp), not in engineering back-office tools.
- Auto-bootstraps from: the NGO's dbt manifest, existing Dalgo Metrics, existing Dalgo Charts, existing Dalgo KPIs, and warehouse catalog as fallback.
- Filters out staging and intermediate tables by default.
- Per-table editor exposes only the small set of fields the human must confirm (grain, kind, primary key, primary time column); everything else is auto-populated with a review affordance.
- Visual join-graph editor for adding relationships between tables.
- Wizard for defining a measure (pick anchor table → pick aggregation → pick column → auto-generate expression).
- Glossary editor (business term → column filter or column alias).
- Seeded question-answer editor.
- PII flag per column.
- Coverage indicator per table (green / amber / red) and org-wide (X of Y tables reviewed, chat status).

### 5.5 Curator queue

- Lives in the semantic-layer editor.
- Populated automatically from chat refusals and thumbs-down feedback.
- Each item shows the original question, the retrieval trail (what chat looked at), and a suggested action ("add a measure", "add a join", "add a glossary term").
- Sorted by frequency of the underlying question pattern.
- One-click resolve routes to the focused editor view for the suggested action.
- Items can be marked "won't fix" with a note.

### 5.6 Reuse of existing Dalgo primitives

- **Measures reuse Dalgo's existing Metric object.** Every existing Metric becomes chat-queryable on day 1 for the orgs that have them. New measures created via the semantic-layer editor are also Metrics — they are usable in Charts and KPIs.
- **KPIs remain what they are today.** They are not part of the semantic layer's authoring surface. In future iterations, chat may serve blessed KPI numbers directly as a shortcut path when a question matches a KPI's definition; for v1, all questions go through the semantic layer.
- **Warehouse credentials per org** already exist; chat uses them to run queries.

### 5.7 Feedback loop and continual improvement

- Thumbs-up answers auto-promote the question-and-answer pair into the example bank used for future retrieval.
- Thumbs-down items route to the curator queue.
- The example bank grows with usage; retrieval quality improves as a direct function of NGO engagement.

### 5.8 Multi-tenant isolation

- Each org has its own semantic layer, its own warehouse credentials, its own example bank, its own curator queue, its own chat history.
- Nothing is shared across orgs — a question asked in one NGO's chat has no visibility of another NGO's data, definitions, or history.

### 5.9 Accuracy expectations

- **Well-covered questions** (matching a seeded example or well-defined measure): high accuracy. Aim for >90% correct.
- **In-domain novel questions** (semantic layer covers the pieces but the question is new): moderate-to-high accuracy. Aim for >85%.
- **Out-of-domain questions**: refuse, don't guess. Refusal precision is a first-class metric.

### 5.10 Trust affordances

- Provenance card is always available on every answer, collapsed by default.
- Refusal messages are actionable, not decorative.
- Answers never make claims beyond what the returned rows support (no invented trends, comparisons, or causes).
- The system never fabricates a measure, table, or column that doesn't exist in the semantic layer.

## 6. Out of scope (explicit)

- **Chart-aware or dashboard-aware chat** — chat does not know what the user is currently viewing.
- **Ad-hoc SQL fallback** on out-of-semantic-layer questions.
- **Agentic multi-step reasoning** ("think, act, observe, revise" loops).
- **Chat via Slack, WhatsApp, or email** — the surface is the Dalgo web product only.
- **Cross-org / cross-tenant queries.**
- **Semantic-layer version history and rollback** — the editor is edit-in-place. Version tracking is internal-only for cache-busting.
- **Multiple semantic layers per org** — one per org in v1.
- **Fine-grained access-control policies** on tables or rows — a single boolean PII tag is v1.
- **A shared semantic-layer library across NGOs** — templates and cross-org reuse are a later concern.
- **Edit-the-resolved-query UX for end users** — corrections happen through the curator queue.
- **KPI shortcut path** — later optimisation.
- **Voice input / voice output.**
- **Uploading files (CSV, PDF) into chat.**
- **Explain-your-reasoning traces from the LLM** — coarse phase messages only in v1.

## 7. Success indicators

- **Number of questions asked per org per week** — basic adoption.
- **Answer rate** — percentage of questions answered vs refused. Falling refusal rate over time = semantic layer maturing.
- **Thumbs-up rate on answers** — trust proxy. Aim for a stable majority thumbs-up.
- **Time-to-first-successful-question after onboarding** — a proxy for how well the bootstrap flow works.
- **Semantic-layer coverage growth** — number of tables, measures, glossary terms, examples added per week per org. Growth curve is the health signal.
- **Curator queue turnover** — items resolved per week vs items opened. Healthy = turnover ≥ opens; unhealthy = queue growing indefinitely.
- **Retention of chat as a daily habit** — repeat use by the same M&E user week over week.

## 8. Dependencies

- **A per-org semantic-layer authoring surface in the Dalgo product** — new build.
- **A per-org semantic-layer runtime** that compiles measure definitions into correct warehouse SQL and executes them, handling joins, aggregations, and time-grain math deterministically. Chosen implementation and interchange format are engineering decisions specified in the plan.
- **A retrieval layer** that maps natural-language questions to the small subset of the semantic layer relevant to answering them.
- **A hosted large-language model** for natural-language interpretation and answer narration.
- **Reuse of the existing Metric primitive** in `DDP_backend` (extended with semantic-layer wiring in the plan). Existing Metric consumers (Charts, KPIs, Alerts) are unaffected.
- **Reuse of existing per-org warehouse credentials** (Postgres and BigQuery).
- **Streaming HTTP support** in the Dalgo backend (already available via the ASGI server).
- **Access to the NGO's dbt project artefacts** for the auto-bootstrap step.

## 9. Rollout

- **First cohort:** 2–3 partner NGOs already using Dalgo, with reasonably documented dbt projects and existing Metrics / KPIs. They provide the initial semantic-layer authoring work and the first real usage data.
- **Second cohort:** partner NGOs with less-documented data. Their onboarding proves out the auto-bootstrap and refusal-driven curation flows on weaker inputs.
- **Chat is off by default** for every org until an onboarding pass raises the semantic layer above the minimum-viable bar.
- **Feature-flagged per org** during the initial rollout so Dalgo staff can toggle it as onboarding completes.

---

*Questions or feedback? Comment on this doc or ping the product team. Engineering approach — semantic-layer runtime choice, retrieval architecture, LLM orchestration, data model — lives in the accompanying plan.*
