"""TASK-101: binds TASK-101-status-sync-resolved-item-id.feature.

`gh` is faked at `butler_core.projects.subprocess.run`, dispatching on the
subcommand the same way tests/bdd/steps/test_task_099_steps.py does. A newly
created item is never listed by `item-list` (matching GitHub's real lag), so
the only way a start sync can reach it is via `item-create`'s own output.
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, parsers, scenarios, then, when

from butler_core.projects import sync_on_pr_merge, sync_on_pr_start
from butler_core.tasks import create_task

scenarios("../features/TASK-101-status-sync-resolved-item-id.feature")

_ENV = {"BUTLER_GITHUB_PROJECT": "5"}
_CREATED_ITEM_ID = "PVTI_created"
_EXISTING_ITEM_ID = "PVTI_existing"
_STATUS_FIELD = {
    "id": "PVTSSF_status",
    "name": "Status",
    "options": [
        {"id": "opt_todo", "name": "Todo"},
        {"id": "opt_in_progress", "name": "In Progress"},
        {"id": "opt_done", "name": "Done"},
    ],
}


def _completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def _gh_side_effect(ctx):
    def _side_effect(argv, *args, **kwargs):
        if argv[0] == "gh" and "item-list" in argv:
            return _completed(stdout=ctx["item_list"])
        if argv[0] == "gh" and "item-create" in argv:
            return ctx["item_create"]
        if argv[0] == "gh" and "view" in argv:
            return _completed(stdout=json.dumps({"id": "PVT_node"}))
        if argv[0] == "gh" and "field-list" in argv:
            return _completed(stdout=json.dumps({"fields": [_STATUS_FIELD]}))
        if argv[0] == "gh" and "item-edit" in argv:
            return _completed()
        return _completed(returncode=1, stderr="unexpected call")

    return _side_effect


@pytest.fixture
def ctx(tmp_path):
    repo_root = tmp_path
    (repo_root / ".git").mkdir()
    tasks_dir = repo_root / "docs" / "tasks"
    task = create_task("Some feature", "desc", tasks_dir=str(tasks_dir))
    return {
        "task": task,
        "tasks_dir": str(tasks_dir),
        "item_list": "",
        "item_create": _completed(stdout=json.dumps({"id": _CREATED_ITEM_ID})),
    }


@pytest.fixture
def mock_run():
    with patch("butler_core.projects.subprocess.run") as mocked:
        yield mocked


def _gh_calls(mock_run, subcommand: str) -> list[list[str]]:
    return [call.args[0] for call in mock_run.call_args_list if subcommand in call.args[0]]


def _edited_item_ids(mock_run) -> list[str]:
    return [argv[argv.index("--id") + 1] for argv in _gh_calls(mock_run, "item-edit")]


def _assert_status_set(mock_run, item_id: str, status: str) -> None:
    option_id = next(o["id"] for o in _STATUS_FIELD["options"] if o["name"] == status)
    edits = [
        argv for argv in _gh_calls(mock_run, "item-edit") if "--single-select-option-id" in argv
    ]
    assert any(
        argv[argv.index("--id") + 1] == item_id
        and argv[argv.index("--single-select-option-id") + 1] == option_id
        for argv in edits
    ), edits


def _run_sync(ctx, mock_run, sync) -> None:
    mock_run.side_effect = _gh_side_effect(ctx)
    ctx["result"] = sync(ctx["task"], env=_ENV, tasks_dir=ctx["tasks_dir"])


@given("a task with no linked Project item")
def _no_linked_item(ctx):
    ctx["item_list"] = ""


@given("a task with a linked Project item")
def _linked_item(ctx):
    ctx["item_list"] = _EXISTING_ITEM_ID


@given(parsers.parse('the Project\'s Status field has an "{option}" option'))
@given(parsers.parse('the Project\'s Status field has a "{option}" option'))
def _status_option_exists(option):
    assert any(o["name"] == option for o in _STATUS_FIELD["options"])


@given("creating the Project item fails")
def _create_fails(ctx):
    ctx["item_create"] = _completed(returncode=1, stderr="HTTP 502")


@given("creating the Project item returns no item ID")
def _create_returns_no_id(ctx):
    ctx["item_create"] = _completed(stdout=json.dumps({"title": "no id here"}))


@when("the start sync runs")
def _start_runs(ctx, mock_run):
    _run_sync(ctx, mock_run, sync_on_pr_start)


@when("the merge sync runs")
def _merge_runs(ctx, mock_run):
    _run_sync(ctx, mock_run, sync_on_pr_merge)


@then(parsers.parse('the Project item created for the task has Status "{status}"'))
def _created_item_has_status(ctx, mock_run, status):
    assert ctx["result"].success, ctx["result"].message
    assert _gh_calls(mock_run, "item-create")
    _assert_status_set(mock_run, _CREATED_ITEM_ID, status)


@then("the created item is not looked up a second time")
def _no_second_lookup(mock_run):
    assert len(_gh_calls(mock_run, "item-list")) == 1


@then(parsers.parse('the linked Project item has Status "{status}"'))
def _linked_item_has_status(ctx, mock_run, status):
    assert ctx["result"].success, ctx["result"].message
    _assert_status_set(mock_run, _EXISTING_ITEM_ID, status)


@then("the status update targets the item found by lookup, not the task ID")
def _targets_looked_up_item(mock_run):
    assert _edited_item_ids(mock_run)
    assert set(_edited_item_ids(mock_run)) == {_EXISTING_ITEM_ID}


@then("a best-effort warning names the task")
def _warning_names_task(ctx):
    assert ctx["result"].success is False
    assert ctx["result"].message.startswith("Warning:")
    assert ctx["task"].id in ctx["result"].message


@then("the warning states that no Project item was found for the task")
def _warning_no_item_found(ctx):
    assert f"no Project item found for {ctx['task'].id}" in ctx["result"].message


@then("no Project item status is changed")
def _no_item_edit(mock_run):
    assert _gh_calls(mock_run, "item-edit") == []


@then("the task ID is never used as a Project item ID")
def _task_id_never_item_id(ctx, mock_run):
    assert ctx["task"].id not in _edited_item_ids(mock_run)


@then("the sync does not raise an error")
def _no_raise(ctx):
    assert "result" in ctx
