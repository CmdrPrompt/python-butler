# TASK-096 Recursion guard for `stage-current-task`/`stage-task` against runaway nested `make`

## Status
in-progress

## Note
Discovered live in `firefly-bills-analyzer` (a consumer project), not in
python-butler itself. Filed here per that project's cross-workspace policy:
task files describing a bug that belongs to butler are created in this repo
after explicit user approval, without editing any butler source from the
consumer project.

## Requirements
**Binding:** Requirement 18 (REQUIREMENTS_TASK_WORKFLOW.md)
**BDD mode:** BDD-ABSENT
**Depends on:** None
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer of a project governed by butler, I want the Makefile to refuse
to run a guarded target (`stage-current-task`, `commit-current-task`,
`pr-current-task`, or `merge-current-task`) if it detects that the same family's
guarded target is already running in this process tree, so that a bug,
misconfiguration, or stale installed `butler` binary that causes re-invocation
fails fast with one clear error instead of silently forking an unbounded tree of
nested `make`/`butler` processes.

## Description
Requirement 15 (TASK-086) fixed one known cause of wrapper/leaf recursion by
ensuring the Stage field can never be executed as a command. However, that fix
lives only in current `butler_core`; a stale installed `butler` from an old
virtualenv that predates that fix can still re-execute the Stage field as a
command, spawning runaway processes as observed on 2026-09-20 in
`firefly-bills-analyzer`. Even if Requirement 15's fix ships everywhere,
another future cause (circular Makefile target, different code path invoking
make, etc.) could produce the same symptom undetected.

This task implements a Makefile-level defense-in-depth guard that catches
recursion from *any* cause: each `*-current-task` wrapper target and its
corresponding `*-task` leaf target will check a unique sentinel environment
variable at entry and refuse to proceed if it is already set, exiting with
exit code 17 and a clear error message. The guard remains effective even
against a stale installed `butler` binary that bypasses Requirement 15's fix,
because the Makefile actually invoked by users comes from the up-to-date
`.butler/` submodule in consumer projects (or the repo root `Makefile` when
running in this repo itself).

Four families are guarded independently (stage, commit, pr, merge) with
per-family sentinels and error messages:
- `BUTLER_STAGE_GUARD` for `stage-current-task`/`stage-task`
- `BUTLER_COMMIT_GUARD` for `commit-current-task`/`commit-task`
- `BUTLER_PR_GUARD` for `pr-current-task`/`pr-task`
- `BUTLER_MERGE_GUARD` for `merge-current-task`/`merge-pr`

**Implementation note:** Add the guard logic to the root `Makefile`. This must
then be copied byte-identically into `src/butler_core/data/Makefile`, which
`butler sync` distributes to consumer projects' `.butler/Makefile`;
`tests/test_quiet_check_targets.py::TestVendoredMakefileDoesNotDrift` enforces
byte-identity between the two. Do not modify `tests/fixtures/Makefile.baseline`,
which is a frozen historical snapshot from commit 64ae502 (TASK-092) used only
by `TestVerboseTargetsUnchanged` to verify that `make -n lint/test/bdd` output
did not drift.

## Branch
**Branch name:** `task/096-recursion-guard-for-stage-current-task`
**Switch/create:** `git checkout -b task/096-recursion-guard-for-stage-current-task`
**Make target:** `make branch-task f=TASK-096`

## Acceptance criteria (Gherkin)

- [ ] 1. Scenario Outline: Refusal on re-entry (sentinel already set)
      Given <SENTINEL> is set to "1" in the environment
      When <TARGET> is invoked
      Then the target exits immediately with exit code 17, prints the exact message: "<ERROR_MESSAGE>", and does not invoke $(MAKE) or butler

      Examples:
      | SENTINEL              | TARGET                      | ERROR_MESSAGE                                                                        |
      | BUTLER_STAGE_GUARD    | make stage-current-task     | Error: stage-current-task/stage-task is already running in this process tree; refusing to recurse. |
      | BUTLER_STAGE_GUARD    | make stage-task f=TASK-001  | Error: stage-current-task/stage-task is already running in this process tree; refusing to recurse. |
      | BUTLER_COMMIT_GUARD   | make commit-current-task    | Error: commit-current-task/commit-task is already running in this process tree; refusing to recurse. |
      | BUTLER_COMMIT_GUARD   | make commit-task f=TASK-001 | Error: commit-current-task/commit-task is already running in this process tree; refusing to recurse. |
      | BUTLER_PR_GUARD       | make pr-current-task        | Error: pr-current-task/pr-task is already running in this process tree; refusing to recurse. |
      | BUTLER_PR_GUARD       | make pr-task f=TASK-001     | Error: pr-current-task/pr-task is already running in this process tree; refusing to recurse. |
      | BUTLER_MERGE_GUARD    | make merge-current-task     | Error: merge-current-task/merge-pr is already running in this process tree; refusing to recurse. |
      | BUTLER_MERGE_GUARD    | make merge-pr f=TASK-001    | Error: merge-current-task/merge-pr is already running in this process tree; refusing to recurse. |

