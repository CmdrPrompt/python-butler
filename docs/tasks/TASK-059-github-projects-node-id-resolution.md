# TASK-059 Resolve GitHub Projects v2 node IDs for the sync's status update

## Status
done

## Requirements
**Binding:** Requirement 5 (REQUIREMENTS_TASK_WORKFLOW.md)
**BDD mode:** BDD-ABSENT
**Depends on:** none
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer running `make merge-current-task`, I want the GitHub Projects sync's status update to actually succeed against a real Projects v2 board, so that merging a task's PR reliably moves its linked Project item to "Done" instead of failing with a GraphQL "could not resolve node" error every time.

## Description
`butler task sync-project <id> --stage merge` (`_sync()` in
`src/butler_core/projects.py`) calls `gh project item-edit --project-id
<project> --field-id "Status" --single-select-option-id "Done"`, where
`<project>` is the raw `BUTLER_GITHUB_PROJECT` number (e.g. `2`). GitHub
Projects v2's GraphQL API requires `--project-id`, `--field-id`, and
`--single-select-option-id` to be the actual GraphQL node IDs
(`PVT_...`, `PVTSSF_...`, and an option ID like `98236657`), not the plain
project number or the literal strings `"Status"`/`"Done"`. This was
confirmed live while completing TASK-058: the `--stage open` item-create
call succeeded (it only needs the plain project number), but `--stage
merge` failed with `GraphQL: Could not resolve to a node with the global id
of '2'`.

This task makes `_sync()` resolve the Project's node ID and the "Status"
field's/"Done" option's node IDs via `gh project view`/`gh project
field-list` before calling `item-edit`, so the merge-stage status update
actually works. It stays within the existing best-effort contract: if the
Project has no "Status" field or "Done" option, that's a warning, not a
raised exception.

**Implementation location:** `src/butler_core/projects.py` (`_sync`, plus
new helper(s) to resolve node IDs), `tests/test_projects.py` and related
test files for the new lookups.

## Branch
**Branch name:** `task/059-github-projects-node-id-resolution`
**Switch/create:** `git checkout -b task/059-github-projects-node-id-resolution`
**Make target:** `make branch-task f=TASK-059`

## Acceptance criteria (Gherkin)

- [x] Scenario: Merge-stage sync resolves node IDs and updates a real Project item
      Given `BUTLER_GITHUB_PROJECT` is set to a valid project number with a "Status" field containing a "Done" option, and a Project item already linked for the task
      When `sync_on_pr_merge` (or `butler task sync-project <id> --stage merge`) runs
      Then the sync looks up the project's node ID and the "Status" field's/"Done" option's node IDs, and calls `gh project item-edit` with those resolved IDs (not the raw project number or the literal strings "Status"/"Done"), succeeding with `SyncResult(success=True, ...)`

- [x] Scenario: Configured Project has no "Status" field or no "Done" option
      Given `BUTLER_GITHUB_PROJECT` points at a Project lacking a "Status" field (or a "Status" field lacking a "Done" option)
      When the merge-stage sync runs
      Then it returns `SyncResult(success=False, ...)` with a warning message, and never raises or blocks the caller

- [x] Scenario: Open-stage item-create is unaffected
      Given the existing `--stage open` behavior (item-create using the plain project number)
      When the open-stage sync runs
      Then its behavior and `gh` invocation are unchanged by this task

## Out of scope
- Reading any field value back from GitHub Projects into the task workflow
  (still strictly one-way, per Requirement 4).
- Changing `BUTLER_GITHUB_PROJECT` to hold a node ID instead of a plain
  number — it stays a human-facing project number; resolution to node IDs
  happens internally in the sync.
- Caching/memoizing resolved node IDs across invocations — each sync call
  may re-resolve them.

## Blockers
None

## Completion
**Date:** 2026-07-31
**Summary:** Split `_sync()` in `src/butler_core/projects.py` into
`_create_item` (open stage, unchanged behavior) and `_update_status_done`
(merge stage), and added `_resolve_project_node_id`/
`_resolve_status_done_field_ids` helpers that call `gh project view` and
`gh project field-list` to look up the Project's GraphQL node ID and the
"Status" field's/"Done" option's node IDs before calling `gh project
item-edit`. A missing "Status" field or "Done" option now returns a
best-effort `SyncResult(success=False, ...)` warning instead of letting
GitHub's GraphQL API reject the raw project number/literal strings. The
`_sync` function itself was split out into a small dispatcher to keep
cyclomatic complexity within the `make lint` gate (previously a single
18-branch function). Verified live against the real
`CmdrPrompt/python-butler` GitHub Project (#2): after node-ID resolution,
`butler task sync-project TASK-058 --stage merge` (run manually, since the
TASK-058 PR had already been merged before this fix landed) successfully
moved the TASK-058 Project item to status "Done". Coverage held at the
99% task-start baseline by adding tests for the merge-stage exception/
failure paths that were previously covered implicitly through the
unsplit function.
**Files changed:**
- `src/butler_core/projects.py` - modified
- `tests/test_projects.py` - modified
- `CHANGELOG.md` - modified
- `REQUIREMENTS_TASK_WORKFLOW.md` - modified (Requirement 5, confirmed with user before implementation)
- `docs/tasks/TASK-059-github-projects-node-id-resolution.md` - modified
**Branch:** `git checkout task/059-github-projects-node-id-resolution`
**Stage:** `git add src/butler_core/projects.py tests/test_projects.py CHANGELOG.md REQUIREMENTS_TASK_WORKFLOW.md docs/tasks/TASK-059-github-projects-node-id-resolution.md`
**Commit:** `git commit -m "Fix GitHub Projects sync to resolve GraphQL node IDs for the merge-stage status update"`
