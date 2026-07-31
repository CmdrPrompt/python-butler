"""Tests for butler_core.git_ops."""

from __future__ import annotations

import shlex
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from butler_core.git_ops import (
    GitOpsError,
    branch_for,
    commit_for,
    merge_pr_for,
    open_pr_for,
    stage_for,
)
from butler_core.tasks import TaskNotFoundError, create_task, read_task


def _completed(returncode: int = 0, stdout: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    return result


class TestBranchFor:
    @patch("butler_core.git_ops.subprocess.run")
    def test_creates_new_branch_when_it_does_not_exist(self, mock_run: MagicMock) -> None:
        mock_run.return_value = _completed(returncode=1)
        task = read_task("TASK-015", tasks_dir="docs/tasks")

        branch_for(task)

        calls = mock_run.call_args_list
        assert calls[0].args[0] == [
            "git",
            "show-ref",
            "--verify",
            "--quiet",
            f"refs/heads/{task.branch_name}",
        ]
        assert calls[1].args[0] == ["git", "fetch", "origin", "main"]
        assert calls[2].args[0] == ["git", "checkout", "-b", task.branch_name, "origin/main"]

    @patch("butler_core.git_ops.subprocess.run")
    def test_new_branch_is_based_on_origin_main_not_the_currently_checked_out_branch(
        self, mock_run: MagicMock
    ) -> None:
        """Regression test: previously `git checkout -b <branch>` (with no
        explicit start point) based the new branch on whatever branch
        happened to be checked out. Since `open_pr_for` no longer returns to
        `main` automatically (TASK-061), a new task branch must be pinned to
        `origin/main` explicitly, not to the current HEAD, to avoid
        accidentally forking off a leftover, already-merged task branch."""
        mock_run.return_value = _completed(returncode=1)
        task = read_task("TASK-015", tasks_dir="docs/tasks")

        branch_for(task)

        checkout_call = next(
            call
            for call in mock_run.call_args_list
            if call.args[0][:3] == ["git", "checkout", "-b"]
        )
        assert checkout_call.args[0][-1] == "origin/main"

    @patch("butler_core.git_ops.subprocess.run")
    def test_switches_to_branch_when_it_already_exists(self, mock_run: MagicMock) -> None:
        mock_run.return_value = _completed(returncode=0)
        task = read_task("TASK-015", tasks_dir="docs/tasks")

        branch_for(task)

        calls = mock_run.call_args_list
        assert calls[1].args[0] == ["git", "checkout", task.branch_name]

    @patch("butler_core.git_ops.subprocess.run")
    def test_switching_to_existing_branch_does_not_fetch_or_reference_origin_main(
        self, mock_run: MagicMock
    ) -> None:
        mock_run.return_value = _completed(returncode=0)
        task = read_task("TASK-015", tasks_dir="docs/tasks")

        branch_for(task)

        commands = [call.args[0] for call in mock_run.call_args_list]
        assert not any("fetch" in cmd for cmd in commands)
        assert not any("origin/main" in cmd for cmd in commands)


class TestStageFor:
    @patch("butler_core.git_ops.subprocess.run")
    def test_runs_fix_format_pymarkdown_add_and_refresh(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        (tmp_path / "README.md").write_text("# hi\n")
        (tmp_path / ".venv").mkdir()
        (tmp_path / ".venv" / "excluded.md").write_text("nope\n")
        task = create_task("Some task", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.return_value = _completed()

        stage_for(task, repo_root=tmp_path)

        commands = [call.args[0] for call in mock_run.call_args_list]
        assert commands[0] == ["uv", "run", "ruff", "check", "--fix", "."]
        assert commands[1] == ["uv", "run", "ruff", "format", "."]
        assert commands[2][:4] == ["uv", "run", "pymarkdown", "--config"]
        assert "./README.md" in commands[2]
        assert not any("venv" in f for f in commands[2])
        assert "--return-code-scheme" in commands[2]
        scheme_index = commands[2].index("--return-code-scheme")
        assert commands[2][scheme_index + 1] == "minimal"
        assert commands[3] == shlex.split(task.stage_cmd)
        assert commands[4] == ["git", "update-index", "-q", "--refresh"]

    def test_does_not_raise_when_pymarkdown_fixes_a_file(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# hi\n")
        task = create_task("Some task", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))

        def fake_run(
            cmd: list[str], check: bool = False, cwd: Path | None = None, **kwargs: object
        ) -> MagicMock:
            if "pymarkdown" in cmd:
                assert "--return-code-scheme" in cmd
                assert cmd[cmd.index("--return-code-scheme") + 1] == "minimal"
                return _completed(returncode=0)
            return _completed(returncode=0)

        with patch("butler_core.git_ops.subprocess.run", side_effect=fake_run):
            stage_for(task, repo_root=tmp_path)

    def test_raises_when_pymarkdown_reports_a_genuine_error(self, tmp_path: Path) -> None:
        (tmp_path / "README.md").write_text("# hi\n")
        task = create_task("Some task", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))

        def fake_run(
            cmd: list[str], check: bool = False, cwd: Path | None = None, **kwargs: object
        ) -> MagicMock:
            if "pymarkdown" in cmd:
                if check:
                    raise subprocess.CalledProcessError(2, cmd)
                return _completed(returncode=2)
            return _completed(returncode=0)

        with (
            patch("butler_core.git_ops.subprocess.run", side_effect=fake_run),
            pytest.raises(subprocess.CalledProcessError),
        ):
            stage_for(task, repo_root=tmp_path)


class TestCommitFor:
    @patch("butler_core.git_ops.subprocess.run")
    def test_commits_with_task_message(self, mock_run: MagicMock) -> None:
        mock_run.return_value = _completed()
        task = read_task("TASK-015", tasks_dir="docs/tasks")

        commit_for(task)

        mock_run.assert_called_once_with(["git", "commit", "-m", task.commit_message], check=True)


class TestOpenPrFor:
    @patch("butler_core.git_ops.subprocess.run")
    def test_pushes_and_creates_pr(self, mock_run: MagicMock, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "Some description body", tasks_dir=str(tasks_dir))
        mock_run.return_value = _completed()

        open_pr_for(task, tasks_dir=str(tasks_dir))

        commands = [call.args[0] for call in mock_run.call_args_list]
        assert commands[0] == ["git", "push", "-u", "origin", "HEAD"]
        assert commands[1][:2] == ["gh", "pr"]
        assert commands[1][2] == "create"
        title_index = commands[1].index("--title") + 1
        assert commands[1][title_index] == f"{task.id} {task.title}"
        body_index = commands[1].index("--body") + 1
        assert "Some description body" in commands[1][body_index]

    @patch("butler_core.git_ops.subprocess.run")
    def test_stays_on_the_task_branch_after_creating_the_pr(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        """Regression test for TASK-061: previously `open_pr_for` ended with
        `git checkout main`, which (a) made the immediately-following
        `sync-project --stage open`/`--stage draft` step spuriously fail
        (the task file only exists on the task branch, not yet on `main`),
        and (b) forced a manual `git checkout task/<NNN>-...` before merging
        the same task. `open_pr_for` must not switch branches at all."""
        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "Some description body", tasks_dir=str(tasks_dir))
        mock_run.return_value = _completed()

        open_pr_for(task, tasks_dir=str(tasks_dir))

        commands = [call.args[0] for call in mock_run.call_args_list]
        assert not any(cmd[:2] == ["git", "checkout"] for cmd in commands)

    def test_raises_task_not_found_error_for_missing_task_file(self, tmp_path: Path) -> None:
        task = create_task("Temp task", "desc", tasks_dir=str(tmp_path))
        (tmp_path / f"{task.id}-temp-task.md").unlink()

        with pytest.raises(TaskNotFoundError, match=f"No task file found matching '{task.id}'"):
            open_pr_for(task, tasks_dir=str(tmp_path))


class TestMergePrFor:
    @patch("butler_core.git_ops.subprocess.run")
    def test_squash_merges_mergeable_pr_and_pulls_main(self, mock_run: MagicMock) -> None:
        task = read_task("TASK-015", tasks_dir="docs/tasks")
        mock_run.side_effect = [
            _completed(stdout="42\n"),
            _completed(stdout="MERGEABLE\n"),
            _completed(),
            _completed(),
            _completed(),
        ]

        merge_pr_for(task)

        commands = [call.args[0] for call in mock_run.call_args_list]
        assert commands[2] == ["gh", "pr", "merge", "42", "--squash", "--delete-branch"]
        assert commands[3] == ["git", "checkout", "main"]
        assert commands[4] == ["git", "pull"]

    @patch("butler_core.git_ops.subprocess.run")
    def test_raises_when_no_open_pr_found(self, mock_run: MagicMock) -> None:
        task = read_task("TASK-015", tasks_dir="docs/tasks")
        mock_run.return_value = _completed(stdout="\n")

        with pytest.raises(GitOpsError, match=f"No open PR for branch {task.branch_name}"):
            merge_pr_for(task)

    @patch("butler_core.git_ops.subprocess.run")
    def test_raises_when_pr_not_mergeable(self, mock_run: MagicMock) -> None:
        task = read_task("TASK-015", tasks_dir="docs/tasks")
        mock_run.side_effect = [
            _completed(stdout="42\n"),
            _completed(stdout="CONFLICTING\n"),
        ]

        with pytest.raises(GitOpsError, match=r"PR #42 not mergeable \(CONFLICTING\)"):
            merge_pr_for(task)
