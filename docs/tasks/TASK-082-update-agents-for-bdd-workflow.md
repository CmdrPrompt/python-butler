# TASK-082 Update agents to support BDD workflow

## Status
done

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

- [x] Scenario: workflow-guardian checks feature files and red state before starting work
      Given a task with Status not `blocked`
      When workflow-guardian approves the start of implementation
      Then it verifies that feature files exist (BDD-ACTIVE) or inline Gherkin is present (BDD-PLANNED/BDD-ABSENT)
      And it verifies the task's scenarios fail or are unbound (red state via `make bdd` if available)

- [x] Scenario: implementation-worker works outside-in
      Given a task with Gherkin scenarios and no step definitions
      When implementation-worker begins
      Then it first writes step definitions (binding steps to fail for the right reason)
      And then drives implementation with the inner TDD loop
      And the task is not considered complete until both `make bdd` and `make test` pass

- [x] Scenario: pr-reviewer verifies criterion coverage
      Given a completed task with acceptance criteria
      When pr-reviewer reviews the PR
      Then it verifies every criterion ID is covered by a passing scenario
      And it rejects the PR if any criterion is uncovered

- [x] Scenario: characterization-test-writer prefers Gherkin for user-facing behavior
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
**Date:** 2026-08-01
**Summary:** Updated four agent definitions (bundled `claude-agents/` source and
mirrored `.claude/agents/` copies, kept byte-identical per `check-agents-sync`)
to enforce/support the BDD outside-in workflow. workflow-guardian gained a
"BDD red-state gate" rule (BDD-032): verify feature files (BDD-ACTIVE) or
inline Gherkin (BDD-PLANNED/BDD-ABSENT) exist, and, where `make bdd` is
available, that scenarios fail or are unbound before implementation starts;
wired into the Operating Procedure as step 7a, before spawning Implementation
Worker. implementation-worker gained an outside-in rule (BDD-033): bind step
definitions first so scenarios fail for the right reason, then drive the
inner Red/Green/Refactor loop, and treat the task incomplete until both
`make bdd` and `make test` pass. pr-reviewer gained a "BDD scenario coverage
gate" (BDD-034): every acceptance criterion ID must be covered by a passing
scenario, or the PR is rejected (REQUEST CHANGES) listing the uncovered IDs.
characterization-test-writer gained guidance (BDD-035) to prefer Gherkin
scenarios for user-facing behavior while keeping internal implementation
behavior as plain pytest. Added 8 docs-level regression tests (TDD:
written red, then made to pass) asserting the required phrases are present
in both copies of all four files, following the existing
`tests/test_workflow_guardian_draft_sync_docs.py` pattern. `make lint` and
`make test` pass; total suite went from 339 to 347 tests, coverage held at
99% (no regression against the task-start baseline). Implementation was
delegated to Implementation Worker in an isolated worktree; its report was
independently re-verified (diffs read directly, `.claude/agents/` vs
`claude-agents/` byte-identity re-checked, `make lint`/`make test` re-run,
new test count re-collected) before merging — no discrepancies found.
task-drafter, requirements-drafter, `templates/*.tmpl` (Copilot-flavored),
and actual `.feature` files were left untouched, per the task's Out of scope
section.
**Files changed:**
- `claude-agents/workflow-guardian.agent.md` - modified (BDD red-state gate)
- `.claude/agents/workflow-guardian.agent.md` - modified (mirror, BDD red-state gate)
- `claude-agents/implementation-worker.agent.md` - modified (outside-in loop, make bdd)
- `.claude/agents/implementation-worker.agent.md` - modified (mirror, outside-in loop, make bdd)
- `claude-agents/pr-reviewer.agent.md` - modified (BDD scenario coverage gate)
- `.claude/agents/pr-reviewer.agent.md` - modified (mirror, BDD scenario coverage gate)
- `claude-agents/characterization-test-writer.agent.md` - modified (Gherkin preference for user-facing behavior)
- `.claude/agents/characterization-test-writer.agent.md` - modified (mirror, Gherkin preference)
- `tests/test_agents_bdd_workflow_docs.py` - created (8 regression tests, one per requirement per file copy)
- `CHANGELOG.md` - modified (behavior-first entry, TASK-082 suffix)
- `docs/tasks/TASK-082-update-agents-for-bdd-workflow.md` - modified (Status, acceptance criteria checkboxes, Completion)
**Branch:** `git checkout task/082-update-agents-for-bdd-workflow`
**Stage:** `git add .claude/agents/characterization-test-writer.agent.md .claude/agents/implementation-worker.agent.md .claude/agents/pr-reviewer.agent.md .claude/agents/workflow-guardian.agent.md claude-agents/characterization-test-writer.agent.md claude-agents/implementation-worker.agent.md claude-agents/pr-reviewer.agent.md claude-agents/workflow-guardian.agent.md tests/test_agents_bdd_workflow_docs.py CHANGELOG.md docs/tasks/TASK-082-update-agents-for-bdd-workflow.md`
**Commit:** `git commit -m "Update agents to support BDD workflow (TASK-082)"`
