# TASK-091 `generate-governance-files FORCE=1` overwrites project name/description with placeholders

## Status
done

## Requirements
**Binding:** Requirements 1-3 (REQUIREMENTS_GOVERNANCE_REGEN.md)
**BDD mode:** BDD-PLANNED
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a consumer project maintainer running `make butler-pull` followed by
`make generate-governance-files FORCE=1` to pick up updated templates/agents/
skills, I want my project's real name and description preserved in
`CLAUDE.md` and `.github/copilot-instructions.md`, so that a routine butler
update doesn't silently clobber my project identity with placeholder text.

## Description
`generate-governance-files` substitutes the `PROJECT_NAME`/
`PROJECT_DESCRIPTION` Make variables into `CLAUDE.md` and
`.github/copilot-instructions.md`. Those variables default to the
placeholders `my-project` / `Describe your project here.`
(`src/butler_core/data/Makefile:13-14`) and are set to the real project's
values only once, interactively, during `make init-project` — the answer is
never persisted anywhere. The documented regeneration path after
`butler-pull` (`make generate-governance-files FORCE=1`, per
`REQUIREMENTS_BUTLER_PULL.md` Requirement 1's use case and BDD-051) never
re-passes those variables, so the Makefile silently falls back to the
placeholder defaults and overwrites the project's real name/description with
generic text — no warning, no diff, no error exit.

Reproduced 2026-08-02 in `firefly-python-api`: after `make butler-pull`
updated `.butler/claude-skills/commit-workflow/SKILL.md`, running
`make generate-governance-files FORCE=1` to pick up that change also
rewrote `CLAUDE.md`'s title from `firefly-python-api` to `my-project` and
its description to `Describe your project here.`, and did the same to
`.github/copilot-instructions.md`. Caught only because the change was
visible in `git diff` before commit; a project that commits without
reviewing the diff would lose this silently.

Fix should extract the current name/description from the existing
`CLAUDE.md` (its `# <name>` H1 and the paragraph below it) when
`PROJECT_NAME=`/`PROJECT_DESCRIPTION=` aren't explicitly passed and a prior
`CLAUDE.md` exists, per REQUIREMENTS_GOVERNANCE_REGEN.md Requirement 1.
Explicit variables still override (Requirement 2). First-time generation
(no prior `CLAUDE.md`) is unaffected (Requirement 3).

## Branch
**Branch name:** `task/091-generate-governance-files-force-overwrites-project-name-description`
**Switch/create:** `git checkout -b task/091-generate-governance-files-force-overwrites-project-name-description`
**Make target:** `make branch-task f=TASK-091`

## Acceptance criteria (Gherkin)
**Feature files:** None

- [x] 1. Scenario: FORCE=1 regeneration preserves existing project name and description
      Given a project has an existing `CLAUDE.md` with title `firefly-python-api`
      and a real description, and `PROJECT_NAME`/`PROJECT_DESCRIPTION` are not
      passed on the command line
      When `make generate-governance-files FORCE=1` runs
      Then `CLAUDE.md` and `.github/copilot-instructions.md` retain the
      `firefly-python-api` name and the original description, not
      `my-project` / `Describe your project here.`
- [x] 2. Scenario: Explicit PROJECT_NAME/PROJECT_DESCRIPTION still override
      Given a project has an existing `CLAUDE.md` with title `firefly-python-api`
      When `make generate-governance-files FORCE=1 PROJECT_NAME="renamed-project" PROJECT_DESCRIPTION="New description."` runs
      Then `CLAUDE.md` and `.github/copilot-instructions.md` show
      `renamed-project` and `New description.`
- [x] 3. Scenario: First-time generation is unaffected
      Given no `CLAUDE.md` exists yet
      When `make generate-governance-files` (with or without `FORCE=1`) runs
      without explicit `PROJECT_NAME`/`PROJECT_DESCRIPTION`
      Then `CLAUDE.md` and `.github/copilot-instructions.md` use the
      Makefile placeholder defaults `my-project` / `Describe your project
      here.`, exactly as before this change

## Out of scope
- Persisting or restoring any other CLAUDE.md customization beyond the
  project name/description line.
- Changing `init-project`'s interactive prompt flow.
- Changing what other template variables are substituted.

## Blockers
None

## Completion
**Date:** 2026-08-03
**Summary:** `generate-governance-files` now extracts the current project
name/description from an existing `CLAUDE.md` (its `# <name>` H1 and the
paragraph below it) when `PROJECT_NAME=`/`PROJECT_DESCRIPTION=` are not
explicitly passed on the command line, and reuses those values for both
`CLAUDE.md` and `.github/copilot-instructions.md` template substitution
instead of falling back to the `my-project` / `Describe your project here.`
Makefile defaults. Uses `$(origin PROJECT_NAME)`/`$(origin
PROJECT_DESCRIPTION)` to distinguish an explicit command-line value (which
still wins, Requirement 2) from the Makefile default. First-time generation
(no prior `CLAUDE.md`) is unaffected (Requirement 3) since extraction only
runs when `CLAUDE.md` already exists on disk. Applied identically to
`Makefile` and the vendored `src/butler_core/data/Makefile` copy.
**Files changed:**

- `Makefile` — modified (extraction logic in `generate-governance-files`)
- `src/butler_core/data/Makefile` — modified (re-synced vendored copy)
- `tests/test_governance_regen_preserves_identity.py` — new (acceptance
  tests for Requirements 1-3)
- `CHANGELOG.md` — modified
- `docs/tasks/TASK-091-generate-governance-files-force-overwrites-project-name-description.md` — modified
**Branch:** `git checkout task/091-generate-governance-files-force-overwrites-project-name-description`
**Stage:** `Makefile src/butler_core/data/Makefile tests/test_governance_regen_preserves_identity.py CHANGELOG.md docs/tasks/TASK-091-generate-governance-files-force-overwrites-project-name-description.md`
**Commit:** `git commit -m "Fix generate-governance-files FORCE=1 clobbering project name/description with placeholders (TASK-091)"`
