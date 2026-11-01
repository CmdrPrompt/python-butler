"""Acceptance tests for TASK-096 / REQUIREMENTS_TASK_WORKFLOW.md Requirement 18.

Each `*-current-task` wrapper target and its corresponding `*-task` leaf
target must refuse to run -- its recipe exits 17 (which GNU Make reports as
`Error 17` and then exits nonzero itself, since Make never forwards a
failed recipe command's exact exit status as its own -- see
`TestRefusalOnReentry`'s docstring), with an exact error message on stderr
and no `$(MAKE)`/`butler` invocation -- when that family's sentinel
environment variable is already set (indicating the same family is already
running somewhere in this process tree), while remaining completely
unaffected in the normal (non-recursive) case.

These tests shell out to real `make -f <repo Makefile> <target>` in a
scratch directory, with a fake `butler` script placed first on `PATH` that
records its argv and each sentinel env var's value (as it actually saw
them) to a log file instead of doing anything real. This is the only way
to observe the actual recursion-guard behavior (exit codes, stderr text,
sentinel export, process-tree effects), unlike the text-parsing style used
by `tests/test_projects_makefile_integration.py` for simpler
recipe-ordering checks.

Every subprocess call carries a timeout so a regression (e.g. an
accidental infinite recursion reintroduced into the guard itself) can
never hang the suite.
"""

from __future__ import annotations

import os
import stat
import subprocess
from pathlib import Path

import pytest

_REPO_ROOT = Path(__file__).resolve().parent.parent
_MAKEFILE = _REPO_ROOT / "Makefile"
_TIMEOUT = 15

_FAKE_BUTLER_SCRIPT = """#!/bin/sh
printf "STAGE=%s COMMIT=%s PR=%s MERGE=%s ARGV=%s\n" \
    "$BUTLER_STAGE_GUARD" "$BUTLER_COMMIT_GUARD" "$BUTLER_PR_GUARD" "$BUTLER_MERGE_GUARD" "$*" \
    >> "$BUTLER_LOG"
exit 0
"""

# Maps each sentinel env var to the short field name it is logged under by
# `_FAKE_BUTLER_SCRIPT`/`_REENTRANT_BUTLER_SCRIPT` above.
_SENTINEL_LOG_KEYS = {
    "BUTLER_STAGE_GUARD": "STAGE",
    "BUTLER_COMMIT_GUARD": "COMMIT",
    "BUTLER_PR_GUARD": "PR",
    "BUTLER_MERGE_GUARD": "MERGE",
}

# Simulates the pre-TASK-086 stale `butler` binary from the 2026-09-20
# incident: when invoked with `task stage`, it re-executes the literal
# Stage field text as a shell command, which re-invokes `make
# stage-current-task` -- reproducing the runaway recursion the guard must
# stop. Uses the default Makefile lookup (no `-f`) since it inherits the
# recipe's cwd, which is a repo containing its own copy of the Makefile
# under test -- exactly like a real consumer project's `.butler/Makefile`.
_REENTRANT_BUTLER_SCRIPT = """#!/bin/sh
printf "STAGE=%s COMMIT=%s PR=%s MERGE=%s ARGV=%s\n" \
    "$BUTLER_STAGE_GUARD" "$BUTLER_COMMIT_GUARD" "$BUTLER_PR_GUARD" "$BUTLER_MERGE_GUARD" "$*" \
    >> "$BUTLER_LOG"
case "$*" in
    *"task stage"*)
        make stage-current-task
        exit $?
        ;;
esac
exit 0
"""

_SENTINEL_ERROR_MESSAGES = {
    "BUTLER_STAGE_GUARD": (
        "Error: stage-current-task/stage-task is already running in this "
        "process tree; refusing to recurse."
    ),
    "BUTLER_COMMIT_GUARD": (
        "Error: commit-current-task/commit-task is already running in this "
        "process tree; refusing to recurse."
    ),
    "BUTLER_PR_GUARD": (
        "Error: pr-current-task/pr-task is already running in this process "
        "tree; refusing to recurse."
    ),
    "BUTLER_MERGE_GUARD": (
        "Error: merge-current-task/merge-pr is already running in this "
        "process tree; refusing to recurse."
    ),
}

_ALL_SENTINELS = tuple(_SENTINEL_ERROR_MESSAGES)


def _write_executable(path: Path, script: str) -> None:
    path.write_text(script)
    mode = path.stat().st_mode
    path.chmod(mode | stat.S_IEXEC | stat.S_IXGRP | stat.S_IXOTH)


