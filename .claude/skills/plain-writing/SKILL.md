---
name: plain-writing
description: Writing rules for plans, specs, research notes, and any user-facing explanation in Dalgo. Use whenever producing a plan.md, research.md, spec.md, or explaining a feature/decision to the user — so the reader (a non-technical NGO program manager, a first-time engineer on the codebase, or a busy reviewer skimming on a phone) can follow without backfilling jargon. Triggered by the planning, spec-writing, and design-handoff commands; also invoke directly when the user says "explain in simple language", "give me an example", or asks you to rewrite something more plainly.
---

# Plain Writing Skill

The reader is a non-technical NGO program manager, a first-time engineer on the codebase, or a busy reviewer skimming on a phone. Write so any of them can follow without rereading. Every concept lands with a concrete example.

Apply these rules to **everything you produce while this skill is loaded** — the plan.md, research.md, your chat replies, and any questions you ask the user.

---

## The 8 Rules

1. **Simple language.** Short sentences. Active voice. Plain English over jargon. If a term is unavoidable (e.g. `@has_permission`, `OrgUser`, "migration", "RBAC"), define it in one line the first time it appears in that document.
2. **Every concept gets a concrete example.** Whenever you state a rule, decision, or behavior, follow it with a small, named example. Use real people and resource names (Priya, Sarah, "Field Performance Dashboard"), not `User A` or `Resource X`.
3. **Show, don't only tell.** Prefer a 3-row table or a 2-line code snippet over a paragraph of prose. If you can draw the data flow as ASCII boxes-and-arrows in 6 lines, do that instead of describing it in 6 sentences.
4. **One idea per paragraph.** If a paragraph runs more than 4 lines, split it.
5. **Define acronyms on first use** in each document. `HLD (High-Level Design)`, `LLD (Low-Level Design)`, `RBAC (role-based access control)`, `RLS (row-level security)`, `PII (personally identifiable information)`, `FK (foreign key)`, `IA (information architecture)`.
6. **No mystery references.** When you say "per §9.1" or "see Spec A", add a half-line of context: *"per §9.1 (anyone can invite as Member; only Admins can invite as Analyst/Admin)"* — so the reader doesn't have to flip back.
7. **User-facing language for behaviors; technical language for code.** When describing what a user sees or does, use product language ("the Admin invites Priya as an Analyst"). When describing implementation, name the file/function/table/migration.
8. **Questions to the user are simple too.** If you call `AskUserQuestion`, write the question and each option in plain words and add a one-line example of what choosing that option means in practice.

---

## The Mini-Block Template

Use this template for every rule, decision, or section. If a section has 5 rules, that's 5 mini-blocks — not one wall of prose.

```
**The rule:** {one short sentence}
**Example:** {one or two sentences with named people and a concrete outcome}
**Why it matters:** {one short sentence — what breaks if we get it wrong}
```

### Example mini-block

> **The rule:** A Member with an Edit grant on a dashboard can re-share that dashboard.
> **Example:** Anjali is a Member. Priya (an Analyst) shares the "Field Performance" dashboard with Anjali at Edit. Anjali can now add the "Funders" group to that dashboard's share list.
> **Why it matters:** It keeps "what you can do" tied to the grant on the resource, not to your role tier. If we tied re-sharing to role, Members could never share — which is the wrong default for an NGO with mostly Member users.

---

## Show, don't only tell — patterns

### Replace prose with a 3-row table

❌ Prose:
> The Admin role can invite users as any of Admin, Analyst, or Member. The Analyst role can invite users only as Member. The Member role can also invite as Member only.

✅ Table:

| Inviter | Can invite as |
|---|---|
| Admin | Admin, Analyst, or Member |
| Analyst | Member only |
| Member | Member only |

### Replace prose with an ASCII flow

❌ Prose:
> The frontend calls the sidebar nav contract which reads the user's permissions from the auth store and filters nav items, hiding any item the user lacks permission for.

✅ Flow:
```
login → /api/currentuserv2 → auth store (permissions[])
                                  │
                                  ▼
                       useUserPermissions()
                                  │
                                  ▼
                    main-layout.tsx getNavItems()
                                  │
                                  ▼
                   .filter(item => !item.hide)
                                  │
                                  ▼
                        rendered sidebar
```

### Replace prose with a code snippet (2 lines max for "show me what it looks like")

❌ Prose:
> The endpoint is gated by the `can_view_dashboards` permission slug applied via the `@has_permission` decorator on the API view function.

✅ Snippet:
```python
@has_permission(["can_view_dashboards"])
def get_dashboards(request):
    return Dashboard.objects.filter(org=request.orguser.org)
```

---

## When to invoke this skill

- The `/engineering/plan-feature` command loads it at the start of a planning run.
- The `/product/write-spec` command loads it when writing a spec.
- The `/design/design-handoff` command loads it when producing `design.md`.
- Any time the user says "explain in simple language", "give me an example", "I don't get it", or asks you to rewrite a document more plainly.
- Any time you're about to write a document that a non-technical reader will see.

If you're loaded for a task but the audience is purely a senior engineer reading code-level details (e.g. an LLD section about a Django migration's reverse function), it's fine to drop the named-example for that *specific* code block — but keep all 8 rules in force elsewhere in the same document.

---

## Self-check before saving any document

Before you write the document to disk, scan it once and answer:

- [ ] Every rule/decision has a named example?
- [ ] No paragraph longer than 4 lines?
- [ ] Every acronym defined on first use?
- [ ] Every "§X" or "see Y" reference has a one-line gloss?
- [ ] At least one table or ASCII flow per major section?
- [ ] Mini-block template used for the load-bearing rules?

If any answer is "no", fix it before saving.
