"""TASK-099: binds TASK-099-draft-open-sync-message-status.feature.

`gh` is faked at `butler_core.projects.subprocess.run`, dispatching on the
subcommand the same way tests/test_projects_start_stage.py does.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from butler_core.projects import sync_on_pr_draft, sync_on_pr_open, sync_on_pr_start
from butler_core.tasks import create_task

scenarios("../features/TASK-099-draft-open-sync-message-status.feature")

_ENV = {"BUTLER_GITHUB_PROJECT": "5"}
_STATUS_FIELD = {
    "id": "PVTSSF_status",
    "name": "Status",
    "options": [
        {"id": "opt_todo", "name": "Todo"},
        {"id": "opt_in_progress", "name": "In Progress"},
    ],
}


def _completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def _gh_side_effect(item_list_stdout: str):
    def _side_effect(argv, *args, **kwargs):
        if argv[0] == "gh" and "item-list" in argv:
            return _completed(stdout=item_list_stdout)
        if argv[0] == "gh" and "view" in argv:
            return _completed(stdout=json.dumps({"id": "PVT_node"}))
        if argv[0] == "gh" and "field-list" in argv:
            return _completed(stdout=json.dumps({"fields": [_STATUS_FIELD]}))
        if argv[0] == "gh" and ("item-create" in argv or "item-edit" in argv):
            return _completed()
        return _completed(returncode=1, stderr="unexpected call")

    return _side_effect


@pytest.fixture
def ctx(tmp_path):
    repo_root = tmp_path
    (repo_root / ".git").mkdir()
    tasks_dir = repo_root / "docs" / "tasks"
    task = create_task("Some feature", "desc", tasks_dir=str(tasks_dir))
    return {"task": task, "tasks_dir": str(tasks_dir), "item_list": ""}


@pytest.fixture
def mock_run():
    with patch("butler_core.projects.subprocess.run") as mocked:
        yield mocked


def _run_sync(ctx, mock_run, sync) -> None:
    mock_run.side_effect = _gh_side_effect(ctx["item_list"])
    ctx["result"] = sync(ctx["task"], env=_ENV, tasks_dir=ctx["tasks_dir"])
    assert ctx["result"].success, ctx["result"].message


@given("a task with no linked Project item")
def _no_linked_item(ctx):
    ctx["item_list"] = ""


@given("a task whose Project item already exists")
@given("a task with a linked Project item")
@given('a task with a Project item whose Status field has an "In Progress" option')
def _linked_item(ctx):
    ctx["item_list"] = "PVTI_existing"


@given(
    "the Project number resolves via $BUTLER_GITHUB_PROJECT and duplicate items exist for the task"
)
def _env_fallback_and_duplicates(ctx):
    ctx["item_list"] = "PVTI_first\nPVTI_second"


@when("the draft sync creates the Project item")
def _draft_creates(ctx, mock_run):
    _run_sync(ctx, mock_run, sync_on_pr_draft)
    assert any("item-create" in call.args[0] for call in mock_run.call_args_list)


@when("the draft sync links the existing item")
def _draft_links(ctx, mock_run):
    _run_sync(ctx, mock_run, sync_on_pr_draft)
    assert not any("item-create" in call.args[0] for call in mock_run.call_args_list)


@when("the draft sync succeeds")
def _draft_succeeds(ctx, mock_run):
    _run_sync(ctx, mock_run, sync_on_pr_draft)


@when("the open sync runs")
def _open_runs(ctx, mock_run):
    _run_sync(ctx, mock_run, sync_on_pr_open)


@when("the start sync runs")
def _start_runs(ctx, mock_run):
    _run_sync(ctx, mock_run, sync_on_pr_start)


@then("the success message names the task id and title")
def _names_id_and_title(ctx):
    task = ctx["task"]
    assert f"Synced {task.id} {task.title} to GitHub Project item" in ctx["result"].message


@then(parsers.parse('the message does not contain "{text}"'))
@then(parsers.parse('the success message does not contain "{text}"'))
def _message_lacks(ctx, text):
    assert text not in ctx["result"].message


@then(parsers.parse('the success message contains "{text}"'))
def _message_contains(ctx, text):
    assert text in ctx["result"].message


@then(parsers.parse('the item\'s Status is set to "{status}"'))
def _status_set(mock_run, status):
    option_id = next(o["id"] for o in _STATUS_FIELD["options"] if o["name"] == status)
    edit = next(call.args[0] for call in mock_run.call_args_list if "item-edit" in call.args[0])
    assert edit[edit.index("--single-select-option-id") + 1] == option_id


@then("the Requirement 17 note and the duplicate-item warning are still appended to the message")
def _notes_appended(ctx):
    lines = ctx["result"].message.splitlines()
    assert "status:" not in lines[0]
    assert any(line.startswith("Warning: multiple existing GitHub Project items") for line in lines)
    assert any("via $BUTLER_GITHUB_PROJECT" in line for line in lines)