- [ ] 2. Scenario Outline: Normal unaffected direct leaf invocation
      Given <SENTINEL> is not set in the environment
      When <LEAF_TARGET> is invoked directly
      Then the target checks the sentinel, finds it unset, exports <SENTINEL>=1, and runs its butler command(s) normally

      Examples:
      | SENTINEL              | LEAF_TARGET             |
      | BUTLER_STAGE_GUARD    | make stage-task f=TASK-001  |
      | BUTLER_COMMIT_GUARD   | make commit-task f=TASK-001 |
      | BUTLER_PR_GUARD       | make pr-task f=TASK-001     |
      | BUTLER_MERGE_GUARD    | make merge-pr f=TASK-001    |

- [ ] 3. Scenario Outline: Normal unaffected wrapper invocation (one-level nesting)
      Given <SENTINEL> is not set in the environment
      When <WRAPPER_TARGET> is invoked
      Then the wrapper checks the sentinel, finds it unset, does not export it, invokes $(MAKE) <LEAF_TARGET>, the leaf exports <SENTINEL>=1, and the flow completes normally

      Examples:
      | SENTINEL              | WRAPPER_TARGET              | LEAF_TARGET  |
      | BUTLER_STAGE_GUARD    | make stage-current-task     | stage-task   |
      | BUTLER_COMMIT_GUARD   | make commit-current-task    | commit-task  |
      | BUTLER_PR_GUARD       | make pr-current-task        | pr-task      |
      | BUTLER_MERGE_GUARD    | make merge-current-task     | merge-pr     |

- [ ] 4. Scenario: Sequential pr-task butler calls in one recipe are unaffected
      Given pr-task is running with BUTLER_PR_GUARD exported
      When pr-task's recipe runs butler task branch, then butler task pr, then butler task sync-project --stage open in sequence within the same recipe
      Then all three calls complete normally and in order; they are sequential within one $(MAKE) invocation, not re-entrant

- [ ] 5. Scenario: Sequential merge-pr butler calls in one recipe are unaffected
      Given merge-pr is running with BUTLER_MERGE_GUARD exported
      When merge-pr's recipe runs butler task merge, then butler task sync-project --stage merge in sequence within the same recipe
      Then both calls complete normally and in order; they are sequential within one $(MAKE) invocation, not re-entrant

- [ ] 6. Scenario: Families are independent; one guard does not block another
      Given BUTLER_STAGE_GUARD is set to "1" (stage family is running)
      When make commit-current-task is invoked
      Then the target checks BUTLER_COMMIT_GUARD (finds it unset), and proceeds normally without blocking

- [ ] 7. Scenario: Recursion via re-entrant stale butler invocation is caught with visible output
      Given a stale butler binary (pre-TASK-086 fix) is on PATH
      When make stage-current-task runs and its leaf exports BUTLER_STAGE_GUARD=1, then invokes butler task stage, which (due to the stale binary) executes a Stage field containing "make stage-current-task" as a command
      Then the re-entrant make process inherits BUTLER_STAGE_GUARD=1, the wrapper checks it, finds it set, exits immediately with exit code 17, prints: "Error: stage-current-task/stage-task is already running in this process tree; refusing to recurse.", does not invoke any further $(MAKE) or butler processes, the refusal message appears in the combined output of the outer make stage-current-task invocation, and the outer make invocation exits non-zero

## Out of scope
- Re-fixing Requirement 15's original cause (already fixed in current source via TASK-086)
- Detecting or warning about a stale installed `butler` version (separate follow-up task)
- Changes to `.butler/` submodule distribution or `make butler-pull`
- A CLI-level recursion check inside `butler task stage`/`commit`/`pr`/`merge` themselves (may be filed as a separate follow-up task; this requirement covers only the Makefile-level guard)

## Blockers
None

## Completion
**Date:**
**Summary:**
**Files changed:**
**Branch:** `git checkout task/096-recursion-guard-for-stage-current-task`
**Stage:** `REQUIREMENTS_TASK_WORKFLOW.md docs/tasks/TASK-096-recursion-guard-for-stage-current-task.md`
**Commit:** `git commit -m "Clarify Requirement 18 exit status: recipe exits 17, make reports Error 17 (TASK-096)"`
