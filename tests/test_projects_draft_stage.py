"""Tests for TASK-060: a repo-local `.butler-project` config file resolved
ahead of the `BUTLER_GITHUB_PROJECT` environment variable, and a new
`--stage draft` option on `butler task sync-project` that creates/links a
Project item the same way `--stage open` does.

Covers docs/tasks/TASK-060-project-draft-stage-sync.md acceptance criteria:
- `.butler-project` resolves the Project number ahead of the environment variable
- Environment variable fallback when no config file exists
- `--stage draft` creates a Project item for a freshly drafted task
- "No Project configured" warning offers both setup options
"""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from butler_cli.__main__ import main
from butler_core.tasks import create_task


def _completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def _owner_repo_lookup_side_effect(owner: str, repo: str):
    def _side_effect(argv, *args, **kwargs):
        if argv[:1] == ["gh"] and "repo" in argv and "view" in argv:
            return _completed(
                returncode=0,
                stdout=f'{{"owner": {{"login": "{owner}"}}, "name": "{repo}"}}',
            )
        if argv[:1] == ["git"] and "remote" in argv:
            return _completed(returncode=0, stdout=f"git@github.com:{owner}/{repo}.git\n")
        return _completed(returncode=1, stderr="unexpected call")

    return _side_effect


class TestButlerProjectFileResolvesAheadOfEnvVar:
    """Scenario: .butler-project resolves the Project number ahead of the
    environment variable."""

    @patch("butler_core.projects.subprocess.run")
    def test_butler_project_file_value_is_used_over_env_var(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_open

        repo_root = tmp_path
        (repo_root / ".git").mkdir()
        (repo_root / ".butler-project").write_text("7\n")
        tasks_dir = repo_root / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))
        mock_run.return_value = _completed(returncode=0, stdout="")

        sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir))

        item_create_call = next(
            call for call in mock_run.call_args_list if "item-create" in call.args[0]
        )
        args = item_create_call.args[0]
        assert args[args.index("item-create") + 1] == "7"


class TestEnvVarFallbackWhenNoConfigFile:
    """Scenario: Environment variable fallback when no config file exists."""

    @patch("butler_core.projects.subprocess.run")
    def test_env_var_used_when_no_butler_project_file(self, mock_run: MagicMock, tmp_path) -> None:
        from butler_core.projects import sync_on_pr_open

        repo_root = tmp_path
        (repo_root / ".git").mkdir()
        tasks_dir = repo_root / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))
        mock_run.return_value = _completed(returncode=0, stdout="")

        sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir))

        item_create_call = next(
            call for call in mock_run.call_args_list if "item-create" in call.args[0]
        )
        args = item_create_call.args[0]
        assert args[args.index("item-create") + 1] == "5"

    @patch("butler_core.projects.subprocess.run")
    def test_no_tasks_dir_given_still_falls_back_to_env_var(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        """Existing callers that never pass `tasks_dir` (e.g. Requirement 4's
        original call sites) keep working unchanged."""
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.return_value = _completed(returncode=0, stdout="")

        sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        item_create_call = next(
            call for call in mock_run.call_args_list if "item-create" in call.args[0]
        )
        args = item_create_call.args[0]
        assert args[args.index("item-create") + 1] == "5"


class TestDraftStageCreatesProjectItem:
    """Scenario: --stage draft creates a Project item for a freshly drafted
    task."""

    @patch("butler_core.projects.subprocess.run")
    def test_cli_stage_draft_creates_project_item_and_exits_zero(
        self, mock_run: MagicMock, tmp_path, monkeypatch
    ) -> None:
        monkeypatch.setenv("BUTLER_GITHUB_PROJECT", "5")
        task = create_task("Some feature", "desc", tasks_dir=str(tmp_path))
        mock_run.return_value = MagicMock(returncode=0, stdout="")

        exit_code = main(
            [
                "--tasks-dir",
                str(tmp_path),
                "task",
                "sync-project",
                task.id,
                "--stage",
                "draft",
            ]
        )

        assert exit_code == 0
        assert any("item-create" in call.args[0] for call in mock_run.call_args_list)

    @patch("butler_core.projects.subprocess.run")
    def test_draft_stage_behaves_like_open_stage(self, mock_run: MagicMock, tmp_path) -> None:
        from butler_core.projects import sync_on_pr_draft, sync_on_pr_open

        task = create_task("Some feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.return_value = _completed(returncode=0, stdout="")

        open_result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})
        draft_result = sync_on_pr_draft(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert open_result.success == draft_result.success
        assert "In Progress" in draft_result.message


class TestNoProjectWarningOffersBothSetupOptions:
    """Scenario: "No Project configured" warning offers both setup
    options."""

    @patch("butler_core.projects.subprocess.run")
    def test_warning_mentions_butler_project_file_as_a_setup_option(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = _owner_repo_lookup_side_effect("CmdrPrompt", "python-butler")

        result = sync_on_pr_open(task, env={})

        assert ".butler-project" in result.message
        assert "export BUTLER_GITHUB_PROJECT=" in result.message
