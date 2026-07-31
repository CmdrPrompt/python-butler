"""CLI-level tests for the GitHub Projects sync entry point (TASK-056).

Covers the "exit code is 0" clause of the Gherkin scenarios for creating a
Projects item on PR open and updating it to Done on merge, and the
best-effort guarantee that a sync failure never causes the encompassing
`butler task pr`/`butler task merge` flow driven by `pr-task`/`merge-pr` to
fail.
"""

from __future__ import annotations

from pathlib import Path
from unittest.mock import MagicMock, patch

from butler_cli.__main__ import main
from butler_core.tasks import create_task


class TestSyncProjectCliOnPrOpen:
    """Scenario: Sync creates GitHub Projects item on PR open with correct
    metadata (exit code clause)."""

    @patch("butler_core.projects.subprocess.run")
    def test_sync_project_open_stage_exits_zero_on_success(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        task = create_task("Some feature", "desc", tasks_dir=str(tmp_path))
        mock_run.return_value = MagicMock(returncode=0, stdout="https://github.com/org/repo/pull/1")

        exit_code = main(
            [
                "--tasks-dir",
                str(tmp_path),
                "task",
                "sync-project",
                task.id,
                "--stage",
                "open",
            ]
        )

        assert exit_code == 0


class TestSyncProjectCliOnPrMerge:
    """Scenario: Sync updates GitHub Projects item status on PR merge (exit
    code clause)."""

    @patch("butler_core.projects.subprocess.run")
    def test_sync_project_merge_stage_exits_zero_on_success(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        task = create_task("Some feature", "desc", tasks_dir=str(tmp_path))
        mock_run.return_value = MagicMock(returncode=0, stdout="https://github.com/org/repo/pull/1")

        exit_code = main(
            [
                "--tasks-dir",
                str(tmp_path),
                "task",
                "sync-project",
                task.id,
                "--stage",
                "merge",
            ]
        )

        assert exit_code == 0


class TestSyncProjectCliBestEffort:
    """Scenario: PR creation succeeds even if Projects sync fails, and
    Scenario: PR merge succeeds even if Projects sync fails -- verified here
    at the dedicated sync entry-point's own CLI boundary: a sync failure
    (no `gh`, no project configured, etc.) must never surface as a non-zero
    exit from the sync step itself, since the Makefile wires this step in
    after PR creation/merge without gating on its result."""

    @patch("butler_core.projects.subprocess.run")
    def test_sync_project_open_stage_exits_zero_when_gh_is_not_installed(
        self, mock_run: MagicMock, tmp_path: Path
    ) -> None:
        task = create_task("Some feature", "desc", tasks_dir=str(tmp_path))
        mock_run.side_effect = FileNotFoundError("gh")

        exit_code = main(
            [
                "--tasks-dir",
                str(tmp_path),
                "task",
                "sync-project",
                task.id,
                "--stage",
                "open",
            ]
        )

        assert exit_code == 0

    @patch("butler_core.projects.subprocess.run")
    def test_sync_project_merge_stage_exits_zero_when_no_project_configured(
        self, mock_run: MagicMock, tmp_path: Path, monkeypatch
    ) -> None:
        """No project configured must still exit 0. Since TASK-057, the sync
        may issue a read-only lookup call (e.g. `gh repo view` or
        `git remote get-url origin`) to build a copy-pasteable setup
        suggestion, so this only asserts no mutating `gh project` write call
        (`item-create`/`item-edit`) is attempted."""
        task = create_task("Some feature", "desc", tasks_dir=str(tmp_path))
        monkeypatch.delenv("BUTLER_GITHUB_PROJECT", raising=False)
        mock_run.return_value = MagicMock(returncode=1, stdout="", stderr="not a repo")

        exit_code = main(
            [
                "--tasks-dir",
                str(tmp_path),
                "task",
                "sync-project",
                task.id,
                "--stage",
                "merge",
            ]
        )

        assert exit_code == 0
        mutating_calls = [
            call
            for call in mock_run.call_args_list
            if "item-create" in call.args[0] or "item-edit" in call.args[0]
        ]
        assert mutating_calls == []
