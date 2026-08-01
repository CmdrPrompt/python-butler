# TASK-084 Add an `obsolete` task Status for work superseded before completion

## Status
todo

## Requirements
**Binding:** Requirement 13 (REQUIREMENTS_TASK_WORKFLOW.md)
**BDD mode:** BDD-ACTIVE
**Feature files:** `tests/bdd/features/TASK-084-obsolete-task-status.feature`
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a Workflow Guardian reconciling task files against reality, I want a
terminal `obsolete` Status distinct from `todo`/`blocked`/`done`, so that a
task superseded by other work (e.g. TASK-039 superseded by TASK-054) is
never miscounted as outstanding or silently mismarked, in the task file or
on the linked GitHub Projects item.

## Description
Add `obsolete` as a fifth task Status value:

- `task-file-format` skill's canonical template documents
  `todo | in-progress | blocked | done | obsolete`, and states that (like
  Status generally) only the Workflow Guardian or the user sets it — and
  only when the task file documents which task/requirement superseded it.
- `butler_core` accepts `obsolete` wherever the four existing values are
  validated/parsed (task creation, `set-status`, Projects sync
  status-matching) — no special-cased behavior beyond being a valid value.
- `butler task sync-project --stage backfill` on an `obsolete` task sets
  the linked Project item's Status to the option matching "Obsolete" via
  the existing generalized status-option resolution; a missing "Obsolete"
  option on the configured Project is a best-effort warning (Requirement 4
  pattern), not a raised exception. Butler does not create the Project's
  "Obsolete" field option itself — that's a one-time manual
  `gh project field-create`/UI action per Project, same as the existing
  four options are already assumed pre-configured.
- A task with Status `obsolete` is a terminal state (unlike `blocked`,
  nothing is expected to resolve it back to `todo`) and MUST NOT be picked
  up for implementation.

## Branch
**Branch name:** `task/084-obsolete-task-status`
**Switch/create:** `git checkout -b task/084-obsolete-task-status`
**Make target:** `make branch-task f=TASK-084`

## Acceptance criteria (Gherkin)

- [ ] See `tests/bdd/features/TASK-084-obsolete-task-status.feature`: Scenario: obsolete is a documented, valid Status value
- [ ] See `tests/bdd/features/TASK-084-obsolete-task-status.feature`: Scenario: butler_core accepts obsolete as a valid Status
- [ ] See `tests/bdd/features/TASK-084-obsolete-task-status.feature`: Scenario: backfill sync sets the Project item's Status to Obsolete
- [ ] See `tests/bdd/features/TASK-084-obsolete-task-status.feature`: Scenario: missing Obsolete option warns instead of raising

## Out of scope
- Butler creating/configuring the Project's "Obsolete" Status field option
  itself — remains a manual one-time setup step, consistent with the
  existing four options.
- Retroactively re-filing TASK-039/TASK-040's Status to `obsolete` — that's
  a separate Workflow Guardian action, once this Status value exists, not
  part of building the feature.
- Any new automated detection of when a task becomes obsolete — Status is
  still set manually per the existing rule.

## Blockers
None

## Completion
**Date:** TBD
**Summary:** TBD
**Files changed:**
- `path/to/file` - created / modified
**Branch:** `git checkout task/084-obsolete-task-status`
**Stage:** `path/to/file1 path/to/file2 CHANGELOG.md`
**Commit:** `git commit -m "Add an obsolete task Status for work superseded before completion"`
