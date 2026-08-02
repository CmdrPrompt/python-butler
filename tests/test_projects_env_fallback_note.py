"""Tests for TASK-090: a visibility note appended to success messages when
Project-number resolution falls back to the `BUTLER_GITHUB_PROJECT`
environment variable instead of a repo-local `.butler-project` file.

Covers REQUIREMENTS_TASK_WORKFLOW.md Requirement 17 acceptance criteria:
- Resolution via env var fallback emits a visibility note
- Resolution via repo-local file emits no such note
"""

from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

from butler_core.tasks import create_task


def _completed(returncode: int = 0, stdout: str = "", stderr: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    result.stderr = stderr
    return result


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


class TestEnvVarFallbackEmitsVisibilityNote:
    """Scenario: Resolution via env var fallback emits a visibility note."""

    @patch("butler_core.projects.subprocess.run")
    def test_open_stage_success_message_includes_env_var_note(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_open

        repo_root = tmp_path
        (repo_root / ".git").mkdir()
        tasks_dir = repo_root / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))
        mock_run.return_value = _completed(returncode=0, stdout="")

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir))

        assert result.success is True
        assert "Note:" in result.message
        assert "$BUTLER_GITHUB_PROJECT" in result.message
        assert ".butler-project" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_merge_stage_success_message_includes_env_var_note(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_merge

        repo_root = tmp_path
        (repo_root / ".git").mkdir()
        tasks_dir = repo_root / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))
        mock_run.side_effect = _merge_stage_success_sequence()

        result = sync_on_pr_merge(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert "Note:" in result.message
        assert "$BUTLER_GITHUB_PROJECT" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_note_includes_the_resolved_project_number(self, mock_run: MagicMock, tmp_path) -> None:
        from butler_core.projects import sync_on_pr_open

        repo_root = tmp_path
        (repo_root / ".git").mkdir()
        tasks_dir = repo_root / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))
        mock_run.return_value = _completed(returncode=0, stdout="")

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir))

        assert "5" in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_no_project_configured_warning_is_unaffected(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        """The env-var-fallback note only applies once a Project number has
        been resolved; it must not appear on (nor alter) the pre-existing
        "no project configured" warning (Requirement 4) when neither the
        file nor the env var is set."""
        from butler_core.projects import sync_on_pr_open

        repo_root = tmp_path
        (repo_root / ".git").mkdir()
        tasks_dir = repo_root / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))

        result = sync_on_pr_open(task, env={}, tasks_dir=str(tasks_dir))

        assert result.success is False
        assert "Note:" not in result.message


class TestButlerProjectFileEmitsNoNote:
    """Scenario: Resolution via repo-local file emits no such note."""

    @patch("butler_core.projects.subprocess.run")
    def test_open_stage_success_message_has_no_note_when_file_present(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_open

        repo_root = tmp_path
        (repo_root / ".git").mkdir()
        (repo_root / ".butler-project").write_text("7\n")
        tasks_dir = repo_root / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))
        mock_run.return_value = _completed(returncode=0, stdout="")

        result = sync_on_pr_open(task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir))

        assert result.success is True
        assert "Note:" not in result.message

    @patch("butler_core.projects.subprocess.run")
    def test_merge_stage_success_message_has_no_note_when_file_present(
        self, mock_run: MagicMock, tmp_path
    ) -> None:
        from butler_core.projects import sync_on_pr_merge

        repo_root = tmp_path
        (repo_root / ".git").mkdir()
        (repo_root / ".butler-project").write_text("7\n")
        tasks_dir = repo_root / "docs" / "tasks"
        task = create_task("My feature", "desc", tasks_dir=str(tasks_dir))
        mock_run.side_effect = _merge_stage_success_sequence()

        result = sync_on_pr_merge(
            task, env={"BUTLER_GITHUB_PROJECT": "5"}, tasks_dir=str(tasks_dir)
        )

        assert "Note:" not in result.message
