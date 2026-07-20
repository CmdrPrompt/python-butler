"""Regression test for TASK-051 / REQUIREMENTS_SUBMODULE.md Requirement 5.

The rest of this file's original scope (TASK-048, TASK-051, TASK-053's
`butler-pull` trim-guard/change-detection behavior) tested `butler-trim` and
the subtree-pull-then-trim cycle, both retired outright by TASK-054 /
REQUIREMENTS_SUBMODULE.md (`butler-trim` is no longer a defined Makefile
target; see `tests/test_butler_submodule.py` for the submodule-based
replacement coverage). Those tests were removed as characterizing behavior
that no longer exists, per REQUIREMENTS_SUBMODULE.md's deprecation of
REQUIREMENTS_BUTLER_PULL.md in full.

`generate-governance-files`'s `claude-skills/` -> `.claude/skills/` copy
behavior (TASK-051 Requirement 3) is mechanism-independent and carried
forward unchanged as REQUIREMENTS_SUBMODULE.md Requirement 5 — this test
still exercises it directly (via a plain `git subtree add`, independent of
any Makefile pull/trim target) to keep that coverage in place.
"""

from __future__ import annotations

import os
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = REPO_ROOT / "Makefile"
TEMPLATES = REPO_ROOT / "templates"
CLAUDE_AGENTS = REPO_ROOT / "claude-agents"
CLAUDE_SKILLS = REPO_ROOT / "claude-skills"


def _run(
    cmd: list[str], cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, env=env or os.environ.copy()
    )
    assert result.returncode == 0, (
        f"{cmd} in {cwd} failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], cwd=cwd)


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True)
    _git(["init", "-b", "main"], cwd=path)
    _git(["config", "user.email", "test@example.com"], cwd=path)
    _git(["config", "user.name", "Test"], cwd=path)


def _build_upstream(path: Path) -> None:
    """A fixture butler source repo: this repo's real Makefile, templates/,
    claude-agents/, and claude-skills/."""
    _init_repo(path)
    shutil.copy(MAKEFILE, path / "Makefile")
    shutil.copytree(TEMPLATES, path / "templates")
    shutil.copytree(CLAUDE_AGENTS, path / "claude-agents")
    shutil.copytree(CLAUDE_SKILLS, path / "claude-skills")
    _git(["add", "-A"], cwd=path)
    _git(["commit", "-m", "initial butler"], cwd=path)


class TestGenerateGovernanceFilesCopiesSkills:
    """Scenario: TASK-051 — `generate-governance-files` must copy every
    `.butler/claude-skills/*/SKILL.md` into `.claude/skills/<name>/SKILL.md`,
    mirroring the existing `claude-agents/` -> `.claude/agents/` copy."""

    def test_skill_files_are_copied_to_claude_skills(self, tmp_path: Path) -> None:
        upstream = tmp_path / "upstream"
        consumer = tmp_path / "consumer"
        _build_upstream(upstream)

        _init_repo(consumer)
        (consumer / "README.md").write_text("# consumer\n")
        (consumer / "Makefile").write_text("include .butler/Makefile\n")
        _git(["add", "-A"], cwd=consumer)
        _git(["commit", "-m", "initial consumer"], cwd=consumer)
        _git(
            ["subtree", "add", "--prefix=.butler", str(upstream), "main", "--squash"],
            cwd=consumer,
        )

        _run(
            ["make", "generate-governance-files", "FORCE=1"],
            cwd=consumer,
            env={**os.environ, "BUTLER_REMOTE": str(upstream)},
        )

        source_skills = sorted((upstream / "claude-skills").iterdir())
        assert source_skills, "fixture upstream must ship at least one claude-skills/<name>/"
        for skill_dir in source_skills:
            copied = consumer / ".claude" / "skills" / skill_dir.name / "SKILL.md"
            assert copied.exists(), (
                f"generate-governance-files must copy claude-skills/{skill_dir.name}/SKILL.md "
                "into .claude/skills/"
            )
            assert copied.read_text() == (skill_dir / "SKILL.md").read_text()
