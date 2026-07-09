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

Markers are consumed (deleted) once reported, so a fixed configuration
does not keep tripping the gate.

Stdlib only.
"""

from __future__ import annotations

import json
import os
import subprocess
import sys
from pathlib import Path


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

    failures = []
    for m in markers:
        try:
            failures.append(json.loads(m.read_text(encoding="utf-8")))
        except (OSError, json.JSONDecodeError):
            pass
        m.unlink(missing_ok=True)  # consume: report each failure once

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

    agents = ", ".join(f"{f.get('agent_type', '?')} ({f.get('agent_id', '?')})" for f in failures)
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
