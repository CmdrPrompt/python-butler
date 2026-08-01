"""Docs-level regression test for TASK-082: workflow-guardian,
implementation-worker, pr-reviewer, and characterization-test-writer agent
definitions support the BDD outside-in workflow, per BDD-032, BDD-033,
BDD-034, and BDD-035 of REQUIREMENTS_BDD.md.
"""

from __future__ import annotations

from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


class TestWorkflowGuardianDocumentsBddRedStateGate:
    def test_claude_agents_workflow_guardian_documents_bdd_red_state_gate(self) -> None:
        text = (_REPO_ROOT / ".claude" / "agents" / "workflow-guardian.agent.md").read_text()

        assert "BDD red-state gate" in text
        assert "make bdd" in text
        assert "red state" in text
        assert "Do not proceed to step 8 until this holds" in text

    def test_bundled_workflow_guardian_documents_bdd_red_state_gate(self) -> None:
        text = (_REPO_ROOT / "claude-agents" / "workflow-guardian.agent.md").read_text()

        assert "BDD red-state gate" in text
        assert "make bdd" in text
        assert "red state" in text
        assert "Do not proceed to step 8 until this holds" in text


class TestImplementationWorkerDocumentsOutsideInLoop:
    def test_claude_agents_implementation_worker_documents_outside_in_loop(self) -> None:
        text = (_REPO_ROOT / ".claude" / "agents" / "implementation-worker.agent.md").read_text()

        assert "Outside-in loop" in text
        assert "make bdd" in text
        assert "Report `make bdd`" in text

    def test_bundled_implementation_worker_documents_outside_in_loop(self) -> None:
        text = (_REPO_ROOT / "claude-agents" / "implementation-worker.agent.md").read_text()

        assert "Outside-in loop" in text
        assert "make bdd" in text
        assert "Report `make bdd`" in text


class TestPrReviewerDocumentsBddScenarioCoverageGate:
    def test_claude_agents_pr_reviewer_documents_bdd_scenario_coverage_gate(self) -> None:
        text = (_REPO_ROOT / ".claude" / "agents" / "pr-reviewer.agent.md").read_text()

        assert "BDD scenario coverage gate" in text
        assert "REQUEST CHANGES listing the uncovered" in text

    def test_bundled_pr_reviewer_documents_bdd_scenario_coverage_gate(self) -> None:
        text = (_REPO_ROOT / "claude-agents" / "pr-reviewer.agent.md").read_text()

        assert "BDD scenario coverage gate" in text
        assert "REQUEST CHANGES listing the uncovered" in text


class TestCharacterizationTestWriterPrefersGherkinForUserFacingBehavior:
    def test_claude_agents_characterization_test_writer_prefers_gherkin(self) -> None:
        text = (
            _REPO_ROOT / ".claude" / "agents" / "characterization-test-writer.agent.md"
        ).read_text()

        assert "Gherkin scenario" in text
        assert "remains plain pytest regardless" in text

    def test_bundled_characterization_test_writer_prefers_gherkin(self) -> None:
        text = (_REPO_ROOT / "claude-agents" / "characterization-test-writer.agent.md").read_text()

        assert "Gherkin scenario" in text
        assert "remains plain pytest regardless" in text
