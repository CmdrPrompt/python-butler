"""Tests for butler_cli.__main__."""

from __future__ import annotations

import shlex
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from butler_cli.__main__ import main
from butler_core.git_ops import GitOpsError
from butler_core.tasks import create_task, read_task, set_status


class TestList:
    def test_prints_all_tasks_when_no_status_filter(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        create_task("First task", "desc one", tasks_dir=str(tmp_path))
        create_task("Second task", "desc two", tasks_dir=str(tmp_path))

        main(["--tasks-dir", str(tmp_path), "task", "list"])

        out = capsys.readouterr().out
        assert "TASK-001 [todo] First task" in out
        assert "TASK-002 [todo] Second task" in out

    def test_filters_by_status(self, tmp_path: Path, capsys: pytest.CaptureFixture[str]) -> None:
        create_task("First task", "desc one", tasks_dir=str(tmp_path))
        second = create_task("Second task", "desc two", tasks_dir=str(tmp_path))
        set_status(second.id, "done", tasks_dir=str(tmp_path))

        main(["--tasks-dir", str(tmp_path), "task", "list", "--status", "done"])

        out = capsys.readouterr().out
        assert "Second task" in out
        assert "First task" not in out


class TestShow:
    def test_prints_structured_task_data(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        create_task("Some feature", "A description.", tasks_dir=str(tmp_path))

        main(["--tasks-dir", str(tmp_path), "task", "show", "TASK-001"])

        out = capsys.readouterr().out
        assert "TASK-001" in out
        assert "Some feature" in out
        assert "todo" in out
        assert "A description." in out

    def test_prints_checked_and_unchecked_acceptance_criteria(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        task = create_task("Some feature", "desc", tasks_dir=str(tmp_path))
        path = tmp_path / f"{task.id}-some-feature.md"
        text = path.read_text().replace(
            "## Acceptance criteria\n",
            "## Acceptance criteria\n\n- [x] done thing\n- [ ] pending thing\n",
        )
        path.write_text(text)

        main(["--tasks-dir", str(tmp_path), "task", "show", task.id])

        out = capsys.readouterr().out
        assert "[x] done thing" in out
        assert "[ ] pending thing" in out

    def test_prints_completion_date_and_summary_when_present(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        task = create_task("Some feature", "desc", tasks_dir=str(tmp_path))
        path = tmp_path / f"{task.id}-some-feature.md"
        text = path.read_text().replace("**Date:** ", "**Date:** 2026-01-01")
        text = text.replace("**Summary:** ", "**Summary:** All done")
        path.write_text(text)

        main(["--tasks-dir", str(tmp_path), "task", "show", task.id])

        out = capsys.readouterr().out
        assert "Completion date: 2026-01-01" in out
        assert "Completion summary: All done" in out

    def test_raises_clean_error_for_unknown_task(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main(["--tasks-dir", str(tmp_path), "task", "show", "TASK-999"])

        assert exit_code == 1
        err = capsys.readouterr().err
        assert "No task file found matching 'TASK-999'" in err


class TestCreate:
    def test_creates_new_task_file_and_prints_id(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        main(
            [
                "--tasks-dir",
                str(tmp_path),
                "task",
                "create",
                "--title",
                "New feature",
                "--description",
                "Implement it.",
            ]
        )

        out = capsys.readouterr().out
        assert "TASK-001" in out
        created = read_task("TASK-001", tasks_dir=str(tmp_path))
        assert created.title == "New feature"
        assert created.description == "Implement it."


class TestCheck:
    def test_checks_criterion_using_one_based_index(self, tmp_path: Path) -> None:
        task = create_task("Checkbox task", "desc", tasks_dir=str(tmp_path))
        path = tmp_path / f"{task.id}-checkbox-task.md"
        text = path.read_text().replace(
            "## Acceptance criteria\n",
            "## Acceptance criteria\n\n- [ ] first\n- [ ] second\n- [ ] third\n",
        )
        path.write_text(text)

        main(["--tasks-dir", str(tmp_path), "task", "check", task.id, "--criterion", "2"])

        updated = read_task(task.id, tasks_dir=str(tmp_path))
        assert [c.checked for c in updated.acceptance_criteria] == [False, True, False]


class TestGitDelegation:
    """Mocks subprocess.run at the git_ops module's external boundary (not the CLI's
    internal git_ops imports) so these tests observe the actual git/gh commands the
    full CLI -> git_ops pipeline would run, rather than merely that an internal
    collaborator function was invoked."""

    @patch("butler_core.git_ops.subprocess.run")
    def test_branch_creates_new_branch_for_task(self, mock_run: MagicMock, tmp_path: Path) -> None:
        task = create_task("Some feature", "desc", tasks_dir=str(tmp_path))
        # non-zero => _branch_exists() reports False, forcing the create-branch path
        mock_run.return_value = MagicMock(returncode=1)

        exit_code = main(["--tasks-dir", str(tmp_path), "task", "branch", task.id])

        assert exit_code == 0, "branch command should exit 0 on success"
        commands = [call.args[0] for call in mock_run.call_args_list]
        assert ["git", "checkout", "-b", task.branch_name] in commands, (
            f"expected a 'git checkout -b {task.branch_name}' invocation, got {commands}"
        )

    @patch("butler_core.git_ops.subprocess.run")
    def test_stage_runs_tasks_stage_command(self, mock_run: MagicMock, tmp_path: Path) -> None:
        task = create_task("Some feature", "desc", tasks_dir=str(tmp_path))
        mock_run.return_value = MagicMock(returncode=0)

        exit_code = main(["--tasks-dir", str(tmp_path), "task", "stage", task.id])

        assert exit_code == 0, "stage command should exit 0 on success"
        commands = [call.args[0] for call in mock_run.call_args_list]
        assert shlex.split(task.stage_cmd) in commands, (
            f"expected the task's stage command {task.stage_cmd!r} to run, got {commands}"
        )

    @patch("butler_core.git_ops.subprocess.run")
    def test_commit_runs_git_commit_with_task_message(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        task = create_task("Some feature", "desc", tasks_dir=str(tmp_path))
        mock_run.return_value = MagicMock(returncode=0)

        exit_code = main(["--tasks-dir", str(tmp_path), "task", "commit", task.id])

        assert exit_code == 0, "commit command should exit 0 on success"
        commands = [call.args[0] for call in mock_run.call_args_list]
        assert ["git", "commit", "-m", task.commit_message] in commands, (
            f"expected a git commit with message {task.commit_message!r}, got {commands}"
        )

    @patch("butler_core.git_ops.subprocess.run")
    def test_pr_opens_pr_with_task_title(self, mock_run: MagicMock, tmp_path: Path) -> None:
        task = create_task("Some feature", "desc", tasks_dir=str(tmp_path))
        mock_run.return_value = MagicMock(returncode=0)

        exit_code = main(["--tasks-dir", str(tmp_path), "task", "pr", task.id])

        assert exit_code == 0, "pr command should exit 0 on success"
        commands = [call.args[0] for call in mock_run.call_args_list]
        expected_title = f"{task.id} {task.title}"
        assert any(
            cmd[:3] == ["gh", "pr", "create"] and expected_title in cmd for cmd in commands
        ), f"expected a 'gh pr create' with title {expected_title!r}, got {commands}"

    @patch("butler_core.git_ops.subprocess.run")
    def test_merge_squash_merges_tasks_pr(self, mock_run: MagicMock, tmp_path: Path) -> None:
        task = create_task("Some feature", "desc", tasks_dir=str(tmp_path))

        def run_side_effect(cmd: list[str], **_kwargs: object) -> MagicMock:
            if cmd[:3] == ["gh", "pr", "list"]:
                return MagicMock(returncode=0, stdout="42\n")
            if cmd[:3] == ["gh", "pr", "view"]:
                return MagicMock(returncode=0, stdout="MERGEABLE\n")
            return MagicMock(returncode=0)

        mock_run.side_effect = run_side_effect

        exit_code = main(["--tasks-dir", str(tmp_path), "task", "merge", task.id])

        assert exit_code == 0, "merge command should exit 0 on success"
        commands = [call.args[0] for call in mock_run.call_args_list]
        assert ["gh", "pr", "merge", "42", "--squash", "--delete-branch"] in commands, (
            f"expected a squash-merge of PR 42, got {commands}"
        )


class TestErrorHandling:
    def test_task_not_found_error_prints_message_and_returns_exit_code_1(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        exit_code = main(["--tasks-dir", str(tmp_path), "task", "branch", "TASK-999"])

        assert exit_code == 1
        err = capsys.readouterr().err
        assert "No task file found matching 'TASK-999'" in err

    @patch("butler_cli.__main__.merge_pr_for")
    def test_git_ops_error_prints_message_and_returns_exit_code_1(
        self, mock_merge_pr_for: MagicMock, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        create_task("Some feature", "desc", tasks_dir=str(tmp_path))
        mock_merge_pr_for.side_effect = GitOpsError("No open PR for branch task/001-some-feature")

        exit_code = main(["--tasks-dir", str(tmp_path), "task", "merge", "TASK-001"])

        assert exit_code == 1
        err = capsys.readouterr().err
        assert "No open PR for branch task/001-some-feature" in err

    def test_check_index_error_prints_message_and_returns_exit_code_1(
        self, tmp_path: Path, capsys: pytest.CaptureFixture[str]
    ) -> None:
        create_task("Some feature", "desc", tasks_dir=str(tmp_path))

        exit_code = main(
            ["--tasks-dir", str(tmp_path), "task", "check", "TASK-001", "--criterion", "1"]
        )

        assert exit_code == 1
        err = capsys.readouterr().err
        assert "No acceptance criterion at index 0" in err
