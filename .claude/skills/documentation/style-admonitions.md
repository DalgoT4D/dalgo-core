# Style: Admonitions

Use sparingly. Only when content genuinely needs to stand out.

## `:::info` — Automatic behaviour or "good to know"

System does something the user should know about but doesn't act on. Also for "Screenshot coming soon" placeholders.

```markdown
:::info
Dalgo creates a draft dashboard the moment you select **+ Create Dashboard**. If you leave without saving, the draft is kept.
:::

:::info Screenshot coming soon
A screenshot of the warehouse connection test will be added here.
:::
```

## `:::note` — Helpful context or prerequisites

Supplementary info that adds context but isn't critical. Also for conditional feature availability.

```markdown
:::note
Superset is only available to organisations on the **Dalgo + Superset** plan.
:::

:::note
You may need to whitelist these IP addresses in your firewall: `13.202.128.47`, `65.2.173.97`
:::
```

## `:::warning` — Destructive or irreversible actions

Use when an action could cause data loss or is hard to undo *once confirmed*. Dalgo often shows a confirmation dialog before a destructive action — the `:::warning` belongs near the action, not on the confirmation step. Do not write "This cannot be undone without canceling" — that's confusing. Write what happens after the user confirms.

```markdown
:::warning
Deleting a connection is permanent and removes all its sync history. This cannot be undone.
:::
```

**Do not use** `:::tip`, `:::danger`, or `:::caution`.

## Conditional features

When a feature requires a specific subscription or setup, declare at the top of the page:

```markdown
:::note
The Superset Usage dashboard requires a **Dalgo + Superset** subscription. Contact support@dalgo.org to add it.
:::
```
