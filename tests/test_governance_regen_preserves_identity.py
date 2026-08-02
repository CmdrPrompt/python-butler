"""Acceptance tests for TASK-091 / REQUIREMENTS_GOVERNANCE_REGEN.md.

`generate-governance-files FORCE=1` must not silently overwrite a project's
real name/description in `CLAUDE.md` and `.github/copilot-instructions.md`
with the Makefile's placeholder defaults (`my-project` /
`Describe your project here.`) when the caller does not explicitly pass
`PROJECT_NAME=`/`PROJECT_DESCRIPTION=` and a prior `CLAUDE.md` already
exists. Explicit values must still override, and first-time generation
(no prior `CLAUDE.md`) must be completely unaffected.
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

PLACEHOLDER_NAME = "my-project"
PLACEHOLDER_DESCRIPTION = "Describe your project here."

REAL_NAME = "firefly-python-api"
REAL_DESCRIPTION = "Python client library for the Firefly III REST API."


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


def _write_existing_claude_md(consumer: Path, name: str, description: str) -> None:
    consumer.joinpath("CLAUDE.md").write_text(
        f"# {name}\n\n{description}\n\n## Some Other Section\n\nUnrelated content.\n"
    )


class TestForceRegenerationPreservesExistingProjectIdentity:
    """Scenario 1 (task file) / Requirement 1 (REQUIREMENTS_GOVERNANCE_REGEN.md):
    FORCE=1 regeneration with an existing CLAUDE.md and no explicit
    PROJECT_NAME/PROJECT_DESCRIPTION must preserve the existing name and
    description in both CLAUDE.md and .github/copilot-instructions.md."""

    def test_claude_md_retains_existing_name_and_description(self, tmp_path: Path) -> None:
        consumer = _build_consumer(tmp_path / "consumer")
        (consumer / ".github").mkdir()
        _write_existing_claude_md(consumer, REAL_NAME, REAL_DESCRIPTION)

        result = _run(["make", "generate-governance-files", "FORCE=1"], cwd=consumer)

        assert result.returncode == 0, (
            f"generate-governance-files FORCE=1 must not abort:\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        claude_md = (consumer / "CLAUDE.md").read_text()
        assert f"# {REAL_NAME}" in claude_md, (
            "CLAUDE.md title must remain the real project name after FORCE=1 "
            f"regeneration, not be overwritten. Got:\n{claude_md[:200]}"
        )
        assert REAL_DESCRIPTION in claude_md, (
            "CLAUDE.md description must remain the real project description "
            f"after FORCE=1 regeneration. Got:\n{claude_md[:200]}"
        )
        assert PLACEHOLDER_NAME not in claude_md.splitlines()[0], (
            "CLAUDE.md title must not fall back to the placeholder 'my-project'"
        )
        assert PLACEHOLDER_DESCRIPTION not in claude_md

    def test_copilot_instructions_retains_existing_description(self, tmp_path: Path) -> None:
        consumer = _build_consumer(tmp_path / "consumer")
        (consumer / ".github").mkdir()
        _write_existing_claude_md(consumer, REAL_NAME, REAL_DESCRIPTION)

        result = _run(["make", "generate-governance-files", "FORCE=1"], cwd=consumer)

        assert result.returncode == 0, (
            f"generate-governance-files FORCE=1 must not abort:\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        copilot_instructions = (consumer / ".github" / "copilot-instructions.md").read_text()
        assert REAL_DESCRIPTION in copilot_instructions, (
            ".github/copilot-instructions.md description must remain the real "
            f"project description after FORCE=1 regeneration. Got:\n"
            f"{copilot_instructions[:200]}"
        )
        assert PLACEHOLDER_DESCRIPTION not in copilot_instructions


class TestExplicitProjectVariablesStillOverrideExistingClaudeMd:
    """Scenario 2 (task file) / Requirement 2 (REQUIREMENTS_GOVERNANCE_REGEN.md):
    explicitly passed PROJECT_NAME=/PROJECT_DESCRIPTION= must take precedence
    over both the Makefile defaults and any value extracted from an existing
    CLAUDE.md."""

    def test_explicit_project_name_and_description_override_existing_claude_md(
        self, tmp_path: Path
    ) -> None:
        consumer = _build_consumer(tmp_path / "consumer")
        (consumer / ".github").mkdir()
        _write_existing_claude_md(consumer, REAL_NAME, REAL_DESCRIPTION)

        result = _run(
            [
                "make",
                "generate-governance-files",
                "FORCE=1",
                "PROJECT_NAME=renamed-project",
                "PROJECT_DESCRIPTION=New description.",
            ],
            cwd=consumer,
        )

        assert result.returncode == 0, (
            f"generate-governance-files FORCE=1 with explicit vars must not abort:\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        claude_md = (consumer / "CLAUDE.md").read_text()
        assert "# renamed-project" in claude_md
        assert "New description." in claude_md
        assert REAL_NAME not in claude_md.splitlines()[0]
        assert REAL_DESCRIPTION not in claude_md

        copilot_instructions = (consumer / ".github" / "copilot-instructions.md").read_text()
        assert "New description." in copilot_instructions
        assert REAL_DESCRIPTION not in copilot_instructions


class TestFirstTimeGenerationIsUnaffected:
    """Scenario 3 (task file) / Requirement 3 (REQUIREMENTS_GOVERNANCE_REGEN.md):
    first-time generation (no prior CLAUDE.md), with or without FORCE=1 and
    no explicit PROJECT_NAME/PROJECT_DESCRIPTION, must still produce the
    Makefile placeholder defaults exactly as before this change."""

    def test_first_time_generation_without_force_uses_placeholder_defaults(
        self, tmp_path: Path
    ) -> None:
        consumer = _build_consumer(tmp_path / "consumer")
        (consumer / ".github").mkdir()

        result = _run(["make", "generate-governance-files"], cwd=consumer)

        assert result.returncode == 0, (
            f"generate-governance-files must not abort:\nstdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        claude_md = (consumer / "CLAUDE.md").read_text()
        assert f"# {PLACEHOLDER_NAME}" in claude_md
        assert PLACEHOLDER_DESCRIPTION in claude_md

        copilot_instructions = (consumer / ".github" / "copilot-instructions.md").read_text()
        assert PLACEHOLDER_DESCRIPTION in copilot_instructions

    def test_first_time_generation_with_force_uses_placeholder_defaults(
        self, tmp_path: Path
    ) -> None:
        consumer = _build_consumer(tmp_path / "consumer")
        (consumer / ".github").mkdir()

        result = _run(["make", "generate-governance-files", "FORCE=1"], cwd=consumer)

        assert result.returncode == 0, (
            f"generate-governance-files FORCE=1 must not abort:\n"
            f"stdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
        claude_md = (consumer / "CLAUDE.md").read_text()
        assert f"# {PLACEHOLDER_NAME}" in claude_md
        assert PLACEHOLDER_DESCRIPTION in claude_md

        copilot_instructions = (consumer / ".github" / "copilot-instructions.md").read_text()
        assert PLACEHOLDER_DESCRIPTION in copilot_instructions
