# TASK-043 Regression test protecting non-recursive architecture

## Status

todo

## Requirements

**Binding:** Requirement 1 from REQUIREMENTS_TASK_WORKFLOW.md
**BDD mode:** BDD-PLANNED
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)

As a maintainer, I want to protect python-butler against regressions to the
non-recursive architecture, so that consumer projects can never again get stuck
in a situation like firefly-python-api, where a stale vendored `.butler/Makefile`
snapshot would cause `make branch-task` and similar task-workflow commands to
recurse infinitely.

## Description

Implement regression tests asserting that `butler_core.git_ops`'s core branch/
stage/commit/pr/merge functions (`branch_for`, `stage_for`, `commit_for`,
`open_pr_for`, `merge_pr_for`) MUST NOT construct a `subprocess` call whose
first argument is `"make"`, and that end-to-end `butler task <cmd>` invocations
complete without spawning a nested `butler` or `make` process. This test suite
formalizes and protects behavior that already exists in this repo's source as
of TASK-023 and must remain invariant going forward.

No production code changes are required; this is pure test coverage.

## Branch

**Branch name:** `task/043-fix-task-command-make-recursion`
**Switch/create:** `git checkout -b task/043-fix-task-command-make-recursion`
**Make target:** `make branch-task f=TASK-043`

## Acceptance criteria (Gherkin)

- [ ] Scenario: `butler_core.git_ops` never constructs subprocess calls to make
      Given the module `butler_core.git_ops` with functions `branch_for`, `stage_for`, `commit_for`, `open_pr_for`, `merge_pr_for`
      When those functions' implementations are inspected (via AST parsing or static analysis)
      Then none of them construct a `subprocess` call whose first argument is the string `"make"`

- [ ] Scenario: End-to-end `butler task branch` does not spawn a nested process
      Given a fixture project with an initialized git repository
      When `butler task branch <task-name>` is invoked as a subprocess with process-tree monitoring
      Then the command completes successfully and no child processes named `butler` or `make` are spawned

- [ ] Scenario: End-to-end `butler task stage` does not spawn a nested process
      Given a fixture project with an initialized git repository and uncommitted changes staged/unstaged
      When `butler task stage` is invoked as a subprocess with process-tree monitoring
      Then the command completes successfully and no child processes named `butler` or `make` are spawned

- [ ] Scenario: End-to-end `butler task commit` does not spawn a nested process
      Given a fixture project with an initialized git repository and staged changes
      When `butler task commit <message>` is invoked as a subprocess with process-tree monitoring
      Then the command completes successfully and no child processes named `butler` or `make` are spawned

- [ ] Scenario: End-to-end `butler task pr` does not spawn a nested process
      Given a fixture project with an initialized git repository configured as a mock GitHub project
      When `butler task pr` is invoked as a subprocess with process-tree monitoring
      Then the command completes successfully and no child processes named `butler` or `make` are spawned

- [ ] Scenario: End-to-end `butler task merge` does not spawn a nested process
      Given a fixture project with an initialized git repository and a mock pull request
      When `butler task merge` is invoked as a subprocess with process-tree monitoring
      Then the command completes successfully and no child processes named `butler` or `make` are spawned

- [ ] Scenario: CHANGELOG.md updated with behavior-first entry
      Given a current CHANGELOG.md
      When this task is completed
      Then CHANGELOG.md contains a new entry describing the regression test coverage added

- [ ] Scenario: Tests pass and coverage maintained
      Given the existing test suite with current coverage baseline
      When `make test` and `make lint` are run after implementation
      Then all tests pass and code coverage does not decrease below the baseline

## Out of scope

- Fixing already-vendored `.butler/Makefile` copies in existing consumer repos (e.g. `firefly-python-api`). Those projects pick up the fix by running `butler sync` (Requirement 3) once it ships.
- Changing the implementation of `butler_core.git_ops` functions themselves — they already implement the correct non-recursive architecture. This task only adds test coverage.
- Modifying the root Makefile task targets — the Makefile already correctly calls `butler task <cmd>` exactly once with no callback.

## Blockers

None

## Completion

**Date:**
**Summary:**
**Files changed:**
**Branch:** `git checkout task/043-fix-task-command-make-recursion`
**Stage:**
**Commit:**
