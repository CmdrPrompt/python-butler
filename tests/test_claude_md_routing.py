"""Acceptance tests for TASK-097 / REQUIREMENTS_CLAUDE_MD_ROUTING.md
Requirements 1-5.

The template checks read `templates/CLAUDE.md.tmpl` directly; the length and
dogfooding checks render it through the real `generate-governance-files`
target in a fixture consumer project vendoring this repo under `.butler/`.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = REPO_ROOT / "Makefile"
TEMPLATES = REPO_ROOT / "templates"
TEMPLATE = TEMPLATES / "CLAUDE.md.tmpl"
CLAUDE_AGENTS = REPO_ROOT / "claude-agents"
CLAUDE_SKILLS = REPO_ROOT / "claude-skills"
DOT_CLAUDE_SKILLS = REPO_ROOT / ".claude" / "skills"
SCAFFOLD = REPO_ROOT / "scaffold"
SKILLS = ["changelog", "characterization-tests", "commit-workflow", "task-file-format", "tdd-cycle"]

BUTLER_NAME = "python-butler"
BUTLER_DESCRIPTION = (
    "Shared infrastructure for Python projects — Makefile targets and AI agents "
    "for spec-driven, TDD development."
)
BUTLER_REQUIREMENTS_PATH = "REQUIREMENTS_*.md"
REGEN_ENV = "BUTLER_REGEN_CLAUDE_MD"


def _build_consumer(path: Path) -> Path:
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


def _render(tmp_path: Path, *make_vars: str) -> str:
    consumer = _build_consumer(tmp_path / "consumer")
    cmd = ["make", "generate-governance-files", "ENABLE_BDD=1", *make_vars]
    result = subprocess.run(cmd, cwd=consumer, capture_output=True, text=True)
    assert result.returncode == 0, f"{cmd} failed:\n{result.stdout}\n{result.stderr}"
    return (consumer / "CLAUDE.md").read_text()


def _section(text: str, heading: str) -> str:
    match = re.search(rf"^## {re.escape(heading)}\n(.*?)(?=^## |\Z)", text, re.M | re.S)
    assert match, f"section '## {heading}' missing"
    return match.group(1)


def _description(skill_md: Path) -> str:
    match = re.search(r'^description: "(.*)"$', skill_md.read_text(), re.M)
    assert match, f"no quoted description in {skill_md}"
    return match.group(1)


class TestTemplateRoutesToSkills:
    """Scenario 1: Template names skills instead of restating skill-owned
    content (Requirement 1)."""

    def test_skill_owned_content_is_not_restated(self) -> None:
        text = TEMPLATE.read_text()
        assert "make commit-current-task           #" not in text
        assert "```bash\nmake branch-task" not in text
        assert "TASK-ID as a suffix reference only" not in text
        assert "Group related work" not in text
        assert "baseline" not in text
        assert "## Bug Discovery" not in text

    def test_skills_are_named(self) -> None:
        text = TEMPLATE.read_text()
        for skill in ["commit-workflow", "task-file-format", "tdd-cycle", "changelog"]:
            assert f"`{skill}`" in text, skill


class TestTemplateKeepsUnownedRules:
    """Scenario 2: Template keeps every rule no skill owns (Requirement 1)."""

    def test_spec_first_gate(self) -> None:
        text = _section(TEMPLATE.read_text(), "Spec-Driven Development")
        assert "{{REQUIREMENTS_PATH}}" in text
        assert "Is this what you intended?" in text
        assert "explicit" in text
        assert "use case" in text

    def test_task_management_auto_apply_and_interfaces(self) -> None:
        text = _section(TEMPLATE.read_text(), "Task Management")
        assert "{{WORKFLOW_GUARDIAN_NAME}}" in text
        assert "automatically" in text
        assert "`make`" in text
        assert "`butler` CLI" in text
        assert "`butler-mcp`" in text
        assert "raw `git`/`gh`" in text
        assert "task/<NNN>-short-description" in text
        assert "`main`" in text

    def test_hypothesis_rule(self) -> None:
        assert "Hypothesis" in _section(TEMPLATE.read_text(), "TDD")

    def test_cross_workspace_boundary_keeps_all_four_rules(self) -> None:
        text = _section(TEMPLATE.read_text(), "Cross-Workspace Boundary")
        assert "out of bounds" in text
        assert "`lib/`" in text
        assert "Never write code" in text
        assert "ask first, then edit" in text
        assert "blocker" in text

    def test_what_not_to_do(self) -> None:
        text = _section(TEMPLATE.read_text(), "What NOT to Do")
        assert "`make lint`" in text
        assert "`make test`" in text
        assert "dependencies" in text
        assert "# type: ignore" in text
        assert "git commit" in text


class TestGeneratedClaudeMdLength:
    """Scenario 3: Generated CLAUDE.md is at most 70 lines (Requirement 2)."""

    def test_at_most_70_lines_excluding_title_and_description(self, tmp_path: Path) -> None:
        title, blank, description, *body = _render(tmp_path).splitlines()
        assert title.startswith("# ") and not blank and description
        assert len(body) <= 70, f"{len(body)} lines"


class TestTemplateReferences:
    """Scenario 4: Template references match what a generated project has
    (Requirement 3)."""

    def test_sync_main_not_git_merge(self) -> None:
        text = TEMPLATE.read_text()
        assert "make sync-main" in text
        assert "git merge main" not in text

    def test_no_github_agents_paths(self) -> None:
        assert ".github/agents/" not in TEMPLATE.read_text()


class TestPythonButlerClaudeMd:
    """Scenario 5: python-butler's CLAUDE.md matches the rendered template
    (Requirement 4)."""

    def test_tracked_claude_md_matches_rendered_template(self, tmp_path: Path) -> None:
        rendered = _render(
            tmp_path,
            f"PROJECT_NAME={BUTLER_NAME}",
            f"PROJECT_DESCRIPTION={BUTLER_DESCRIPTION}",
            f"REQUIREMENTS_PATH={BUTLER_REQUIREMENTS_PATH}",
        )
        target = REPO_ROOT / "CLAUDE.md"
        if os.environ.get(REGEN_ENV) == "1":
            target.write_text(rendered)
        assert target.exists() and target.read_text() == rendered, (
            "CLAUDE.md differs from templates/CLAUDE.md.tmpl. Regenerate with: "
            f"{REGEN_ENV}=1 uv run pytest tests/test_claude_md_routing.py"
        )


class TestSkillDescriptions:
    """Scenario 6: Skill descriptions are at most 200 characters
    (Requirement 5)."""

    def test_descriptions_are_short_and_state_when_to_use(self) -> None:
        for skill in SKILLS:
            description = _description(CLAUDE_SKILLS / skill / "SKILL.md")
            assert len(description) <= 200, f"{skill}: {len(description)} chars"
            assert re.match(r"Use (when|before|after) ", description), skill

    def test_skill_directories_stay_identical(self) -> None:
        for skill in SKILLS:
            assert (CLAUDE_SKILLS / skill / "SKILL.md").read_bytes() == (
                DOT_CLAUDE_SKILLS / skill / "SKILL.md"
            ).read_bytes(), skill
