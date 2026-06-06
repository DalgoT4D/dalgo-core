# From Spreadsheets to AI Assistants: How We're Teaching Claude to Speak Dalgo

*A plain-English account of what we learned building an AI interface for NGO data teams*

---

## Why We're Writing This

Over the past few weeks, we've been building something called **Dalgo MCP** — a way to let AI assistants like Claude talk directly to your Dalgo data platform. We made a lot of mistakes, learned a lot from other projects, and arrived at some surprising insights about what it actually takes to make AI useful for NGO data work.

This post is our attempt to share all of that — without the jargon.

---

## First: What Problem Are We Solving?

NGO data teams have a hard job. They collect data in the field, load it into a warehouse, clean it with transformations, and then turn it into dashboards so program managers can make decisions. Dalgo was built to make that pipeline manageable — replacing manual Excel work with automated, reliable data flows.

But here's what we kept hearing from partners: **even with Dalgo, getting answers is slow.**

Want to know if last night's data sync worked? Log in. Navigate to Pipelines. Find the right one. Click through to the run history. Read the logs.

Want to know how many beneficiaries were reached in Maharashtra last month? Open the warehouse browser. Find the right schema. Find the right table. Run a query. Wait.

It's not broken — it just requires a lot of clicking and knowing where things live. For a program manager managing three projects across two states, that friction adds up.

**The question we started asking: what if you could just ask?**

"Did last night's pipeline run successfully?"
"Show me the beneficiary count by district for this quarter."
"Why did the transform fail?"

That's what Dalgo MCP is — a bridge that lets Claude ask these questions on your behalf, directly to your Dalgo instance.

---

## What Is MCP? (Plain English)

MCP stands for **Model Context Protocol**. The name sounds complicated, but the idea is simple.

Imagine Claude as an assistant sitting at a desk. Without MCP, Claude can only talk to you — it can read what you paste into the chat and respond, but it can't actually go check your data or click buttons on your behalf.

MCP gives Claude a **set of tools** — like giving the assistant a phone with your Dalgo app open. Now when you ask "did the pipeline run?", Claude can actually look it up rather than just guessing.

Each tool is a small, defined action: "list the schemas in the warehouse", "get the logs for this pipeline run", "trigger a sync". Claude picks the right tools, calls them in sequence, and brings you back a real answer.

---

## What We Learned From Other MCPs

Before building our own, we spent a lot of time studying how other teams have done this. Three projects taught us the most.

### 1. dbt-mcp: Tools Are Not Enough

The team building the MCP for dbt (the transformation tool Dalgo uses under the hood) made an interesting decision: they don't just give the AI a list of tools. They also give it **82 prompt files** — short markdown documents that explain *how to use* the tools wisely.

A tool can tell Claude "here's how to run a dbt model." A prompt file tells Claude "here's when you should run it, what to check before you do, what failure looks like, and what to try next."

**Lesson learned:** The quality of an AI assistant isn't just about what it *can* do — it's about whether it knows *when* to do it, in what order, and what to check along the way. We're now building similar guidance files for Dalgo's most important workflows: verifying a pipeline run, debugging a sync failure, checking transform output.

### 2. Tool Count Kills Context

When we launched the first version of Dalgo MCP, it exposed **51 tools** — one for each action you can take in Dalgo. That sounds impressive, but it created a hidden problem.

Every tool has a description. All those descriptions together take up space in Claude's "working memory" (called the context window). With 51 tools loaded, Claude was spending a third of its thinking capacity just reading the tool list — before it even started working on your question.

Other MCP projects (including tools built for Stripe, Linear, and GitHub) have run into the same wall. The solution they've converged on: **hide low-level tools and expose high-level ones.** Instead of exposing "get pipeline", "get pipeline run", "get pipeline run logs" as three separate tools, you expose one: "check pipeline status" — and internally it calls the others as needed.

**Lesson learned:** Less is more. We're cutting Dalgo MCP from 51 tools down to ~25, making it faster and smarter.

### 3. Context Goes Cold Between Sessions

This one surprised us. Every time you start a new conversation with Claude, it starts from zero. It doesn't remember that your main data schema is called `public_beneficiary`, that your Prefect pipelines follow a `{project}_{source}_{frequency}` naming convention, or that your warehouse is on BigQuery.

So every session begins with Claude re-discovering your setup — asking questions you've answered before, or making mistakes because it doesn't know your conventions.

The pattern other teams have found: a **memory file** — a short markdown document that lives in your Dalgo setup and gets injected at the start of every session. It tells Claude the things it needs to know about your organization before it starts working.

**Lesson learned:** We're building a `dalgo.md` pattern — a file your team edits once, that Claude reads every time it connects. Think of it as onboarding notes for your AI data analyst.

---

## What We're Building: The Dalgo MCP Feature Set

Here's a plain-English breakdown of what Dalgo MCP can do once it's live.

### Data Warehouse Access
Claude can browse your warehouse — listing schemas, tables, and columns — and fetch actual rows of data. When it does, it automatically masks sensitive columns (names, emails, phone numbers) so your data never leaks into the chat.

*Example: "What tables do we have in the beneficiary schema?" → Claude lists them, with column descriptions.*

### Pipeline Monitoring
Claude can check your Prefect orchestration pipelines — seeing which are scheduled, which ran recently, and whether the last run succeeded or failed. It can even read the logs.

