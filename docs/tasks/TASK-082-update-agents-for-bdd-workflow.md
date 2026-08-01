# TASK-082 Update agents to support BDD workflow

## Status
todo

## Requirements
**Binding:** BDD-032, BDD-033, BDD-034, BDD-035
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-079, TASK-080, TASK-081
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a workflow orchestrator, I want workflow-guardian, implementation-worker,
pr-reviewer, and characterization-test-writer to understand and enforce the
outer (BDD) and inner (TDD) loops, so that a task's Gherkin scenarios drive
step definitions, step definitions drive implementation, and nothing is
marked complete without full scenario coverage.

## Description
Update the instructions and validation logic in four agents. task-drafter
(BDD-036/037) and requirements-drafter (unaffected) are **not** in scope
here — task-drafter's mechanical scenario derivation, `[VALUE TBD]`
blocking, and never-edits-requirements behavior were already implemented
and confirmed in TASK-042, before this repo's `tests/bdd/`/`make bdd`
tooling existed.

1. **workflow-guardian** (BDD-032, remaining part not covered by TASK-042):
   in addition to the `Status` not `blocked` gate TASK-042 already added,
   verify that the task's feature files exist (BDD-ACTIVE) or inline
   Gherkin is present (BDD-PLANNED/BDD-ABSENT), and, where `make bdd` is
   available, that the task's scenarios fail or are unbound before
   implementation starts — confirming red state.

2. **implementation-worker** (BDD-033): work outside-in — bind step
   definitions first so scenarios fail for the right reason, then drive
   implementation with the inner TDD loop. Do not consider the task
   complete until both `make bdd` and `make test` pass.

3. **pr-reviewer** (BDD-034): verify that every acceptance criterion ID in
   the task file is covered by a passing scenario. Reject the PR listing
   uncovered criteria.

4. **characterization-test-writer** (BDD-035): when documenting existing
   user-facing behavior, prefer Gherkin scenarios; internal implementation
   behavior remains plain pytest.

## Branch
**Branch name:** `task/082-update-agents-for-bdd-workflow`
**Switch/create:** `git checkout -b task/082-update-agents-for-bdd-workflow`
**Make target:** `make branch-task f=TASK-082`

## Acceptance criteria (Gherkin)

- [ ] Scenario: workflow-guardian checks feature files and red state before starting work
      Given a task with Status not `blocked`
      When workflow-guardian approves the start of implementation
      Then it verifies that feature files exist (BDD-ACTIVE) or inline Gherkin is present (BDD-PLANNED/BDD-ABSENT)
      And it verifies the task's scenarios fail or are unbound (red state via `make bdd` if available)

- [ ] Scenario: implementation-worker works outside-in
      Given a task with Gherkin scenarios and no step definitions
      When implementation-worker begins
      Then it first writes step definitions (binding steps to fail for the right reason)
      And then drives implementation with the inner TDD loop
      And the task is not considered complete until both `make bdd` and `make test` pass

- [ ] Scenario: pr-reviewer verifies criterion coverage
      Given a completed task with acceptance criteria
      When pr-reviewer reviews the PR
      Then it verifies every criterion ID is covered by a passing scenario
      And it rejects the PR if any criterion is uncovered

- [ ] Scenario: characterization-test-writer prefers Gherkin for user-facing behavior
      Given existing user-facing behavior to document
      When characterization-test-writer creates tests
      Then it prefers Gherkin scenarios
      And internal implementation behavior remains as plain pytest

## Out of scope
- Re-implementing task-drafter's BDD-036/037 behavior — already done in TASK-042.
- Creating or modifying actual `.feature` files (that is implementation work per agent).
- Updating CLAUDE.md or Copilot instructions (covered by TASK-083).
- Modifying the requirements-drafter agent itself.

## Blockers
None

## Completion
**Date:** YYYY-MM-DD
**Summary:** What was done, any decisions made, and what was left out and why.
**Files changed:**
- `path/to/file` - created / modified
**Branch:** `git checkout task/082-update-agents-for-bdd-workflow`
**Stage:** `git add path/to/file1 path/to/file2 CHANGELOG.md`
**Commit:** `git commit -m "Update agents to support BDD workflow"`
