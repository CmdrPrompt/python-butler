"""Tests for butler_core.uninstall."""

from __future__ import annotations

import os
import subprocess
from pathlib import Path
from unittest.mock import MagicMock

import pytest
from hypothesis import given
from hypothesis import strategies as st

from butler_core.uninstall import (
    CATEGORIES,
    DirtyWorkingTreeError,
    InvalidCategoryError,
    apply_uninstall,
    plan_uninstall,
    remove_makefile_include,
)

# Local git submodule fetches over a plain filesystem path are blocked by
# default (CVE-2022-39253 hardening) unless explicitly allowed. This is a
# test-fixture concern only; every git invocation below that adds/updates a
# submodule from a local path passes this in its environment.
_ALLOW_FILE_PROTOCOL_ENV = {**os.environ, "GIT_ALLOW_PROTOCOL": "file"}


def _git(args: list[str], cwd: Path) -> subprocess.CompletedProcess[str]:
    result = subprocess.run(
        ["git", *args],
        cwd=cwd,
        capture_output=True,
        text=True,
        env=_ALLOW_FILE_PROTOCOL_ENV,
    )
    assert result.returncode == 0, (
        f"git {args} in {cwd} failed:\nstdout:\n{result.stdout}\nstderr:\n{result.stderr}"
    )
    return result


def _init_repo(path: Path) -> None:
    path.mkdir(parents=True, exist_ok=True)
    _git(["init", "-b", "main"], cwd=path)
    _git(["config", "user.email", "test@example.com"], cwd=path)
    _git(["config", "user.name", "Test"], cwd=path)


def _add_butler_submodule(project_root: Path, tmp_path_factory: pytest.TempPathFactory) -> None:
    """Adopt `.butler` in `project_root` as a real git submodule pointing at a
    throwaway local upstream repo -- TASK-054 / REQUIREMENTS_SUBMODULE.md
    Requirement 6's target layout, replacing the plain `.butler/` directory
    that today's `apply_uninstall`'s `subtree` category (`shutil.rmtree`)
    assumes."""
    upstream = tmp_path_factory.mktemp("upstream")
    _init_repo(upstream)
    (upstream / "Makefile").write_text("# fixture butler Makefile\n")
    _git(["add", "-A"], cwd=upstream)
    _git(["commit", "-m", "initial butler"], cwd=upstream)

    _init_repo(project_root)
    _git(["commit", "--allow-empty", "-m", "initial consumer"], cwd=project_root)
    _git(["submodule", "add", str(upstream), ".butler"], cwd=project_root)
    _git(["commit", "-m", "add .butler submodule"], cwd=project_root)


_INCLUDE_LINE = "include .butler/Makefile"

_non_include_lines = st.text(alphabet=st.characters(blacklist_characters="\n"), max_size=20).filter(
    lambda s: s.strip() != _INCLUDE_LINE
)


class TestRemoveMakefileInclude:
    @given(other_lines=st.lists(_non_include_lines, max_size=5))
    def test_leaves_text_unchanged_when_include_line_absent(self, other_lines: list[str]) -> None:
        text = "\n".join(other_lines)

        assert remove_makefile_include(text) == text

    @given(
        other_lines=st.lists(_non_include_lines, max_size=3),
        occurrences=st.integers(min_value=1, max_value=4),
    )
    def test_removes_all_occurrences_of_include_line(
        self, other_lines: list[str], occurrences: int
    ) -> None:
        text = "\n".join([*other_lines, *([_INCLUDE_LINE] * occurrences)]) + "\n"

        result = remove_makefile_include(text)

        assert _INCLUDE_LINE not in result, (
            f"expected no occurrences of the include line, got {result!r}"
        )

    @given(padding=st.text(alphabet=" \t", max_size=5))
    def test_removes_include_line_regardless_of_surrounding_whitespace(self, padding: str) -> None:
        text = f"{padding}{_INCLUDE_LINE}{padding}\n"

        assert remove_makefile_include(text) == ""

    def test_preserves_unrelated_surrounding_lines(self) -> None:
        text = "VAR := 1\ninclude .butler/Makefile\n\ntarget:\n\techo hi\n"

        result = remove_makefile_include(text)

        assert result == "VAR := 1\n\ntarget:\n\techo hi\n", (
            f"expected unrelated lines preserved unchanged, got {result!r}"
        )


