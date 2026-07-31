# TASK-061 Stay on the task branch after opening a PR

## Status
done

## Requirements
**Binding:** Requirement 7 (REQUIREMENTS_TASK_WORKFLOW.md)
**BDD mode:** BDD-ABSENT
**Depends on:** none
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer who usually merges a task's PR right after opening it, I want `make pr-current-task` to leave me on the task branch instead of switching to `main`, so that I can run `make merge-current-task` immediately without a manual `git checkout` first, and so the Projects draft/open sync (which needs the task file that only exists on the task branch) stops spuriously failing.

## Description
`open_pr_for` in `src/butler_core/git_ops.py` currently ends with `git
checkout main` right after `gh pr create`. This was observed three times in
one session (TASK-058, TASK-059, TASK-060): the following `sync-project
--stage open`/`--stage draft` step fails with "No task file found" because
it now runs against `main`, where the task file doesn't exist yet, and
merging the same task requires a manual `git checkout task/<NNN>-...`
first.

This task:
1. Removes the trailing `git checkout main` from `open_pr_for`, so the
   working tree stays on the task branch after the PR is created.
2. Changes `branch_for` so that when it creates a **new** branch (the
   branch does not already exist locally), it fetches and bases the new
   branch on `origin/main` instead of on whatever branch is currently
   checked out — closing the risk that a new task branch accidentally
   forks off a leftover, already-merged task branch now that `open_pr_for`
   no longer returns to `main` automatically. Switching to an **existing**
   branch is unchanged.

`merge_pr_for` needs no change: it already resolves the target branch from
the task object (`gh pr list --head <branch>`), not from the current
working-tree branch, and already ends with `git checkout main` + `git
pull`.

**Implementation location:** `src/butler_core/git_ops.py` (`open_pr_for`,
`branch_for`), `tests/test_git_ops.py`.

## Branch
**Branch name:** `task/061-stay-on-task-branch-after-pr`
**Switch/create:** `git checkout -b task/061-stay-on-task-branch-after-pr`
**Make target:** `make branch-task f=TASK-061`

## Acceptance criteria (Gherkin)

- [x] Scenario: Opening a PR leaves the working tree on the task branch
      Given a task branch with an implemented, committed change
      When `open_pr_for` (or `butler task pr <id>` / `make pr-task`/`pr-current-task`) runs and successfully creates the PR
      Then the working tree remains checked out on the task branch; no `git checkout main` is issued

- [x] Scenario: Creating a new task branch bases it on origin/main, not the current branch
      Given the working tree is currently checked out on a different, already-existing branch (e.g. a previously merged task branch), and the target task branch does not exist locally yet
      When `branch_for` runs for the new task
      Then it fetches and creates the new branch from `origin/main`, not from the currently checked-out branch's tip

- [x] Scenario: Switching to an existing task branch is unaffected
      Given the target task branch already exists locally
      When `branch_for` runs for that task
      Then it simply checks out the existing branch, with no fetch or rebase against `origin/main`

- [x] Scenario: Merging still works without a manual branch switch
      Given a PR was just opened via `open_pr_for` and the working tree is still on the task branch
      When `merge_pr_for` runs immediately afterward
      Then it resolves and merges the correct PR (by branch name, not by current working-tree branch) and ends on `main` with `main` pulled, exactly as before

## Out of scope
- Any change to `merge_pr_for`'s own logic or its final `git checkout
  main` + `git pull` — it already behaves correctly.
- Any change to the `sync-project` entry point itself (Requirement 4/5/6) —
  this task only removes the condition that caused it to spuriously fail.
- Consumer-facing `.butler/Makefile` content — the Makefile's `pr-task`/
  `branch-task` recipes are unchanged; the behavior change is entirely
  inside `git_ops.py`.

## Blockers
None

## Completion
**Date:** 2026-07-31
**Summary:** Removed the trailing `git checkout main` from `open_pr_for` in
`src/butler_core/git_ops.py` — it now stops after `gh pr create`, leaving
the working tree on the task branch. `branch_for` now fetches
`origin/main` and runs `git checkout -b <branch> origin/main` (instead of
plain `git checkout -b <branch>`, which based the new branch on whatever
was currently checked out) when creating a brand-new branch; switching to
an already-existing branch is unchanged. `merge_pr_for` needed no changes
— it already resolves the PR by branch name via `gh pr list --head
<branch>`, not by the current working-tree branch. Updated
`tests/test_git_ops.py` (new/changed assertions for both functions) and
one assertion in `tests/test_cli.py` that pinned the old two-argument
`checkout -b` call. Verified live: opened and merged this task's own PR
(#61) using the new code path — after `make pr-current-task` the shell
stayed on `task/061-stay-on-task-branch-after-pr` with no manual
`git checkout` needed before `make merge-current-task`, and the
`sync-project --stage open` step succeeded on the first try (previously it
always failed with "No task file found" on TASK-058/059/060 because it
ran against `main`).
**Files changed:**
- `src/butler_core/git_ops.py` - modified
- `tests/test_git_ops.py` - modified
- `tests/test_cli.py` - modified
- `CHANGELOG.md` - modified
- `REQUIREMENTS_TASK_WORKFLOW.md` - modified (Requirement 7, confirmed with user before implementation)
- `docs/tasks/TASK-061-stay-on-task-branch-after-pr.md` - modified
**Branch:** `git checkout task/061-stay-on-task-branch-after-pr`
**Stage:** `git add src/butler_core/git_ops.py tests/test_git_ops.py tests/test_cli.py CHANGELOG.md REQUIREMENTS_TASK_WORKFLOW.md docs/tasks/TASK-061-stay-on-task-branch-after-pr.md`
**Commit:** `git commit -m "Stop switching to main after opening a PR; base new task branches on origin/main"`
