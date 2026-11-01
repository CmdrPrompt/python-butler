"""TASK-084: binds TASK-084-obsolete-task-status.feature.

`gh` is faked at `butler_core.projects.subprocess.run`, dispatching on the
subcommand the same way tests/bdd/steps/test_task_099_steps.py does.
"""

from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from pytest_bdd import given, scenarios, then, when

from butler_cli.__main__ import main
from butler_core.projects import _match_status_option, sync_on_pr_backfill
from butler_core.tasks import create_task, read_task, set_status

scenarios("../features/TASK-084-obsolete-task-status.feature")

_SKILL = Path(__file__).resolve().parents[3] / ".claude/skills/task-file-format/SKILL.md"
_ENV = {"BUTLER_GITHUB_PROJECT": "5"}
_BASE_OPTIONS = [
    {"id": "opt_todo", "name": "Todo"},
    {"id": "opt_in_progress", "name": "In Progress"},
    {"id": "opt_done", "name": "Done"},
]
_OBSOLETE_OPTION = {"id": "opt_obsolete", "name": "Obsolete"}


def _completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def _gh_side_effect(status_field: dict):
    def _side_effect(argv, *args, **kwargs):
        if argv[0] == "gh" and "item-list" in argv:
            return _completed(stdout="PVTI_existing")
        if argv[0] == "gh" and "view" in argv:
            return _completed(stdout=json.dumps({"id": "PVT_node"}))
        if argv[0] == "gh" and "field-list" in argv:
            return _completed(stdout=json.dumps({"fields": [status_field]}))
        if argv[0] == "gh" and ("item-create" in argv or "item-edit" in argv):
            return _completed()
        if argv[0] == "git":
            return _completed(returncode=1)
        return _completed(returncode=1, stderr="unexpected call")

    return _side_effect


@pytest.fixture
def ctx(tmp_path):
    tasks_dir = tmp_path / "docs" / "tasks"
    task = create_task("Superseded feature", "desc", tasks_dir=str(tasks_dir))
    set_status(task.id, "obsolete", tasks_dir=str(tasks_dir))
    return {"task_id": task.id, "tasks_dir": str(tasks_dir)}


@pytest.fixture
def mock_run():
    with patch("butler_core.projects.subprocess.run") as mocked:
        yield mocked


@given("the task-file-format skill's canonical template")
def _skill_template(ctx):
    ctx["skill"] = _SKILL.read_text(encoding="utf-8")


@when("a reader looks at the Status line")
def _status_line(ctx):
    template = ctx["skill"].split("## Status\n", 1)[1]
    ctx["status_line"] = template.splitlines()[0]


@then("it lists `todo | in-progress | blocked | done | obsolete`")
def _lists_obsolete(ctx):
    assert ctx["status_line"] == "todo | in-progress | blocked | done | obsolete"


@then(
    "a nearby note states only the Workflow Guardian or the user sets `obsolete`, "
    "and only when the file documents the superseding task/requirement"
)
def _ownership_note(ctx):
    roles = ctx["skill"].split("## Status transitions and role boundaries", 1)[1]
    note = next(line for line in roles.split("\n- ") if "`obsolete`" in line)
    assert "Workflow Guardian" in note
    assert "user" in note
    assert "supersed" in note


@given("a task file with `## Status` set to `obsolete`")
def _obsolete_task(ctx):
    assert read_task(ctx["task_id"], tasks_dir=ctx["tasks_dir"]).status == "obsolete"


@when("`butler task show`/`set-status`/the Projects sync status-matching process it")
def _process_obsolete(ctx, capsys):
    ctx["show_exit"] = main(["--tasks-dir", ctx["tasks_dir"], "task", "show", ctx["task_id"]])
    ctx["show_out"] = capsys.readouterr().out
    ctx["set_status_exit"] = main(
        ["--tasks-dir", ctx["tasks_dir"], "task", "set-status", ctx["task_id"], "obsolete"]
    )
    fields = [
        {"id": "PVTSSF_status", "name": "Status", "options": [*_BASE_OPTIONS, _OBSOLETE_OPTION]}
    ]
    ctx["match"] = _match_status_option(fields, "obsolete")


@then("it is accepted identically to `todo`/`in-progress`/`blocked`/`done`, with no error")
def _accepted(ctx):
    assert ctx["show_exit"] in (0, None)
    assert "obsolete" in ctx["show_out"]
    assert ctx["set_status_exit"] in (0, None)
    assert read_task(ctx["task_id"], tasks_dir=ctx["tasks_dir"]).status == "obsolete"
    assert ctx["match"] == ("PVTSSF_status", "opt_obsolete")


@given(
    "a task file with Status `obsolete` and a configured GitHub Project "
    'whose Status field has an "Obsolete" option'
)
def _project_with_obsolete(ctx):
    ctx["status_field"] = {
        "id": "PVTSSF_status",
        "name": "Status",
        "options": [*_BASE_OPTIONS, _OBSOLETE_OPTION],
    }


@given('a configured GitHub Project whose Status field has no "Obsolete" option')
def _project_without_obsolete(ctx):
    ctx["status_field"] = {"id": "PVTSSF_status", "name": "Status", "options": _BASE_OPTIONS}


@when("`butler task sync-project <ID> --stage backfill` runs")
@when("`--stage backfill` runs against an `obsolete` task")
def _run_backfill(ctx, mock_run):
    mock_run.side_effect = _gh_side_effect(ctx["status_field"])
    task = read_task(ctx["task_id"], tasks_dir=ctx["tasks_dir"])
    ctx["result"] = sync_on_pr_backfill(task, env=_ENV, tasks_dir=ctx["tasks_dir"])


@then('the linked Project item\'s Status is set to "Obsolete"')
def _status_obsolete(ctx, mock_run):
    assert ctx["result"].success, ctx["result"].message
    assert "status: Obsolete" in ctx["result"].message
    status_edits = [
        call.args[0]
        for call in mock_run.call_args_list
        if "item-edit" in call.args[0] and "--single-select-option-id" in call.args[0]
    ]
    assert len(status_edits) == 1
    argv = status_edits[0]
    assert argv[argv.index("--id") + 1] == "PVTI_existing"
    assert argv[argv.index("--single-select-option-id") + 1] == "opt_obsolete"


@then("it produces a best-effort warning and does not raise or block")
def _warns(ctx):
    assert ctx["result"].success is False
    assert "obsolete" in ctx["result"].message
