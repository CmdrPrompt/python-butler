"""Tests asserting the GitHub Projects sync entry point is wired into the
`pr-task`/`pr-current-task` and `merge-pr`/`merge-current-task` Makefile
targets as an added, non-blocking step (TASK-056).

Follows the text-parsing convention established by
test_makefile_cli_flag_drift.py rather than actually shelling out to `make`,
so these tests stay hermetic and fast.
"""

from __future__ import annotations

import re
from pathlib import Path

_REPO_ROOT = Path(__file__).resolve().parent.parent


def _target_recipe(makefile_text: str, target: str) -> list[str]:
    """Return the recipe lines (tab-indented lines) belonging to `target:`,
    up to the next unindented line."""
    lines = makefile_text.splitlines()
    recipe: list[str] = []
    capturing = False
    target_re = re.compile(rf"^{re.escape(target)}\s*:")
    for line in lines:
        if target_re.match(line):
            capturing = True
            continue
        if capturing:
            if line.startswith("\t"):
                recipe.append(line)
            elif line.strip() == "":
                continue
            else:
                break
    return recipe


class TestSyncInvokedAfterPrOpened:
    """Scenario: Sync is invoked as an added step in pr-task / pr-current-task."""

    def test_pr_task_target_invokes_sync_project_after_opening_the_pr(self) -> None:
        makefile_text = (_REPO_ROOT / "Makefile").read_text()
        recipe = _target_recipe(makefile_text, "pr-task")

        pr_line_index = next(
            i for i, line in enumerate(recipe) if "task pr $(f)" in line or "task pr " in line
        )
        sync_lines = [line for line in recipe if "sync-project" in line or "sync_project" in line]

        assert sync_lines, (
            f"expected pr-task recipe to include a GitHub Projects sync step, got: {recipe}"
        )
        sync_line_index = recipe.index(sync_lines[0])
        assert sync_line_index > pr_line_index, (
            f"the sync step must run after the PR is opened, got recipe order: {recipe}"
        )

    def test_pr_task_sync_step_does_not_gate_target_success_on_sync_failure(self) -> None:
        """Best-effort: a failing sync step must not abort the `pr-task`
        target. Make aborts a recipe when a command's exit status is
        nonzero unless the line is prefixed with `-` or the failure is
        otherwise suppressed (e.g. `|| true`)."""
        makefile_text = (_REPO_ROOT / "Makefile").read_text()
        recipe = _target_recipe(makefile_text, "pr-task")
        sync_lines = [line for line in recipe if "sync-project" in line or "sync_project" in line]

        assert sync_lines, (
            f"expected pr-task recipe to include a GitHub Projects sync step, got: {recipe}"
        )
        sync_line = sync_lines[0].strip().lstrip("@")
        detail = f"expected a non-blocking sync step ('-' or '|| true'), got: {sync_line!r}"
        assert sync_line.startswith("-") or "|| true" in sync_line, detail


class TestSyncInvokedAfterBranchCreated:
    """Scenario: Sync is invoked as an added step in branch-task, right
    after the task branch is created/switched to (TASK-065)."""

    def test_branch_task_target_invokes_sync_project_after_creating_the_branch(self) -> None:
        makefile_text = (_REPO_ROOT / "Makefile").read_text()
        recipe = _target_recipe(makefile_text, "branch-task")

        branch_line_index = next(
            i
            for i, line in enumerate(recipe)
            if "task branch $(f)" in line or "task branch " in line
        )
        sync_lines = [line for line in recipe if "sync-project" in line or "sync_project" in line]

        assert sync_lines, (
            f"expected branch-task recipe to include a GitHub Projects sync step, got: {recipe}"
        )
        sync_line_index = recipe.index(sync_lines[0])
        assert sync_line_index > branch_line_index, (
            f"the sync step must run after the branch is created, got recipe order: {recipe}"
        )
        assert "--stage start" in sync_lines[0], (
            f"expected the branch-task sync step to use --stage start, got: {sync_lines[0]!r}"
        )

    def test_branch_task_sync_step_does_not_gate_target_success_on_sync_failure(self) -> None:
        makefile_text = (_REPO_ROOT / "Makefile").read_text()
        recipe = _target_recipe(makefile_text, "branch-task")
        sync_lines = [line for line in recipe if "sync-project" in line or "sync_project" in line]

        assert sync_lines, (
            f"expected branch-task recipe to include a GitHub Projects sync step, got: {recipe}"
        )
        sync_line = sync_lines[0].strip().lstrip("@")
        detail = f"expected a non-blocking sync step ('-' or '|| true'), got: {sync_line!r}"
        assert sync_line.startswith("-") or "|| true" in sync_line, detail


