# TASK-100 Merge must not crash when local main holds commits already squashed into the PR

## Status
done

## Requirements
**Binding:** Requirement 19, Requirement 7, Requirement 4 (REQUIREMENTS_TASK_WORKFLOW.md)
**BDD mode:** BDD-ACTIVE
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer who commits a new task file and requirement on local `main`
before branching, I want `make merge-current-task` to finish cleanly after the
squash merge, so that I do not land in a diverged `main`, a merge conflict and
a Python traceback, and so that the merge-stage Projects sync still runs.

## Description
**Bug:** After the squash merge, `merge_pr_for` runs a bare `git pull` on `main`; when local `main` holds unpushed commits that the squash commit already contains, `main` and `origin/main` have diverged, the pull fails (or attempts a conflicting merge) and butler crashes with an uncaught `CalledProcessError`, so the merge-stage Projects sync never runs.
**Location:** `src/butler_core/git_ops.py:145` (`subprocess.run(["git", "pull"], check=True)` in `merge_pr_for`); contributing cause `src/butler_core/git_ops.py:31-34` (`branch_for` bases new branches on `origin/main`)
**Requirement violated:** Requirement 19 (added for this task). Related context: Requirement 7, "`merge_pr_for` ... already ends by checking out and pulling `main` once the merge succeeds" (describes the behaviour, does not define it for diverged `main`), and Requirement 4, "PR creation and merge MUST succeed identically whether or not the Projects sync succeeds" (the merge-stage sync is skipped here because the merge step crashes).
**Severity:** high

Observed 2026-11-01 while completing TASK-098 (PR #104, squash commit fada677):

1. The documented flow commits the new task file and requirement on local
   `main` with `make commit-output` (task files must exist on `main` before
   `make branch-task`). These commits are never pushed directly.
2. `branch_for` runs `git fetch origin main` then `git checkout -b <branch>
   origin/main`, so the local-only `main` commits are not on the new branch.
   The `--stage start` sync fails with "No task file found matching
   'TASK-098'" (non-fatal). Workaround used: `make sync-main` (merges local
   `main` into the branch) and `make branch-task` again.
3. The local `main` commits ride along in the task PR and are squash-merged
   into one commit.
4. `merge_pr_for` then runs `git pull` on `main`. Local `main` still has the 2
   unpushed commits (d9ca3ed, 4e948d6) whose content is already in the squash
   commit, so `main` and `origin/main` have diverged. Fast-forward fails
   ("Not possible to fast-forward"), a merge is attempted and yields add/add
   conflicts in the task file and the feature file (edited on the branch after
   being committed on `main`). `git pull` exits 1 and butler dies with a
   traceback (`_cmd_merge` -> `merge_pr_for` -> `subprocess.run`). The local
   and remote task branches were already deleted.
5. `make merge-pr` stops at the failed `butler task merge` line, so the
   `sync-project --stage merge` line never ran: TASK-098 stayed "In Progress"
   in GitHub Project 2 though its PR is merged. Recovery needed a manual
   `git merge --abort` and `git reset --hard origin/main`.

Requirement analysis: Requirement 7 makes basing new branches on `origin/main`
deliberate (so a new branch never forks off a leftover task branch); that
behaviour is correct and must not be reverted blindly. No requirement says
what `merge_pr_for` does when local `main` is ahead of or diverged from
`origin/main`, nor that a git failure after the merge must be reported as a
clean error rather than a traceback. Requirement 19 was added for this case
and confirmed by the user on 2026-11-01.

Fix directions (not binding):

- (a) `branch_for` bases a new branch on local `main` when it is ahead of
  `origin/main`, or merges it in. This makes the `--stage start` sync work
  (task file present on the branch) but does NOT fix the crash: local `main`
  still holds the same commits after the squash merge, so `git pull` still
  diverges. It also weakens Requirement 7's guarantee unless restricted to
  `main` (not other branches). Treat as a separate, optional follow-up.
- (b) After the squash merge, `merge_pr_for` captures the PR head commit
  before merging (`gh pr view <n> --json headRefOid`), then fetches
  `origin/main`. If local `main` is behind or equal, it fast-forwards
  (`git pull --ff-only`). If local `main` has commits not in `origin/main`
  and every one of them is an ancestor of the merged PR head (their content
  is in the squash commit), it moves local `main` to `origin/main` with `git
  reset --keep origin/main` (keeps uncommitted work; refuses rather than
  discarding it). Otherwise (commits genuinely not in the PR) it changes
  nothing and raises `GitOpsError` stating that the PR is merged, that local
  `main` has unpushed commits not in the PR, and the exact command to resolve
  it. No traceback in any case.
- (c) Run (or retry) the merge-stage sync even when the local pull fails. This
  needs a Makefile/CLI change to tell "PR not merged" from "PR merged, local
  update failed", and treats the symptom rather than the cause.

Recommendation: (b). It fixes the root cause (local `main` is left diverged
from content that is already merged), is safe because it only discards
commits provably contained in the merged PR, never loses unpushed work, and
turns every remaining failure into an actionable `GitOpsError`. With (b) the
pull no longer fails in the observed flow, so the existing `make merge-pr`
ordering already runs the merge-stage sync; (c) is not needed.

