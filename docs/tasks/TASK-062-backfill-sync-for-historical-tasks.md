# TASK-062 Backfill sync for historical tasks (`--stage backfill`)

## Status
todo

## Requirements
**Binding:** Requirement 8 (REQUIREMENTS_TASK_WORKFLOW.md)
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-059, TASK-060
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer looking back at historical tasks completed before the GitHub
Projects sync was added (e.g. TASK-001 through TASK-059), I want a way to
backfill those tasks' actual completion history into the Project board — with
correct Status, creation date, and completion date — so that the Project item
reflects the task's real timeline, not today's date and a default status.

## Description
Requirement 6 (TASK-060) added a draft-stage sync that creates GitHub Projects
items when new tasks are written going forward. But tasks completed before that
sync existed (TASK-001 through TASK-059) either have no Project items at all,
or ones that were created at PR-open/merge time with the current date and the
default Status, losing the historical context of when the task was actually
created and completed.

A new sync stage, `--stage backfill`, MUST exist alongside the existing
`open`/`draft`/`merge` stages. Given a single task ID, it MUST:

1. Create/link a Project item for the task (using the same item-creation logic
   as `--stage open`/`draft`).
2. Set the item's "Status" field to match the task file's own `## Status`
   value (e.g. `todo`, `in-progress`, `done`), generalizing the existing
   Done-only status resolution (`_resolve_status_done_field_ids`) to resolve
   any status option by name, matching case-insensitively and treating `-` as
   a space (e.g. `in-progress` in the task file matches an option named
   "In Progress" on the Project).
3. If the configured Project has a "Created" date field, set it to the git
   commit date the task file was first added (earliest commit touching the
   file, from `git log --diff-filter=A --follow`).
4. If the configured Project has a "Closed" date field and the task's
   `## Status` is `done`, set it to the task file's own Completion date
   (`## Completion` / `**Date:**`) when present and parseable as a date;
   otherwise fall back to the task file's most recent git commit date.
   If the status is not `done`, the "Closed" field MUST stay unset.

A missing "Created" or "Closed" field on the configured Project MUST NOT fail
the sync — each field is set independently and silently skipped if absent.
A missing "Status" field/option and complete Project-resolution failure still
follow Requirement 4's best-effort warning contract (warn, never raise, never
block).

Backfill is invoked per task ID, the same way `open`/`draft`/`merge` are
(e.g. `butler task sync-project TASK-001 --stage backfill`). Looping over
every file in `docs/tasks/` to backfill a whole repo's history in one command
is out of scope; a maintainer or external script calls it once per task ID.

**Implementation location:** `src/butler_core/projects.py` (generalized status
resolution, new backfill-stage logic for Created/Closed fields),
`src/butler_cli/__main__.py` (CLI plumbing for `--stage backfill` if argparse
choices need updating), `tests/test_projects.py` / `tests/test_projects_cli.py`
or similar per existing test naming conventions.

## Branch
**Branch name:** `task/062-backfill-sync-for-historical-tasks`
**Switch/create:** `git checkout -b task/062-backfill-sync-for-historical-tasks`
**Make target:** `make branch-task f=TASK-062`

## Acceptance criteria (Gherkin)

- [ ] Scenario: Create and link a Project item with backfill
      Given a task file with ID TASK-001 has no linked Project item yet, and a GitHub Project is resolvable (via `.butler-project` or `BUTLER_GITHUB_PROJECT`)
      When `butler task sync-project TASK-001 --stage backfill` runs
      Then a Project item is created and linked for the task

- [ ] Scenario: Set Status to match the task file's Status value (case-insensitive, hyphen to space)
      Given a task file with `## Status` = `in-progress` exists, and a Project with a "Status" field containing an option named "In Progress" is resolvable
      When `butler task sync-project <id> --stage backfill` runs
      Then the Project item's Status is set to "In Progress" (matched case-insensitively from `in-progress`, with `-` converted to space)

- [ ] Scenario: Set Created date to the task file's first commit date
      Given a task file exists whose first commit (via `git log --diff-filter=A --follow`) is 2026-03-02, and a Project with a "Created" date field is resolvable
      When `butler task sync-project <id> --stage backfill` runs
      Then the Project item's Created date field is set to 2026-03-02

- [ ] Scenario: Set Closed date to Completion date when Status is done and Completion date is present/parseable
      Given a task file with `## Status` = `done` and `## Completion` section containing `**Date:** 2026-03-05` exists, and a Project with a "Closed" date field is resolvable
      When `butler task sync-project <id> --stage backfill` runs
      Then the Project item's Closed date field is set to 2026-03-05

- [ ] Scenario: Fall back to most recent commit date for Closed when Completion date is absent/unparseable and Status is done
      Given a task file with `## Status` = `done` exists with no parseable Completion date (missing or malformed `## Completion` section), and a Project with a "Closed" date field is resolvable
      When `butler task sync-project <id> --stage backfill` runs
      Then the Project item's Closed date field is set to the task file's most recent git commit date

- [ ] Scenario: Leave Closed field unset when task Status is not done
      Given a task file with `## Status` = `todo` (not `done`) exists, and a Project with a "Closed" date field is resolvable
      When `butler task sync-project <id> --stage backfill` runs
      Then the Project item's Closed date field is not set and remains empty

- [ ] Scenario: Silently skip missing Created date field without warning
      Given a task file exists, a Project is resolvable but has no "Created" date field, and the sync would succeed otherwise
      When `butler task sync-project <id> --stage backfill` runs
      Then the sync succeeds without producing a warning, and the Project item is created without a Created field set

- [ ] Scenario: Silently skip missing Closed date field without warning
      Given a task file with `## Status` = `done` exists, a Project is resolvable but has no "Closed" date field, and the sync would succeed otherwise
      When `butler task sync-project <id> --stage backfill` runs
      Then the sync succeeds without producing a warning, and the Project item is created without a Closed field set

## Out of scope
- Looping over `docs/tasks/` to backfill all historical tasks in one command
  — backfill is invoked once per task ID by a maintainer or external script.
- Changing the `--stage open`/`--stage draft`/`--stage merge` behavior, only
  generalizing status resolution and adding backfill-specific date-field logic.
- Reading any data from GitHub Projects back into the task workflow or any
  agent (Requirement 4 one-way contract is unchanged).
- Task Drafter agent changes (Requirement 6 states it stays read/grep/glob/write
  only; Workflow Guardian or external tooling invokes backfill manually).

## Blockers
None

## Completion
**Date:**
**Summary:**
**Files changed:**
**Branch:** `git checkout task/062-backfill-sync-for-historical-tasks`
**Stage:** `git add src/butler_core/projects.py src/butler_cli/__main__.py tests/test_projects*.py CHANGELOG.md docs/tasks/TASK-062-backfill-sync-for-historical-tasks.md`
**Commit:** `git commit -m "Add --stage backfill for syncing historical task completion dates to GitHub Projects"`
