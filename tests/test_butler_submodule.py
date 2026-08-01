"""Failing (red-phase) characterization tests for TASK-054 / REQUIREMENTS_SUBMODULE.md.

These tests describe the target behavior of switching `.butler` distribution
from a `git subtree` to a `git submodule`. They exercise the real
`butler-fetch`/`butler-pull`/`butler-check`/`butler-trim`/`butler-uninstall`
Makefile targets, plus `README.md`'s adoption/migration text, against a
fixture "upstream" butler source repo and a "consumer" repo that has adopted
`.butler` as a git submodule (mirroring the harness style used in
`test_butler_pull_governance_regen.py`, but for submodule instead of subtree
adoption).

None of REQUIREMENTS_SUBMODULE.md's Requirements 1-6 are implemented yet, so
every test in this file is expected to fail against the current
subtree-based `Makefile`/`README.md` — that is the correct red state for
TASK-054. Do not weaken these assertions to make them pass early; that would
mean the test stopped specifying the new behavior.
"""

from __future__ import annotations

import os
import re
import shutil
import subprocess
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
MAKEFILE = REPO_ROOT / "Makefile"
README = REPO_ROOT / "README.md"
TEMPLATES = REPO_ROOT / "templates"
CLAUDE_AGENTS = REPO_ROOT / "claude-agents"
CLAUDE_SKILLS = REPO_ROOT / "claude-skills"
SCAFFOLD = REPO_ROOT / "scaffold"

# Local git submodule fetches over a plain filesystem path are blocked by
# default (CVE-2022-39253 hardening) unless explicitly allowed. This is a
# test-fixture concern only (the real BUTLER_REMOTE is an https:// URL);
# every git/make invocation below that touches a submodule remote passes
# this in its environment.
_ALLOW_FILE_PROTOCOL = {"GIT_ALLOW_PROTOCOL": "file"}


def _env(upstream: Path) -> dict[str, str]:
    return {**os.environ, **_ALLOW_FILE_PROTOCOL, "BUTLER_REMOTE": str(upstream)}


def _run(
    cmd: list[str], cwd: Path, env: dict[str, str] | None = None, check: bool = True
) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        cmd, cwd=cwd, capture_output=True, text=True, env=env or os.environ.copy()
    )
    if check:
        assert result.returncode == 0, (
            f"{cmd} in {cwd} failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
        )
    return result


def _git(
    args: list[str], cwd: Path, env: dict[str, str] | None = None
) -> subprocess.CompletedProcess[str]:
    return _run(["git", *args], cwd=cwd, env=env)


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
    shutil.copytree(SCAFFOLD, path / "scaffold")
    _git(["add", "-A"], cwd=path)
    _git(["commit", "-m", "initial butler"], cwd=path)


def _adopt_via_submodule(consumer: Path, upstream: Path) -> None:
    """Adopt `.butler` as a git submodule (the *target* adoption mechanism
    per REQUIREMENTS_SUBMODULE.md Requirement 1), independent of whether the
    Makefile/README have been updated yet to document/automate it.

    The consumer gets its own root Makefile that `include`s the vendored
    `.butler/Makefile`, exactly as a real adopting project does.
    """
    _init_repo(consumer)
    (consumer / "README.md").write_text("# consumer\n")
    (consumer / "Makefile").write_text("include .butler/Makefile\n")
    _git(["add", "-A"], cwd=consumer)
    _git(["commit", "-m", "initial consumer"], cwd=consumer)
    _git(
        ["submodule", "add", str(upstream), ".butler"],
        cwd=consumer,
        env=_env(upstream),
    )
    _git(["commit", "-m", "add .butler submodule"], cwd=consumer)


