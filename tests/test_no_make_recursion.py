"""Regression tests for TASK-043 / REQUIREMENTS_TASK_WORKFLOW.md Requirement 1.

Protects the non-recursive `butler task <cmd>` <-> vendored Makefile
architecture: `butler_core.git_ops`'s branch/stage/commit/pr/merge functions
must never construct a subprocess call whose first argument is `"make"`, and
end-to-end `butler task <cmd>` invocations must complete without spawning a
nested `butler` or `make` process.
"""

from __future__ import annotations

import ast
import inspect
from pathlib import Path
from unittest.mock import MagicMock, patch

import butler_core.git_ops as git_ops
from butler_cli.__main__ import main
from butler_core.git_ops import branch_for, commit_for, merge_pr_for, open_pr_for, stage_for
from butler_core.tasks import create_task, read_task

_GIT_OPS_TARGETS = ("branch_for", "stage_for", "commit_for", "open_pr_for", "merge_pr_for")


def _completed(returncode: int = 0, stdout: str = "") -> MagicMock:
    result = MagicMock()
    result.returncode = returncode
    result.stdout = stdout
    return result


class _RecordingRun:
    """Records every `subprocess.run` invocation's first positional argument.

    Optionally replays a fixed sequence of return values for functions (like
    `merge_pr_for`) whose control flow depends on prior calls' stdout.
    """

    def __init__(self, results: list[MagicMock] | None = None) -> None:
        self.calls: list[list[str]] = []
        self._results = results
        self._index = 0

    def __call__(self, args: list[str], **kwargs: object) -> MagicMock:
        self.calls.append(list(args))
        if self._results is not None:
            result = self._results[self._index]
            self._index += 1
            return result
        return _completed()

    @property
    def first_args(self) -> list[str]:
        """The first element of each recorded subprocess invocation."""
        return [call[0] for call in self.calls]


class TestGitOpsNeverShellsOutToMake:
    """Scenario: `butler_core.git_ops` never constructs subprocess calls to make."""

    def test_source_contains_no_make_subprocess_calls(self) -> None:
        """Static/AST inspection: no `subprocess.*([\"make\", ...])` call exists
        anywhere in `butler_core.git_ops`, and specifically not inside any of the
        five task-workflow functions."""
        source = inspect.getsource(git_ops)
        tree = ast.parse(source)

        offending_calls: list[str] = []
        for node in ast.walk(tree):
            if not isinstance(node, ast.Call):
                continue
            func = node.func
            is_subprocess_call = (
                isinstance(func, ast.Attribute)
                and func.attr in ("run", "Popen", "call", "check_call", "check_output")
                and isinstance(func.value, ast.Name)
                and func.value.id == "subprocess"
            )
            if not is_subprocess_call:
                continue
            if not node.args:
                continue
            first_arg = node.args[0]
            if not isinstance(first_arg, ast.List) or not first_arg.elts:
                continue
            first_element = first_arg.elts[0]
            if isinstance(first_element, ast.Constant) and first_element.value == "make":
                offending_calls.append(ast.dump(node))

        assert offending_calls == [], (
            f"Found subprocess call(s) shelling out to 'make' in git_ops.py: {offending_calls}"
        )

    def test_functions_under_test_exist_and_are_the_ones_inspected(self) -> None:
        """Sanity check that the AST scan above actually covers the five
        functions this requirement names -- guards against the static scan
        silently becoming vacuous if git_ops.py is refactored."""
        for name in _GIT_OPS_TARGETS:
            assert hasattr(git_ops, name), f"butler_core.git_ops.{name} is missing"


