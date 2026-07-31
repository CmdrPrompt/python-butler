"""Tests for TASK-057: enhance the "no project configured" warning with
repo-specific setup instructions.

Covers TASK-057 acceptance criteria (Gherkin scenarios) in
docs/tasks/TASK-057-enhance-no-project-warning.md:
- Warning includes repo-specific setup commands when owner/repo can be
  determined at runtime (via `gh repo view --json owner,name` or by parsing
  the `origin` remote URL).
- Warning falls back to the existing generic message when owner/repo cannot
  be determined (`gh` not installed/authenticated, no `origin` remote).
- The repo-specific suggestion is directly copy-pasteable (exact owner and
  repository name substituted, no placeholders).

These tests only exercise the public `sync_on_pr_open`/`sync_on_pr_merge`
entry points with `BUTLER_GITHUB_PROJECT` unset, mocking
`butler_core.projects.subprocess.run` the same way tests/test_projects.py
does. The mock's `side_effect` inspects the invoked command so the tests
stay agnostic to whether the implementation determines owner/repo via
`gh repo view` or by parsing the `origin` remote URL with `git`.
"""

from __future__ import annotations

import subprocess
from unittest.mock import MagicMock, patch

from butler_core.tasks import create_task


def _completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


def _owner_repo_lookup_side_effect(owner: str, repo: str):
    """Build a `subprocess.run` side_effect that answers either a
    `gh repo view --json owner,name` call or a `git remote get-url origin`
    call (whichever the implementation chooses) with data resolving to the
    given owner/repo, and answers anything else (e.g. a `gh project ...`
    write call, which must never be reached while no project is configured)
    with a generic failure."""

    def _side_effect(argv, *args, **kwargs):
        if argv[:1] == ["gh"] and "repo" in argv and "view" in argv:
            return _completed(
                returncode=0,
                stdout=f'{{"owner": {{"login": "{owner}"}}, "name": "{repo}"}}',
            )
        if argv[:1] == ["git"] and "remote" in argv:
            return _completed(
                returncode=0,
                stdout=f"git@github.com:{owner}/{repo}.git\n",
            )
        return _completed(returncode=1, stderr="unexpected call")

    return _side_effect


def _lookup_fails_side_effect(argv, *args, **kwargs):
    """Simulate `gh` not installed/authenticated and no `origin` remote:
    every lookup attempt fails without raising."""
    return _completed(returncode=1, stderr="gh: not authenticated")


class TestWarningIncludesRepoSpecificSetupCommandsWhenDeterminable:
    """Scenario: Warning includes repo-specific setup commands when
    owner/repo can be determined."""

    @patch("butler_core.projects.subprocess.run")
    def test_warning_includes_gh_project_create_command_with_actual_owner_and_repo(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = _owner_repo_lookup_side_effect("CmdrPrompt", "python-butler")

        result = sync_on_pr_open(task, env={})

        assert "gh project create --owner CmdrPrompt --title python-butler" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_warning_includes_export_butler_github_project_command(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = _owner_repo_lookup_side_effect("CmdrPrompt", "python-butler")

        result = sync_on_pr_open(task, env={})

        assert "export BUTLER_GITHUB_PROJECT=" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_warning_still_reports_no_project_configured_reason(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = _owner_repo_lookup_side_effect("CmdrPrompt", "python-butler")

        result = sync_on_pr_open(task, env={})

        assert result.success is False
        assert "no project configured for this repo" in result.message.lower()

    @patch("butler_core.projects.subprocess.run")
    def test_result_is_still_reported_as_a_warning_not_raised(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = _owner_repo_lookup_side_effect("CmdrPrompt", "python-butler")

        result = sync_on_pr_open(task, env={})

        assert result.success is False
        assert "Warning" in result.message


class TestWarningFallsBackToGenericMessageWhenOwnerRepoCannotBeDetermined:
    """Scenario: Warning falls back to generic message when owner/repo
    cannot be determined."""

    @patch("butler_core.projects.subprocess.run")
    def test_message_contains_generic_no_project_configured_text(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = _lookup_fails_side_effect

        result = sync_on_pr_open(task, env={})

        assert "no project configured for this repo" in result.message.lower()

    @patch("butler_core.projects.subprocess.run")
    def test_message_does_not_include_concrete_setup_commands(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = _lookup_fails_side_effect

        result = sync_on_pr_open(task, env={})

        assert "gh project create" not in result.message
        assert "export BUTLER_GITHUB_PROJECT=" not in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_does_not_raise_when_gh_is_not_installed(self, mock_run: MagicMock, tmp_path) -> None:
        """`gh` not installed at all (FileNotFoundError) while probing for
        owner/repo must never propagate; sync still returns the generic
        warning."""
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = FileNotFoundError("gh")

        result = sync_on_pr_open(task, env={})

        assert result.success is False
        assert "no project configured for this repo" in result.message.lower()

    @patch("butler_core.projects.subprocess.run")
    def test_does_not_raise_when_owner_repo_lookup_raises_called_process_error(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = subprocess.CalledProcessError(
            1, ["git", "remote", "get-url", "origin"], stderr="fatal: No such remote 'origin'"
        )

        result = sync_on_pr_open(task, env={})

        assert result.success is False
        assert "no project configured for this repo" in result.message.lower()


class TestRepoSpecificSuggestionIsDirectlyCopyPasteable:
    """Scenario: Repo-specific suggestion is directly copy-pasteable."""

    @patch("butler_core.projects.subprocess.run")
    def test_suggested_command_matches_exact_owner_and_repo_with_no_placeholders(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = _owner_repo_lookup_side_effect("CmdrPrompt", "python-butler")

        result = sync_on_pr_open(task, env={})

        assert "<owner>" not in result.message
        assert "<repo>" not in result.message
        assert "gh project create --owner CmdrPrompt --title python-butler" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_suggestion_also_appears_on_sync_on_pr_merge_when_no_project_configured(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        """The enhanced warning applies to any sync path that hits the
        "no project configured" branch, including the PR-merge status
        update sync, not only PR-open."""
        from butler_core.projects import sync_on_pr_merge

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = _owner_repo_lookup_side_effect("CmdrPrompt", "python-butler")

        result = sync_on_pr_merge(task, env={})

        assert "gh project create --owner CmdrPrompt --title python-butler" in result.message