Existing tests that will need updating:
- `tests/test_git_ops.py:246-261` (`test_squash_merges_mergeable_pr_and_pulls_main`) feeds a fixed 5-element `side_effect` and asserts `commands[4] == ["git", "pull"]`; the command sequence changes (head-commit lookup, fetch, ancestry checks, `--ff-only`/reset), so it must be rewritten.
- `tests/test_git_ops.py:264-280` (no open PR / not mergeable) should keep passing.
- `tests/test_no_make_recursion.py:222-272` (`merge_pr_for` recorder) depends on the stdout of prior calls; the added calls must be handled by its fake.
- `tests/test_cli.py:437-442` already covers `GitOpsError` from `merge_pr_for`; add a case asserting the new post-merge error message and no traceback.
- `mcp/tests/test_server.py:118-125` wraps `merge_pr_for`; check it still passes.
- Prefer a real-git test (temporary repos with a bare `origin`) for the diverged-main scenarios rather than mocking `subprocess.run`.

## Branch
**Branch name:** `task/100-merge-diverged-local-main-pull-crash`
**Switch/create:** `git checkout -b task/100-merge-diverged-local-main-pull-crash`
**Make target:** `make branch-task f=TASK-100`

## Acceptance criteria (Gherkin)
**Feature files:** tests/bdd/features/TASK-100-merge-diverged-local-main-pull-crash.feature

- [x] 1. See `tests/bdd/features/TASK-100-merge-diverged-local-main-pull-crash.feature`: Scenario "Merge succeeds when local main commits are already in the squashed PR" (@AC-1)
- [x] 2. See `tests/bdd/features/TASK-100-merge-diverged-local-main-pull-crash.feature`: Scenario "Local main is fast-forwarded when it has no unpushed commits" (@AC-2)
- [x] 3. See `tests/bdd/features/TASK-100-merge-diverged-local-main-pull-crash.feature`: Scenario "Unpushed local main commits that are not in the PR are preserved and reported" (@AC-3)
- [x] 4. See `tests/bdd/features/TASK-100-merge-diverged-local-main-pull-crash.feature`: Scenario "A failed local update after the merge is a clean error, not a traceback" (@AC-4)
- [x] 5. See `tests/bdd/features/TASK-100-merge-diverged-local-main-pull-crash.feature`: Scenario "The merge-stage Projects sync runs after a merge with local-only main commits" (@AC-5)

## Out of scope
- Changing `branch_for` to base new branches on local `main` (direction (a)); Requirement 7 deliberately bases new branches on `origin/main`. File separately if the failing `--stage start` sync is to be fixed.
- Pushing local `main` directly (no direct push to `main`).
- Changing the GitHub Projects sync logic itself.

## Blockers
None

## Completion
**Date:** 2026-11-01
**Summary:** `merge_pr_for` now reads the PR head SHA (`gh pr view --json headRefOid`) before the squash merge, because `--delete-branch` removes the branch, and replaces the bare `git pull` with `_update_local_main` (Requirement 19): checkout `main`, `git fetch origin main`, then `git pull --ff-only` when local `main` is an ancestor of `origin/main`, `git reset --keep origin/main` when local `main` is an ancestor of the PR head (all local-only commits are in the squash commit), and otherwise a one-line `GitOpsError` that leaves `main` untouched and names `git log origin/main..main`, `git rebase origin/main` and `git reset --keep origin/main`. Every post-merge git command runs through `_git_after_merge`, which captures stderr and turns a non-zero exit or `CalledProcessError` into a single-line `GitOpsError`; the CLI already prints `GitOpsError` as one stderr line, so `src/butler_cli/__main__.py` is unchanged. Ancestry is checked with `git merge-base --is-ancestor` exit codes rather than parsed output. `branch_for` is unchanged (Requirement 7). BDD scenarios run against real git repos with a bare origin and a fake `gh` on PATH (also serving the Projects calls for @AC-5, which drives the real `Makefile`); @AC-2 was already green before the fix and acts as a regression guard. Existing merge tests in `tests/test_git_ops.py` and `tests/test_no_make_recursion.py` moved from fixed call sequences to a command-keyed fake; a unit test for a non-zero git exit after the merge was added to keep coverage at the baseline. Requirement 19 was added to `REQUIREMENTS_TASK_WORKFLOW.md` and confirmed by the user before implementation; the task file, feature file and requirement were carried uncommitted onto the task branch instead of being committed on `main`, to avoid the very bug this task fixes. `make lint`, `make test` (432 passed, 9 xfailed), `make bdd` (10 passed, 9 xfailed) and the `mcp/` tests (18 passed) pass. Coverage 98.92% (827/836), not below the task-start baseline of 98.90% (806/815).
**Files changed:**
- `REQUIREMENTS_TASK_WORKFLOW.md` - modified (Requirement 19)
- `src/butler_core/git_ops.py` - modified
- `tests/test_git_ops.py` - modified
- `tests/test_no_make_recursion.py` - modified
- `tests/test_cli.py` - modified
- `CHANGELOG.md` - modified
- `docs/tasks/TASK-100-merge-diverged-local-main-pull-crash.md` - created
- `tests/bdd/features/TASK-100-merge-diverged-local-main-pull-crash.feature` - created
- `tests/bdd/steps/test_task_100_steps.py` - created
**Branch:** `git checkout task/100-merge-diverged-local-main-pull-crash`
**Stage:** `REQUIREMENTS_TASK_WORKFLOW.md src/butler_core/git_ops.py tests/test_git_ops.py tests/test_no_make_recursion.py tests/test_cli.py CHANGELOG.md docs/tasks/TASK-100-merge-diverged-local-main-pull-crash.md tests/bdd/features/TASK-100-merge-diverged-local-main-pull-crash.feature tests/bdd/steps/test_task_100_steps.py`
**Commit:** `git commit -m "Keep merge from crashing when local main already holds the squashed commits (TASK-100)"`
