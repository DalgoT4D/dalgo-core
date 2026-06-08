#!/usr/bin/env python3
"""Claude Code status line for dalgo-core.

Reads the status-line JSON payload on stdin and prints a single line:
  <model> │ $<cost> │ +N/-M lines │ <duration>

Invoked by Claude Code on every render — keep it fast and dependency-free.
"""
import json
import sys


def fmt_duration(ms: float) -> str:
    if ms <= 0:
        return ""
    secs = ms / 1000
    if secs < 60:
        return f"{secs:.0f}s"
    mins = secs / 60
    if mins < 60:
        return f"{mins:.1f}m"
    return f"{mins/60:.1f}h"


def main() -> None:
    try:
        data = json.load(sys.stdin)
    except Exception:
        return

    model = (
        data.get("model", {}).get("display_name")
        or data.get("model", {}).get("id")
        or "claude"
    )
    cost = data.get("cost", {}) or {}
    total_cost = float(cost.get("total_cost_usd") or 0)
    lines_added = int(cost.get("total_lines_added") or 0)
    lines_removed = int(cost.get("total_lines_removed") or 0)
    duration_ms = float(cost.get("total_duration_ms") or 0)

    parts = [model, f"${total_cost:.2f}"]
    if lines_added or lines_removed:
        parts.append(f"+{lines_added}/-{lines_removed}")
    dur = fmt_duration(duration_ms)
    if dur:
        parts.append(dur)

    sys.stdout.write(" │ ".join(parts))


if __name__ == "__main__":
    main()
