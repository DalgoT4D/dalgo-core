---
name: sandbox
description: Use when the user wants a fresh, isolated local dev environment for a new feature — or to list/tear down existing ones. Triggers on /sandbox, "new sandbox", "spin up an environment", "sandbox for <feature>", "destroy the sandbox".
---

# Dev Sandbox

## Overview

`scripts/sandbox.sh` (in dalgo-core) creates a complete isolated local environment:
git worktrees for DDP_backend + webapp_v2 on a new `feature/<name>` branch off
`origin/main`, a dedicated Postgres DB with fresh migrations and seed fixtures, a
dedicated redis-server, and backend/frontend/celery running under pm2 on their own
ports. Spec and rationale: `features/dev-sandbox/spec.md`.

This skill is the conversational front door. The script does all the work — never
reimplement its steps by hand.

## Workflow

1. **Ask what they're working on** (skip if they already said). Derive a short
   kebab-case name from the answer — e.g. "trying a new chart filter UI" →
   `chart-filters`. Confirm the name with the user if the derivation isn't obvious.
2. **Ask about chat only if relevant**: if the feature touches Chat with Data, add
   `--with-chat`. Otherwise don't ask — default stack has no chat.
3. **Run it**:
   ```bash
   cd /Users/siddhant/Documents/Dalgo/dalgo-core
   ./scripts/sandbox.sh create <name>            # add --with-chat if needed
   ```
   Takes ~3–5 min (npm ci dominates). Use a generous Bash timeout (600000) or run
   in background and report when done.
4. **Report the summary block verbatim** — URLs, branch, login credentials, and the
   destroy one-liner. The login password is generated per-sandbox and also stored in
   `.dalgo-worktrees/<name>/sandbox.json`.
5. From then on, do the feature work **inside the worktrees**
   (`.dalgo-worktrees/<name>/DDP_backend` and `.../webapp_v2`), following each
   repo's own CLAUDE.md.

Other commands:

```bash
./scripts/sandbox.sh list                      # what exists, running or stopped
./scripts/sandbox.sh destroy <name>            # keeps the feature branch
./scripts/sandbox.sh destroy <name> --delete-branch
```

## Rules

- **Never manage sandbox processes by PID** — always pm2 by name
  (`pm2 restart django-asgi-sbx-<name>`, `pm2 logs webapp-sbx-<name>`).
- **Never point a sandbox at the shared dev DB or shared redis** — isolation is the
  whole point. The script's env overrides handle this; don't undo them.
- If `create` fails midway, run `destroy <name>` and retry — create refuses to run
  over leftovers.
- Before `destroy`, remind the user whether the branch has unpushed commits
  (`git -C .dalgo-worktrees/<name>/DDP_backend log --oneline origin/main..HEAD`);
  the branch survives destroy unless `--delete-branch` is passed.
- The script copies `.env` secrets with `cp`/`sed` in the shell — never read or
  print the values.

## What a sandbox does NOT include

Prefect server/proxy, airbyte, superset — pipeline/orchestration endpoints won't
work in a sandbox (the backend boots fine without them). For pipeline features,
work against the main dev stack on 8002/3001 instead.