class TestPlanUninstall:
    def test_lists_subtree_removal_when_butler_dir_exists(self, tmp_path: Path) -> None:
        (tmp_path / ".butler").mkdir()

        actions = plan_uninstall(tmp_path, ["subtree"])

        assert any(".butler" in action for action in actions), (
            f"expected a planned action mentioning .butler, got {actions}"
        )

    def test_omits_subtree_action_when_butler_dir_absent(self, tmp_path: Path) -> None:
        actions = plan_uninstall(tmp_path, ["subtree"])

        assert actions == [], f"expected no planned actions, got {actions}"

    def test_lists_makefile_include_removal_when_present(self, tmp_path: Path) -> None:
        (tmp_path / "Makefile").write_text("include .butler/Makefile\n")

        actions = plan_uninstall(tmp_path, ["makefile"])

        assert any("Makefile" in action for action in actions), (
            f"expected a planned action mentioning Makefile, got {actions}"
        )

    def test_lists_governance_files_present(self, tmp_path: Path) -> None:
        (tmp_path / "CLAUDE.md").write_text("# CLAUDE.md\n")

        actions = plan_uninstall(tmp_path, ["governance"])

        assert any("CLAUDE.md" in action for action in actions), (
            f"expected a planned action mentioning CLAUDE.md, got {actions}"
        )

    def test_does_not_touch_filesystem(self, tmp_path: Path) -> None:
        (tmp_path / ".butler").mkdir()
        (tmp_path / "Makefile").write_text("include .butler/Makefile\n")
        (tmp_path / "CLAUDE.md").write_text("# CLAUDE.md\n")

        plan_uninstall(tmp_path, list(CATEGORIES))

        assert (tmp_path / ".butler").exists(), "plan_uninstall must not remove .butler/"
        assert (tmp_path / "CLAUDE.md").exists(), "plan_uninstall must not remove CLAUDE.md"
        assert "include .butler/Makefile" in (tmp_path / "Makefile").read_text(), (
            "plan_uninstall must not modify Makefile"
        )

    def test_raises_on_unknown_category(self, tmp_path: Path) -> None:
        with pytest.raises(InvalidCategoryError):
            plan_uninstall(tmp_path, ["not-a-real-category"])


