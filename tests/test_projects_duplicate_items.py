"""Tests for TASK-063: GitHub Projects sync must link to an existing Project
item instead of creating a duplicate when more than one sync stage runs for
the same task, and must handle a multi-line/multi-match `item-list` lookup
safely instead of concatenating IDs into a single malformed `--id` value.

Covers docs/tasks/TASK-063-projects-sync-creates-duplicate-items.md
acceptance criteria (Gherkin scenarios):
- Characterization test: today's (fixed) behavior reuses an existing item
  instead of creating a second one
- Bug fixed: a second sync stage for the same task does not create a new
  item, and multi-match lookups are handled safely (first match used, not
  concatenated)
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from butler_core.projects import sync_on_pr_merge, sync_on_pr_open
from butler_core.tasks import create_task


def _completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


class TestSecondSyncStageReusesExistingItem:
    """Scenario: a second sync stage (e.g. `--stage open` after `--stage
    draft`) for the same task must reuse the item already linked to it
    instead of creating a second one.

    This also documents (characterizes) the fix: before TASK-063,
    `_create_item` never consulted `item-list` at all, so `gh project
    item-create` ran unconditionally on every call and running `draft` then
    `open` for the same task produced two Project items.
    """

    @patch("butler_core.projects.subprocess.run")
    def test_does_not_invoke_item_create_when_an_item_already_exists(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        task = create_task(
            "Backfill sync for historical tasks", "desc", tasks_dir=str(tmp_path / "docs" / "tasks")
        )
        mock_run.return_value = _completed(returncode=0, stdout="PVTI_existing")

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is True
        assert not any("item-create" in call.args[0] for call in mock_run.call_args_list)

    @patch("butler_core.projects.subprocess.run")
    def test_invokes_item_list_lookup_before_deciding_whether_to_create(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.return_value = _completed(returncode=0, stdout="")

        sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert any("item-list" in call.args[0] for call in mock_run.call_args_list)
        assert any("item-create" in call.args[0] for call in mock_run.call_args_list)

    @patch("butler_core.projects.subprocess.run")
    def test_success_message_still_includes_task_id_and_title_when_reused(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.return_value = _completed(returncode=0, stdout="PVTI_existing")

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert task.id in result.message
        assert task.title in result.message


class TestCreateItemFailsAfterLookupFindsNoExistingItem:
    """Coverage for `_create_item`'s own exception handling around the
    `item-create` call, reached only when the preceding `item-list` lookup
    found no existing item (empty stdout) and creation is actually
    attempted."""

    @patch("butler_core.projects.subprocess.run")
    def test_gh_not_found_during_item_create_returns_warning(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))

        def _side_effect(argv, *args, **kwargs):
            if "item-list" in argv:
                return _completed(returncode=0, stdout="")
            raise FileNotFoundError("gh")

        mock_run.side_effect = _side_effect

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is False
        assert "not found" in result.message.lower()

    @patch("butler_core.projects.subprocess.run")
    def test_called_process_error_during_item_create_returns_warning(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        import subprocess

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))

        def _side_effect(argv, *args, **kwargs):
            if "item-list" in argv:
                return _completed(returncode=0, stdout="")
            raise subprocess.CalledProcessError(1, argv, stderr="permission denied")

        mock_run.side_effect = _side_effect

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is False
        assert "permission denied" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_unexpected_os_error_during_item_create_returns_warning(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))

        def _side_effect(argv, *args, **kwargs):
            if "item-list" in argv:
                return _completed(returncode=0, stdout="")
            raise PermissionError("denied")

        mock_run.side_effect = _side_effect

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is False
        assert "denied" in result.message


class TestMultiMatchLookupHandledSafely:
    """Scenario: `_item_list_lookup`'s callers must not assume exactly one
    line of output -- a multi-line/multi-match result (e.g. a stale
    duplicate from before this fix) must not be concatenated into a single
    malformed `--id` value."""

    @patch("butler_core.projects.subprocess.run")
    def test_create_item_uses_first_match_and_does_not_concatenate_ids(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.return_value = _completed(returncode=0, stdout="PVTI_first\nPVTI_second")

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is True
        assert not any("item-create" in call.args[0] for call in mock_run.call_args_list)

    @patch("butler_core.projects.subprocess.run")
    def test_status_update_uses_first_match_id_not_the_concatenated_stdout(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        import json

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))

        def _side_effect(argv, *args, **kwargs):
            if "item-list" in argv:
                return _completed(returncode=0, stdout="PVTI_first\nPVTI_second")
            if "view" in argv:
                return _completed(returncode=0, stdout=json.dumps({"id": "PVT_node"}))
            if "field-list" in argv:
                return _completed(
                    returncode=0,
                    stdout=json.dumps(
                        {
                            "fields": [
                                {
                                    "id": "PVTSSF_status",
                                    "name": "Status",
                                    "options": [{"id": "opt_done", "name": "Done"}],
                                }
                            ]
                        }
                    ),
                )
            if "item-edit" in argv:
                return _completed(returncode=0, stdout="")
            return _completed(returncode=1, stderr="unexpected call")

        mock_run.side_effect = _side_effect

        result = sync_on_pr_merge(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is True
        item_edit_call = next(
            call for call in mock_run.call_args_list if "item-edit" in call.args[0]
        )
        argv = item_edit_call.args[0]
        assert argv[argv.index("--id") + 1] == "PVTI_first"