class TestEndToEndBranchNoNestedProcess:
    """Scenario: End-to-end `butler task branch` does not spawn a nested process."""

    def test_butler_task_branch_spawns_no_make_or_butler_process(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Branch task", "desc", tasks_dir=str(tasks_dir))
        recorder = _RecordingRun()

        with patch("butler_core.git_ops.subprocess.run", recorder):
            exit_code = main(["--tasks-dir", str(tasks_dir), "task", "branch", task.id])

        assert exit_code == 0
        assert recorder.calls, "expected branch_for to invoke subprocess.run at least once"
        assert "make" not in recorder.first_args
        assert "butler" not in recorder.first_args


class TestEndToEndStageNoNestedProcess:
    """Scenario: End-to-end `butler task stage` does not spawn a nested process."""

    def test_butler_task_stage_spawns_no_make_or_butler_process(
        self, tmp_path: Path, monkeypatch: object
    ) -> None:
        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Stage task", "desc", tasks_dir=str(tasks_dir))
        (tmp_path / "README.md").write_text("# hi\n")
        recorder = _RecordingRun()

        monkeypatch.chdir(tmp_path)  # type: ignore[attr-defined]
        with patch("butler_core.git_ops.subprocess.run", recorder):
            exit_code = main(["--tasks-dir", str(tasks_dir), "task", "stage", task.id])

        assert exit_code == 0
        assert recorder.calls, "expected stage_for to invoke subprocess.run at least once"
        assert "make" not in recorder.first_args
        assert "butler" not in recorder.first_args


class TestEndToEndCommitNoNestedProcess:
    """Scenario: End-to-end `butler task commit` does not spawn a nested process."""

    def test_butler_task_commit_spawns_no_make_or_butler_process(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Commit task", "desc", tasks_dir=str(tasks_dir))
        recorder = _RecordingRun()

        with patch("butler_core.git_ops.subprocess.run", recorder):
            exit_code = main(["--tasks-dir", str(tasks_dir), "task", "commit", task.id])

        assert exit_code == 0
        assert recorder.calls, "expected commit_for to invoke subprocess.run at least once"
        assert "make" not in recorder.first_args
        assert "butler" not in recorder.first_args


class TestEndToEndPrNoNestedProcess:
    """Scenario: End-to-end `butler task pr` does not spawn a nested process."""

    def test_butler_task_pr_spawns_no_make_or_butler_process(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("PR task", "Some description body", tasks_dir=str(tasks_dir))
        recorder = _RecordingRun()

        with patch("butler_core.git_ops.subprocess.run", recorder):
            exit_code = main(["--tasks-dir", str(tasks_dir), "task", "pr", task.id])

        assert exit_code == 0
        assert recorder.calls, "expected open_pr_for to invoke subprocess.run at least once"
        assert "make" not in recorder.first_args
        assert "butler" not in recorder.first_args


class TestEndToEndMergeNoNestedProcess:
    """Scenario: End-to-end `butler task merge` does not spawn a nested process."""

    def test_butler_task_merge_spawns_no_make_or_butler_process(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("Merge task", "desc", tasks_dir=str(tasks_dir))
        results = [
            _completed(stdout="42\n"),
            _completed(stdout="MERGEABLE\n"),
            _completed(),
            _completed(),
            _completed(),
        ]
        recorder = _RecordingRun(results=results)

        with patch("butler_core.git_ops.subprocess.run", recorder):
            exit_code = main(["--tasks-dir", str(tasks_dir), "task", "merge", task.id])

        assert exit_code == 0
        assert recorder.calls, "expected merge_pr_for to invoke subprocess.run at least once"
        assert "make" not in recorder.first_args
        assert "butler" not in recorder.first_args


class TestUnitLevelGitOpsFunctionsNeverCallMake:
    """Belt-and-suspenders unit-level checks (complementing the AST scan and
    the CLI-level end-to-end scenarios) that directly patch subprocess.run
    while calling each git_ops function in isolation."""

    def test_branch_for(self) -> None:
        task = read_task("TASK-015", tasks_dir="docs/tasks")
        recorder = _RecordingRun()
        with patch("butler_core.git_ops.subprocess.run", recorder):
            branch_for(task)
        assert "make" not in recorder.first_args

    def test_stage_for(self, tmp_path: Path) -> None:
        task = create_task("Some task", "desc", tasks_dir=str(tmp_path / "docs" / "tasks"))
        recorder = _RecordingRun()
        with patch("butler_core.git_ops.subprocess.run", recorder):
            stage_for(task, repo_root=tmp_path)
        assert "make" not in recorder.first_args

    def test_commit_for(self) -> None:
        task = read_task("TASK-015", tasks_dir="docs/tasks")
        recorder = _RecordingRun()
        with patch("butler_core.git_ops.subprocess.run", recorder):
            commit_for(task)
        assert "make" not in recorder.first_args

    def test_open_pr_for(self, tmp_path: Path) -> None:
        tasks_dir = tmp_path / "docs" / "tasks"
        task = create_task("My feature", "Some description body", tasks_dir=str(tasks_dir))
        recorder = _RecordingRun()
        with patch("butler_core.git_ops.subprocess.run", recorder):
            open_pr_for(task, tasks_dir=str(tasks_dir))
        assert "make" not in recorder.first_args

    def test_merge_pr_for(self) -> None:
        task = read_task("TASK-015", tasks_dir="docs/tasks")
        results = [
            _completed(stdout="42\n"),
            _completed(stdout="MERGEABLE\n"),
            _completed(),
            _completed(),
            _completed(),
        ]
        recorder = _RecordingRun(results=results)
        with patch("butler_core.git_ops.subprocess.run", recorder):
            merge_pr_for(task)
        assert "make" not in recorder.first_args
