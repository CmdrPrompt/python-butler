# TASK-079 Scaffold pytest-bdd support in template and example projects

## Status
done

## Requirements
**Binding:** BDD-001, BDD-002, BDD-003, BDD-016
**BDD mode:** BDD-ABSENT
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a new user adopting butler, I want my project scaffolded with `pytest-bdd`
configured and example BDD files in place, so that I can immediately write
acceptance criteria as Gherkin scenarios without manual setup.

## Description
Update the scaffold templates in `pyproject.toml` and `Makefile` generators so
that every new project includes:
- `pytest-bdd` as a dev dependency
- pytest configuration to collect tests/bdd/ by default
- Directory skeleton `tests/bdd/features/` and `tests/bdd/steps/` with
  `.gitkeep` or example files
- One removable example feature file and one example step definition file,
  clearly marked as demonstrations

This change applies to both `make init-project` and `make generate-governance-files`.

## Branch
**Branch name:** `task/079-scaffold-pytest-bdd-support`
**Switch/create:** `git checkout -b task/079-scaffold-pytest-bdd-support`
**Make target:** `make branch-task f=TASK-079`

## Acceptance criteria (Gherkin)

- [ ] Scenario: pytest-bdd is a dev dependency
      Given a new project is bootstrapped with `make init-project` or
            `make generate-governance-files`
      When `pyproject.toml` is inspected
      Then `pytest-bdd` appears in the `dev` dependency group

- [ ] Scenario: pytest collects tests/bdd/ by default
      Given a new project's `pyproject.toml`
      When the `tool.pytest.ini_options` section is inspected
      Then `testpaths` includes `"tests/bdd/"`

- [ ] Scenario: BDD directory skeleton exists
      Given a new project is bootstrapped
      When the file system is inspected
      Then `tests/bdd/features/` exists
      And `tests/bdd/steps/` exists
      And each directory contains `.gitkeep` or an example file

- [ ] Scenario: Example feature file demonstrates conventions
      Given a bootstrapped project
      When `tests/bdd/features/` is listed
      Then at least one `.feature` file exists
      And it is clearly marked as an example (comment or filename prefix)
      And it contains Given/When/Then steps demonstrating declarative style

- [ ] Scenario: Example step definition file demonstrates conventions
      Given a bootstrapped project
      When `tests/bdd/steps/` is listed
      Then at least one `.py` file exists
      And it is clearly marked as an example
      And it demonstrates step registration and reuse conventions

## Out of scope
- Implementing actual BDD test runners or CI targets (covered by TASK-080)
- Documentation or README updates about BDD conventions (covered by later tasks)
- Migration of existing projects' test files to BDD format

## Blockers
None

## Completion
**Date:** 2026-08-01
**Summary:** Added `pytest-bdd` to the scaffold `pyproject.toml.tmpl` dev
dependency group and appended `"tests/bdd/"` to `testpaths`. Added a new
`make generate-bdd-scaffold` target that creates `tests/bdd/features/` and
`tests/bdd/steps/` with one example `.feature` file and one example
pytest-bdd step-definition file (both clearly marked as removable
examples, verified to actually run and pass under pytest-bdd). Wired the
new target into both `init-project` and `generate-governance-files`, and
synced the vendored copy at `src/butler_core/data/Makefile`. Updated the
two existing submodule/subtree fixture builders
(`tests/test_butler_submodule.py`, `tests/test_butler_pull_governance_regen.py`)
to vendor `scaffold/` too, since `generate-governance-files` now depends on
it. Nothing was left out; the actual `make bdd` test-runner target is
TASK-080's scope.
**Files changed:**
- `scaffold/pyproject.toml.tmpl` - modified (pytest-bdd dep, testpaths)
- `scaffold/tests/bdd/features/example_search.feature.tmpl` - created
- `scaffold/tests/bdd/steps/test_example_search_steps.py.tmpl` - created
- `Makefile` - modified (new `generate-bdd-scaffold` target, wired into
  `init-project` and `generate-governance-files`)
- `src/butler_core/data/Makefile` - modified (synced vendored copy)
- `tests/test_bdd_scaffold.py` - created
- `tests/test_butler_submodule.py` - modified (fixture vendors `scaffold/`)
- `tests/test_butler_pull_governance_regen.py` - modified (fixture vendors `scaffold/`)
- `CHANGELOG.md` - modified
**Branch:** `git checkout task/079-scaffold-pytest-bdd-support`
**Stage:** `git add scaffold/ Makefile src/butler_core/data/Makefile tests/test_bdd_scaffold.py tests/test_butler_submodule.py tests/test_butler_pull_governance_regen.py CHANGELOG.md docs/tasks/TASK-079-scaffold-pytest-bdd-support.md`
**Commit:** `git commit -m "Scaffold pytest-bdd support in init-project and generate-governance-files"`
