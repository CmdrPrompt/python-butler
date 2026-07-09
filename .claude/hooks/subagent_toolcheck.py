#!/usr/bin/env python3
"""SubagentStop hook: detect subagents that finished without a single
tool call (the "narrated tool calls" failure mode from TASK-025/TASK-034).

Behavior:
  - Reads the SubagentStop JSON from stdin (contains agent_id,
    agent_type, agent_transcript_path).
  - Counts real tool_use blocks in the subagent transcript.
  - If zero tool calls AND the agent produced at least one assistant
    turn: writes a marker file under .claude/state/agent-failures/.
    The companion PostToolUse hook (agent_result_gate.py) picks the
    marker up and delivers a blocking error to the coordinator.
  - Always exits 0: retrying the subagent in-context is pointless when
    the cause is a broken tool configuration, so we do NOT block the
    stop here. Escalation happens in the parent instead.

Stdlib only.
"""

from __future__ import annotations

import json
import os
import sys
import time
from pathlib import Path


def count_tool_uses(transcript_path: Path) -> tuple[int, int]:
    """Return (tool_use_blocks, assistant_turns) in a JSONL transcript."""
    tool_uses = 0
    assistant_turns = 0
    with transcript_path.open(encoding="utf-8") as fh:
        for line in fh:
            line = line.strip()
            if not line:
                continue
            try:
                event = json.loads(line)
            except json.JSONDecodeError:
                continue
            msg = event.get("message") or {}
            if msg.get("role") != "assistant":
                continue
            assistant_turns += 1
            content = msg.get("content") or []
            if isinstance(content, list):
                tool_uses += sum(
                    1 for b in content if isinstance(b, dict) and b.get("type") == "tool_use"
                )
    return tool_uses, assistant_turns


def main() -> int:
    try:
        payload = json.load(sys.stdin)
    except json.JSONDecodeError:
        return 0  # never break the workflow on our own parse errors

    transcript = payload.get("agent_transcript_path")
    if not transcript:
        return 0
    transcript_path = Path(os.path.expanduser(transcript))
    if not transcript_path.is_file():
        return 0

    tool_uses, assistant_turns = count_tool_uses(transcript_path)
    if tool_uses > 0 or assistant_turns == 0:
        return 0

    project_dir = Path(os.environ.get("CLAUDE_PROJECT_DIR", "."))
    marker_dir = project_dir / ".claude" / "state" / "agent-failures"
    marker_dir.mkdir(parents=True, exist_ok=True)

    agent_id = payload.get("agent_id", "unknown")
    marker = marker_dir / f"{agent_id}.json"
    marker.write_text(
        json.dumps(
            {
                "agent_id": agent_id,
                "agent_type": payload.get("agent_type"),
                "assistant_turns": assistant_turns,
                "tool_uses": 0,
                "transcript": str(transcript_path),
                "detected_at": time.strftime("%Y-%m-%dT%H:%M:%SZ", time.gmtime()),
                "diagnosis": (
                    "Subagent finished with 0 tool calls. Most likely cause: "
                    "invalid 'tools:' frontmatter in the .agent.md definition "
                    "(unknown tool names are dropped silently). Run: "
                    "make validate-agents"
                ),
            },
            indent=2,
        ),
        encoding="utf-8",
    )
    return 0


if __name__ == "__main__":
    sys.exit(main())
