# TASK-085 Mark butler sync deprecated

## Status
todo

## Requirements
**Binding:** Requirement 14: `butler sync` marked deprecated ahead of removal
**BDD mode:** BDD-ACTIVE
**Feature files:** `tests/bdd/features/TASK-085-mark-butler-sync-deprecated.feature`
**Depends on:** TASK-071
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer, I want users to see a clear deprecation notice when they run
`butler sync --help` or read the function docstrings, so that they know the
command applies only to `git subtree`-based projects and will be removed,
and they can migrate to the submodule-based distribution model
(`REQUIREMENTS_SUBMODULE.md`) instead.

## Description
Add a visible deprecation notice to `butler sync` without changing its actual
behavior or removing the command. The notice MUST appear in:

1. The CLI help text for `butler sync --help` (`src/butler_cli/__main__.py`'s
   `sync` subparser)
2. The docstring of `sync_makefile()` in `src/butler_core/sync.py`
3. The docstring of `check_sync()` in `src/butler_core/sync.py`

The deprecation message MUST state that:
- The command is deprecated
- It applies only to `git subtree`-based consumer projects
- It will be removed in a future release
- `REQUIREMENTS_SUBMODULE.md` documents the current (submodule-based)
  distribution mechanism

The command's actual behavior MUST NOT change, and all existing sync tests
MUST continue to pass unchanged. This is a documentation/help-text-only
change; actual removal of the `sync` command, `src/butler_core/sync.py`, and
its tests is tracked as a follow-up implementation task once this notice has
shipped (per Requirement 14's final paragraph).

## Branch
**Branch name:** `task/085-mark-butler-sync-deprecated`
**Switch/create:** `git checkout -b task/085-mark-butler-sync-deprecated`
**Make target:** `make branch-task f=TASK-085`

## Acceptance criteria (Gherkin)
- [ ] See `tests/bdd/features/TASK-085-mark-butler-sync-deprecated.feature`: Scenario: butler sync --help displays deprecation notice
- [ ] See `tests/bdd/features/TASK-085-mark-butler-sync-deprecated.feature`: Scenario: sync_makefile docstring mentions deprecation
- [ ] See `tests/bdd/features/TASK-085-mark-butler-sync-deprecated.feature`: Scenario: check_sync docstring mentions deprecation
- [ ] See `tests/bdd/features/TASK-085-mark-butler-sync-deprecated.feature`: Scenario: Existing sync behavior continues unchanged
- [ ] See `tests/bdd/features/TASK-085-mark-butler-sync-deprecated.feature`: Scenario: All existing sync tests pass

## Out of scope
- Removing the `sync` command itself from `src/butler_cli/__main__.py`
- Removing or deprecating `src/butler_core/sync.py`
- Removing or updating sync-related test files
- Removing the `sync` target from the Makefile or other wrapper scripts
- Changing the command's actual behavior or any of its flags
- Removing sync documentation from README.md or other reference docs (only adding
  a deprecation notice, not removing documented behavior)
- Actually migrating consumer projects off `git subtree` to `git submodule` (that
  is the user's responsibility per REQUIREMENTS_SUBMODULE.md)

## Blockers
None

## Completion
**Date:**
**Summary:**
**Files changed:**
**Branch:** `git checkout task/085-mark-butler-sync-deprecated`
**Stage:** `src/butler_cli/__main__.py src/butler_core/sync.py CHANGELOG.md`
**Commit:** `git commit -m "Add deprecation notice to butler sync command and docstrings"`