class TestReadmeAdoptionUsesSubmodule:
    """Scenario: adoption uses git submodule instead of git subtree."""

    @staticmethod
    def _adoption_sections() -> str:
        text = README.read_text()
        matches = re.findall(
            r"## Adopting in a (?:new|existing) project\n(.*?)(?=\n## )", text, re.DOTALL
        )
        assert matches, "expected README.md to have 'Adopting in a ... project' section(s)"
        return "\n".join(matches)

    def test_adoption_instructions_use_git_submodule_add(self) -> None:
        sections = self._adoption_sections()

        assert "git submodule add" in sections, (
            "README's adoption instructions must use 'git submodule add', not 'git subtree add'"
        )

    def test_adoption_instructions_no_longer_use_git_subtree_add(self) -> None:
        sections = self._adoption_sections()

        assert "git subtree add" not in sections, (
            "README's adoption instructions must not use 'git subtree add' anymore"
        )

    def test_adoption_instructions_no_longer_run_butler_trim(self) -> None:
        sections = self._adoption_sections()

        assert "butler-trim" not in sections, (
            "README's adoption instructions must not tell the user to run "
            "'make butler-trim FORCE=1' anymore -- butler-trim is retired"
        )


class TestButlerFetchMovesSubmodulePointerWithoutMerging:
    """Scenario: butler-fetch/butler-pull move the submodule pointer, no merge."""

    def test_fetch_advances_the_submodule_pointer_to_latest_upstream_commit(
        self, tmp_path: Path
    ) -> None:
        upstream = tmp_path / "upstream"
        consumer = tmp_path / "consumer"
        _build_upstream(upstream)
        _adopt_via_submodule(consumer, upstream)

        (upstream / "new-file.txt").write_text("new upstream content\n")
        _git(["add", "-A"], cwd=upstream)
        _git(["commit", "-m", "add new-file.txt"], cwd=upstream)
        latest_upstream_commit = _git(["rev-parse", "HEAD"], cwd=upstream).stdout.strip()

        _run(["make", "butler-fetch"], cwd=consumer, env=_env(upstream))

        pointer_after = _git(["rev-parse", "HEAD"], cwd=consumer / ".butler").stdout.strip()
        assert pointer_after == latest_upstream_commit, (
            "butler-fetch must advance .butler's submodule pointer to the latest "
            "commit on the tracked branch of the butler remote"
        )

    def test_fetch_does_not_run_a_subtree_merge(self, tmp_path: Path) -> None:
        upstream = tmp_path / "upstream"
        consumer = tmp_path / "consumer"
        _build_upstream(upstream)
        _adopt_via_submodule(consumer, upstream)

        (upstream / "new-file.txt").write_text("new upstream content\n")
        _git(["add", "-A"], cwd=upstream)
        _git(["commit", "-m", "add new-file.txt"], cwd=upstream)

        consumer_head_before = _git(["rev-parse", "HEAD"], cwd=consumer).stdout.strip()

        _run(["make", "butler-fetch"], cwd=consumer, env=_env(upstream))

        consumer_head_after = _git(["rev-parse", "HEAD"], cwd=consumer).stdout.strip()
        assert consumer_head_after == consumer_head_before, (
            "butler-fetch must not create a merge/subtree commit in the consumer's "
            "own history -- only the submodule gitlink entry (an unstaged working- "
            "tree change) should move"
        )

    def test_fetch_prints_the_git_add_and_commit_follow_up_without_running_it(
        self, tmp_path: Path
    ) -> None:
        upstream = tmp_path / "upstream"
        consumer = tmp_path / "consumer"
        _build_upstream(upstream)
        _adopt_via_submodule(consumer, upstream)

        (upstream / "new-file.txt").write_text("new upstream content\n")
        _git(["add", "-A"], cwd=upstream)
        _git(["commit", "-m", "add new-file.txt"], cwd=upstream)

        result = _run(["make", "butler-fetch"], cwd=consumer, env=_env(upstream))

        assert "git add .butler" in result.stdout, (
            "butler-fetch must print the exact 'git add .butler' follow-up instead "
            "of committing automatically"
        )
        assert "git commit" in result.stdout
        status = _git(["status", "--porcelain"], cwd=consumer).stdout
        assert status.strip() != "", (
            "the pointer change must be left as an uncommitted working-tree change "
            "for the user to commit themselves"
        )

    def test_pull_advances_the_submodule_pointer_with_no_tree_merge(self, tmp_path: Path) -> None:
        upstream = tmp_path / "upstream"
        consumer = tmp_path / "consumer"
        _build_upstream(upstream)
        _adopt_via_submodule(consumer, upstream)

        (upstream / "new-file.txt").write_text("new upstream content\n")
        _git(["add", "-A"], cwd=upstream)
        _git(["commit", "-m", "add new-file.txt"], cwd=upstream)
        latest_upstream_commit = _git(["rev-parse", "HEAD"], cwd=upstream).stdout.strip()
        consumer_head_before = _git(["rev-parse", "HEAD"], cwd=consumer).stdout.strip()

        _run(["make", "butler-pull"], cwd=consumer, env=_env(upstream))

        pointer_after = _git(["rev-parse", "HEAD"], cwd=consumer / ".butler").stdout.strip()
        consumer_head_after = _git(["rev-parse", "HEAD"], cwd=consumer).stdout.strip()
        assert pointer_after == latest_upstream_commit
        assert consumer_head_after == consumer_head_before, (
            "butler-pull must not merge butler's tree into the consumer's own history"
        )


