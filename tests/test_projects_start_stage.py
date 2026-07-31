"""Tests for TASK-065: a new `--stage start` sync stage that creates/links a
GitHub Projects item and sets its Status to "In Progress" as soon as
implementation begins (`make branch-task`).

Covers docs/tasks/TASK-065-start-of-implementation-sync.md acceptance
criteria (Gherkin scenarios):
- `--stage start` creates and links a Project item
- `--stage start` reuses an existing linked item instead of creating a duplicate
- `--stage start` sets Status to "In Progress"
- Missing "Status" field or "In Progress" option warns without blocking
"""

from __future__ import annotations

import json
import subprocess
from unittest.mock import MagicMock, patch

from butler_cli.__main__ import main
from butler_core.tasks import create_task


def _completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


_STATUS_FIELD_WITH_IN_PROGRESS = {
    "id": "PVTSSF_status",
    "name": "Status",
    "options": [
        {"id": "opt_todo", "name": "Todo"},
        {"id": "opt_in_progress", "name": "In Progress"},
        {"id": "opt_done", "name": "Done"},
    ],
}


def _make_side_effect(
    *,
    existing_item_id: str = "",
    project_node_id: str = "PVT_node",
    fields: list[dict] | None = None,
):
    """Dispatches on command content: `item-list` returns `existing_item_id`
    (empty string means "no existing item", matching `_item_list_lookup`'s
    real empty-stdout-on-no-match behavior)."""
    fields = fields if fields is not None else [_STATUS_FIELD_WITH_IN_PROGRESS]

    def _side_effect(argv, *args, **kwargs):
        if argv[0] == "gh" and "item-create" in argv:
            return _completed(returncode=0, stdout="")
        if argv[0] == "gh" and "item-list" in argv:
            return _completed(returncode=0, stdout=existing_item_id)
        if argv[0] == "gh" and "view" in argv:
            return _completed(returncode=0, stdout=json.dumps({"id": project_node_id}))
        if argv[0] == "gh" and "field-list" in argv:
            return _completed(returncode=0, stdout=json.dumps({"fields": fields}))
        if argv[0] == "gh" and "item-edit" in argv:
            return _completed(returncode=0, stdout="")
        return _completed(returncode=1, stderr="unexpected call")

    return _side_effect


