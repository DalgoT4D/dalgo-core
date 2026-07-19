# Chart approval HITL — v2.2 tasks

Plan: `features/chat-with-data/v2.2/plan.md`
Branch: work landed directly on `feature/chat-with-data` (both repos — user's call).

**DEVIATION from plan, discovered in H1:** langgraph `interrupt()` cannot run in
async execution on Python 3.10 (config-contextvar limitation; needs 3.11). The
feature therefore pins the project to **Python 3.11**: `.python-version`,
`requires-python>=3.11`, CI matrix. All 319 pinned deps resolve unchanged; full
suite green locally. ⚠ Deploy-side interpreter (no Dockerfile in repo) must be
confirmed 3.11 before merge.

**Design change from plan (user review):** no `approval` build flag — the gate is
`RunContext.require_approval` read by the middleware's `when` predicate, so evals/
REPL run the exact production graph topology with approval off.

## H1 — Backend: middleware + pause

- [x] HumanInTheLoopMiddleware always in build_agent; `when` reads RunContext.require_approval
- [x] _chart_approval_summary description callable
- [x] turn_runner: __interrupt__ chunk → approval_request event + clean stream stop
- [x] audit row status="awaiting_approval"
- [x] evals runner + REPL set context.require_approval=False
- [x] recursion-limit comment updated; regression test green with new stack
- [x] tests (test_chart_approval.py): pause payload; approve/reject cycles;
      non-chart tools don't pause; require_approval=False never pauses

## H2 — Backend: resume

- [x] run_turn(resume_decision=...) → Command(resume={"decisions":[...]}) path
- [x] consumer: approval_response action, pending flag, turn-lock re-acquire
- [x] runner tests: approve → tool runs once + chip; reject → no chart + graceful text
- [x] consumer test: approval_response with no pending interrupt / bad decision → error

## H3 — Frontend: highlighted approval card

- [x] useChatWithData: approval state on the message + pendingApproval + respondToApproval
- [x] ApprovalCard.tsx: accent border + ring highlight, Approve/Cancel, collapses to
      "Chart approved ✓ / Chart declined" after the decision
- [x] composer disabled + placeholder swap while pending (page + drawer wired)
- [x] tests: reducer approval events; ApprovalCard render/actions/collapse (1548 total green)

## H4 — Polish + docs

- [x] core/ai/CLAUDE.md: approval seam (one dict entry), require_approval convention,
      py3.11 requirement, WS event addition
- [x] reconnect-while-pending limitation: documented here — a pending card is lost on
      reload (checkpoint keeps the turn paused; user re-asks). Fine for v1.

## Extra finds during execution

- [x] py3.11 enum-format bug in mention emails: `f"{comment.target_type}"` renders
      "CommentTargetType.CHART" on 3.11 → broken deep links. Fixed with .value
      normalization in mention_service. (Found by the full suite under the new pin.)