class TestButlerCheckComparesSubmodulePointer:
    """Scenario: butler-check compares the submodule pointer, not .butler-version."""

    def test_reports_up_to_date_when_submodule_pointer_matches_remote_head(
        self, tmp_path: Path
    ) -> None:
        upstream = tmp_path / "upstream"
        consumer = tmp_path / "consumer"
        _build_upstream(upstream)
        _adopt_via_submodule(consumer, upstream)
        # No new upstream commits since adoption: the submodule pointer
        # already matches the tracked branch's HEAD, and there is no
        # .butler-version file at all (that file is a subtree-only artifact).
        assert not (consumer / ".butler-version").exists()

        result = _run(["make", "butler-check"], cwd=consumer, env=_env(upstream))

        assert "up to date" in result.stdout.lower(), (
            "butler-check must compare .butler's recorded submodule commit against "
            "the remote's tracked branch, not look for a .butler-version file "
            f"(got: {result.stdout!r})"
        )

    def test_reports_update_available_when_submodule_pointer_is_behind_remote(
        self, tmp_path: Path
    ) -> None:
        upstream = tmp_path / "upstream"
        consumer = tmp_path / "consumer"
        _build_upstream(upstream)
        _adopt_via_submodule(consumer, upstream)

        (upstream / "new-file.txt").write_text("new upstream content\n")
        _git(["add", "-A"], cwd=upstream)
        _git(["commit", "-m", "add new-file.txt"], cwd=upstream)

        result = _run(["make", "butler-check"], cwd=consumer, env=_env(upstream))

        assert "updates available" in result.stdout.lower()
        assert "make butler-pull" in result.stdout


class TestButlerTrimIsRemoved:
    """Scenario: butler-trim and its guard logic are removed."""

    def test_butler_trim_is_no_longer_a_defined_makefile_target(self, tmp_path: Path) -> None:
        upstream = tmp_path / "upstream"
        consumer = tmp_path / "consumer"
        _build_upstream(upstream)
        _adopt_via_submodule(consumer, upstream)

        result = subprocess.run(
            ["make", "butler-trim"],
            cwd=consumer,
            capture_output=True,
            text=True,
            env=_env(upstream),
        )

        assert result.returncode != 0, (
            "make butler-trim must fail (target no longer defined) once butler-trim is retired"
        )
        assert "no rule to make target" in (result.stdout + result.stderr).lower(), (
            f"expected a 'No rule to make target' failure, got:\n"
            f"stdout: {result.stdout}\nstderr: {result.stderr}"
        )

    def test_templates_claude_agents_and_claude_skills_remain_after_pull(
        self, tmp_path: Path
    ) -> None:
        upstream = tmp_path / "upstream"
        consumer = tmp_path / "consumer"
        _build_upstream(upstream)
        _adopt_via_submodule(consumer, upstream)

        (upstream / "templates" / "new.tmpl").write_text("placeholder\n")
        _git(["add", "-A"], cwd=upstream)
        _git(["commit", "-m", "add new template"], cwd=upstream)

        _run(["make", "butler-pull"], cwd=consumer, env=_env(upstream))

        assert (consumer / ".butler" / "templates").exists(), (
            "no trim step must ever remove .butler/templates/"
        )
        assert (consumer / ".butler" / "claude-agents").exists(), (
            "no trim step must ever remove .butler/claude-agents/"
        )
        assert (consumer / ".butler" / "claude-skills").exists(), (
            "no trim step must ever remove .butler/claude-skills/"
        )


