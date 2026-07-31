# TASK-066 GitHub Projects item body is empty instead of coming from the task file

## Status
done

## Requirements
**Binding:** Requirements 4 and 11 (REQUIREMENTS_TASK_WORKFLOW.md)
**BDD mode:** BDD-ABSENT
**Depends on:** None (references the finding from TASK-064's Completion; not blocked by it)
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story. Requirements 4 and 11 are confirmed and binding; implementation may proceed.

## Story (context, not binding)
As a maintainer who opens a GitHub Projects item (draft or, after
conversion, a real Issue) for a task, I want to see the same description
that the task's PR shows, so the item is useful on its own instead of being
a bare, empty-body placeholder.

## Description
**Bug (observed live, 2026-07-31):** `_create_item()` in
`src/butler_core/projects.py` calls `gh project item-create` with only
`--title`:

```python
result = _run_gh(
    [
        "project",
        "item-create",
        project,
        "--owner",
        owner,
        "--title",
        f"{task.id} {task.title}",
    ],
    env,
)
```

No `--body` is ever passed, so every Project item `_create_item` creates
(via `sync_on_pr_draft`, `sync_on_pr_open`, `sync_on_pr_backfill`, and
`_start`/`sync_on_pr_start`) has an empty body. While the item stays a
`DraftIssue`, the empty body isn't very visible in the Project board UI. It
becomes clearly visible once an item is converted to a real GitHub Issue
(e.g. via the Project UI's "Convert to issue" action) — confirmed live
against this repo's own Project #2: issues #65–#72 (one per existing task
item) were all converted with empty bodies, in contrast to a real PR like
`https://github.com/CmdrPrompt/python-butler/pull/64`, whose body is
populated from the task file's `## Description` section.

The existing PR-body mechanism, `_pr_body()` in `src/butler_core/git_ops.py`
(extracts everything from `## Description` up to `## Completion`), is
**not** the right model to copy here — discussed with the user, who
confirmed the Project item's body must NOT mirror the PR's full technical
`## Description` (often long, implementation-heavy detail meant for
reviewers, not a board glance). Instead, the item body should carry only:

1. The task file's `## Story` section (short, readable "As a ... I want
   ... so that ..." context) — not `## Description`.
2. The task file's `## Acceptance criteria` section (the Gherkin scenarios
   that define done) — without the implementation detail that lives under
   `## Description`.
3. A link back to the task file itself (e.g.
   `docs/tasks/TASK-XXX-*.md` path or a GitHub blob URL), and, once one
   exists, the PR — so the board item is a useful, self-contained summary
   with a path to the full detail rather than a duplicate of it.

**Proposed fix (per user direction):** `_create_item()` should pass
`--body` to `gh project item-create`, built from the Story +
Acceptance-criteria sections plus a task-file link, per the scoping above
— NOT the same extraction `_pr_body()` uses for PRs. This needs its own
extraction helper (e.g. `_project_item_body()`), not a reuse of
`_pr_body()`. `_create_item()` does not currently receive a
`tasks_dir`/file path; its caller, `_sync()`, does receive `tasks_dir`
(used elsewhere in this module by `_task_file_path()`/`_git_log_dates()`
for the backfill stage) but does not thread it through to
`_create_item()`.

**Requirement 11 (confirmed 2026-07-31):** Requirement 4's scope is now
formally extended to include body content. The requirement text defines
exactly what MUST go into the Project item body (Story + Acceptance
criteria + task-file link, plus PR link when one exists), and what MUST
NOT (the Description section), and specifies the need for a separate
extraction helper to keep Project item logic distinct from PR-body logic.

## Branch
**Branch name:** `task/066-project-item-body-from-task-file`
**Switch/create:** `git checkout -b task/066-project-item-body-from-task-file`
**Make target:** `make branch-task f=TASK-066`

## Acceptance criteria (Gherkin)

- [x] Scenario: Project item body includes Story, Acceptance criteria, and task file link (no PR yet)
      Given a task file with `## Story` and `## Acceptance criteria` sections,
      and no PR exists yet for the task
      When `_create_item()` creates a new Project item for that task (e.g. via
      `sync_on_pr_draft`)
      Then the created item's body contains the task file's `## Story` section,
      its `## Acceptance criteria` section, and a link back to the task file,
      and does NOT contain the `## Description` section's content or a PR link

- [x] Scenario: Project item body includes PR link when a PR exists
      Given a task file with `## Story` and `## Acceptance criteria` sections,
      and a PR exists for the task
      When `_create_item()` creates a new Project item for that task (e.g. via
      `sync_on_pr_open` and `sync_on_pr_backfill`)
      Then the created item's body contains the task file's `## Story` section,
      its `## Acceptance criteria` section, a link back to the task file, and
      a link to the PR, and does NOT contain the `## Description` section's content

- [x] Scenario: Missing task file falls back to the existing title-only behavior
      Given `tasks_dir` is unset, or no task file can be located for the task
      When `_create_item()` runs
      Then the item is still created with `--title` only (current behavior),
      per Requirement 4's best-effort warning contract — a missing file MUST
      NOT block item creation

- [x] make lint && make test pass

- [x] CHANGELOG.md updated

## Out of scope
- Updating the body of a Project item that already exists (this task only
  covers item *creation*; retroactively backfilling bodies onto the 8
  already-converted real Issues #65–#72, or any other existing item, is not
  part of this task).
- Any change to how `open_pr_for()`/`_pr_body()` build PR bodies — this task
  only extends the Project-item path to use a separate extraction logic
  (Story + Acceptance criteria, never Description).
- Any change to the "Convert to issue" board behavior itself (that's a
  GitHub Projects UI action, not something `butler` controls).

## Blockers
None

## Completion
**Date:** 2026-08-01
**Summary:** `_create_item()` now passes `--body` to `gh project
item-create`, built by a new `_project_item_body()` helper from the task
file's `## Story` and `## Acceptance criteria` sections (verbatim) plus a
repo-relative link to the task file — never the `## Description` section,
and never reusing `_pr_body()`'s extraction logic (a dedicated
`_extract_section()` helper is used instead). A PR link (via a GitHub "PRs
for this branch" search URL, `_project_item_pr_link()`) is appended for
call sites where a PR already exists (`sync_on_pr_open`,
`sync_on_pr_backfill`) but omitted for `sync_on_pr_draft`/`sync_on_pr_start`,
which run before a PR exists. `tasks_dir` is now threaded through
`_create_item()`/`_start()`/`_sync()`. A missing/unresolvable task file
falls back to today's `--title`-only creation without raising, per
Requirement 4's best-effort contract. Requirement 11 was added to
REQUIREMENTS_TASK_WORKFLOW.md (confirmed by the user) to formalize this
scope. `make lint && make test` pass: 306 tests (up from the 297 baseline),
99% coverage (795 stmts/7 missing, up from 757/8 — no regression).
**Files changed:** `REQUIREMENTS_TASK_WORKFLOW.md` (Requirement 11 added),
`docs/tasks/TASK-066-project-item-body-from-task-file.md`,
`src/butler_core/projects.py`, `tests/test_projects.py`, `CHANGELOG.md`
**Branch:** `git checkout task/066-project-item-body-from-task-file`
**Stage:** `git add REQUIREMENTS_TASK_WORKFLOW.md docs/tasks/TASK-066-project-item-body-from-task-file.md src/butler_core/projects.py tests/test_projects.py CHANGELOG.md`
**Commit:** `git commit -m "Fix GitHub Projects item body being empty instead of coming from the task file"`
