"""Tests for TASK-062: a new `--stage backfill` sync stage that backfills a
historical task's GitHub Projects item with its real Status, Created date,
and Closed date, instead of today's date and a default status.

Covers docs/tasks/TASK-062-backfill-sync-for-historical-tasks.md acceptance
criteria (Gherkin scenarios):
- Create and link a Project item with backfill
- Set Status to match the task file's Status value (case-insensitive, hyphen to space)
- Set Created date to the task file's first commit date
- Set Closed date to Completion date when Status is done and Completion date is present/parseable
- Fall back to most recent commit date for Closed when Completion date is absent/unparseable
- Leave Closed field unset when task Status is not done
- Silently skip missing Created date field without warning
- Silently skip missing Closed date field without warning
"""

from __future__ import annotations

import json
import re
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from butler_cli.__main__ import main
from butler_core.tasks import create_task, read_task


def _completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def _set_status_and_completion_date(
    tasks_dir: Path, task_id: str, status: str, completion_date: str | None = None
) -> None:
    path = next(Path(tasks_dir).glob(f"{task_id}*.md"))
    text = path.read_text()
    text = re.sub(r"(^## Status\s*\n+)(\S+)", rf"\g<1>{status}", text, flags=re.MULTILINE)
    if completion_date is not None:
        text = re.sub(
            r"(^\*\*Date:\*\*)(.*)$", rf"\g<1> {completion_date}", text, flags=re.MULTILINE
        )
    path.write_text(text)


def _make_side_effect(
    *,
    item_id: str = "PVTI_item1",
    project_node_id: str = "PVT_node",
    fields: list[dict] | None = None,
    first_commit_lines: list[str] | None = None,
    latest_commit_lines: list[str] | None = None,
):
    """Dispatches on command content rather than call order, so the test
    stays robust if the implementation's call order changes: `git log`
    invocations are told apart by `--diff-filter=A` (first-commit lookup)
    vs. the plain `-1` (most-recent-commit lookup); `gh` invocations are
    told apart by their subcommand keyword.
    """
    fields = fields if fields is not None else []
    first_commit_lines = first_commit_lines or []
    latest_commit_lines = latest_commit_lines or []

    def _side_effect(argv, *args, **kwargs):
        if argv[0] == "git":
            if "--diff-filter=A" in argv:
                return _completed(returncode=0, stdout="\n".join(first_commit_lines))
            return _completed(returncode=0, stdout="\n".join(latest_commit_lines))
        if "item-create" in argv:
            return _completed(returncode=0, stdout="")
        if "item-list" in argv:
            return _completed(returncode=0, stdout=item_id)
        if "view" in argv:
            return _completed(returncode=0, stdout=json.dumps({"id": project_node_id}))
        if "field-list" in argv:
            return _completed(returncode=0, stdout=json.dumps({"fields": fields}))
        if "item-edit" in argv:
            return _completed(returncode=0, stdout="")
        return _completed(returncode=1, stderr="unexpected call")

    return _side_effect


_STATUS_FIELD = {
    "id": "PVTSSF_status",
    "name": "Status",
    "options": [
        {"id": "opt_todo", "name": "Todo"},
        {"id": "opt_in_progress", "name": "In Progress"},
        {"id": "opt_done", "name": "Done"},
    ],
}


def _item_edit_calls_for_field(mock_run: MagicMock, field_id: str) -> list:
    calls = []
    for call in mock_run.call_args_list:
        argv = call.args[0]
        if argv[0] == "gh" and "item-edit" in argv and "--field-id" in argv:
            if argv[argv.index("--field-id") + 1] == field_id:
                calls.append(call)
    return calls