class TestApplyUninstall:
    @staticmethod
    def _clean(_root: Path) -> bool:
        return False

    def test_removes_butler_directory(self, tmp_path: Path) -> None:
        (tmp_path / ".butler").mkdir()

        apply_uninstall(tmp_path, ["subtree"], dirty_check=self._clean)

        assert not (tmp_path / ".butler").exists()

    def test_removes_only_include_line_from_makefile(self, tmp_path: Path) -> None:
        (tmp_path / "Makefile").write_text(
            "VAR := 1\ninclude .butler/Makefile\n\nall:\n\techo hi\n"
        )

        apply_uninstall(tmp_path, ["makefile"], dirty_check=self._clean)

        result = (tmp_path / "Makefile").read_text()
        assert "include .butler/Makefile" not in result
        assert "VAR := 1" in result
        assert "all:" in result

    def test_removes_governance_files(self, tmp_path: Path) -> None:
        (tmp_path / "CLAUDE.md").write_text("# CLAUDE.md\n")
        (tmp_path / ".claude").mkdir()
        (tmp_path / ".claude" / "agents").mkdir()

        apply_uninstall(tmp_path, ["governance"], dirty_check=self._clean)

        assert not (tmp_path / "CLAUDE.md").exists()
        assert not (tmp_path / ".claude" / "agents").exists()

    def test_never_touches_docs_tasks_directory(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "docs" / "tasks"
        tasks_dir.mkdir(parents=True)
        task_file = tasks_dir / "TASK-001-example.md"
        task_file.write_text("# TASK-001 Example\n")
        (tmp_path / ".butler").mkdir()
        (tmp_path / "Makefile").write_text("include .butler/Makefile\n")
        (tmp_path / "CLAUDE.md").write_text("# CLAUDE.md\n")

        apply_uninstall(tmp_path, list(CATEGORIES), dirty_check=self._clean)

        assert task_file.read_text() == "# TASK-001 Example\n", (
            "docs/tasks/ must never be modified by any uninstall category"
        )

    def test_returns_list_of_actions_taken(self, tmp_path: Path) -> None:
        (tmp_path / ".butler").mkdir()

        actions = apply_uninstall(tmp_path, ["subtree"], dirty_check=self._clean)

        assert any(".butler" in action for action in actions), (
            f"expected the returned actions to describe the .butler removal, got {actions}"
        )

    def test_raises_dirty_working_tree_error_when_dirty_and_not_forced(
        self, tmp_path: Path
    ) -> None:
        (tmp_path / ".butler").mkdir()

        with pytest.raises(DirtyWorkingTreeError):
            apply_uninstall(tmp_path, ["subtree"], dirty_check=lambda _root: True)

        assert (tmp_path / ".butler").exists(), (
            "nothing should be removed when the dirty-tree guard trips"
        )

    def test_proceeds_when_dirty_but_forced(self, tmp_path: Path) -> None:
        (tmp_path / ".butler").mkdir()

        apply_uninstall(tmp_path, ["subtree"], force=True, dirty_check=lambda _root: True)

        assert not (tmp_path / ".butler").exists()

    def test_raises_on_unknown_category(self, tmp_path: Path) -> None:
        with pytest.raises(InvalidCategoryError):
            apply_uninstall(tmp_path, ["not-a-real-category"], dirty_check=self._clean)

    def test_default_dirty_check_uses_real_git_status(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        mock_run = MagicMock(return_value=MagicMock(returncode=0, stdout=" M some_file.py\n"))
        monkeypatch.setattr("butler_core.uninstall.subprocess.run", mock_run)
        (tmp_path / ".butler").mkdir()

        with pytest.raises(DirtyWorkingTreeError):
            apply_uninstall(tmp_path, ["subtree"])

        assert mock_run.called, "expected the default dirty-check to shell out to git status"


class TestSubtreeCategoryRemovesGitSubmoduleCleanly:
    """Failing (red-phase) characterization tests for TASK-054 /
    REQUIREMENTS_SUBMODULE.md Requirement 6: the `subtree` category must
    remove a `.butler` *git submodule* correctly (`git submodule deinit -f`
    + `git rm -f`, plus the `.gitmodules` entry and `.git/modules/.butler`
    metadata) instead of a plain `shutil.rmtree(.butler)`, which leaves both
    behind. None of this is implemented yet, so these are expected to fail
    against the current `apply_uninstall`/`plan_uninstall`.
    """

    @staticmethod
    def _clean(_root: Path) -> bool:
        return False

    def test_apply_uninstall_removes_the_gitmodules_entry(
        self, tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
    ) -> None:
        _add_butler_submodule(tmp_path, tmp_path_factory)

        apply_uninstall(tmp_path, ["subtree"], dirty_check=self._clean)

        assert not (tmp_path / ".butler").exists()
        gitmodules = tmp_path / ".gitmodules"
        if gitmodules.exists():
            assert ".butler" not in gitmodules.read_text(), (
                "the .gitmodules entry for .butler must be removed (or the file "
                "removed entirely if it becomes empty)"
            )

    def test_apply_uninstall_removes_git_modules_metadata(
        self, tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
    ) -> None:
        _add_butler_submodule(tmp_path, tmp_path_factory)
        assert (tmp_path / ".git" / "modules" / ".butler").exists(), (
            "fixture assumption: adding a real git submodule populates .git/modules/.butler"
        )

        apply_uninstall(tmp_path, ["subtree"], dirty_check=self._clean)

        assert not (tmp_path / ".git" / "modules" / ".butler").exists(), (
            "apply_uninstall's subtree category must run 'git submodule deinit -f "
            ".butler' (not a plain shutil.rmtree), or .git/modules/.butler metadata "
            "is left behind"
        )

    def test_plan_uninstall_describes_a_submodule_deinit(
        self, tmp_path: Path, tmp_path_factory: pytest.TempPathFactory
    ) -> None:
        _add_butler_submodule(tmp_path, tmp_path_factory)

        actions = plan_uninstall(tmp_path, ["subtree"])

        assert any("submodule deinit" in action for action in actions), (
            f"expected a planned action describing a submodule deinit, got {actions}"
        )

    def test_apply_uninstall_is_a_noop_when_butler_dir_absent(self, tmp_path: Path) -> None:
        actions = apply_uninstall(tmp_path, ["subtree"], dirty_check=self._clean)

        assert actions == []
        assert not (tmp_path / ".butler").exists()

    def test_apply_uninstall_falls_back_to_rmtree_when_git_rm_fails(
        self, tmp_path: Path, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        (tmp_path / ".butler").mkdir()
        (tmp_path / ".gitmodules").write_text('[submodule ".butler"]\n\tpath = .butler\n')

        def _fake_run(cmd: list[str], **_kwargs: object) -> MagicMock:
            returncode = 1 if cmd[:2] == ["git", "rm"] else 0
            return MagicMock(returncode=returncode, stdout="", stderr="")

        monkeypatch.setattr("butler_core.uninstall.subprocess.run", _fake_run)

        apply_uninstall(tmp_path, ["subtree"], dirty_check=self._clean)

        assert not (tmp_path / ".butler").exists(), (
            "when 'git rm' fails, apply_uninstall must fall back to a plain rmtree"
        )
