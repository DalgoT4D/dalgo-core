# Ship a Feature — Background (Agent Mode)

## Input: $ARGUMENTS

Thin launcher. Spawns the `ship-orchestrator` agent with a fresh isolated context.

Use this when you want the pipeline to run in the background without tying up your
session, or when comparing orchestration quality against command mode.

---

Spawn the **`ship-orchestrator`** agent with input: `$ARGUMENTS`

That's it. The orchestrator takes over from here.

When it completes, it will print the final output including the PR URL and
human intervention count.

To compare results with command mode, both write to the same
`features/{feature-name}/{version}/pipeline.md` with their `Mode:` field set.