class TestGenerateGovernanceFilesStillCopiesSkillsViaSubmodule:
    """Scenario: generate-governance-files still copies claude-skills content,
    unchanged, when `.butler` is a submodule checkout that has since been
    updated via `butler-pull`."""

    def test_new_skill_pulled_via_submodule_is_copied_by_generate_governance_files(
        self, tmp_path: Path
    ) -> None:
        upstream = tmp_path / "upstream"
        consumer = tmp_path / "consumer"
        _build_upstream(upstream)
        _adopt_via_submodule(consumer, upstream)

        new_skill_dir = upstream / "claude-skills" / "new-example"
        new_skill_dir.mkdir()
        (new_skill_dir / "SKILL.md").write_text(
            "---\nname: new-example\ndescription: Added by the TASK-054 test.\n---\n"
        )
        _git(["add", "-A"], cwd=upstream)
        _git(["commit", "-m", "add new-example skill"], cwd=upstream)

        _run(["make", "butler-pull"], cwd=consumer, env=_env(upstream))
        _run(
            ["make", "generate-governance-files", "FORCE=1"],
            cwd=consumer,
            env=_env(upstream),
        )

        copied = consumer / ".claude" / "skills" / "new-example" / "SKILL.md"
        assert copied.exists(), (
            "generate-governance-files must still copy "
            ".butler/claude-skills/<name>/SKILL.md into .claude/skills/ after a "
            "submodule-based butler-pull, unchanged from today's subtree-based "
            "behavior"
        )
        assert copied.read_text() == (new_skill_dir / "SKILL.md").read_text()


class TestReadmeDocumentsSubtreeToSubmoduleMigration:
    """Scenario: a documented migration path exists for subtree-based consumers."""

    def test_readme_has_a_migration_section(self) -> None:
        text = README.read_text()

        assert re.search(r"## .*[Mm]igrat", text), (
            "README.md must document a migration section for existing "
            "subtree-based consumers to convert .butler to a submodule"
        )

    def test_migration_section_documents_updating_the_makefile_include_line(self) -> None:
        text = README.read_text()
        match = re.search(r"## .*[Mm]igrat.*?\n(.*?)(?=\n## |\Z)", text, re.DOTALL)

        assert match, "expected a migration section to exist"
        section = match.group(1)
        assert "include .butler/Makefile" in section, (
            "the migration section must cover updating the Makefile's "
            "'include .butler/Makefile' line if its path changed"
        )


class TestButlerUninstallRemovesSubmoduleCleanly:
    """Scenario: butler-uninstall removes the submodule cleanly."""

    def test_subtree_category_deinits_and_removes_the_submodule(self, tmp_path: Path) -> None:
        upstream = tmp_path / "upstream"
        consumer = tmp_path / "consumer"
        _build_upstream(upstream)
        _adopt_via_submodule(consumer, upstream)

        _run(
            ["make", "butler-uninstall", "CATEGORIES=subtree"],
            cwd=consumer,
            env=_env(upstream),
        )

        assert not (consumer / ".butler").exists(), "the .butler/ working tree must be removed"
        gitmodules = consumer / ".gitmodules"
        if gitmodules.exists():
            assert ".butler" not in gitmodules.read_text(), (
                "the .gitmodules entry for .butler must be removed (or the file "
                "removed entirely if it becomes empty)"
            )
        assert not (consumer / ".git" / "modules" / ".butler").exists(), (
            "make butler-uninstall CATEGORIES=subtree must run 'git submodule "
            "deinit -f .butler' + 'git rm -f .butler', not a plain 'rm -rf "
            ".butler', which leaves .git/modules/.butler metadata behind"
        )

    def test_subtree_category_uses_git_submodule_deinit_not_plain_rm(self, tmp_path: Path) -> None:
        upstream = tmp_path / "upstream"
        consumer = tmp_path / "consumer"
        _build_upstream(upstream)
        _adopt_via_submodule(consumer, upstream)

        result = _run(
            ["make", "butler-uninstall", "CATEGORIES=subtree", "DRY_RUN=1"],
            cwd=consumer,
            env=_env(upstream),
        )

        assert "submodule deinit" in result.stdout, (
            f"expected the dry-run output to describe a submodule deinit, got: {result.stdout!r}"
        )
