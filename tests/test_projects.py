"""Tests for butler_core.projects: best-effort one-way sync of task metadata
to a linked GitHub Projects (v2) item.

Covers TASK-056 acceptance criteria (Gherkin scenarios):
- GitHub Projects sync entry point exists as a separate module
- Sync creates GitHub Projects item on PR open with correct metadata
- Sync updates GitHub Projects item status on PR merge
- Sync gracefully handles missing Project configuration
- Sync gracefully handles gh not authenticated
- Sync gracefully handles gh not installed
- Sync is one-way; no data read from GitHub Projects
"""

from __future__ import annotations

import json
import subprocess
from pathlib import Path
from unittest.mock import MagicMock, patch

from butler_core.tasks import Task, create_task


def _completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


class TestModuleIsSeparateFromGitOps:
    """Scenario: GitHub Projects sync entry point exists as a separate module."""

    def test_projects_module_can_be_imported(self) -> None:
        import butler_core.projects as projects_module

        assert projects_module is not None

    def test_projects_module_exposes_sync_on_pr_open_and_sync_on_pr_merge(self) -> None:
        from butler_core import projects

        assert callable(projects.sync_on_pr_open)
        assert callable(projects.sync_on_pr_merge)

    def test_git_ops_module_does_not_define_projects_sync_functions(self) -> None:
        """The sync logic must not be inlined into git_ops.py's
        branch/stage/commit/pr/merge functions; git_ops.py must not define
        or re-export the projects sync entry points itself."""
        from butler_core import git_ops

        assert not hasattr(git_ops, "sync_on_pr_open")
        assert not hasattr(git_ops, "sync_on_pr_merge")


class TestItemListLookupPagination:
    """TASK-089 / REQUIREMENTS_TASK_WORKFLOW.md Requirement 16: the item-list
    lookup must retrieve every Project item, not just `gh`'s default 30-item
    page, before applying the title-prefix filter."""

    def test_item_list_lookup_passes_a_limit_above_ghs_default_page_size(self) -> None:
        from butler_core.projects import _item_list_lookup

        task = Task(
            id="TASK-999",
            title="Some task",
            status="todo",
            description="desc",
            branch_name="task/999-some-task",
            switch_create_cmd="git checkout -b task/999-some-task",
            stage_paths=[],
            commit_message="Some task",
            acceptance_criteria=[],
            completion=None,
        )

        with patch("butler_core.projects.subprocess.run") as mock_run:
            mock_run.return_value = _completed(returncode=0, stdout="")
            _item_list_lookup(task, project="2", owner="acme", env=None)

        argv = mock_run.call_args.args[0]
        assert "--limit" in argv or "-L" in argv, (
            f"expected item-list to pass a --limit above gh's default page size (30), got {argv}"
        )
        limit_flag = "--limit" if "--limit" in argv else "-L"
        limit_value = int(argv[argv.index(limit_flag) + 1])
        assert limit_value > 30, (
            f"--limit {limit_value} does not exceed gh's default page size (30)"
        )


