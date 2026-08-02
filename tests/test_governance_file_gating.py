"""Acceptance tests for TASK-092 / REQUIREMENTS_GOVERNANCE_FILE_GATING.md.

`generate-governance-files` must gate `CLAUDE.md` and
`.github/copilot-instructions.md` on their own existence independently,
so a missing file is generated even when a sibling guarded file already
exists.
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


def _run(cmd: list[str], cwd: Path, input: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, input=input)


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


class TestMissingClaudeMdIsGeneratedWhenCopilotInstructionsAlreadyExists:
    """Scenario 1: Requirement 1 — a missing guarded output file must be
    generated even when a sibling guarded output file already exists."""

    def test_claude_md_is_created_and_copilot_instructions_left_unchanged(
        self, tmp_path: Path
    ) -> None:
        consumer = _build_consumer(tmp_path / "consumer")
        (consumer / ".github").mkdir()
        pre_existing = "# pre-existing copilot instructions\n"
        (consumer / ".github" / "copilot-instructions.md").write_text(pre_existing)

        result = _run(["make", "generate-governance-files"], cwd=consumer)

        assert result.returncode == 0, (
            f"generate-governance-files must not abort:\nstdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        assert (consumer / "CLAUDE.md").exists(), (
            "CLAUDE.md must be generated even though .github/copilot-instructions.md "
            "already existed"
        )
        assert (consumer / ".github" / "copilot-instructions.md").read_text() == pre_existing
        assert (
            ".github/copilot-instructions.md already exists. Run with FORCE=1 "
            "to overwrite." in result.stdout
        )


class TestExistingFilesAreNotOverwrittenWithoutForce:
    """Scenario 2: Requirement 2 — a guarded file that already exists is
    left untouched without FORCE=1."""

    def test_neither_file_changes_when_both_already_exist(self, tmp_path: Path) -> None:
        consumer = _build_consumer(tmp_path / "consumer")
        (consumer / ".github").mkdir()
        claude_md_content = "# pre-existing CLAUDE.md\n"
        copilot_content = "# pre-existing copilot instructions\n"
        (consumer / "CLAUDE.md").write_text(claude_md_content)
        (consumer / ".github" / "copilot-instructions.md").write_text(copilot_content)

        result = _run(["make", "generate-governance-files"], cwd=consumer)

        assert result.returncode == 0
        assert (consumer / "CLAUDE.md").read_text() == claude_md_content
        assert (consumer / ".github" / "copilot-instructions.md").read_text() == copilot_content


class TestInitProjectCompletionMessageListsOnlyGeneratedFiles:
    """Scenario 3: Requirement 3 — init-project's final "Stage and commit
    with" instructions must list CLAUDE.md when it was freshly generated,
    even though a sibling guarded file was skipped."""

    def test_git_add_line_lists_claude_md(self, tmp_path: Path) -> None:
        consumer = _build_consumer(tmp_path / "consumer")
        (consumer / ".github").mkdir()
        (consumer / ".github" / "copilot-instructions.md").write_text(
            "# pre-existing copilot instructions\n"
        )

        result = _run(
            ["make", "init-project"],
            cwd=consumer,
            input="\n\n\n\n",
        )

        assert result.returncode == 0, (
            f"init-project must succeed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        assert (consumer / "CLAUDE.md").exists()
        add_line = next(
            line for line in result.stdout.splitlines() if line.strip().startswith("git add")
        )
        assert "CLAUDE.md" in add_line
