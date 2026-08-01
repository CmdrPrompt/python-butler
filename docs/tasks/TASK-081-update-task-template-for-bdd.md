# TASK-081 Update task template to support Gherkin acceptance criteria

## Status
todo

## Requirements
**Binding:** BDD-025, BDD-026
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-079
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a task author, I want the task template to structure acceptance criteria
as numbered items with explicit Gherkin scenarios or feature file references,
so that I can trace each criterion to a runnable spec and the implementation
team knows exactly which behaviors to verify.

## Description
Update the task template in `.claude/skills/task-file-format/` and any
related documentation to add:

1. Replace free-text acceptance criteria section with a structured format:
   numbered criteria, each followed by its Gherkin scenario (inline) or a
   reference to the feature file containing it (file path + scenario name)
2. Add a `Feature files:` field listing the `.feature` files belonging to the
   task (if BDD-ACTIVE mode)
3. Ensure the template guidance explains the mapping between requirements'
   preconditions (Given), triggers (When), and obligations/measurable values
   (Then)

This change applies to the canonical template and its documentation.

## Branch
**Branch name:** `task/081-update-task-template-for-bdd`
**Switch/create:** `git checkout -b task/081-update-task-template-for-bdd`
**Make target:** `make branch-task f=TASK-081`

## Acceptance criteria (Gherkin)

- [ ] Scenario: task template includes numbered acceptance criteria
      Given the canonical task template
      When the acceptance criteria section is inspected
      Then criteria are numbered (1, 2, 3, ...)
      And each criterion is followed by its Gherkin scenario or feature file reference

- [ ] Scenario: task template includes Feature files field
      Given the canonical task template
      When the acceptance criteria section is inspected
      Then a `Feature files:` field exists
      And it lists paths to `.feature` files (e.g., `tests/bdd/features/TASK-XXX-*.feature`)

- [ ] Scenario: task template guidance explains Given/When/Then mapping
      Given the task template documentation
      When the acceptance criteria section guidance is read
      Then it explicitly states: precondition → Given, trigger → When, obligation/measurable values → Then

- [ ] Scenario: inline scenarios and feature file references coexist
      Given a task file using the updated template
      When both inline Gherkin and feature file references appear
      Then both formats are supported without ambiguity
      And the guidance clarifies when to use each (inline for BDD-PLANNED/BDD-ABSENT, file reference for BDD-ACTIVE)

## Out of scope
- Migrating existing task files to the new format (that is future work)
- Creating `.feature` files (covered by task-drafter and implementation-worker)
- Modifying the BDD mode selection logic (covered by separate agent tasks)

## Blockers
None

## Completion
**Date:** YYYY-MM-DD
**Summary:** What was done, any decisions made, and what was left out and why.
**Files changed:**
- `path/to/file` - created / modified
**Branch:** `git checkout task/081-update-task-template-for-bdd`
**Stage:** `git add path/to/file1 path/to/file2 CHANGELOG.md`
**Commit:** `git commit -m "Update task template to support Gherkin acceptance criteria"`
