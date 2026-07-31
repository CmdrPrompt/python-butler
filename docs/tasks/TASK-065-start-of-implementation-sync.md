# TASK-065 Start-of-implementation sync sets Status to "In Progress" (`--stage start`)

## Status
todo

## Requirements
**Binding:** Requirement 9 (REQUIREMENTS_TASK_WORKFLOW.md)
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-059, TASK-060, TASK-062, TASK-063
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer starting work on a task, I want the task's linked GitHub
Projects item to move to "In Progress" as soon as I create/switch to its
branch, so the Project board reflects that implementation has actually
begun instead of sitting at the Project's default column until the PR is
merged.

## Description
Today the linked Project item only moves past its default Status column at
`--stage merge` (set to Done) or via a one-off `--stage backfill` run.
Between `--stage draft`/`--stage open` and the merge, the item stays at
whatever the Project's default Status option is, even while implementation
is already underway on the task branch.

A new sync stage, `--stage start`, MUST exist alongside `draft`/`open`/
`merge`/`backfill`. It MUST:

1. Create/link a Project item for the task, reusing the lookup-then-reuse
   behavior `_create_item` already implements (Requirement 4/TASK-063) —
   no new duplicate-creation logic.
2. Set the item's "Status" field to the option matching "In Progress",
   using the same generalized status-option resolution
   `--stage backfill` already uses (`_resolve_status_option_field_ids`,
   TASK-062) rather than a new hardcoded lookup.

A missing "Status" field or "In Progress" option on the configured Project
MUST follow Requirement 4's best-effort warning contract (warn, never
raise, never block).

`make branch-task` MUST invoke `butler task sync-project <id> --stage start`
as an added step immediately after `butler task branch` creates or switches
to the task branch — mirroring exactly how `--stage open`/`--stage merge`
are already added `make` steps in `pr-task`/`merge-pr`
(`Makefile:257`/`Makefile:270`), each prefixed with `-` so a sync failure
never fails the `make` target. This MUST NOT be inlined into `branch_for`
in `src/butler_core/git_ops.py`, preserving Requirement 4's encapsulation
constraint (the sync stays a separate entry point from the
branch/stage/commit/pr/merge call sites). There is no
`branch-current-task` target — unlike `pr`/`merge`, branch creation has no
"current task" to resolve from before the branch exists.

**Implementation location:** `src/butler_core/projects.py` (new
`sync_on_pr_start`/`_start` function reusing `_create_item` and
`_resolve_status_option_field_ids` with `"In Progress"`),
`src/butler_cli/__main__.py` (`"start"` added to the `--stage` argparse
choices at line 69, dispatched in `_cmd_sync_project`), `Makefile`
(`branch-task` target, line 211-213, gets a `-butler --tasks-dir
$(TASKS_DIR) task sync-project $(f) --stage start` line after the existing
`butler ... task branch $(f)` line), plus tests in
`tests/test_projects.py`/a new `tests/test_projects_start_stage.py` and
`tests/test_projects_makefile_integration.py`.

## Branch
**Branch name:** `task/065-start-of-implementation-sync`
**Switch/create:** `git checkout -b task/065-start-of-implementation-sync`
**Make target:** `make branch-task f=TASK-065`

## Acceptance criteria (Gherkin)

- [ ] Scenario: `--stage start` creates and links a Project item
      Given a task file has no linked Project item yet, and a GitHub Project is resolvable (via `.butler-project` or `BUTLER_GITHUB_PROJECT`)
      When `butler task sync-project <id> --stage start` runs
      Then a Project item is created and linked for the task

- [ ] Scenario: `--stage start` reuses an existing linked item instead of creating a duplicate
      Given a task already has a linked Project item (matched by TASK-ID title prefix)
      When `butler task sync-project <id> --stage start` runs
      Then no new item is created — the existing item is reused

- [ ] Scenario: `--stage start` sets Status to "In Progress"
      Given a Project with a "Status" field containing an option named "In Progress" is resolvable
      When `butler task sync-project <id> --stage start` runs
      Then the Project item's Status is set to "In Progress"

- [ ] Scenario: Missing "Status" field or "In Progress" option warns without blocking
      Given a Project is resolvable but has no "Status" field, or no option matching "In Progress"
      When `butler task sync-project <id> --stage start` runs
      Then the sync returns a best-effort warning and does not raise

- [ ] Scenario: `make branch-task` invokes the start-stage sync after creating/switching the branch
      Given a task ID and a configured GitHub Project
      When `make branch-task f=<id>` runs
      Then `butler task branch <id>` runs first, followed by `butler task sync-project <id> --stage start`, and the sync step's own failure does not fail the `make` target

- [ ] make lint && make test pass

- [ ] CHANGELOG.md updated

## Out of scope
- Changing `--stage draft`/`--stage open`/`--stage merge`/`--stage backfill`
  behavior — only a new stage is added alongside them.
- Reading any data back from GitHub Projects into the task workflow or any
  agent (Requirement 4's one-way contract is unchanged).
- Any change to `_create_item`'s existing duplicate-item lookup/reuse logic
  (TASK-063) beyond calling it from the new stage.
- Retroactively running `--stage start` for tasks whose branches already
  exist — this task only wires the sync into `make branch-task`'s own flow
  going forward, the same scope boundary `--stage backfill` (TASK-062) drew
  for historical items.

## Blockers
None

## Completion
**Date:**
**Summary:**
**Files changed:**
**Branch:** `git checkout task/065-start-of-implementation-sync`
**Stage:** `git add src/butler_core/projects.py src/butler_cli/__main__.py Makefile tests/test_projects*.py CHANGELOG.md docs/tasks/TASK-065-start-of-implementation-sync.md`
**Commit:** `git commit -m "Add --stage start for syncing GitHub Project item status to In Progress when implementation begins"`
