"""Supplementary characterization tests for butler_core.projects covering
error-handling branches not exercised by the TASK-056 acceptance-criteria
tests in tests/test_projects.py (added to keep coverage at/above the
task-start baseline; not part of the pinned Test Writer contract)."""

from __future__ import annotations

from unittest.mock import MagicMock, patch

from butler_core.tasks import create_task


def _completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


class TestClassifyGhFailureFallback:
    @patch("butler_core.projects.subprocess.run")
    def test_generic_failure_with_empty_stderr_reports_generic_message(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.return_value = _completed(returncode=1, stderr="")

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is False
        assert "gh command failed" in result.message


class TestSyncOnPrMergeItemLookupFailure:
    @patch("butler_core.projects.subprocess.run")
    def test_returns_failure_when_item_lookup_call_fails(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_merge

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.return_value = _completed(returncode=1, stderr="some project error")

        result = sync_on_pr_merge(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is False
        assert "some project error" in result.message


class TestSyncHandlesUnexpectedOsError:
    @patch("butler_core.projects.subprocess.run")
    def test_returns_failure_result_without_raising_on_permission_error(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_open

        task = create_task("My feature", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        mock_run.side_effect = PermissionError("denied")

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"})

        assert result.success is False
        assert "Warning" in result.message
        assert task.id in result.message