class TestBackfillCreatesAndLinksProjectItem:
    """Scenario: Create and link a Project item with backfill."""

    @patch("butler_core.projects.subprocess.run")
    def test_cli_stage_backfill_creates_project_item_and_exits_zero(
        self, mock_run: MagicMock, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.setenv("BUTLER_GITHUB_PROJECT", "5")
        task = create_task("Historical feature", "desc", tasks_dir=str(tmp_path))
        mock_run.side_effect = _make_side_effect()

        exit_code = main(
            [
                "--tasks-dir",
                str(tmp_path),
                "task",
                "sync-project",
                task.id,
                "--stage",
                "backfill",
            ]
        )

        assert exit_code == 0
        assert any(
            call.args[0][0] == "gh" and "item-create" in call.args[0]
            for call in mock_run.call_args_list
        )

    @patch("butler_core.projects.subprocess.run")
    def test_sync_on_pr_backfill_returns_success_when_item_created(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_backfill

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Historical feature", "desc", tasks_dir=str(tasks_dir))
        mock_run.side_effect = _make_side_effect(fields=[_STATUS_FIELD])

        result = sync_on_pr_backfill(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is True
        assert task.id in result.message


class TestBackfillSetsStatusCaseInsensitiveHyphenToSpace:
    """Scenario: Set Status to match the task file's Status value
    (case-insensitive, hyphen to space)."""

    @patch("butler_core.projects.subprocess.run")
    def test_status_option_matched_case_insensitively_with_hyphen_as_space(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_backfill

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Historical feature", "desc", tasks_dir=str(tasks_dir))
        _set_status_and_completion_date(tasks_dir, task.id, "in-progress")
        task = read_task(task.id, tasks_dir=str(tasks_dir))

        fields = [
            {
                "id": "PVTSSF_status",
                "name": "Status",
                "options": [
                    {"id": "opt_todo", "name": "Todo"},
                    {"id": "opt_in_progress", "name": "In Progress"},
                    {"id": "opt_done", "name": "Done"},
                ],
            }
        ]
        mock_run.side_effect = _make_side_effect(fields=fields)

        result = sync_on_pr_backfill(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is True
        status_edit_call = next(
            call
            for call in mock_run.call_args_list
            if call.args[0][0] == "gh"
            and "item-edit" in call.args[0]
            and "--single-select-option-id" in call.args[0]
        )
        argv = status_edit_call.args[0]
        assert argv[argv.index("--field-id") + 1] == "PVTSSF_status"
        assert argv[argv.index("--single-select-option-id") + 1] == "opt_in_progress"


class TestBackfillSetsCreatedDateToFirstCommitDate:
    """Scenario: Set Created date to the task file's first commit date."""

    @patch("butler_core.projects.subprocess.run")
    def test_created_date_field_uses_earliest_commit_date(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_backfill

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Historical feature", "desc", tasks_dir=str(tasks_dir))

        fields = [_STATUS_FIELD, {"id": "PVTF_created", "name": "Created"}]
        mock_run.side_effect = _make_side_effect(
            fields=fields,
            first_commit_lines=[
                "2026-03-05T12:00:00+00:00",
                "2026-03-02T09:00:00+00:00",
            ],
        )

        result = sync_on_pr_backfill(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is True
        created_calls = _item_edit_calls_for_field(mock_run, "PVTF_created")
        assert len(created_calls) == 1
        argv = created_calls[0].args[0]
        assert argv[argv.index("--date") + 1] == "2026-03-02"


class TestBackfillSetsClosedDateToCompletionDate:
    """Scenario: Set Closed date to Completion date when Status is done and
    Completion date is present/parseable."""

    @patch("butler_core.projects.subprocess.run")
    def test_closed_date_uses_completion_date_when_parseable(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_backfill

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Historical feature", "desc", tasks_dir=str(tasks_dir))
        _set_status_and_completion_date(tasks_dir, task.id, "done", completion_date="2026-03-05")
        task = read_task(task.id, tasks_dir=str(tasks_dir))

        fields = [_STATUS_FIELD, {"id": "PVTF_closed", "name": "Closed"}]
        mock_run.side_effect = _make_side_effect(
            fields=fields, latest_commit_lines=["2026-09-01T00:00:00+00:00"]
        )

        result = sync_on_pr_backfill(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is True
        closed_calls = _item_edit_calls_for_field(mock_run, "PVTF_closed")
        assert len(closed_calls) == 1
        argv = closed_calls[0].args[0]
        assert argv[argv.index("--date") + 1] == "2026-03-05"


class TestBackfillFallsBackToMostRecentCommitForClosedDate:
    """Scenario: Fall back to most recent commit date for Closed when
    Completion date is absent/unparseable and Status is done."""

    @patch("butler_core.projects.subprocess.run")
    def test_falls_back_to_latest_commit_when_completion_date_missing(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_backfill

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Historical feature", "desc", tasks_dir=str(tasks_dir))
        _set_status_and_completion_date(tasks_dir, task.id, "done")
        task = read_task(task.id, tasks_dir=str(tasks_dir))
        assert task.completion is None

        fields = [_STATUS_FIELD, {"id": "PVTF_closed", "name": "Closed"}]
        mock_run.side_effect = _make_side_effect(
            fields=fields, latest_commit_lines=["2026-04-09T00:00:00+00:00"]
        )

        result = sync_on_pr_backfill(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is True
        closed_calls = _item_edit_calls_for_field(mock_run, "PVTF_closed")
        assert len(closed_calls) == 1
        argv = closed_calls[0].args[0]
        assert argv[argv.index("--date") + 1] == "2026-04-09"

    @patch("butler_core.projects.subprocess.run")
    def test_falls_back_to_latest_commit_when_completion_date_unparseable(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_backfill

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Historical feature", "desc", tasks_dir=str(tasks_dir))
        _set_status_and_completion_date(tasks_dir, task.id, "done", completion_date="not-a-date")
        task = read_task(task.id, tasks_dir=str(tasks_dir))
        assert task.completion is not None
        assert task.completion.date == "not-a-date"

        fields = [_STATUS_FIELD, {"id": "PVTF_closed", "name": "Closed"}]
        mock_run.side_effect = _make_side_effect(
            fields=fields, latest_commit_lines=["2026-05-11T00:00:00+00:00"]
        )

        result = sync_on_pr_backfill(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is True
        closed_calls = _item_edit_calls_for_field(mock_run, "PVTF_closed")
        assert len(closed_calls) == 1
        argv = closed_calls[0].args[0]
        assert argv[argv.index("--date") + 1] == "2026-05-11"


class TestBackfillLeavesClosedFieldUnsetWhenNotDone:
    """Scenario: Leave Closed field unset when task Status is not done."""

    @patch("butler_core.projects.subprocess.run")
    def test_closed_field_never_touched_when_status_not_done(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_backfill

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Historical feature", "desc", tasks_dir=str(tasks_dir))
        _set_status_and_completion_date(tasks_dir, task.id, "todo")
        task = read_task(task.id, tasks_dir=str(tasks_dir))

        fields = [_STATUS_FIELD, {"id": "PVTF_closed", "name": "Closed"}]
        mock_run.side_effect = _make_side_effect(
            fields=fields, latest_commit_lines=["2026-04-09T00:00:00+00:00"]
        )

        result = sync_on_pr_backfill(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is True
        assert _item_edit_calls_for_field(mock_run, "PVTF_closed") == []


class TestBackfillSilentlySkipsMissingCreatedField:
    """Scenario: Silently skip missing Created date field without warning."""

    @patch("butler_core.projects.subprocess.run")
    def test_succeeds_without_warning_and_without_created_edit_call(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_backfill

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Historical feature", "desc", tasks_dir=str(tasks_dir))
        mock_run.side_effect = _make_side_effect(fields=[_STATUS_FIELD])

        result = sync_on_pr_backfill(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is True
        assert "Warning" not in result.message
        assert not any(
            call.args[0][0] == "gh" and "item-edit" in call.args[0] and "--date" in call.args[0]
            for call in mock_run.call_args_list
        )


class TestBackfillSilentlySkipsMissingClosedField:
    """Scenario: Silently skip missing Closed date field without warning."""

    @patch("butler_core.projects.subprocess.run")
    def test_succeeds_without_warning_and_without_closed_edit_call(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_backfill

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Historical feature", "desc", tasks_dir=str(tasks_dir))
        _set_status_and_completion_date(tasks_dir, task.id, "done", completion_date="2026-03-05")
        task = read_task(task.id, tasks_dir=str(tasks_dir))
        mock_run.side_effect = _make_side_effect(fields=[_STATUS_FIELD])

        result = sync_on_pr_backfill(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is True
        assert "Warning" not in result.message
        assert not any(
            call.args[0][0] == "gh" and "item-edit" in call.args[0] and "--date" in call.args[0]
            for call in mock_run.call_args_list
        )


class TestBackfillStageIsAValidCliChoice:
    """Additional CLI-level coverage: `--stage backfill` is a valid argparse
    choice end-to-end (does not raise SystemExit from argparse rejecting it)."""

    @patch("butler_core.projects.subprocess.run")
    def test_backfill_is_accepted_by_argparse_and_dispatches_to_sync_on_pr_backfill(
        self, mock_run: MagicMock, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.setenv("BUTLER_GITHUB_PROJECT", "5")
        task = create_task("Historical feature", "desc", tasks_dir=str(tmp_path))
        mock_run.side_effect = _make_side_effect()

        exit_code = main(
            [
                "--tasks-dir",
                str(tmp_path),
                "task",
                "sync-project",
                task.id,
                "--stage",
                "backfill",
            ]
        )

        assert exit_code == 0


class TestBackfillMissingProjectResolutionStillWarns:
    """Requirement 4's best-effort contract still applies when the Project
    itself can't be resolved at all (unrelated to the Created/Closed
    fields, which are opportunistic)."""

    @patch("butler_core.projects.subprocess.run")
    def test_no_project_configured_returns_warning(self, mock_run: MagicMock, tmp_path) -> None:
        from butler_core.projects import sync_on_pr_backfill

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Historical feature", "desc", tasks_dir=str(tasks_dir))

        result = sync_on_pr_backfill(task, env={}, tasks_dir=str(tasks_dir))

        assert result.success is False
        assert "Warning" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_missing_status_option_on_project_returns_warning(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_backfill

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Historical feature", "desc", tasks_dir=str(tasks_dir))
        fields = [
            {"id": "PVTSSF_status", "name": "Status", "options": [{"id": "x", "name": "Todo"}]}
        ]
        # Task status is "todo" by default, but simulate the Project only
        # having options that don't match to exercise the warning path.
        _set_status_and_completion_date(tasks_dir, task.id, "in-progress")
        task = read_task(task.id, tasks_dir=str(tasks_dir))
        mock_run.side_effect = _make_side_effect(fields=fields)

        result = sync_on_pr_backfill(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is False
        assert "Warning" in result.message


class TestTaskFilePathHelper:
    """Unit coverage for `_task_file_path`'s "no date available" fallback
    paths, which backfill relies on to silently skip Created/Closed without
    warning rather than raising."""

    def test_returns_none_when_tasks_dir_is_none(self, tmp_path) -> None:
        from butler_core.projects import _task_file_path
        from butler_core.tasks import Task

        task = Task(
            id="TASK-999",
            title="Untracked",
            status="todo",
            description="",
            branch_name="",
            switch_create_cmd="",
            stage_cmd="",
            commit_message="",
            acceptance_criteria=[],
        )

        assert _task_file_path(task, None) is None

    def test_returns_none_when_no_file_matches(self, tmp_path) -> None:
        from butler_core.projects import _task_file_path
        from butler_core.tasks import Task

        task = Task(
            id="TASK-999",
            title="Untracked",
            status="todo",
            description="",
            branch_name="",
            switch_create_cmd="",
            stage_cmd="",
            commit_message="",
            acceptance_criteria=[],
        )

        assert _task_file_path(task, str(tmp_path)) is None


class TestGitLogDatesHelper:
    """Unit coverage for `_git_log_dates`'s failure paths: any git
    invocation failure is treated as "no date available", never raised."""

    @patch("butler_core.projects.subprocess.run")
    def test_returns_empty_list_when_git_raises_oserror(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import _git_log_dates

        mock_run.side_effect = FileNotFoundError("git")

        assert _git_log_dates(tmp_path, tmp_path / "file.md", ["-1"]) == []

    @patch("butler_core.projects.subprocess.run")
    def test_returns_empty_list_when_git_exits_non_zero(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import _git_log_dates

        mock_run.return_value = _completed(returncode=128, stderr="not a git repository")

        assert _git_log_dates(tmp_path, tmp_path / "file.md", ["-1"]) == []


class TestClosedDateHelper:
    """Unit coverage for `_closed_date`'s fallback when no repo/file is
    available at all (backfill invoked with no `tasks_dir` or no matching
    task file), which must return None rather than raise."""

    def test_returns_none_when_no_repo_root_or_file_path(self) -> None:
        from butler_core.projects import _closed_date
        from butler_core.tasks import Completion, Task

        task = Task(
            id="TASK-999",
            title="Untracked",
            status="done",
            description="",
            branch_name="",
            switch_create_cmd="",
            stage_cmd="",
            commit_message="",
            acceptance_criteria=[],
            completion=Completion(date=""),
        )

        assert _closed_date(task, None, None) is None


class TestBackfillPropagatesFailuresFromEachStep:
    """Coverage for backfill's own error/warning paths beyond the
    Created/Closed opportunistic fields: item-create failure, item-list
    failure, the status item-edit call itself failing, and unexpected `gh`
    exceptions raised partway through."""

    @patch("butler_core.projects.subprocess.run")
    def test_item_create_failure_is_returned_as_is(self, mock_run: MagicMock, tmp_path) -> None:
        from butler_core.projects import sync_on_pr_backfill

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Historical feature", "desc", tasks_dir=str(tasks_dir))

        def _side_effect(argv, *args, **kwargs):
            if argv[0] == "gh" and "item-create" in argv:
                return _completed(returncode=1, stderr="permission denied")
            return _completed(returncode=1, stderr="unexpected call")

        mock_run.side_effect = _side_effect

        result = sync_on_pr_backfill(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is False
        assert "Warning" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_item_list_failure_returns_warning(self, mock_run: MagicMock, tmp_path) -> None:
        from butler_core.projects import sync_on_pr_backfill

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Historical feature", "desc", tasks_dir=str(tasks_dir))

        def _side_effect(argv, *args, **kwargs):
            if argv[0] == "gh" and "item-create" in argv:
                return _completed(returncode=0, stdout="")
            if argv[0] == "gh" and "item-list" in argv:
                return _completed(returncode=1, stderr="permission denied")
            return _completed(returncode=1, stderr="unexpected call")

        mock_run.side_effect = _side_effect

        result = sync_on_pr_backfill(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is False
        assert "Warning" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_status_item_edit_failure_returns_warning(self, mock_run: MagicMock, tmp_path) -> None:
        from butler_core.projects import sync_on_pr_backfill

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Historical feature", "desc", tasks_dir=str(tasks_dir))

        def _side_effect(argv, *args, **kwargs):
            if argv[0] == "gh" and "item-create" in argv:
                return _completed(returncode=0, stdout="")
            if argv[0] == "gh" and "item-list" in argv:
                return _completed(returncode=0, stdout="PVTI_item1")
            if argv[0] == "gh" and "view" in argv:
                return _completed(returncode=0, stdout=json.dumps({"id": "PVT_node"}))
            if argv[0] == "gh" and "field-list" in argv:
                return _completed(returncode=0, stdout=json.dumps({"fields": [_STATUS_FIELD]}))
            if argv[0] == "gh" and "item-edit" in argv:
                return _completed(returncode=1, stderr="permission denied")
            return _completed(returncode=1, stderr="unexpected call")

        mock_run.side_effect = _side_effect

        result = sync_on_pr_backfill(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is False
        assert "Warning" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_gh_not_found_partway_through_backfill_returns_warning(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_backfill

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Historical feature", "desc", tasks_dir=str(tasks_dir))

        def _side_effect(argv, *args, **kwargs):
            if argv[0] == "gh" and "item-create" in argv:
                return _completed(returncode=0, stdout="")
            raise FileNotFoundError("gh")

        mock_run.side_effect = _side_effect

        result = sync_on_pr_backfill(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is False
        assert "not found" in result.message.lower()

    @patch("butler_core.projects.subprocess.run")
    def test_called_process_error_partway_through_backfill_returns_warning(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_backfill

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Historical feature", "desc", tasks_dir=str(tasks_dir))

        def _side_effect(argv, *args, **kwargs):
            if argv[0] == "gh" and "item-create" in argv:
                return _completed(returncode=0, stdout="")
            raise subprocess.CalledProcessError(1, argv, stderr="permission denied")

        mock_run.side_effect = _side_effect

        result = sync_on_pr_backfill(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is False
        assert "Warning" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_unexpected_os_error_partway_through_backfill_returns_warning(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_backfill

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Historical feature", "desc", tasks_dir=str(tasks_dir))

        def _side_effect(argv, *args, **kwargs):
            if argv[0] == "gh" and "item-create" in argv:
                return _completed(returncode=0, stdout="")
            raise PermissionError("denied")

        mock_run.side_effect = _side_effect

        result = sync_on_pr_backfill(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is False
        assert "Warning" in result.message