*Example: "Why did last night's sync fail?" → Claude pulls the logs and summarizes the error.*

### Source & Sync Management
Claude can list your Airbyte data sources and connections, and trigger syncs when needed.

*Example: "Trigger a sync for the Kobo form data." → Claude calls the API and confirms it's started.*

### Dashboards & Charts
Claude can list your dashboards and charts, create new ones, and pull the underlying data.

*Example: "Show me the chart data for beneficiaries by state." → Claude fetches and summarizes it.*

### dbt Transforms
Claude can see your dbt project, run transformations, view the DAG (the map of how models depend on each other), and sync sources.

*Example: "Run the beneficiary_summary model and tell me if it succeeded." → Claude runs it and reads the result.*

### Reports
Claude can create point-in-time snapshots of dashboards — useful for "as of last month" reporting.

### Documentation Search
Claude can search Dalgo's own documentation, so it can explain features and guide users through the platform.

---

## The Safety Problem We Almost Missed

When you give an AI access to real systems, you need to be very careful about what it's allowed to do on its own.

There's a big difference between Claude **reading** your pipeline status and Claude **deleting** a pipeline. Between **listing** chart data and **creating** a new chart.

Early in our build, all 51 tools looked the same to Claude — it had no way to know which ones were safe to call automatically and which ones should require your confirmation.

We fixed this by adding **safety annotations** to every tool:

- **Read-only:** This tool only reads data, it can never change anything. Claude can call it freely.
- **Destructive:** This tool deletes or modifies data. Claude should always ask before calling it.
- **Idempotent:** This tool can be safely called multiple times — calling it twice has the same effect as calling it once.

*Example: "List schemas" is read-only. "Delete pipeline" is destructive. "Trigger pipeline run" is not idempotent — running it twice means two pipeline runs.*

With these annotations in place, Claude knows when to act and when to pause and ask you first. This is especially important for NGO teams where a wrong deletion could mean losing months of data work.

---

## The Log Problem: When Data Is Too Big

Here's a specific technical problem we didn't anticipate.

Pipeline run logs can be enormous — thousands of lines of output from a Prefect run. When Claude tries to read those logs, it can overflow its working memory entirely, leaving no room to actually analyze what went wrong.

We solved this with **token-aware truncation**: instead of dumping the entire log into the chat, Claude reads the first 100 lines and the last 100 lines, and tells you how many were skipped in the middle.

This is the same pattern a senior engineer uses when debugging: read the beginning to understand the context, jump to the end to find the error, skip the boring middle.

*Result: Claude can now debug pipeline failures on logs of any size, without choking.*

---

## Why This Matters for NGO Users Specifically

Everything we've described so far is useful for any data team. But there are reasons this matters *especially* for NGO partners using Dalgo.

**1. Your data team is small (or doesn't exist)**

Most Dalgo partners are program managers or coordinators who also happen to be responsible for the data. They didn't sign up to be data engineers. Asking them to navigate warehouse schemas and dbt runs is asking a lot. A conversational interface lowers that barrier significantly.

**2. Your questions are urgent and time-bound**

"Did the Kobo sync work before the field visit tomorrow?"
"Can you show me last quarter's numbers before the donor call in an hour?"

These aren't research questions — they're operational questions with time pressure. Claude can answer them in seconds instead of requiring 15 minutes of navigation.

**3. You're on slow internet and shared devices**

The Dalgo interface is already designed to be lightweight, but every extra click costs time. A single chat message that returns a clear answer beats five browser tabs on a 3G connection.

**4. Your data has PII**

Beneficiary names, addresses, phone numbers — this is sensitive data that must never leak. The automatic PII masking in Dalgo MCP means Claude can help you analyze your data without exposing individuals, even in a chat window.

---

## What's Still Being Built

Dalgo MCP is live and functional, but we're not done. Here's what's next:

**Guided verification workflows** — Prompt files that teach Claude how to verify a full data pipeline end-to-end: did the sync complete? Did the transform run? Is the dashboard showing fresh data?

**Organization memory file** — The `dalgo.md` pattern so Claude knows your schema names, pipeline conventions, and team setup from session one.

**Fewer, smarter tools** — Cutting from 51 to ~25 by hiding implementation details and exposing higher-level actions.

**Tool count CI check** — A script that runs in our test suite and fails if someone accidentally adds too many tools, keeping context window usage under control.

**Evaluation suite** — A set of natural language questions with known correct answers, so we can measure whether Claude is actually picking the right tools for the right questions.

---

## The Bigger Picture

We believe the next big shift in data tooling for NGOs isn't a new dashboard — it's a new interface. Not "here's a chart that shows you the answer" but "here's an assistant that finds the answer for you."

MCP is the plumbing that makes that possible. Dalgo MCP is our implementation of it — built specifically for the workflows, constraints, and data realities of social-impact organizations.

If you're a Dalgo user and want to try this, reach out to us. We're running this with early partners now and actively incorporating feedback.

If you're building your own MCP integration and want to avoid the mistakes we made (51 tools, unbounded logs, cold-start context loss), the short version is: **fewer tools, more guidance, always think about context size, and annotate for safety from day one.**

---

*Dalgo is open-source (AGPL-3.0) and built for NGOs. If your organization manages complex data pipelines on a small budget and a small team, it might be exactly what you need.*

*Questions or feedback? Open an issue on GitHub or write to us at the Dalgo community forum.*