class TestSyncOnPrOpen:
    """Scenario: Sync creates GitHub Projects item on PR open with correct
    metadata."""

    @patch("butler_core.projects.subprocess.run")
    def test_returns_success_result_when_gh_succeeds(self, mock_run: MagicMock, tmp_path) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task(
            "Add dark mode toggle", "desc", tasks_dir=str(tmp_path / "docs" / "tasks")
        )
        mock_run.return_value = _completed(
            returncode=0, stdout="https://github.com/org/repo/pull/1"
        )

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is True

    @patch("butler_core.projects.subprocess.run")
    def test_success_message_includes_task_id_and_title(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task(
            "Add dark mode toggle", "desc", tasks_dir=str(tmp_path / "docs" / "tasks")
        )
        mock_run.return_value = _completed(
            returncode=0, stdout="https://github.com/org/repo/pull/1"
        )

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert task.id in result.message
        assert task.title in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_invokes_gh_cli_to_create_or_link_the_project_item(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.return_value = _completed(
            returncode=0, stdout="https://github.com/org/repo/pull/1"
        )

        sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert mock_run.called
        first_call_command = mock_run.call_args_list[0].args[0]
        assert first_call_command[0] == "gh"


def _merge_stage_success_sequence(
    item_id: str = "PVTI_item1",
    project_node_id: str = "PVT_kwHOAAnLPc4BfBkx",
    status_field_id: str = "PVTSSF_status",
    done_option_id: str = "98236657",
) -> list[MagicMock]:
    """The four sequential `gh` calls a successful merge-stage sync makes:
    item-list, project view, field-list, item-edit."""
    return [
        _completed(returncode=0, stdout=item_id),
        _completed(returncode=0, stdout=json.dumps({"id": project_node_id})),
        _completed(
            returncode=0,
            stdout=json.dumps(
                {
                    "fields": [
                        {
                            "id": status_field_id,
                            "name": "Status",
                            "options": [
                                {"id": "f75ad846", "name": "Todo"},
                                {"id": done_option_id, "name": "Done"},
                            ],
                        }
                    ]
                }
            ),
        ),
        _completed(returncode=0, stdout=""),
    ]


class TestSyncOnPrMerge:
    """Scenario: Sync updates GitHub Projects item status on PR merge."""

    @patch("butler_core.projects.subprocess.run")
    def test_returns_success_result_when_status_update_succeeds(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_merge

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = _merge_stage_success_sequence()

        result = sync_on_pr_merge(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is True

    @patch("butler_core.projects.subprocess.run")
    def test_success_message_reports_status_done(self, mock_run: MagicMock, tmp_path) -> None:
        from butler_core.projects import sync_on_pr_merge

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = _merge_stage_success_sequence()

        result = sync_on_pr_merge(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert "Done" in result.message
        assert task.id in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_invokes_gh_cli_to_update_status_field(self, mock_run: MagicMock, tmp_path) -> None:
        from butler_core.projects import sync_on_pr_merge

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = _merge_stage_success_sequence()

        sync_on_pr_merge(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert mock_run.called
        assert all(call.args[0][0] == "gh" for call in mock_run.call_args_list)

    @patch("butler_core.projects.subprocess.run")
    def test_item_edit_uses_resolved_node_ids_not_the_raw_project_number_or_literal_names(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        """Regression test for the GraphQL failure confirmed live against a
        real Projects v2 board while completing TASK-058: `--project-id`,
        `--field-id`, and `--single-select-option-id` must be the resolved
        GraphQL node IDs, not the plain project number ("5") or the literal
        strings "Status"/"Done"."""
        from butler_core.projects import sync_on_pr_merge

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = _merge_stage_success_sequence(
            project_node_id="PVT_kwHOAAnLPc4BfBkx",
            status_field_id="PVTSSF_status",
            done_option_id="98236657",
        )

        sync_on_pr_merge(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        item_edit_call = next(
            call for call in mock_run.call_args_list if "item-edit" in call.args[0]
        )
        args = item_edit_call.args[0]
        assert args[args.index("--project-id") + 1] == "PVT_kwHOAAnLPc4BfBkx"
        assert args[args.index("--field-id") + 1] == "PVTSSF_status"
        assert args[args.index("--single-select-option-id") + 1] == "98236657"

    @patch("butler_core.projects.subprocess.run")
    def test_missing_status_field_on_project_returns_warning_without_raising(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_merge

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = [
            _completed(returncode=0, stdout="PVTI_item1"),
            _completed(returncode=0, stdout=json.dumps({"id": "PVT_kwHOAAnLPc4BfBkx"})),
            _completed(returncode=0, stdout=json.dumps({"fields": [{"id": "x", "name": "Title"}]})),
        ]

        result = sync_on_pr_merge(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is False
        assert "Warning" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_missing_done_option_on_status_field_returns_warning_without_raising(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_merge

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = [
            _completed(returncode=0, stdout="PVTI_item1"),
            _completed(returncode=0, stdout=json.dumps({"id": "PVT_kwHOAAnLPc4BfBkx"})),
            _completed(
                returncode=0,
                stdout=json.dumps(
                    {
                        "fields": [
                            {
                                "id": "PVTSSF_status",
                                "name": "Status",
                                "options": [{"id": "f75ad846", "name": "Todo"}],
                            }
                        ]
                    }
                ),
            ),
        ]

        result = sync_on_pr_merge(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is False
        assert "Warning" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_item_edit_failure_after_successful_resolution_returns_warning(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_merge

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        sequence = _merge_stage_success_sequence()
        sequence[-1] = _completed(returncode=1, stderr="permission denied")
        mock_run.side_effect = sequence

        result = sync_on_pr_merge(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is False
        assert "Warning" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_gh_not_installed_during_status_update_returns_warning_without_raising(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_merge

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = FileNotFoundError("gh")

        result = sync_on_pr_merge(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is False
        assert "not found" in result.message.lower()

    @patch("butler_core.projects.subprocess.run")
    def test_unexpected_os_error_during_status_update_returns_warning_without_raising(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_merge

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = PermissionError("denied")

        result = sync_on_pr_merge(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is False
        assert "Warning" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_called_process_error_during_status_update_returns_warning_without_raising(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_merge

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = subprocess.CalledProcessError(1, ["gh"], stderr="permission denied")

        result = sync_on_pr_merge(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is False
        assert "Warning" in result.message


class TestSyncHandlesMissingProjectConfiguration:
    """Scenario: Sync gracefully handles missing Project configuration."""

    @patch("butler_core.projects.subprocess.run")
    def test_returns_failure_result_without_raising(self, mock_run: MagicMock, tmp_path) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))

        result = sync_on_pr_open(task, env={})

        assert result.success is False

    @patch("butler_core.projects.subprocess.run")
    def test_warning_message_mentions_no_project_configured(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))

        result = sync_on_pr_open(task, env={})

        assert "Warning" in result.message
        assert task.id in result.message
        assert "no project configured" in result.message.lower()

    @patch("butler_core.projects.subprocess.run")
    def test_does_not_attempt_to_create_or_edit_a_project_item_when_no_project_configured(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        """When no project is configured, the sync must never attempt to
        write a GitHub Projects item (`gh project item-create` /
        `item-edit`). TASK-057 permits a read-only lookup call (e.g. `gh
        repo view` or `git remote get-url origin`) to determine the
        owner/repo for the warning's setup suggestion, so this no longer
        asserts zero subprocess calls (see TASK-057)."""
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))

        sync_on_pr_open(task, env={})

        mutating_calls = [
            call
            for call in mock_run.call_args_list
            if "item-create" in call.args[0] or "item-edit" in call.args[0]
        ]
        assert mutating_calls == []


class TestSyncHandlesGhNotAuthenticated:
    """Scenario: Sync gracefully handles gh not authenticated."""

    @patch("butler_core.projects.subprocess.run")
    def test_returns_failure_result_without_raising(self, mock_run: MagicMock, tmp_path) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.return_value = _completed(
            returncode=1, stderr="gh: To use GitHub CLI, please run: gh auth login"
        )

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is False

    @patch("butler_core.projects.subprocess.run")
    def test_warning_message_mentions_not_authenticated(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.return_value = _completed(
            returncode=1, stderr="gh: To use GitHub CLI, please run: gh auth login"
        )

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert "Warning" in result.message
        assert task.id in result.message
        assert "authenticat" in result.message.lower()


class TestSyncHandlesGhNotInstalled:
    """Scenario: Sync gracefully handles gh not installed."""

    @patch("butler_core.projects.subprocess.run")
    def test_returns_failure_result_without_raising(self, mock_run: MagicMock, tmp_path) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = FileNotFoundError("gh")

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is False

    @patch("butler_core.projects.subprocess.run")
    def test_warning_message_mentions_gh_not_found(self, mock_run: MagicMock, tmp_path) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = FileNotFoundError("gh")

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert "Warning" in result.message
        assert task.id in result.message
        assert "not found" in result.message.lower()

    @patch("butler_core.projects.subprocess.run")
    def test_does_not_raise_on_unexpected_subprocess_error(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        """Best-effort: any gh invocation failure (e.g. missing permissions
        reported as a CalledProcessError) must be swallowed and reported as
        a warning result rather than propagated to the caller."""
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = subprocess.CalledProcessError(1, ["gh"], stderr="permission denied")

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is False
        assert "Warning" in result.message


class TestSyncIsOneWay:
    """Scenario: Sync is one-way; no data read from GitHub Projects."""

    @patch("butler_core.projects.subprocess.run")
    def test_sync_on_pr_open_does_not_modify_the_task_file_on_disk(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_open

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))
        task_file = next(tasks_dir.glob(f"{task.id}*.md"))
        original_contents = task_file.read_text()
        mock_run.return_value = _completed(
            returncode=0, stdout="https://github.com/org/repo/pull/1"
        )

        sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert task_file.read_text() == original_contents

    @patch("butler_core.projects.subprocess.run")
    def test_sync_on_pr_merge_does_not_modify_the_task_file_on_disk(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_merge

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))
        task_file = next(tasks_dir.glob(f"{task.id}*.md"))
        original_contents = task_file.read_text()
        mock_run.return_value = _completed(
            returncode=0, stdout="https://github.com/org/repo/pull/1"
        )

        sync_on_pr_merge(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert task_file.read_text() == original_contents

    @patch("butler_core.projects.subprocess.run")
    def test_sync_on_pr_open_result_carries_no_field_values_read_back_from_github(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        """The result object exposes only success/message (what was
        written); it must not surface any field values GitHub Projects
        happened to already hold (e.g. an outdated title), which would
        indicate a read-back rather than a write-only sync."""
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.return_value = _completed(
            returncode=0,
            stdout='{"title": "Some outdated title set manually in the Project"}',
        )

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert "outdated title" not in result.message
        assert set(vars(result).keys()) <= {"success", "message"}


def _add_story_and_acceptance(
    tasks_dir: Path, task_id: str, story: str, acceptance_scenario: str
) -> None:
    """Insert `## Story` (with `story`) before `## Description`, and append
    `acceptance_scenario` inside the (otherwise empty) `## Acceptance
    criteria` section that `create_task`'s default template renders."""
    path = next(Path(tasks_dir).glob(f"{task_id}*.md"))
    text = path.read_text()
    text = text.replace("## Description", f"## Story\n\n{story}\n\n## Description", 1)
    text = text.replace(
        "## Acceptance criteria\n\n", f"## Acceptance criteria\n\n{acceptance_scenario}\n\n", 1
    )
    path.write_text(text)


def _owner_repo_lookup_ok(owner: str = "acme", repo: str = "widgets") -> MagicMock:
    return _completed(returncode=0, stdout=json.dumps({"owner": {"login": owner}, "name": repo}))


class TestProjectItemBodyFromTaskFile:
    """Covers TASK-066 / Requirement 11 acceptance criteria (Gherkin
    scenarios):
    - Project item body includes Story, Acceptance criteria, and task file
      link (no PR yet)
    - Project item body includes PR link when a PR exists
    - Missing task file falls back to the existing title-only behavior
    """

    @patch("butler_core.projects.subprocess.run")
    def test_body_includes_story_and_acceptance_and_task_file_link_no_pr(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_draft

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task(
            "My feature",
            "Long implementation-heavy detail that must not leak into the board.",
            tasks_dir=str(tasks_dir),
        )
        _add_story_and_acceptance(
            tasks_dir,
            task.id,
            "As a maintainer, I want to see the task's context on the board.",
            "- [ ] Scenario: the board shows something useful",
        )
        mock_run.return_value = _completed(returncode=0, stdout="")

        result = sync_on_pr_draft(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is True
        item_create_call = next(
            call for call in mock_run.call_args_list if "item-create" in call.args[0]
        )
        argv = item_create_call.args[0]
        assert "--body" in argv
        body = argv[argv.index("--body") + 1]
        assert "As a maintainer, I want to see the task's context on the board." in body
        assert "Scenario: the board shows something useful" in body
        assert "Task file:" in body
        assert task.id in body
        assert "Long implementation-heavy detail that must not leak" not in body
        assert "PR:" not in body

    @patch("butler_core.projects.subprocess.run")
    def test_body_includes_pr_link_when_a_pr_exists(self, mock_run: MagicMock, tmp_path) -> None:
        from butler_core.projects import sync_on_pr_open

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task(
            "My feature",
            "Long implementation-heavy detail that must not leak into the board.",
            tasks_dir=str(tasks_dir),
        )
        _add_story_and_acceptance(
            tasks_dir,
            task.id,
            "As a maintainer, I want to see the task's context on the board.",
            "- [ ] Scenario: the board shows something useful",
        )

        def _side_effect(argv, *args, **kwargs):
            if argv[0] == "gh" and "item-list" in argv:
                return _completed(returncode=0, stdout="")
            if argv[0] == "gh" and argv[1:3] == ["repo", "view"]:
                return _owner_repo_lookup_ok()
            if argv[0] == "gh" and "item-create" in argv:
                return _completed(returncode=0, stdout="")
            return _completed(returncode=1, stderr="unexpected call")

        mock_run.side_effect = _side_effect

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir))

        assert result.success is True
        item_create_call = next(
            call for call in mock_run.call_args_list if "item-create" in call.args[0]
        )
        argv = item_create_call.args[0]
        body = argv[argv.index("--body") + 1]
        assert "As a maintainer, I want to see the task's context on the board." in body
        assert "Scenario: the board shows something useful" in body
        assert "Task file:" in body
        assert "PR: https://github.com/acme/widgets/pulls?q=is%3Apr+head%3A" in body
        assert task.branch_name in body

    @patch("butler_core.projects.subprocess.run")
    def test_start_stage_body_never_includes_a_pr_link(self, mock_run: MagicMock, tmp_path) -> None:
        """`sync_on_pr_start` runs before a PR exists (`make branch-task`),
        so unlike `sync_on_pr_open`/`sync_on_pr_backfill`, its created
        item's body must never carry a PR link."""
        from butler_core.projects import sync_on_pr_start

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))
        _add_story_and_acceptance(
            tasks_dir, task.id, "As a maintainer, I want context.", "- [ ] Scenario: works"
        )

        def _side_effect(argv, *args, **kwargs):
            if argv[0] == "gh" and "item-list" in argv:
                return _completed(returncode=0, stdout="")
            if argv[0] == "gh" and "item-create" in argv:
                return _completed(returncode=0, stdout="")
            if argv[0] == "gh" and "view" in argv and "project" in argv:
                return _completed(returncode=0, stdout=json.dumps({"id": "PVT_node"}))
            if argv[0] == "gh" and "field-list" in argv:
                return _completed(
                    returncode=0,
                    stdout=json.dumps(
                        {
                            "fields": [
                                {
                                    "id": "PVTSSF_status",
                                    "name": "Status",
                                    "options": [{"id": "opt_in_progress", "name": "In Progress"}],
                                }
                            ]
                        }
                    ),
                )
            if argv[0] == "gh" and "item-edit" in argv:
                return _completed(returncode=0, stdout="")
            return _completed(returncode=1, stderr="unexpected call")

        mock_run.side_effect = _side_effect

        result = sync_on_pr_start(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is True
        item_create_call = next(
            call for call in mock_run.call_args_list if "item-create" in call.args[0]
        )
        argv = item_create_call.args[0]
        body = argv[argv.index("--body") + 1]
        assert "PR:" not in body

    @patch("butler_core.projects.subprocess.run")
    def test_missing_task_file_falls_back_to_title_only_creation(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_draft

        task = Task(
            id="TASK-999",
            title="Untracked",
            status="todo",
            description="desc",
            branch_name="task/999-untracked",
            switch_create_cmd="",
            stage_paths=[],
            commit_message="",
            acceptance_criteria=[],
        )
        mock_run.return_value = _completed(returncode=0, stdout="")

        result = sync_on_pr_draft(task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=None)

        assert result.success is True
        item_create_call = next(
            call for call in mock_run.call_args_list if "item-create" in call.args[0]
        )
        argv = item_create_call.args[0]
        assert "--body" not in argv
        assert "--title" in argv

    @patch("butler_core.projects.subprocess.run")
    def test_no_task_file_matching_task_id_falls_back_to_title_only_creation(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_draft

        tasks_dir = tmp_path / "docs" / "tasks"
        tasks_dir.mkdir(parents=True)
        task = Task(
            id="TASK-999",
            title="Untracked",
            status="todo",
            description="desc",
            branch_name="task/999-untracked",
            switch_create_cmd="",
            stage_paths=[],
            commit_message="",
            acceptance_criteria=[],
        )
        mock_run.return_value = _completed(returncode=0, stdout="")

        result = sync_on_pr_draft(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert result.success is True
        item_create_call = next(
            call for call in mock_run.call_args_list if "item-create" in call.args[0]
        )
        argv = item_create_call.args[0]
        assert "--body" not in argv

    @patch("butler_core.projects.subprocess.run")
    def test_pr_link_omitted_when_owner_repo_cannot_be_resolved(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        """Best-effort: an unresolvable owner/repo must not block item
        creation or the rest of the body, only the PR link line itself."""
        from butler_core.projects import sync_on_pr_open

        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))
        _add_story_and_acceptance(
            tasks_dir, task.id, "As a maintainer, I want context.", "- [ ] Scenario: works"
        )

        def _side_effect(argv, *args, **kwargs):
            if argv[0] == "gh" and "item-list" in argv:
                return _completed(returncode=0, stdout="")
            if argv[0] == "gh" and argv[1:3] == ["repo", "view"]:
                return _completed(returncode=1, stderr="not a repo")
            if argv[0] == "git":
                return _completed(returncode=1, stderr="no remote")
            if argv[0] == "gh" and "item-create" in argv:
                return _completed(returncode=0, stdout="")
            return _completed(returncode=1, stderr="unexpected call")

        mock_run.side_effect = _side_effect

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir))

        assert result.success is True
        item_create_call = next(
            call for call in mock_run.call_args_list if "item-create" in call.args[0]
        )
        argv = item_create_call.args[0]
        body = argv[argv.index("--body") + 1]
        assert "PR:" not in body
        assert "Task file:" in body


class TestExtractSectionHelper:
    """Unit coverage for `_extract_section`, the Story/Acceptance-criteria
    extraction `_project_item_body` uses -- kept separate from `_pr_body()`
    in git_ops.py per Requirement 11."""

    def test_returns_empty_string_when_heading_absent(self) -> None:
        from butler_core.projects import _extract_section

        assert _extract_section("## Other\n\ncontent\n", "Story") == ""

    def test_stops_at_next_top_level_heading(self) -> None:
        from butler_core.projects import _extract_section

        text = "## Story\n\nAs a user...\n\n## Description\n\nleaked detail\n"

        section = _extract_section(text, "Story")

        assert "As a user..." in section
        assert "leaked detail" not in section

    def test_captures_to_end_of_text_when_no_following_heading(self) -> None:
        from butler_core.projects import _extract_section

        text = "## Acceptance criteria\n\n- [ ] Scenario: last section\n"

        section = _extract_section(text, "Acceptance criteria")

        assert "Scenario: last section" in section
