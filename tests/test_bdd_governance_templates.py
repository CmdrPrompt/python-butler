"""Acceptance tests for TASK-083 / REQUIREMENTS_BDD.md BDD-040, BDD-041,
BDD-042, BDD-051.

Exercises the real `generate-governance-files` and `init-project` Makefile
targets against a fixture consumer project vendoring this repo's Makefile
and `templates/` directory under `.butler/`.
"""

from __future__ import annotations

import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = REPO_ROOT / "Makefile"
TEMPLATES = REPO_ROOT / "templates"
CLAUDE_AGENTS = REPO_ROOT / "claude-agents"
CLAUDE_SKILLS = REPO_ROOT / "claude-skills"
SCAFFOLD = REPO_ROOT / "scaffold"


def _run(cmd: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(cmd, cwd=cwd, capture_output=True, text=True)
    assert result.returncode == 0, (
        f"{cmd} in {cwd} failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result


def _build_consumer(path: Path) -> Path:
    """A consumer project vendoring this repo's Makefile + templates/ + scaffold/
    under .butler/, mirroring how `generate-governance-files` is used downstream."""
    path.mkdir(parents=True)
    (path / "Makefile").write_text("include .butler/Makefile\n")
    butler = path / ".butler"
    butler.mkdir()
    shutil.copy(MAKEFILE, butler / "Makefile")
    shutil.copytree(TEMPLATES, butler / "templates")
    shutil.copytree(SCAFFOLD, butler / "scaffold")
    shutil.copytree(CLAUDE_AGENTS, butler / "claude-agents")
    shutil.copytree(CLAUDE_SKILLS, butler / "claude-skills")
    return path


class TestClaudeMdTemplateIncludesBddSection:
    """Scenario: CLAUDE.md template includes BDD section (BDD-040)."""

    def test_bdd_section_covers_required_conventions(self) -> None:
        text = (TEMPLATES / "CLAUDE.md.tmpl").read_text()
        assert "tests/bdd/features/" in text
        assert "tests/bdd/steps/" in text
        assert "TASK-<NNN>-<short-description>.feature" in text
        assert "declarative" in text.lower()
        assert "one behavior per scenario" in text.lower()
        assert "@AC-" in text or "criterion" in text.lower()
        assert "outside-in" in text.lower()
        assert "make bdd" in text


class TestCopilotInstructionsBddSectionMatchesClaude:
    """Scenario: Copilot instructions receive semantically identical BDD
    content (BDD-041)."""

    def test_bdd_section_covers_required_conventions(self) -> None:
        text = (TEMPLATES / "copilot-instructions.md.tmpl").read_text()
        assert "tests/bdd/features/" in text
        assert "tests/bdd/steps/" in text
        assert "TASK-<NNN>-<short-description>.feature" in text
        assert "declarative" in text.lower()
        assert "one behavior per scenario" in text.lower()
        assert "@AC-" in text or "criterion" in text.lower()
        assert "outside-in" in text.lower()
        assert "make bdd" in text


class TestGenerateGovernanceFilesEmitsBddByDefault:
    """Scenario: make generate-governance-files emits BDD additions by
    default (BDD-042)."""

    def test_claude_md_and_copilot_instructions_include_bdd_section(self, tmp_path: Path) -> None:
        consumer = _build_consumer(tmp_path / "consumer")
        _run(["make", "generate-governance-files"], cwd=consumer)

        claude_md = (consumer / "CLAUDE.md").read_text()
        copilot = (consumer / ".github" / "copilot-instructions.md").read_text()
        assert "tests/bdd/features/" in claude_md
        assert "tests/bdd/features/" in copilot
        assert "<!--BDD:START-->" not in claude_md
        assert "<!--BDD:START-->" not in copilot

    def test_scaffold_directories_are_created(self, tmp_path: Path) -> None:
        consumer = _build_consumer(tmp_path / "consumer")
        _run(["make", "generate-governance-files"], cwd=consumer)

        assert (consumer / "tests" / "bdd" / "features").is_dir()
        assert (consumer / "tests" / "bdd" / "steps").is_dir()


class TestEnableBddZeroOmitsBddAdditions:
    """Scenario: ENABLE_BDD=0 omits BDD sections (BDD-042)."""

    def test_claude_md_and_copilot_instructions_omit_bdd_section(self, tmp_path: Path) -> None:
        consumer = _build_consumer(tmp_path / "consumer")
        _run(["make", "generate-governance-files", "ENABLE_BDD=0"], cwd=consumer)

        claude_md = (consumer / "CLAUDE.md").read_text()
        copilot = (consumer / ".github" / "copilot-instructions.md").read_text()
        assert "tests/bdd/features/" not in claude_md
        assert "tests/bdd/features/" not in copilot
        assert "<!--BDD:START-->" not in claude_md
        assert "<!--BDD:START-->" not in copilot

    def test_scaffold_directories_are_not_created(self, tmp_path: Path) -> None:
        consumer = _build_consumer(tmp_path / "consumer")
        _run(["make", "generate-governance-files", "ENABLE_BDD=0"], cwd=consumer)

        assert not (consumer / "tests" / "bdd").exists()