def _fake_butler_bin(tmp_path: Path, script: str = _FAKE_BUTLER_SCRIPT) -> Path:
    bin_dir = tmp_path / "fakebin"
    bin_dir.mkdir(exist_ok=True)
    _write_executable(bin_dir / "butler", script)
    return bin_dir


def _base_env(tmp_path: Path, bin_dir: Path, butler_log: Path) -> dict[str, str]:
    env = dict(os.environ)
    for sentinel in _ALL_SENTINELS:
        env.pop(sentinel, None)
    env["PATH"] = f"{bin_dir}{os.pathsep}{env.get('PATH', '')}"
    env["BUTLER_LOG"] = str(butler_log)
    env["MAKEFILE_UNDER_TEST"] = str(_MAKEFILE)
    return env


def _run_make(cwd: Path, args: list[str], env: dict[str, str]) -> subprocess.CompletedProcess[str]:
    return subprocess.run(
        ["make", "-f", str(_MAKEFILE), *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
    )


def _run_make_default(
    cwd: Path, args: list[str], env: dict[str, str]
) -> subprocess.CompletedProcess[str]:
    """Runs `make` with the default Makefile lookup (no `-f`), so a
    wrapper target's `$(MAKE) <leaf>` child process -- which does not
    inherit a `-f` flag -- finds the same Makefile via `cwd`, exactly as
    it would in a real repo/consumer project."""
    return subprocess.run(
        ["make", *args],
        cwd=cwd,
        env=env,
        capture_output=True,
        text=True,
        timeout=_TIMEOUT,
    )


def _init_task_branch_repo(tmp_path: Path, num: str) -> Path:
    """A throwaway git repo on a `task/<num>-...` branch, with its own copy
    of the Makefile under test in its root, so `git branch --show-current`
    resolves the way a wrapper target expects and a wrapper's nested
    `$(MAKE) <leaf>` (no `-f` flag) finds the right Makefile via `cwd`."""
    repo = tmp_path / "repo"
    repo.mkdir()

    def run(*args: str) -> subprocess.CompletedProcess[str]:
        return subprocess.run(
            args, cwd=repo, check=True, timeout=_TIMEOUT, capture_output=True, text=True
        )

    run("git", "init", "-q")
    run("git", "config", "user.email", "test@example.com")
    run("git", "config", "user.name", "Test")
    (repo / "Makefile").write_text(_MAKEFILE.read_text())
    (repo / "README.md").write_text("hi\n")
    run("git", "add", "Makefile", "README.md")
    run("git", "commit", "-q", "-m", "init")
    run("git", "checkout", "-q", "-b", f"task/{num}-fixture-branch")
    return repo


def _log_lines(butler_log: Path) -> list[str]:
    if not butler_log.exists():
        return []
    return [line for line in butler_log.read_text().splitlines() if line.strip()]


def _field(line: str, name: str) -> str:
    """Extract the value of a `NAME=value` field logged by the fake butler
    script (e.g. `_field(line, "STAGE")` reads `BUTLER_STAGE_GUARD`'s value
    as butler itself saw it in its environment)."""
    marker = f"{name}="
    start = line.index(marker) + len(marker)
    return line[start:].split(" ", 1)[0]


def _assert_sentinel_exported_to_butler(line: str, sentinel: str) -> None:
    key = _SENTINEL_LOG_KEYS[sentinel]
    assert _field(line, key) == "1", (
        f"expected butler to see {sentinel}=1 in its environment, got line: {line!r}"
    )


class TestRefusalOnReentry:
    """Scenario Outline 1: every guarded target refuses immediately, with
    the exact per-family message, when its sentinel is already set -- for
    both the wrapper and the leaf target of every family. Applies equally
    to the 4 wrapper rows and the 4 leaf rows below.

    Note on exit code 17: the guard's own recipe uses a literal `exit 17`,
    matching the Requirement 18 mechanism exactly. But GNU Make never
    forwards a failed recipe command's exact exit status as `make`'s own
    process exit status -- it always reports 2 to its caller (verified
    empirically; this is documented GNU Make behavior, not a bug here),
    while still printing the underlying code in its own diagnostic (e.g.
    `make: *** [stage-task] Error 17`). So the top-level `make` process
    invoked directly by a human/script exits nonzero (never literally 17),
    while `17` remains visible in the combined output via that
    diagnostic -- which is what these tests assert."""

    @pytest.mark.parametrize(
        ("sentinel", "args"),
        [
            ("BUTLER_STAGE_GUARD", ["stage-current-task"]),
            ("BUTLER_STAGE_GUARD", ["stage-task", "f=TASK-001"]),
            ("BUTLER_COMMIT_GUARD", ["commit-current-task"]),
            ("BUTLER_COMMIT_GUARD", ["commit-task", "f=TASK-001"]),
            ("BUTLER_PR_GUARD", ["pr-current-task"]),
            ("BUTLER_PR_GUARD", ["pr-task", "f=TASK-001"]),
            ("BUTLER_MERGE_GUARD", ["merge-current-task"]),
            ("BUTLER_MERGE_GUARD", ["merge-pr", "f=TASK-001"]),
        ],
    )
    def test_refuses_with_error_17_and_exact_message_on_stderr(
        self, tmp_path: Path, sentinel: str, args: list[str]
    ) -> None:
        bin_dir = _fake_butler_bin(tmp_path)
        butler_log = tmp_path / "butler.log"
        env = _base_env(tmp_path, bin_dir, butler_log)
        env[sentinel] = "1"

        result = _run_make(tmp_path, args, env)

        assert result.returncode != 0, (result.stdout, result.stderr)
        assert "Error 17" in result.stderr, result.stderr
        assert _SENTINEL_ERROR_MESSAGES[sentinel] in result.stderr, result.stderr
        # For the wrapper rows specifically: if the wrapper had wrongly run
        # `$(MAKE) <leaf>` before refusing (instead of refusing first), the
        # leaf would see the same set sentinel and print the identical
        # message a second time. Asserting exactly one occurrence (for
        # every row, wrapper or leaf) catches that regression.
        message = _SENTINEL_ERROR_MESSAGES[sentinel]
        assert result.stderr.count(message) == 1, (
            f"expected the refusal message exactly once (no $(MAKE)/butler "
            f"invocation reaching a second guard check), got: {result.stderr!r}"
        )
        assert _log_lines(butler_log) == [], "butler must not be invoked on refusal"


class TestNormalDirectLeafInvocation:
    """Scenario Outline 2: with the sentinel unset, a leaf target invoked
    directly checks the sentinel, finds it unset, exports it, and runs its
    butler command(s) normally."""

    @pytest.mark.parametrize(
        ("sentinel", "args"),
        [
            ("BUTLER_STAGE_GUARD", ["stage-task", "f=TASK-001"]),
            ("BUTLER_COMMIT_GUARD", ["commit-task", "f=TASK-001"]),
            ("BUTLER_PR_GUARD", ["pr-task", "f=TASK-001"]),
            ("BUTLER_MERGE_GUARD", ["merge-pr", "f=TASK-001"]),
        ],
    )
    def test_leaf_runs_butler_normally_when_sentinel_unset(
        self, tmp_path: Path, sentinel: str, args: list[str]
    ) -> None:
        bin_dir = _fake_butler_bin(tmp_path)
        butler_log = tmp_path / "butler.log"
        env = _base_env(tmp_path, bin_dir, butler_log)

        result = _run_make(tmp_path, args, env)

        assert result.returncode == 0, (result.stdout, result.stderr)
        lines = _log_lines(butler_log)
        assert lines, "expected butler to be invoked at least once"
        for line in lines:
            _assert_sentinel_exported_to_butler(line, sentinel)


class TestNormalWrapperInvocation:
    """Scenario Outline 3: with the sentinel unset, a wrapper checks it,
    does not export it, invokes `$(MAKE) <leaf>`, and the leaf exports the
    sentinel and completes the flow normally (the one legitimate level of
    nesting)."""

    @pytest.mark.parametrize(
        ("sentinel", "wrapper_target"),
        [
            ("BUTLER_STAGE_GUARD", "stage-current-task"),
            ("BUTLER_COMMIT_GUARD", "commit-current-task"),
            ("BUTLER_PR_GUARD", "pr-current-task"),
            ("BUTLER_MERGE_GUARD", "merge-current-task"),
        ],
    )
    def test_wrapper_delegates_to_leaf_which_runs_butler(
        self, tmp_path: Path, sentinel: str, wrapper_target: str
    ) -> None:
        repo = _init_task_branch_repo(tmp_path, num="001")
        bin_dir = _fake_butler_bin(tmp_path)
        butler_log = tmp_path / "butler.log"
        env = _base_env(tmp_path, bin_dir, butler_log)

        result = _run_make_default(repo, [wrapper_target], env)

        # The wrapper must not itself export the sentinel: this is verified
        # implicitly by the flow succeeding at all. If the wrapper had
        # exported it before invoking `$(MAKE) <leaf>`, the leaf would
        # inherit it, its own guard would refuse (Error 17), and
        # `returncode` below would be nonzero instead of 0.
        assert result.returncode == 0, (result.stdout, result.stderr)
        lines = _log_lines(butler_log)
        assert lines, "expected the leaf to invoke butler at least once"
        for line in lines:
            _assert_sentinel_exported_to_butler(line, sentinel)


class TestSequentialPrTaskButlerCalls:
    """Scenario 4: pr-task's three sequential butler calls within one
    recipe are unaffected by the guard -- they all run, in order."""

    def test_all_three_calls_run_in_order(self, tmp_path: Path) -> None:
        bin_dir = _fake_butler_bin(tmp_path)
        butler_log = tmp_path / "butler.log"
        env = _base_env(tmp_path, bin_dir, butler_log)

        result = _run_make(tmp_path, ["pr-task", "f=TASK-001"], env)

        assert result.returncode == 0, (result.stdout, result.stderr)
        lines = _log_lines(butler_log)
        assert len(lines) == 3, lines
        assert "task branch" in lines[0], lines
        assert "task pr" in lines[1], lines
        assert "task sync-project" in lines[2], lines
        for line in lines:
            _assert_sentinel_exported_to_butler(line, "BUTLER_PR_GUARD")


class TestSequentialMergePrButlerCalls:
    """Scenario 5: merge-pr's two sequential butler calls within one recipe
    are unaffected by the guard -- both run, in order."""

    def test_both_calls_run_in_order(self, tmp_path: Path) -> None:
        bin_dir = _fake_butler_bin(tmp_path)
        butler_log = tmp_path / "butler.log"
        env = _base_env(tmp_path, bin_dir, butler_log)

        result = _run_make(tmp_path, ["merge-pr", "f=TASK-001"], env)

        assert result.returncode == 0, (result.stdout, result.stderr)
        lines = _log_lines(butler_log)
        assert len(lines) == 2, lines
        assert "task merge" in lines[0], lines
        assert "task sync-project" in lines[1], lines
        for line in lines:
            _assert_sentinel_exported_to_butler(line, "BUTLER_MERGE_GUARD")


class TestFamilyIndependence:
    """Scenario 6: one family's sentinel does not block a different
    family's target."""

    def test_stage_guard_set_does_not_block_commit_task(self, tmp_path: Path) -> None:
        bin_dir = _fake_butler_bin(tmp_path)
        butler_log = tmp_path / "butler.log"
        env = _base_env(tmp_path, bin_dir, butler_log)
        env["BUTLER_STAGE_GUARD"] = "1"

        result = _run_make(tmp_path, ["commit-task", "f=TASK-001"], env)

        assert result.returncode == 0, (result.stdout, result.stderr)
        assert _log_lines(butler_log), "expected commit-task to invoke butler normally"


class TestReentrantStaleButlerIsCaught:
    """Scenario 7: a stale butler binary that re-executes `make
    stage-current-task` as a command is caught by the inherited sentinel --
    its recipe exits 17 (reported by the inner `make` as `Error 17`) and
    prints the exact message, visible in the outer invocation's combined
    output -- and the outer invocation exits non-zero without spawning
    further nested processes."""

    def test_reentrant_stale_butler_is_refused_by_inherited_sentinel(self, tmp_path: Path) -> None:
        repo = _init_task_branch_repo(tmp_path, num="002")
        bin_dir = _fake_butler_bin(tmp_path, script=_REENTRANT_BUTLER_SCRIPT)
        butler_log = tmp_path / "butler.log"
        env = _base_env(tmp_path, bin_dir, butler_log)

        result = _run_make_default(repo, ["stage-current-task"], env)

        assert result.returncode != 0, (result.stdout, result.stderr)
        combined = result.stdout + result.stderr
        assert _SENTINEL_ERROR_MESSAGES["BUTLER_STAGE_GUARD"] in combined, combined
        # Bounded process count: the fake butler is invoked exactly once
        # (the re-entrant `make stage-current-task` it spawns refuses
        # before ever reaching butler again).
        lines = _log_lines(butler_log)
        assert len(lines) == 1, lines
