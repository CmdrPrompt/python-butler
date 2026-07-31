"""Docs-level regression test for TASK-060: Workflow Guardian's agent
definition documents the draft-stage GitHub Projects sync step, and Task
Drafter's own definition is untouched (no Bash/GitHub interaction added),
per Requirement 6 of REQUIREMENTS_TASK_WORKFLOW.md.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


class TestWorkflowGuardianDocumentsDraftStageSync:
    def test_claude_agents_workflow_guardian_mentions_stage_draft_sync(self) -> None:
        text = (_REPO_ROOT / ".claude" / "agents" / "workflow-guardian.agent.md").read_text()

        assert "sync-project" in text
        assert "--stage draft" in text

    def test_bundled_workflow_guardian_mentions_stage_draft_sync(self) -> None:
        text = (_REPO_ROOT / "claude-agents" / "workflow-guardian.agent.md").read_text()

        assert "sync-project" in text
        assert "--stage draft" in text


class TestTaskDrafterToolSetIsUnchanged:
    def test_task_drafter_has_no_bash_tool(self) -> None:
        text = (_REPO_ROOT / ".claude" / "agents" / "task-drafter.agent.md").read_text()
        tools_line = next(line for line in text.splitlines() if line.startswith("tools:"))

        assert "Bash" not in tools_line
