# TASK-090 Warn when Project resolution falls back to the global `BUTLER_GITHUB_PROJECT` env var

## Status
todo

## Requirements
**Binding:** Requirement 6 (REQUIREMENTS_TASK_WORKFLOW.md)
**BDD mode:** BDD-ABSENT
**Depends on:** None
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer working across multiple repos governed by butler, I want to
be told when a repo's Project number resolution used the global
`BUTLER_GITHUB_PROJECT` environment variable instead of a repo-local
`.butler-project` file, so that I notice immediately when a repo is
silently borrowing another repo's Project number instead of failing loudly
or being flagged.

## Description
Discovered live in `CmdrPrompt/firefly-bank-importer`: a new GitHub Project
(#3) was created for that repo, but the repo had no `.butler-project` file
at its root. `BUTLER_GITHUB_PROJECT=2` was exported globally in the user's
shell profile for unrelated work on `python-butler`'s own Project (#2).
Per Requirement 6, `_project_number()` correctly fell back to the env var
when the file was absent — but this meant every sync in
`firefly-bank-importer` silently wrote to `python-butler`'s Project (#2)
instead of the intended Project (#3), with no warning at any point, because
Requirement 4's "no project configured" warning only fires when the env var
is *also* unset. There is currently no way to distinguish, from butler's
output, "this repo correctly resolved its Project via the env var" from
"this repo has no local config and is silently reusing whatever Project the
shell happens to have set for a different repo."

Add a distinct warning (or informational message) emitted whenever
project-number resolution used the `BUTLER_GITHUB_PROJECT` environment
variable fallback rather than a repo-local `.butler-project` file, e.g.:

```
Note: TASK-XXX synced to GitHub Project 2 via $BUTLER_GITHUB_PROJECT (no .butler-project file in this repo) - if this isn't the right Project for this repo, run: echo <number> > .butler-project
```

This MUST be additive to Requirement 6's existing resolution order (file
first, env var fallback) — no change to which Project ultimately gets used,
only visibility into which source was used. The message MUST NOT fire when
`.butler-project` is present (the common, already-unambiguous case), and
MUST NOT block or fail the sync (same best-effort posture as Requirement 4).

## Branch
**Branch name:** `task/090-warn-on-env-var-project-fallback`
**Switch/create:** `git checkout -b task/090-warn-on-env-var-project-fallback`
**Make target:** `make branch-task f=TASK-090`

## Acceptance criteria (Gherkin)

- [ ] Scenario: Resolution via env var fallback emits a visibility note
      Given a repo with no `.butler-project` file
      And `BUTLER_GITHUB_PROJECT` set in the environment
      When a sync stage resolves the Project number
      Then a "Note: ... via $BUTLER_GITHUB_PROJECT (no .butler-project file in this repo)" message is emitted
      And the sync still proceeds against that Project number

- [ ] Scenario: Resolution via repo-local file emits no such note
      Given a repo with a `.butler-project` file present
      When a sync stage resolves the Project number
      Then no env-var-fallback note is emitted

## Out of scope
- Changing Requirement 6's resolution precedence (file first, env var
  fallback) — unchanged
- Refusing to sync, or requiring confirmation, when falling back to the env
  var — still best-effort per Requirement 4
- Retroactively auditing other repos for a missing `.butler-project` file
  (each repo's own maintainer's responsibility; `firefly-bank-importer`'s
  was fixed directly, outside this task)

## Blockers
None

## Completion
**Date:** TBD
**Summary:** TBD
**Files changed:**
- `path/to/file` - created / modified
**Branch:** `git checkout task/090-warn-on-env-var-project-fallback`
**Stage:** `path/to/file1 path/to/file2 CHANGELOG.md`
**Commit:** `git commit -m "Warn when Project resolution falls back to the global BUTLER_GITHUB_PROJECT env var"`
