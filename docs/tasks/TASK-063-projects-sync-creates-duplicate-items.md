# TASK-063 GitHub Projects sync creates duplicate items instead of linking to an existing one

## Status
done

## Requirements
**Binding:** Requirement 4 (REQUIREMENTS_TASK_WORKFLOW.md)
**BDD mode:** BDD-ABSENT
**Depends on:** None
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer running more than one sync stage for the same task (e.g.
`--stage draft` right after Task Drafter, then `--stage open` automatically
via `make pr-current-task`, then `--stage merge` via `make merge-current-task`),
I want the sync to reuse the single Project item already linked to that task
instead of creating a new one each time, so the Project board doesn't
accumulate duplicate items and the merge-stage status update doesn't fail.

## Description
**Bug:** `_create_item()` in `src/butler_core/projects.py` unconditionally
runs `gh project item-create` on every call, with no check for whether a
Project item already exists for the task. `sync_on_pr_draft`,
`sync_on_pr_open`, and `sync_on_pr_backfill` all funnel into `_create_item`,
so running more than one of these stages for the same task (a normal
sequence: draft -> open -> merge, or the new backfill stage run more than
once) creates one Project item per call instead of reusing the one already
linked.

This was observed live while completing TASK-062: `--stage draft` was run
manually, then `make pr-current-task` ran `--stage open` automatically,
producing two Project items both titled `TASK-062 Backfill sync for
historical tasks...`. The subsequent `--stage merge` step's status-update
lookup, `_item_list_lookup()`'s `--jq` filter (`select(.content.title |
startswith(task.id)) | .id`), matched both items and returned their two IDs
newline-joined in one string. `_update_status_done()` (and the new
`_backfill()` added by TASK-062) both do `item_result.stdout.strip()` and
pass that directly as the single `--id` value to `gh project item-edit`,
producing a malformed ID and a GraphQL failure:

```text
Warning: could not sync TASK-062 to GitHub Projects (GraphQL: Could not
resolve to a node with the global id of
'PVTI_lAHOAAnLPc4BfBkxzg02Ge8
PVTI_lAHOAAnLPc4BfBkxzg02QOQ' (updateProjectV2ItemFieldValue)) - continuing
```

The failure was correctly reported as a best-effort warning and did not
block the merge (Requirement 4's contract held), but the underlying
duplication and the unsafe single-ID assumption are both real defects.

**Location:** `src/butler_core/projects.py:201-227` (`_create_item`,
no existing-item check) and `src/butler_core/projects.py:273-291`
(`_item_list_lookup`/callers assume exactly one matching line of output).
**Requirement violated:** "attempt to **create or link** a GitHub Projects
item for that PR" (Requirement 4, REQUIREMENTS_TASK_WORKFLOW.md) — the
"or link" half is unimplemented; every call creates.
**Severity:** high (silently corrupts the Project board with duplicates and
breaks the merge-stage status update whenever more than one sync stage runs
for the same task, which is the normal multi-stage flow this repo uses on
every task).

**Implementation location (for the follow-up fix, not this task):**
`src/butler_core/projects.py` (`_create_item`, `_item_list_lookup` and its
callers `_update_status_done`/`_backfill`), plus regression tests in
`tests/test_projects.py` / `tests/test_projects_backfill.py` or a new
`tests/test_projects_duplicate_items.py`.

## Branch
**Branch name:** `task/063-projects-sync-creates-duplicate-items`
**Switch/create:** `git checkout -b task/063-projects-sync-creates-duplicate-items`
**Make target:** `make branch-task f=TASK-063`

## Acceptance criteria (Gherkin)

- [x] Characterization test added that captures the current (broken) behavior
      Given a task already has a linked GitHub Projects item
      When a second sync stage (e.g. `--stage open` after `--stage draft`) runs for the same task
      Then a test demonstrates `_create_item`/`gh project item-create` is invoked again, producing a second item (documenting today's duplication bug as-is)

- [x] Requirement updated in the requirements document if needed
      Given Requirement 4 already says "create or link" but only "create" is implemented
      When this task is scoped
      Then confirm with the user whether Requirement 4's text needs clarification (e.g. explicit "link to an existing item, identified by title prefix, before falling back to creating a new one") or is already sufficient as binding text for the fix

- [x] Bug fixed, test updated to assert the correct behavior
      Given a task already has a linked GitHub Projects item
      When any sync stage runs again for that task
      Then no new item is created — the existing item (found via the same title-prefix lookup `_item_list_lookup` already performs) is reused/linked instead, and `_item_list_lookup`'s callers handle a multi-line/multi-match result safely (e.g. use the first match and log/warn on an unexpected multiple-match instead of concatenating IDs) rather than assuming exactly one line of output

- [x] make lint && make test pass

- [x] CHANGELOG.md updated

## Out of scope
- Cleaning up any further duplicate items already created on real GitHub
  Project boards by past sync runs — that is a one-off manual cleanup, not
  code behavior (the TASK-062 duplicate found live was already removed
  manually outside this task).
- Any change to the one-way sync contract (Requirement 4): still nothing is
  read back from GitHub Projects into task files, the CLI, or any agent.
- Any change to `--stage backfill`'s Status/Created/Closed field logic
  beyond the shared `_create_item`/item-lookup fix (TASK-062's own
  acceptance criteria are unaffected by this bug).

## Blockers
None

## Completion
**Date:** 2026-07-31
**Summary:** `_create_item` now looks up an existing Project item (by
TASK-ID title prefix, via the shared `_item_list_lookup`) before creating
one, and reuses it instead of creating a duplicate across `draft`/`open`/
`merge`/`backfill` sync stages. `_update_status_done` and
`_backfill_resolve_and_set_status` now take only the first matching item ID
via a new `_select_item_id` helper instead of assuming exactly one line of
`item-list` output, so a stale multi-match can no longer be concatenated
into a malformed `--id` value. Requirement 4 in
`REQUIREMENTS_TASK_WORKFLOW.md` was clarified (user-confirmed) to spell out
that "link" means look-up-then-reuse across all sync stages.
**Files changed:** `REQUIREMENTS_TASK_WORKFLOW.md`,
`src/butler_core/projects.py`, `tests/test_projects_backfill.py`,
`tests/test_projects_duplicate_items.py` (new), `CHANGELOG.md`,
`docs/tasks/TASK-063-projects-sync-creates-duplicate-items.md`
**Branch:** `git checkout task/063-projects-sync-creates-duplicate-items`
**Stage:** `git add src/butler_core/projects.py tests/test_projects*.py CHANGELOG.md docs/tasks/TASK-063-projects-sync-creates-duplicate-items.md`
**Commit:** `git commit -m "Fix GitHub Projects sync creating duplicate items instead of linking to an existing one"`
