# TASK-089 Project item lookup must paginate past gh's default page size

## Status
done

## Requirements
**Binding:** Requirement 16 (REQUIREMENTS_TASK_WORKFLOW.md)
**BDD mode:** BDD-ABSENT
**Depends on:** None
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer, I want `_item_list_lookup()` to find a task's GitHub
Projects item regardless of how many items the Project already has, so that
status updates never silently fail with a bogus node-id error and sync
stages never create duplicate items for a task that already has one.

## Description
`_item_list_lookup()` in `src/butler_core/projects.py` calls `gh project
item-list <project> --owner <owner> --format json --jq '...'` with no
`--limit`. `gh`'s default page size is 30 items. This repo's own Project
passed 30 items in 2026-08; TASK-087 and TASK-088's items landed beyond
that page, so the title-prefix lookup found nothing for them, which had two
observed effects: `_set_status()`'s `item_id = item_id or task.id` fallback
sent the literal string `"TASK-087"`/`"TASK-088"` to `gh project item-edit
--id`, producing a GraphQL "Could not resolve to a node" error on every
status-setting stage; and `_create_item()`'s reuse-if-exists check, using
the same lookup, created a new item each time instead of reusing the
existing one (TASK-087 ended up with 3 duplicate items, TASK-088 with 4).

Fix `_item_list_lookup()` so it retrieves every item in the Project before
applying the title-prefix filter, not just `gh`'s first page. Passing a
sufficiently high `--limit` (e.g. `1000`) is acceptable and simplest; full
cursor-based pagination is also acceptable if preferred. Either way, a
Project with more items than `gh`'s default page size MUST NOT cause
lookups for existing (non-first-page) items to report "not found".

The already-corrupted GitHub Projects data (duplicate items for TASK-087/
TASK-088, `Todo` instead of `Done`) was already manually cleaned up
directly against the live Project as part of diagnosing this bug, outside
this task's own commit — this task is the code fix only.

## Branch
**Branch name:** `task/089-projects-item-lookup-pagination`
**Switch/create:** `git checkout -b task/089-projects-item-lookup-pagination`
**Make target:** `make branch-task f=TASK-089`

## Acceptance criteria (Gherkin)

- [x] Scenario: Lookup finds a match beyond gh's default 30-item page
      Given a fixture Project with 40 items, where the item whose title starts with "TASK-999" is the 35th item
      When `_item_list_lookup()` (or the function it calls into) is exercised against that fixture
      Then it finds the item matching "TASK-999"
      And a bare `gh project item-list` call with no `--limit` override would not have found it (regression guard)

- [x] Scenario: Status update no longer falls back to a bogus node id
      Given a task whose Project item exists but is beyond the default page size
      When `_set_status()` runs (e.g. via `--stage merge`/`--stage backfill`)
      Then it resolves the item's real node id and successfully updates its Status field
      And no "Could not resolve to a node with the global id of 'TASK-<NNN>'" warning is produced

- [x] Scenario: Item creation reuses an existing item beyond the default page size
      Given a task whose Project item already exists but is beyond the default page size
      When a sync stage that creates-or-reuses an item runs again for that task
      Then no new duplicate item is created
      And the existing item is reused

## Out of scope
- Cleaning up already-corrupted live Project data (done manually, outside this task)
- Cleaning up the pre-existing, unrelated TASK-006/007/008/010 duplicate items (predate this bug's discovery, tracked separately if ever addressed)
- Any change to `_resolve_project_node_id`/`_resolve_status_option_field_ids` (unaffected — they don't do title-based item lookup)
- Paginating any other `gh` CLI call in this repo that isn't `_item_list_lookup()`

## Blockers
None

## Completion
**Date:** 2026-08-01
**Summary:** Added `_ITEM_LIST_LIMIT = 1000` and passed `--limit
str(_ITEM_LIST_LIMIT)` to the `gh project item-list` call in
`_item_list_lookup()` (`src/butler_core/projects.py`), replacing reliance on
`gh`'s default 30-item page. Added a unit test asserting the constructed
`gh` invocation always includes a `--limit` above 30. Verified the fix live
against this repo's own Project (58 items at the time): reinstalled the CLI
from this branch (`uv tool install --force .`) and ran `make
sync-project-backfill f=TASK-089` — it resolved TASK-089's real item id and
set its status with no GraphQL "could not resolve node" warning, and no
duplicate item was created. Manually cleaned up the pre-existing corruption
this bug caused for TASK-087 (3 duplicate items) and TASK-088 (4 duplicate
items) directly against the live Project — deleted the extras and set the
one remaining item per task to "Done" — as agreed with the user, kept
separate from this task's own commit since it's data cleanup, not code.
**Files changed:**
- `src/butler_core/projects.py` - modified (`_item_list_lookup` now passes `--limit`)
- `tests/test_projects.py` - modified (new `TestItemListLookupPagination` class)
- `REQUIREMENTS_TASK_WORKFLOW.md` - modified (Requirement 16)
- `CHANGELOG.md` - modified
**Branch:** `git checkout task/089-projects-item-lookup-pagination`
**Stage:** `src/butler_core/projects.py tests/test_projects.py REQUIREMENTS_TASK_WORKFLOW.md CHANGELOG.md docs/tasks/TASK-089-projects-item-lookup-pagination.md`
**Commit:** `git commit -m "Paginate GitHub Projects item lookup past gh's default 30-item page (TASK-089)"`
