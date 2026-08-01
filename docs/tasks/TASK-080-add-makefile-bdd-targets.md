# TASK-080 Add Makefile targets for BDD execution and diagnostics

## Status
todo

## Requirements
**Binding:** BDD-010, BDD-011, BDD-012, BDD-013, BDD-050
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-079
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a developer, I want dedicated Makefile targets to run BDD scenarios and
check for missing step definitions, so that I can verify spec-driven development
at the acceptance level without hand-crafting pytest commands or worrying about
backward compatibility in projects without BDD.

## Description
Add four Makefile targets to butler's Makefile and emit them to projects via
`make generate-governance-files`:

1. `make bdd`: runs `uv run pytest tests/bdd/ -v`
2. `make bdd-missing`: lists scenarios without bound step definitions
3. Update `make test` to include BDD scenarios (via pytest collection)
4. Update `make help` to show `bdd` and `bdd-missing` with one-line descriptions
5. Graceful degradation: if `tests/bdd/` does not exist, `make bdd` prints an
   adoption hint and exits 0 (supports existing projects without BDD)

## Branch
**Branch name:** `task/080-add-makefile-bdd-targets`
**Switch/create:** `git checkout -b task/080-add-makefile-bdd-targets`
**Make target:** `make branch-task f=TASK-080`

## Acceptance criteria (Gherkin)

- [ ] Scenario: make bdd runs pytest tests/bdd/ verbosely
      Given a project with `make bdd` target available
      When `make bdd` is invoked
      Then `uv run pytest tests/bdd/ -v` is executed
      And any failing scenarios cause make to exit non-zero

- [ ] Scenario: make test includes BDD scenarios
      Given a project with pytest configured per TASK-079
      When `make test` is run
      Then BDD scenarios in `tests/bdd/` are collected and executed
      And the full test suite result reflects both unit and BDD tests

- [ ] Scenario: make bdd-missing lists unbound scenarios
      Given a project with scenarios missing step definitions
      When `make bdd-missing` is invoked
      Then scenarios without bound steps are listed
      And make exits non-zero

- [ ] Scenario: make help shows bdd and bdd-missing descriptions
      Given a project's Makefile
      When `make help` is run
      Then `bdd` target is listed with a one-line description
      And `bdd-missing` target is listed with a one-line description

- [ ] Scenario: make bdd degrades gracefully without tests/bdd/
      Given a project without `tests/bdd/` directory
      When `make bdd` is invoked
      Then an adoption hint message is printed
      And make exits 0 (does not fail)

## Out of scope
- Integration with pre-commit hooks (BDD-012 proposes CI-only execution)
- Custom pytest plugins beyond pytest-bdd's built-in capabilities
- Documentation or tutorial for the targets

## Blockers
None

## Completion
**Date:** YYYY-MM-DD
**Summary:** What was done, any decisions made, and what was left out and why.
**Files changed:**
- `path/to/file` - created / modified
**Branch:** `git checkout task/080-add-makefile-bdd-targets`
**Stage:** `git add path/to/file1 path/to/file2 CHANGELOG.md`
**Commit:** `git commit -m "Add Makefile targets for BDD execution and diagnostics"`
