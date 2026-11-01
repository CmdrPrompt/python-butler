# TASK-099 Draft and open sync messages must not claim an unset Status

## Status
todo

## Requirements
**Binding:** Requirement 6 (including its success-message clause), Requirement 4 (REQUIREMENTS_TASK_WORKFLOW.md)
**BDD mode:** BDD-ACTIVE
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer watching GitHub Projects status sync, I want the draft and
open sync output to report only what the sync actually did, so that I am not
told an item is "In Progress" when the Project still shows it as "Todo".

## Description
**Bug:** `_create_item` returns the hardcoded success message "Synced {id} {title} to GitHub Project item (status: In Progress)" even though it never sets a Status, so `--stage draft` and `--stage open` misreport the Project status.
**Location:** `src/butler_core/projects.py:442` (existing item linked) and `src/butler_core/projects.py:461` (new item created)
**Requirement violated:** "The success message of the `draft` and `open` sync stages MUST NOT claim a Project Status that the sync did not set; it reports the task id and title only, while stages that set a Status (`start`, `backfill`, `merge`) continue to name it." (Requirement 6)
**Severity:** low

`_create_item` is used by `sync_on_pr_draft` (`butler task sync-project <ID>
--stage draft`, `make sync-project-draft`) and `sync_on_pr_open` (`--stage
open`, run by `make pr-current-task`) via `_sync(status=None)`. `_start`
(`--stage start`) also calls `_create_item` but then calls
`_set_status("In Progress")` and returns its own message (line ~553), which is
correct and must stay unchanged.

Observed 2026-11-01: `make sync-project-draft f=TASK-098` printed "(status:
In Progress)", while `gh project item-list 2 --owner CmdrPrompt` showed
TASK-098 as "Todo".

Requirement 6 states the item status is left at the Project's default, so the
message cannot know the status. The Requirement 6 and Requirement 17
use-case examples were aligned with the success-message clause when the
clause was added; they no longer show a status for `draft`/`open`.

Proposed fix direction (not binding): the draft/open message reads "Synced
{id} {title} to GitHub Project item" with no status claim; the start,
backfill and merge messages, which do set a status, keep naming it.
Requirement 17's env-fallback note and the duplicate-item warning appended to
the message must keep working.

Existing tests that will need updating:
- `tests/test_projects_draft_stage.py:148` (`test_draft_stage_behaves_like_open_stage`) asserts `"In Progress" in draft_result.message`; it must instead assert the message names no status.
- `tests/test_projects.py:126-127` and `tests/test_projects_duplicate_items.py:77-78` assert only the task id and title in the message; they should keep passing and need no change unless the message format changes beyond removing the status.
- `tests/test_projects_start_stage.py:177` asserts "In Progress" for `--stage start`; it must remain unchanged (guard against over-correction).

## Branch
**Branch name:** `task/099-draft-open-sync-message-status`
**Switch/create:** `git checkout -b task/099-draft-open-sync-message-status`
**Make target:** `make branch-task f=TASK-099`

## Acceptance criteria (Gherkin)
**Feature files:** tests/bdd/features/TASK-099-draft-open-sync-message-status.feature

- [ ] 1. See `tests/bdd/features/TASK-099-draft-open-sync-message-status.feature`: Scenario "Draft sync of a new item does not claim a status" (@AC-1)
- [ ] 2. See `tests/bdd/features/TASK-099-draft-open-sync-message-status.feature`: Scenario "Draft sync of an already linked item does not claim a status" (@AC-2)
- [ ] 3. See `tests/bdd/features/TASK-099-draft-open-sync-message-status.feature`: Scenario "Open sync does not claim a status" (@AC-3)
- [ ] 4. See `tests/bdd/features/TASK-099-draft-open-sync-message-status.feature`: Scenario "Start sync still reports In Progress" (@AC-4)
- [ ] 5. See `tests/bdd/features/TASK-099-draft-open-sync-message-status.feature`: Scenario "Appended notes are preserved" (@AC-5)

## Out of scope
- Making `--stage draft` or `--stage open` set a Status (Requirement 6 says no default status is forced).
- Changing the `--stage start`, `backfill` or `merge` messages.
- Changing the GitHub Projects status-sync timing.

## Blockers
None

## Completion
**Date:** YYYY-MM-DD
**Summary:** What was done, any decisions made, and what was left out and why.
**Files changed:**
- `path/to/file` - created / modified
**Branch:** `git checkout task/099-draft-open-sync-message-status`
**Stage:** `src/butler_core/projects.py tests/test_projects_draft_stage.py CHANGELOG.md docs/tasks/TASK-099-draft-open-sync-message-status.md tests/bdd/features/TASK-099-draft-open-sync-message-status.feature tests/bdd/steps/test_task_099_steps.py`
**Commit:** `git commit -m "Stop draft and open sync messages claiming a Status they did not set (TASK-099)"`
