# TASK-087 Migrate pending task files' Stage field to the new plain-path-list format

## Status
done

## Requirements
**Binding:** Requirement 15: Task file Completion `Stage:` field is data, not an executable command
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-086
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer, I want every still-open (non-`done`) task file's Completion
`**Stage:**` field to already use the new plain-file-list format TASK-086
introduced, so that when one of these tasks is eventually completed, running
`butler task stage`/`make stage-current-task` against it stages exactly the
right files instead of a leftover `git add ...` prefix being parsed as two
bogus path tokens.

## Description
Requirement 15 explicitly exempts already-`done` (historical) task files from
migration, since their Stage field is never re-parsed. This task closes the
gap for task files that are *not yet* `done` and therefore will still be
staged/committed for real:

For every `docs/tasks/TASK-*.md` file whose `## Status` is not `done`, and
whose Completion `**Stage:**` field is a filled-in backtick value starting
with `git add`, strip the leading `git add` prefix so the field is a bare
whitespace-separated file list, matching the format `render_task()` now
produces. Task files with an empty/`TBD`/placeholder Stage field, or whose
Status could not be parsed (pre-existing malformed headers, e.g. TASK-039,
TASK-040), are left untouched — there is nothing meaningful to migrate.

## Branch
**Branch name:** `task/087-migrate-pending-task-files-stage-field-to-new-format`
**Switch/create:** `git checkout -b task/087-migrate-pending-task-files-stage-field-to-new-format`
**Make target:** `make branch-task f=TASK-087`

## Acceptance criteria (Gherkin)

- [ ] Scenario: Every non-done task file's Stage field has no leading git add
      Given all `docs/tasks/TASK-*.md` files with `## Status` not equal to `done`
      When their Completion `**Stage:**` field is inspected
      Then no such field starts with `git add`
      And `butler_core.tasks.parse_task()` on each still succeeds without error

- [ ] Scenario: Done task files are left untouched
      Given a `docs/tasks/TASK-*.md` file with `## Status` equal to `done`
      When this task's migration runs
      Then that file's Completion section is unchanged

## Out of scope
- Fixing TASK-039/TASK-040's malformed `# TASK-NNN: Title` header (missing-header
  parse failure, pre-existing and unrelated to the Stage field format)
- Migrating `done` task files (explicitly excluded by Requirement 15)
- Any change to `butler_core` or `git_ops.py` (TASK-086 already did that)

## Blockers
None

## Completion
**Date:** 2026-08-01
**Summary:** Stripped the leading `git add` prefix from the Completion `**Stage:**`
field of every non-`done` task file that had one: TASK-027, TASK-049,
TASK-084, TASK-085. TASK-055's `**Stage:** TBD` and TASK-039/TASK-040 (no
Stage field / unparseable header, pre-existing and out of scope) were left
untouched, as was every already-`done` task file per Requirement 15.
Verified with `butler_core.tasks.parse_task()` that all four migrated files
still parse cleanly and `full` test suite passes unchanged.
**Files changed:**
- `docs/tasks/TASK-027-packaging-and-optionality.md` - modified (Stage field)
- `docs/tasks/TASK-049-document-manual-venv-activation.md` - modified (Stage field)
- `docs/tasks/TASK-084-obsolete-task-status.md` - modified (Stage field)
- `docs/tasks/TASK-085-mark-butler-sync-deprecated.md` - modified (Stage field)
- `docs/tasks/TASK-087-migrate-pending-task-files-stage-field-to-new-format.md` - created
**Branch:** `git checkout task/087-migrate-pending-task-files-stage-field-to-new-format`
**Stage:** `docs/tasks/TASK-027-packaging-and-optionality.md docs/tasks/TASK-049-document-manual-venv-activation.md docs/tasks/TASK-084-obsolete-task-status.md docs/tasks/TASK-085-mark-butler-sync-deprecated.md docs/tasks/TASK-087-migrate-pending-task-files-stage-field-to-new-format.md`
**Commit:** `git commit -m "Migrate pending task files' Stage field to the new plain-path-list format (TASK-087)"`