class TestSyncInvokedAfterPrMerged:
    """Scenario: Sync is invoked as an added step in merge-pr / merge-current-task."""

    def test_merge_pr_target_invokes_sync_project_after_merging_the_pr(self) -> None:
        makefile_text = (_REPO_ROOT / "Makefile").read_text()
        recipe = _target_recipe(makefile_text, "merge-pr")

        merge_line_index = next(
            i for i, line in enumerate(recipe) if "task merge $(f)" in line or "task merge " in line
        )
        sync_lines = [line for line in recipe if "sync-project" in line or "sync_project" in line]

        assert sync_lines, (
            f"expected merge-pr recipe to include a GitHub Projects sync step, got: {recipe}"
        )
        sync_line_index = recipe.index(sync_lines[0])
        assert sync_line_index > merge_line_index, (
            f"the sync step must run after the PR is merged, got recipe order: {recipe}"
        )

    def test_merge_pr_sync_step_does_not_gate_target_success_on_sync_failure(self) -> None:
        makefile_text = (_REPO_ROOT / "Makefile").read_text()
        recipe = _target_recipe(makefile_text, "merge-pr")
        sync_lines = [line for line in recipe if "sync-project" in line or "sync_project" in line]

        assert sync_lines, (
            f"expected merge-pr recipe to include a GitHub Projects sync step, got: {recipe}"
        )
        sync_line = sync_lines[0].strip().lstrip("@")
        detail = f"expected a non-blocking sync step ('-' or '|| true'), got: {sync_line!r}"
        assert sync_line.startswith("-") or "|| true" in sync_line, detail


class TestStandaloneDraftSyncTarget:
    """Scenario: A standalone `make` target reaches `--stage draft`
    (TASK-069, extending Requirement 6)."""

    def test_target_depends_on_check_butler(self) -> None:
        makefile_text = (_REPO_ROOT / "Makefile").read_text()
        target_line = next(
            line
            for line in makefile_text.splitlines()
            if re.match(r"^sync-project-draft\s*:", line)
        )
        assert "check-butler" in target_line, (
            f"expected sync-project-draft to depend on check-butler, got: {target_line!r}"
        )

    def test_target_invokes_the_draft_stage_via_the_f_argument(self) -> None:
        makefile_text = (_REPO_ROOT / "Makefile").read_text()
        recipe = _target_recipe(makefile_text, "sync-project-draft")
        sync_lines = [line for line in recipe if "task sync-project" in line]

        assert sync_lines, (
            f"expected sync-project-draft recipe to invoke sync-project, got: {recipe}"
        )
        assert "--stage draft" in sync_lines[0], (
            f"expected the sync-project-draft recipe to use --stage draft, got: {sync_lines[0]!r}"
        )
        assert "$(f)" in sync_lines[0], (
            f"expected the sync-project-draft recipe to use the f= argument, got: {sync_lines[0]!r}"
        )

    def test_target_does_not_call_back_into_make(self) -> None:
        """Non-recursion guard (TASK-043's invariant): the recipe must be a
        single direct `butler` call, never `$(MAKE)`/`make` calling back
        into the CLI target that could re-trigger this same step."""
        makefile_text = (_REPO_ROOT / "Makefile").read_text()
        recipe = _target_recipe(makefile_text, "sync-project-draft")
        for line in recipe:
            stripped = line.strip().lstrip("@").lstrip("-")
            assert "$(MAKE)" not in stripped and not stripped.startswith("make "), (
                f"sync-project-draft must not call back into make, got: {line!r}"
            )


class TestStandaloneBackfillSyncTarget:
    """Scenario: A standalone `make` target reaches `--stage backfill`
    (TASK-069, extending Requirement 8)."""

    def test_target_depends_on_check_butler(self) -> None:
        makefile_text = (_REPO_ROOT / "Makefile").read_text()
        target_line = next(
            line
            for line in makefile_text.splitlines()
            if re.match(r"^sync-project-backfill\s*:", line)
        )
        assert "check-butler" in target_line, (
            f"expected sync-project-backfill to depend on check-butler, got: {target_line!r}"
        )

    def test_target_invokes_the_backfill_stage_via_the_f_argument(self) -> None:
        makefile_text = (_REPO_ROOT / "Makefile").read_text()
        recipe = _target_recipe(makefile_text, "sync-project-backfill")
        sync_lines = [line for line in recipe if "task sync-project" in line]

        assert sync_lines, (
            f"expected sync-project-backfill recipe to invoke sync-project, got: {recipe}"
        )
        detail = (
            f"expected --stage backfill in the sync-project-backfill recipe, got: {sync_lines[0]!r}"
        )
        assert "--stage backfill" in sync_lines[0], detail
        detail = (
            f"expected the f= argument in the sync-project-backfill recipe, got: {sync_lines[0]!r}"
        )
        assert "$(f)" in sync_lines[0], detail

    def test_target_does_not_call_back_into_make(self) -> None:
        makefile_text = (_REPO_ROOT / "Makefile").read_text()
        recipe = _target_recipe(makefile_text, "sync-project-backfill")
        for line in recipe:
            stripped = line.strip().lstrip("@").lstrip("-")
            assert "$(MAKE)" not in stripped and not stripped.startswith("make "), (
                f"sync-project-backfill must not call back into make, got: {line!r}"
            )