class TestStartStageCreatesAndLinksProjectItem:
    """Scenario: `--stage start` creates and links a Project item."""

    @patch("butler_core.projects.subprocess.run")
    def test_creates_a_project_item_when_none_exists_yet(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_start

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))
        mock_run.side_effect = _make_side_effect()

        result = sync_on_pr_start(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is True
        assert any("item-create" in call.args[0] for call in mock_run.call_args_list)

    @patch("butler_core.projects.subprocess.run")
    def test_cli_stage_start_creates_project_item_and_exits_zero(
        self, mock_run: MagicMock, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.setenv("BUTLER_GITHUB_PROJECT", "5")
        task = create_task("Some feature", "desc", tasks_dir=str(tmp_path))
        mock_run.side_effect = _make_side_effect()

        exit_code = main(
            [
                "--tasks-dir",
                str(tmp_path),
                "task",
                "sync-project",
                task.id,
                "--stage",
                "start",
            ]
        )

        assert exit_code == 0
        assert any("item-create" in call.args[0] for call in mock_run.call_args_list)


class TestStartStageReusesExistingItem:
    """Scenario: `--stage start` reuses an existing linked item instead of
    creating a duplicate."""

    @patch("butler_core.projects.subprocess.run")
    def test_does_not_invoke_item_create_when_an_item_already_exists(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_start

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))
        mock_run.side_effect = _make_side_effect(existing_item_id="PVTI_existing")

        result = sync_on_pr_start(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is True
        assert not any("item-create" in call.args[0] for call in mock_run.call_args_list)


class TestStartStageSetsStatusToInProgress:
    """Scenario: `--stage start` sets Status to "In Progress"."""

    @patch("butler_core.projects.subprocess.run")
    def test_item_edit_sets_status_field_to_in_progress_option(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_start

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))
        mock_run.side_effect = _make_side_effect(existing_item_id="PVTI_existing")

        result = sync_on_pr_start(
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
        assert argv[argv.index("--id") + 1] == "PVTI_existing"
        assert argv[argv.index("--field-id") + 1] == "PVTSSF_status"
        assert argv[argv.index("--single-select-option-id") + 1] == "opt_in_progress"

    @patch("butler_core.projects.subprocess.run")
    def test_success_message_reports_in_progress(self, mock_run: MagicMock, tmp_path) -> None:
        from butler_core.projects import sync_on_pr_start

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))
        mock_run.side_effect = _make_side_effect(existing_item_id="PVTI_existing")

        result = sync_on_pr_start(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert "In Progress" in result.message
        assert task.id in result.message


class TestStartStageMissingStatusFieldWarnsWithoutBlocking:
    """Scenario: Missing "Status" field or "In Progress" option warns
    without blocking."""

    @patch("butler_core.projects.subprocess.run")
    def test_missing_in_progress_option_returns_warning_without_raising(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_start

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))
        fields = [
            {
                "id": "PVTSSF_status",
                "name": "Status",
                "options": [{"id": "opt_todo", "name": "Todo"}],
            }
        ]
        mock_run.side_effect = _make_side_effect(existing_item_id="PVTI_existing", fields=fields)

        result = sync_on_pr_start(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is False
        assert "Warning" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_missing_status_field_entirely_returns_warning_without_raising(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_start

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))
        mock_run.side_effect = _make_side_effect(existing_item_id="PVTI_existing", fields=[])

        result = sync_on_pr_start(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is False
        assert "Warning" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_no_project_configured_returns_warning(self, mock_run: MagicMock, tmp_path) -> None:
        from butler_core.projects import sync_on_pr_start

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))

        result = sync_on_pr_start(task, env={}, tasks_dir=str(tasks_dir))

        assert result.success is False
        assert "Warning" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_item_create_failure_is_returned_as_is(self, mock_run: MagicMock, tmp_path) -> None:
        from butler_core.projects import sync_on_pr_start

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))

        def _side_effect(argv, *args, **kwargs):
            if "item-list" in argv:
                return _completed(returncode=0, stdout="")
            if "item-create" in argv:
                return _completed(returncode=1, stderr="permission denied")
            return _completed(returncode=1, stderr="unexpected call")

        mock_run.side_effect = _side_effect

        result = sync_on_pr_start(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is False
        assert "Warning" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_gh_not_found_during_status_update_returns_warning(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_start

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))

        def _side_effect(argv, *args, **kwargs):
            if "item-create" in argv:
                return _completed(returncode=0, stdout="")
            raise FileNotFoundError("gh")

        mock_run.side_effect = _side_effect

        result = sync_on_pr_start(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is False
        assert "not found" in result.message.lower()

    @patch("butler_core.projects.subprocess.run")
    def test_called_process_error_during_status_update_returns_warning(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_start

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))

        def _side_effect(argv, *args, **kwargs):
            if "item-create" in argv:
                return _completed(returncode=0, stdout="")
            raise subprocess.CalledProcessError(1, argv, stderr="permission denied")

        mock_run.side_effect = _side_effect

        result = sync_on_pr_start(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is False
        assert "Warning" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_unexpected_os_error_during_status_update_returns_warning(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_start

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))

        def _side_effect(argv, *args, **kwargs):
            if "item-create" in argv:
                return _completed(returncode=0, stdout="")
            raise PermissionError("denied")

        mock_run.side_effect = _side_effect

        result = sync_on_pr_start(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is False
        assert "Warning" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_status_item_edit_failure_returns_warning(self, mock_run: MagicMock, tmp_path) -> None:
        from butler_core.projects import sync_on_pr_start

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))

        def _side_effect(argv, *args, **kwargs):
            if argv[0] == "gh" and "item-create" in argv:
                return _completed(returncode=0, stdout="")
            if argv[0] == "gh" and "item-list" in argv:
                return _completed(returncode=0, stdout="PVTI_item1")
            if argv[0] == "gh" and "view" in argv:
                return _completed(returncode=0, stdout=json.dumps({"id": "PVT_node"}))
            if argv[0] == "gh" and "field-list" in argv:
                return _completed(
                    returncode=0,
                    stdout=json.dumps({"fields": [_STATUS_FIELD_WITH_IN_PROGRESS]}),
                )
            if argv[0] == "gh" and "item-edit" in argv:
                return _completed(returncode=1, stderr="permission denied")
            return _completed(returncode=1, stderr="unexpected call")

        mock_run.side_effect = _side_effect

        result = sync_on_pr_start(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is False
        assert "Warning" in result.message


class TestStartStageIsAValidCliChoice:
    """Additional CLI-level coverage: `--stage start` is a valid argparse
    choice end-to-end."""

    @patch("butler_core.projects.subprocess.run")
    def test_start_is_accepted_by_argparse_and_dispatches_to_sync_on_pr_start(
        self, mock_run: MagicMock, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.setenv("BUTLER_GITHUB_PROJECT", "5")
        task = create_task("Some feature", "desc", tasks_dir=str(tmp_path))
        mock_run.side_effect = _make_side_effect()

        exit_code = main(
            [
                "--tasks-dir",
                str(tmp_path),
                "task",
                "sync-project",
                task.id,
                "--stage",
                "start",
            ]
        )

        assert exit_code == 0
