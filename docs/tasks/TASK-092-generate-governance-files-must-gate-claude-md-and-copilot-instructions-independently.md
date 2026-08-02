# TASK-092 `generate-governance-files` must gate `CLAUDE.md` and `.github/copilot-instructions.md` independently

## Status
todo

## Requirements
**Binding:** Requirements 1-3 (REQUIREMENTS_GOVERNANCE_FILE_GATING.md)
**BDD mode:** BDD-PLANNED
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a new project maintainer running `make init-project` for the first time,
I want `CLAUDE.md` to be generated even if a previous partial run already
created `.github/copilot-instructions.md`, so that I'm not permanently stuck
unable to generate `CLAUDE.md` without `FORCE=1` overwriting files that
weren't actually missing.

## Description
`generate-governance-files` (`src/butler_core/data/Makefile:457-461`) guards
`CLAUDE.md` and `.github/copilot-instructions.md` behind two sequential
existence checks before writing either file. If
`.github/copilot-instructions.md` already exists (e.g. from an earlier
interrupted or FORCE-less `init-project` run) but `CLAUDE.md` does not, the
second check aborts the entire recipe with exit code 1 — before the line
that writes `CLAUDE.md` (`src/butler_core/data/Makefile:468`) is ever
reached. Every subsequent run hits the identical abort, since
`copilot-instructions.md`'s check never passes without `FORCE=1`, and
`CLAUDE.md`'s check never fails since it's still missing: the project is
stuck.

Reproduced 2026-08-02 in `firefly-household-splitter`: `.github/`,
`.gitignore`, and `.pre-commit-config.yaml` existed from a prior run, but
`CLAUDE.md` did not. Running `make init-project` printed
`.github/copilot-instructions.md already exists. Run with FORCE=1 to
overwrite.` and aborted `generate-governance-files` with `Error 1`, yet the
"✓ Done. Stage and commit with" message still listed `CLAUDE.md` in its
`git add` instructions (`src/butler_core/data/Makefile:378`), so `git add
CLAUDE.md` failed with `pathspec 'CLAUDE.md' did not match any files`.

Fix: gate each guarded output file (`CLAUDE.md`,
`.github/copilot-instructions.md`) on its own existence check independently,
so a missing file is generated regardless of whether a sibling file already
exists, per REQUIREMENTS_GOVERNANCE_FILE_GATING.md Requirement 1. A file
that already exists is still left untouched without `FORCE=1`, per
Requirement 2. The `init-project` completion message must only list files
that were actually written during that run, per Requirement 3.

## Branch
**Branch name:** `task/092-generate-governance-files-must-gate-claude-md-and-copilot-instructions-independently`
**Switch/create:** `git checkout -b task/092-generate-governance-files-must-gate-claude-md-and-copilot-instructions-independently`
**Make target:** `make branch-task f=TASK-092`

## Acceptance criteria (Gherkin)
**Feature files:** None

- [ ] 1. Scenario: Missing CLAUDE.md is generated even when copilot-instructions.md already exists
      Given `.github/copilot-instructions.md` exists and `CLAUDE.md` does not,
      and `FORCE` is not set
      When `make generate-governance-files` runs
      Then `CLAUDE.md` is created
      And `.github/copilot-instructions.md` is left unchanged
      And the command reports `.github/copilot-instructions.md already exists. Run with FORCE=1 to overwrite.`
      without exiting with a non-zero status that prevents `CLAUDE.md` from being written
- [ ] 2. Scenario: A file that already exists is not overwritten without FORCE=1
      Given both `CLAUDE.md` and `.github/copilot-instructions.md` already exist
      When `make generate-governance-files` runs without `FORCE=1`
      Then neither file's content changes
- [ ] 3. Scenario: init-project's completion message lists only files actually written
      Given `.github/copilot-instructions.md` exists and `CLAUDE.md` does not
      When `make init-project` runs and answers the interactive prompts
      Then the final "Stage and commit with" `git add` line lists `CLAUDE.md`
      but does not list `.github/copilot-instructions.md`'s containing path
      as newly generated when it was skipped

## Out of scope
- Changing what `FORCE=1` overwrites once all guarded files already exist.
- Deduplicating the guard-and-generate pattern across other single-file
  `generate-*` targets.
- The shell-quoting bug covered by TASK-093 / REQUIREMENTS_TEMPLATE_VAR_SHELL_SAFETY.md.

## Blockers
None

## Completion
**Date:**
**Summary:**
**Files changed:**
**Branch:** `git checkout task/092-generate-governance-files-must-gate-claude-md-and-copilot-instructions-independently`
**Stage:**
**Commit:**
