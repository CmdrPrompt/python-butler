"""Acceptance tests for TASK-093 / REQUIREMENTS_TEMPLATE_VAR_SHELL_SAFETY.md.

A `PROJECT_NAME` / `PROJECT_DESCRIPTION` value containing a single quote
must not break the shell command that substitutes it into `sed`-generated
output files.
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

DESCRIPTION_WITH_QUOTE = "Tracks each member's monthly share."


def _run(cmd: list[str], cwd: Path, input: str | None = None) -> subprocess.CompletedProcess[str]:
    return subprocess.run(cmd, cwd=cwd, capture_output=True, text=True, input=input)


def _build_consumer(path: Path) -> Path:
    """A consumer project vendoring this repo's Makefile + templates/ + scaffold/
    under .butler/, mirroring how `generate-*` targets are used downstream."""
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


class TestGeneratePyprojectToleratesSingleQuote:
    """Scenario 1: a single quote in PROJECT_DESCRIPTION does not break
    generate-pyproject."""

    def test_description_with_quote_is_written_verbatim(self, tmp_path: Path) -> None:
        consumer = _build_consumer(tmp_path / "consumer")

        result = _run(
            ["make", "generate-pyproject", f"PROJECT_DESCRIPTION={DESCRIPTION_WITH_QUOTE}"],
            cwd=consumer,
        )

        assert result.returncode == 0, (
            f"generate-pyproject must not abort:\nstdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        pyproject = (consumer / "pyproject.toml").read_text()
        assert DESCRIPTION_WITH_QUOTE in pyproject


class TestGenerateGovernanceFilesToleratesSingleQuote:
    """Scenario 2: a single quote in PROJECT_DESCRIPTION does not break
    generate-governance-files."""

    def test_description_with_quote_is_written_verbatim(self, tmp_path: Path) -> None:
        consumer = _build_consumer(tmp_path / "consumer")

        result = _run(
            [
                "make",
                "generate-governance-files",
                f"PROJECT_DESCRIPTION={DESCRIPTION_WITH_QUOTE}",
            ],
            cwd=consumer,
        )

        assert result.returncode == 0, (
            f"generate-governance-files must not abort:\nstdout:\n{result.stdout}\n"
            f"stderr:\n{result.stderr}"
        )
        claude_md = (consumer / "CLAUDE.md").read_text()
        copilot_instructions = (consumer / ".github" / "copilot-instructions.md").read_text()
        assert DESCRIPTION_WITH_QUOTE in claude_md
        assert DESCRIPTION_WITH_QUOTE in copilot_instructions


class TestPlainDescriptionIsUnaffected:
    """Scenario 3: a description without special characters continues to
    produce identical output to current behavior."""

    def test_generate_pyproject_and_governance_files_unaffected(self, tmp_path: Path) -> None:
        consumer = _build_consumer(tmp_path / "consumer")
        plain_description = "Describe your project here."

        pyproject_result = _run(
            ["make", "generate-pyproject", f"PROJECT_DESCRIPTION={plain_description}"],
            cwd=consumer,
        )
        governance_result = _run(
            [
                "make",
                "generate-governance-files",
                f"PROJECT_DESCRIPTION={plain_description}",
            ],
            cwd=consumer,
        )

        assert pyproject_result.returncode == 0
        assert governance_result.returncode == 0
        assert plain_description in (consumer / "pyproject.toml").read_text()
        assert plain_description in (consumer / "CLAUDE.md").read_text()
        assert plain_description in (consumer / ".github" / "copilot-instructions.md").read_text()
