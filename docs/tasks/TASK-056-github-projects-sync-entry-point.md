# TASK-056 Implement separate entry point for GitHub Projects task metadata sync

## Status

done

## Requirements

**Binding:** Requirement 4 from REQUIREMENTS_TASK_WORKFLOW.md
**BDD mode:** BDD-PLANNED
**Depends on:** TASK-045 (for CLI framework and best-effort pattern)
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As an implementation worker maintaining a task-driven python-butler project,
I want the task workflow to automatically mirror task metadata (TASK-ID, title,
status) to a linked GitHub Projects (v2) item when I open a PR and merge it,
so that the project's task board reflects the current status without manual
updates or bidirectional reading from GitHub Projects.

## Description

Implement a separate, encapsulated entry point for syncing task metadata from
a task file to a linked GitHub Projects (v2) item, distinct from the existing
git_ops.py branch/stage/commit/pr/merge functions. The sync must:

1. Be invoked as an added step in `make pr-current-task`/`make pr-task` after the PR is opened (to create or link a GitHub Projects item and populate TASK-ID/title fields)
2. Be invoked as an added step in `make merge-current-task`/`make merge-pr` after the PR is merged (to update the linked Projects item's status to "Done")
3. Use the `gh` CLI or GitHub GraphQL API to interact with GitHub Projects
4. Be best-effort: failures (no Project configured, `gh` not authenticated, `gh` not installed, etc.) must produce a warning and MUST NOT cause PR creation or merge to fail
5. Be one-way only: the sync reads task metadata from the task file and writes to GitHub Projects, but never reads anything back from GitHub Projects into the CLI, git_ops.py, Makefile, or any agent's task-file behavior

The sync entry point must be a separate, maintainable module (e.g.
`src/butler_core/projects.py` or similar) so that a future, heavier
integration (e.g. GitHub Projects as source of truth) can replace or extend
it without requiring changes to git_ops.py's existing functions.

## Branch

**Branch name:** `task/056-github-projects-sync-entry-point`
**Switch/create:** `git checkout -b task/056-github-projects-sync-entry-point`
**Make target:** `make branch-task f=TASK-056`

## Acceptance criteria (Gherkin)

- [x] Scenario: GitHub Projects sync entry point exists as a separate module
      Given the butler_core codebase
      When examining the module structure
      Then a separate module exists (e.g. `butler_core.projects` or `butler_core.gh_sync`) that encapsulates all GitHub Projects sync logic and is distinct from git_ops.py

- [x] Scenario: Sync creates GitHub Projects item on PR open with correct metadata
      Given a task file with TASK-ID, title, and an open PR linked to it
      When the sync function is invoked after PR creation
      Then a new GitHub Projects item is created (or an existing one is found and linked) with the TASK-ID and title populated from the task file, and the exit code is 0

- [x] Scenario: Sync updates GitHub Projects item status on PR merge
      Given a task file and a linked GitHub Projects item
      When the sync function is invoked after PR merge
      Then the linked item's status field is updated to "Done" (or the equivalent terminal state in the configured Project), and the exit code is 0

- [x] Scenario: Sync gracefully handles missing Project configuration
      Given a repository with no GitHub Project configured
      When the sync function is invoked during PR creation
      Then the function emits a warning message (e.g. "Warning: could not sync TASK-XXX to GitHub Projects (no project configured for this repo) - continuing") and returns gracefully with exit code 0, NOT propagating as an error to the caller

- [x] Scenario: Sync gracefully handles gh not authenticated
      Given a repository with a GitHub Project configured but `gh` is not authenticated
      When the sync function is invoked
      Then the function emits a warning message (e.g. "Warning: could not sync TASK-XXX to GitHub Projects (gh: not authenticated) - continuing") and returns gracefully with exit code 0

- [x] Scenario: Sync gracefully handles gh not installed
      Given a system where `gh` CLI is not installed
      When the sync function is invoked
      Then the function emits a warning message (e.g. "Warning: could not sync TASK-XXX to GitHub Projects (gh: not found) - continuing") and returns gracefully with exit code 0

- [x] Scenario: PR creation succeeds even if Projects sync fails
      Given a task and an open PR with a sync failure (no Project, missing permissions, etc.)
      When `make pr-current-task` or `make pr-task` is run
      Then the PR is opened successfully and the make target exits 0, regardless of the sync result

- [x] Scenario: PR merge succeeds even if Projects sync fails
      Given a merged PR with a sync failure (no Project, missing permissions, etc.)
      When `make merge-current-task` or `make merge-pr` is run
      Then the PR merge completes successfully and the make target exits 0, regardless of the sync result

- [x] Scenario: Sync is one-way; no data read from GitHub Projects
      Given a GitHub Projects item with fields different from the task file (e.g. outdated title, manual status change)
      When the sync function runs during PR creation or merge
      Then the sync only writes TASK-ID, title, and status (when merging) from the task file to GitHub Projects, and never reads any field values back from GitHub Projects into the task file or CLI

- [x] Scenario: Sync is invoked as an added step in pr-task / pr-current-task
      Given a task on the task branch and an open PR
      When `make pr-task f=TASK-056` (or `make pr-current-task`) is run
      Then the output includes the Projects sync result (success or warning) as an added step after the PR is opened (e.g. "Synced TASK-056 ... to GitHub Project item (status: In Progress)" or "Warning: could not sync TASK-056 to GitHub Projects (...) - continuing")

- [x] Scenario: Sync is invoked as an added step in merge-pr / merge-current-task
      Given a merged PR and its linked task
      When `make merge-pr f=TASK-056` (or `make merge-current-task`) is run
      Then the output includes the Projects sync result (success or warning) as an added step after the PR is merged (e.g. "Updated GitHub Project item for TASK-056 to status: Done" or "Warning: could not update GitHub Project item for TASK-056 (...) - continuing")

- [x] Scenario: CHANGELOG.md updated with behavior-first entry
      Given a current CHANGELOG.md
      When this task is completed
      Then CHANGELOG.md contains a new entry describing the GitHub Projects sync functionality added

- [x] Scenario: Tests pass and coverage maintained
      Given the existing test suite with current coverage baseline
      When `make test` and `make lint` are run after implementation
      Then all tests pass and code coverage does not decrease below the baseline

## Out of scope

- Making GitHub Projects a source of truth for task state. The task file remains the sole source of truth; no data is read back from GitHub Projects.
- Changing how Workflow Guardian, Task Drafter, Implementation Worker, or any other agent reads or writes `docs/tasks/TASK-XXX-*.md` files. The sync does not affect agent behavior.
- Automatically configuring which GitHub Project to link to; the project must be pre-configured (via repository settings, environment variable, or a config file the task specifies).
- Syncing any other GitHub Project features or custom fields beyond TASK-ID, title, and status.
- Supporting GitHub Projects v1 (classic); only v2 (table view) is in scope.
- Implementing a more complex/bidirectional integration with GitHub Projects (that would be a future requirement, not part of this one).

## Blockers

None

## Completion

**Date:** 2026-07-31
**Summary:** Implemented `butler_core.projects` as a separate module encapsulating a
best-effort, one-way sync of task metadata (TASK-ID, title, status) to a linked GitHub
Projects (v2) item via the `gh` CLI. Added `sync_on_pr_open`/`sync_on_pr_merge`, each
returning a `SyncResult(success, message)` and never raising. Added the
`butler task sync-project <task_id> --stage open|merge` CLI subcommand and wired it as a
non-blocking (`-` prefixed) step into the `pr-task` and `merge-pr` Makefile targets, run
after the existing PR-open/merge logic (which `pr-current-task`/`merge-current-task`
inherit via their `$(MAKE) pr-task`/`$(MAKE) merge-pr` delegation). The target Project is
read from the `BUTLER_GITHUB_PROJECT` environment variable; missing configuration, `gh`
not installed, `gh` not authenticated, and any other `gh` failure are all reported as a
warning result and never propagate as an error.

**Files changed:**

- `src/butler_core/projects.py`
- `src/butler_cli/__main__.py`
- `Makefile`
- `src/butler_core/data/Makefile`
- `CHANGELOG.md`
- `docs/tasks/TASK-056-github-projects-sync-entry-point.md`
- `tests/test_projects.py`
- `tests/test_projects_cli.py`
- `tests/test_projects_makefile_integration.py`
- `tests/test_projects_extra_coverage.py`

**Branch:** `git checkout task/056-github-projects-sync-entry-point`
**Stage:** `git add src/butler_core/projects.py src/butler_cli/__main__.py Makefile src/butler_core/data/Makefile CHANGELOG.md docs/tasks/TASK-056-github-projects-sync-entry-point.md tests/test_projects.py tests/test_projects_cli.py tests/test_projects_makefile_integration.py tests/test_projects_extra_coverage.py`
**Commit:** `git commit -m "Implement GitHub Projects task metadata sync as separate entry point (TASK-056)"`
