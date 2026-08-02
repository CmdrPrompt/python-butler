# TASK-093 Template variable substitution breaks (and corrupts unrelated files) on single quotes in PROJECT_DESCRIPTION

## Status
todo

## Requirements
**Binding:** Requirement 1 (REQUIREMENTS_TEMPLATE_VAR_SHELL_SAFETY.md)
**BDD mode:** BDD-PLANNED
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a project maintainer answering `init-project`'s interactive
`PROJECT_DESCRIPTION` prompt in plain English, I want ordinary punctuation
like an apostrophe in "member's" to work, so that a natural project
description doesn't corrupt the entire governance-file generation run or
leave stray files touched.

## Description
`generate-pyproject` and `generate-governance-files` build `sed` command
lines by letting Make expand `$(PROJECT_NAME)`/`$(PROJECT_DESCRIPTION)`
directly inside a single-quoted `sed -e 's|...|...|g'` argument
(`src/butler_core/data/Makefile:84-89`, `468-482`). Make performs this as
plain text substitution before handing the line to `/bin/sh -c`, so any
single quote in the value closes the enclosing shell string early and
corrupts the rest of the command.

Reproduced 2026-08-02 in `firefly-household-splitter`, first attempt
(`make init-project`, no `FORCE`): a description containing "member's"
caused `generate-pyproject` to fail with `unexpected EOF while looking for
matching` and `pyproject.toml` was never written.

Reproduced again 2026-08-02, second attempt (`make init-project FORCE=1`):
the same apostrophe corrupted quote-parsing for the rest of the
`\`-continued script that also invokes `generate-governance-files`,
`generate-gitignore`, and `generate-pre-commit-config` as nested `$(MAKE)`
calls. The run emitted `sed: unescaped newline inside substitute pattern`,
then executed leftover template tokens and substituted values as bare shell
commands (`{{BUG_TRIAGE_NAME}}: command not found`, `Computes: command not
found`, `docs/Requirements_Firefly-Household-Splitter.md: Permission
denied`), and ended with `make[2]: *** [help] Broken pipe` /
`make[1]: *** [generate-governance-files] Error 127`. `CLAUDE.md` was still
never created, and a previously-tracked root file
(`Requirements_Firefly-Household-Splitter.md`) ended up deleted from the
working tree — evidence that the corruption is not confined to the one
`sed` call that introduced it, but can affect files unrelated to what
`generate-*` is supposed to touch.

Fix should pass `PROJECT_NAME`/`PROJECT_DESCRIPTION` (and other free-text
template variables) into the `sed` invocation in a way that's safe against
single quotes — e.g. via an exported shell variable referenced inside the
`sed` script rather than direct Make text substitution into a single-quoted
literal — per REQUIREMENTS_TEMPLATE_VAR_SHELL_SAFETY.md Requirement 1.

## Branch
**Branch name:** `task/093-template-variable-substitution-breaks-on-single-quotes`
**Switch/create:** `git checkout -b task/093-template-variable-substitution-breaks-on-single-quotes`
**Make target:** `make branch-task f=TASK-093`

## Acceptance criteria (Gherkin)
**Feature files:** None

- [ ] 1. Scenario: PROJECT_DESCRIPTION with a single quote does not break generate-pyproject
      Given `PROJECT_DESCRIPTION` is set to `Tracks each member's monthly share.`
      When `make generate-pyproject PROJECT_DESCRIPTION="Tracks each member's monthly share."` runs
      Then the command exits 0
      And `pyproject.toml`'s description field contains `Tracks each member's monthly share.` verbatim, apostrophe included
- [ ] 2. Scenario: PROJECT_DESCRIPTION with a single quote does not break generate-governance-files
      Given `PROJECT_DESCRIPTION` is set to `Tracks each member's monthly share.`
      When `make generate-governance-files PROJECT_DESCRIPTION="Tracks each member's monthly share."` runs
      Then the command exits 0
      And `CLAUDE.md` and `.github/copilot-instructions.md` contain `Tracks each member's monthly share.` verbatim
- [ ] 3. Scenario: A description without special characters is unaffected
      Given `PROJECT_DESCRIPTION` is set to `Describe your project here.`
      When `make generate-pyproject` and `make generate-governance-files` run
      Then the generated files are byte-for-byte identical to current behavior

## Out of scope
- Handling arbitrary binary/control characters or multi-line values in
  `PROJECT_NAME`/`PROJECT_DESCRIPTION`.
- The independent-file-gating bug covered by TASK-092 /
  REQUIREMENTS_GOVERNANCE_FILE_GATING.md.

## Blockers
None

## Completion
**Date:**
**Summary:**
**Files changed:**
**Branch:** `git checkout task/093-template-variable-substitution-breaks-on-single-quotes`
**Stage:**
**Commit:**
