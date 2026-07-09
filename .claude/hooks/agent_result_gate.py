#!/usr/bin/env python3
"""PostToolUse hook (matcher: Agent|Task): hard gate for zero-tool-call
subagents.

Runs in the parent session right after a subagent returns. If the
SubagentStop hook (subagent_toolcheck.py) left a failure marker, this
hook:

  1. Runs scripts/validate_agents.py to confirm/deny the config-error
     hypothesis.
  2. Exits 2 with a directive on stderr. Exit 2 on PostToolUse feeds
     stderr straight back to the coordinator model as a deterministic
     instruction: treat as CONFIGURATION ERROR, do not retry or respawn
     until validate-agents passes.

Markers are consumed (deleted) once read, exactly as before. Markers older
than the staleness threshold (60 minutes) are informational only and do not
contribute to exit code or error message.

Stdlib only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from datetime import datetime, timezone
from pathlib import Path

# Staleness threshold in seconds (60 minutes)
STALENESS_THRESHOLD_SECONDS = 60 * 60


def is_marker_stale(marker_data: dict[str, object]) -> bool:
    """Check if a marker is older than the staleness threshold.

    A marker with missing or unparseable detected_at is treated as fresh
    (fail toward reporting, not toward silent dropping).
    """
    detected_at_str = marker_data.get("detected_at")
    if not isinstance(detected_at_str, str):
        return False  # treat as fresh if missing or not a string

    try:
        # detected_at is ISO-8601 UTC: "2026-07-09T12:34:56Z"
        detected_at = datetime.fromisoformat(detected_at_str.rstrip("Z")).replace(
            tzinfo=timezone.utc
        )
        age_seconds = (datetime.now(tz=timezone.utc) - detected_at).total_seconds()
        return age_seconds >= STALENESS_THRESHOLD_SECONDS
    except (ValueError, TypeError):
        return False  # treat as fresh if unparseable


def main() -> int:
    # stdin must be consumed even if unused, but we do not depend on it.
    try:
        json.load(sys.stdin)
    except json.JSONDecodeError:
        pass

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    marker_dir = project_dir / ".claude" / "state" / "agent-failures"
    if not marker_dir.is_dir():
        return 0
    markers = sorted(marker_dir.glob("*.json"))
    if not markers:
        return 0

    all_failures = []
    for m in markers:
        try:
            all_failures.append(json.loads(m.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            pass
        m.unlink(missing_ok=True)  # consume: delete all markers regardless of age

    # Separate fresh from stale failures
    fresh_failures = [f for f in all_failures if not is_marker_stale(f)]

    # If all markers are stale, exit silently with 0
    if not fresh_failures:
        return 0

    # Fresh markers trigger the gate
    validator = project_dir / "scripts" / "validate_agents.py"
    validation = "validator not found (scripts/validate_agents.py missing)"
    if validator.is_file():
        result = subprocess.run(
            [sys.executable, str(validator), str(project_dir / ".claude" / "agents")],
            capture_output=True,
            text=True,
            timeout=30,
        )
        validation = result.stdout.strip() or result.stderr.strip()

    agents = ", ".join(
        f"{f.get('agent_type', '?')} ({f.get('agent_id', '?')})" for f in fresh_failures
    )
    sys.stderr.write(
        "SUBAGENT HARD GATE TRIPPED: the following subagent(s) finished "
        f"with ZERO tool calls: {agents}. This is a known failure mode "
        "caused by invalid 'tools:' frontmatter in .claude/agents/*.agent.md "
        "(unknown tool names are silently dropped, leaving the agent with no "
        "tools -- it then narrates tool calls as plain text).\n\n"
        "DO NOT retry, respawn, or send follow-up messages to the subagent: "
        "a model without tools cannot comply. Treat this as a configuration "
        "error.\n\n"
        f"Automatic validation result:\n{validation}\n\n"
        "Required action: report this to the user, and do not continue the "
        "task until 'make validate-agents' passes.\n"
    )
    return 2


if __name__ == "__main__":
    sys.exit(main())
