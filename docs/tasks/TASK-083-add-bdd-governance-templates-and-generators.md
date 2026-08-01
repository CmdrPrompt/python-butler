# TASK-083 Add BDD governance templates and enable ENABLE_BDD flag for generators

## Status
todo

## Requirements
**Binding:** BDD-040, BDD-041, BDD-042, BDD-051
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-081, TASK-082
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a project maintainer, I want my `CLAUDE.md` and Copilot instructions to
document BDD conventions and directory structure, and I want to control whether
new projects are scaffolded with BDD support via an optional `ENABLE_BDD` flag,
so that I can adopt BDD incrementally in both new and existing projects.

## Description
Add and update governance templates and generator logic:

1. **CLAUDE.md template**: Add a BDD section covering directory layout
   (per BDD-015), naming conventions (feature file naming), style (per BDD-018),
   criterion mapping (per BDD-019), and the outside-in loop (per BDD-033).

2. **Copilot instructions template**: Add semantically identical BDD content
   to the Copilot instructions and agent files (`.github/agents/`).

3. **Generator logic** (`make init-project` and `make generate-governance-files`):
   - Emit all BDD additions (template sections, scaffold directories, example files)
     by default with no new required variables
   - Add an optional `ENABLE_BDD` flag (default `1`) so that when `ENABLE_BDD=0`,
     generators omit BDD sections and scaffold entries (backward compatibility)

4. **Existing project adoption path**: Document `make generate-governance-files FORCE=1`
   as the way for pre-existing projects to regenerate files with BDD support.

## Branch
**Branch name:** `task/083-add-bdd-governance-templates-and-generators`
**Switch/create:** `git checkout -b task/083-add-bdd-governance-templates-and-generators`
**Make target:** `make branch-task f=TASK-083`

## Acceptance criteria (Gherkin)

- [ ] Scenario: CLAUDE.md template includes BDD section
      Given the CLAUDE.md template
      When the BDD section is inspected
      Then it covers directory layout (`tests/bdd/features/`, `tests/bdd/steps/`)
      And it documents naming per BDD-015 (TASK-<NNN>-<short-description>.feature)
      And it documents style per BDD-018 (declarative, one behavior per scenario)
      And it documents criterion mapping per BDD-019 (each AC maps to at least one scenario)
      And it documents the outside-in loop per BDD-033 (bind steps, then inner TDD)

- [ ] Scenario: Copilot instructions receive semantically identical BDD content
      Given the Copilot instructions template and corresponding Claude template
      When both are inspected
      Then BDD sections in both are semantically equivalent
      And they cover the same directory layout, naming, style, mapping, and loop logic

- [ ] Scenario: make init-project emits BDD additions by default
      Given `make init-project` is run without ENABLE_BDD specified
      When the generated project is inspected
      Then CLAUDE.md includes a BDD section
      And Copilot instructions (if generated) include a BDD section
      And scaffold directories and example files are in place

- [ ] Scenario: make generate-governance-files emits BDD additions by default
      Given `make generate-governance-files` is run without ENABLE_BDD specified
      When the generated files are inspected
      Then updated CLAUDE.md and Copilot instructions include BDD sections
      And any scaffold files are created with BDD support

- [ ] Scenario: ENABLE_BDD=0 omits BDD sections
      Given `make init-project ENABLE_BDD=0` or `make generate-governance-files ENABLE_BDD=0`
      When the generated files are inspected
      Then CLAUDE.md does not include a BDD section
      And Copilot instructions do not include BDD content
      And scaffold directories (tests/bdd/) are not created

- [ ] Scenario: Existing projects adopt BDD via FORCE=1
      Given an existing project without BDD support
      When `make generate-governance-files FORCE=1` is run
      Then CLAUDE.md and Copilot instructions are regenerated with BDD sections
      And the README or documentation mentions this as the adoption path

## Out of scope
- README updates (covered by a separate requirements-drafter round for BDD-XXX IDs)
- Creating agent files for Copilot (those are managed separately by the Copilot setup flow)
- Migration of historical tasks to BDD format

## Blockers
None

## Completion
**Date:** YYYY-MM-DD
**Summary:** What was done, any decisions made, and what was left out and why.
**Files changed:**
- `path/to/file` - created / modified
**Branch:** `git checkout task/083-add-bdd-governance-templates-and-generators`
**Stage:** `git add path/to/file1 path/to/file2 CHANGELOG.md`
**Commit:** `git commit -m "Add BDD governance templates and enable ENABLE_BDD flag for generators"`
