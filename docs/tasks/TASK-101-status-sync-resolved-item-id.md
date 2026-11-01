# TASK-101 Status sync acts only on a resolved Project item ID, never on the task ID

## Status
done

## Requirements
**Binding:** Requirement 20 (REQUIREMENTS_TASK_WORKFLOW.md), together with the two final checkboxes under "## Acceptance criteria (overall)" of REQUIREMENTS_TASK_WORKFLOW.md that Requirement 20 adds
**BDD mode:** BDD-ACTIVE
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer watching GitHub Projects status sync, I want every status-setting
sync stage to act on the Project item it resolved, so that a newly created item
shows the status the stage set, and a missing item is reported as a warning
instead of failing with a GraphQL error.

## Description
Every status-setting sync stage (`start`, `merge`, `backfill`) looks up the
task's Project item and, when the lookup finds nothing, falls back to passing
the task ID itself as the item's node ID. GitHub rejects that
(`Could not resolve to a node with the global id of 'TASK-084'`).

The lookup finds nothing right after an item has been created, because a new
item is not yet listed. `--stage start` on a task with no existing item therefore
creates the item but leaves its Status at the Project default, instead of
"In Progress", until a later stage sets it.

Requirement 20 requires:

- When a stage creates the item itself, it takes the new item's node ID from the
  creation output and uses that ID for every following edit in the same stage,
  without a second lookup.
- When a stage links an existing item, it uses the ID returned by the lookup
  (Requirement 16: first match if several, as today).
- The task ID is never passed as a Project item ID. If no item ID can be
  resolved, the stage returns a best-effort warning (Requirement 4) naming the
  task and stating that no Project item was found for it, and makes no item
  edit call.

Observed 2026-11-01: `make branch-task f=TASK-084` created the item in
`--stage start`, then warned with the GraphQL error above. The item stayed at
its default Status until `--stage merge` set it to "Done".

Code facts (context only, not binding): the fallback `item_id = item_id or
task.id` in `_set_status` (used by `--stage start` and `--stage merge`) and in
`_backfill_resolve_and_set_status` (`--stage backfill`) in
`src/butler_core/projects.py` is the path that passes the task ID. `_create_item`
currently discards the output of the item creation call.

## Branch
**Branch name:** `task/101-status-sync-resolved-item-id`
**Switch/create:** `git checkout -b task/101-status-sync-resolved-item-id`
**Make target:** `make branch-task f=TASK-101`

## Acceptance criteria (Gherkin)
**Feature files:** tests/bdd/features/TASK-101-status-sync-resolved-item-id.feature

- [x] 1. See `tests/bdd/features/TASK-101-status-sync-resolved-item-id.feature`: Scenario "Start sync on a new item sets its status in one run" (@AC-1)
- [x] 2. See `tests/bdd/features/TASK-101-status-sync-resolved-item-id.feature`: Scenario "Sync of a task with an existing item updates the item found by lookup" (@AC-2)
- [x] 3. See `tests/bdd/features/TASK-101-status-sync-resolved-item-id.feature`: Scenario "No Project item can be resolved when the lookup finds nothing and creation fails" (@AC-3)
- [x] 4. See `tests/bdd/features/TASK-101-status-sync-resolved-item-id.feature`: Scenario "No Project item can be resolved when the created item has no ID" (@AC-4)
- [x] 5. See `tests/bdd/features/TASK-101-status-sync-resolved-item-id.feature`: Scenario "Merge sync of an existing item updates the item found by lookup" (@AC-5)

## Out of scope
- Changing the lookup itself, including pagination (Requirement 16, already covered by TASK-089).
- Changing the success messages of any stage (Requirement 6 / TASK-099).
- Setting a Status in `--stage draft` or `--stage open`, which Requirement 6 leaves at the Project default.
- Reading any status back from GitHub Projects into the task workflow (Requirement 4 is one-way).
- Changing the Project item body or the `--stage backfill` date fields.

## Blockers
None

## Completion
**Date:** 2026-11-01
**Summary:** Every status-setting sync stage now acts only on a resolved
Project item ID. `gh project item-create` runs with `--format json` and the
new item's `id` is read from its output (`_created_item_id`), so `--stage
start` sets "In Progress" on a just-created item without a second lookup.
`_resolve_or_create_item` returns the lookup's first match or the created
item's id; `_start` and `_backfill` pass it on, and `_set_status` (merge)
looks it up itself. The `item_id or task.id` fallback is gone: when no item
ID can be resolved, the stage warns "no Project item found for <TASK-ID>"
(with the `gh` failure reason when creation failed) and makes no
`item-edit` call. Draft/open messages and failure warnings are unchanged.
Test fakes that returned empty `item-create` output, or listed a created
item on a second `item-list`, were updated to match `gh`'s real behavior.
**Files changed:**
- `src/butler_core/projects.py` - modified
- `tests/bdd/steps/test_task_101_steps.py` - modified
- `tests/test_projects_created_item_id.py` - created
- `tests/test_projects_backfill.py` - modified
- `tests/test_projects_start_stage.py` - modified
- `tests/test_projects.py` - modified
- `CHANGELOG.md` - modified
**Branch:** `git checkout task/101-status-sync-resolved-item-id`
**Stage:** `docs/tasks/TASK-101-status-sync-resolved-item-id.md src/butler_core/projects.py tests/bdd/steps/test_task_101_steps.py tests/test_projects_created_item_id.py tests/test_projects_backfill.py tests/test_projects_start_stage.py tests/test_projects.py CHANGELOG.md`
**Commit:** `git commit -m "Set Project item Status via the resolved item ID, never the task ID (TASK-101)"`
