# TASK-088 Dogfood the BDD scaffold in python-butler and migrate pending tasks to BDD-ACTIVE

## Status
done

## Requirements
**Binding:** BDD-052, BDD-053
**BDD mode:** BDD-PLANNED
**Depends on:** TASK-083
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer, I want python-butler itself to run its own BDD scaffold
(not just ship the capability for consumer projects), and I want the two
pending tasks that already have concrete Gherkin acceptance criteria
(TASK-084, TASK-085) to have those criteria live as real `.feature` files
with `BDD mode: BDD-ACTIVE`, so that `make bdd`/`make bdd-missing` are
meaningful in this repo and those two tasks are ready for
implementation-worker's outside-in loop when picked up.

## Description
1. **Dogfood the scaffold (BDD-052):** add `pytest-bdd` to this repo's own
   `pyproject.toml` dev dependencies; create `tests/bdd/features/` and
   `tests/bdd/steps/` with the example scenario (mirroring
   `scaffold/tests/bdd/features/example_search.feature.tmpl` and its step
   file, de-templated). `testpaths` already includes `tests/bdd/` implicitly
   (it's nested under `tests/`), so no `pyproject.toml` `testpaths` edit is
   required — verify this holds instead of assuming it.

2. **Lift TASK-084 and TASK-085 (BDD-053):** for each of these two task
   files (both `todo`, both `BDD-ABSENT`, both with concrete non-`TBD`
   Gherkin acceptance criteria):
   - Create `tests/bdd/features/TASK-<NNN>-<slug>.feature` with each
     acceptance criterion's Given/When/Then copied verbatim as a Scenario.
   - Create a minimal `tests/bdd/steps/test_task_<NNN>_steps.py` that only
     calls pytest-bdd's `scenarios("../features/TASK-<NNN>-<slug>.feature")`
     — no `@given`/`@when`/`@then` step implementations. This is binding,
     not implementation: it makes the scenarios visible to `make
     bdd`/`make bdd-missing` as unbound (red state per BDD-032), which a
     bare `.feature` file alone would not be, since pytest-bdd never
     auto-discovers `.feature` files without a `scenarios()` call.
   - Update the task file: `**BDD mode:**` to `BDD-ACTIVE`, and replace each
     Gherkin acceptance criterion's inline Given/When/Then body with a
     reference to its feature file and scenario name, per BDD-019 /
     BDD-025 (`See tests/bdd/features/TASK-<NNN>-<slug>.feature: Scenario:
     <name>`).
   - TASK-055 is explicitly out of scope (its acceptance criteria are still
     `TBD`; nothing concrete exists to lift).

3. Do not write any `@given`/`@when`/`@then` step implementations — that
   remains implementation-worker's job when TASK-084/TASK-085 are actually
   picked up.

## Branch
**Branch name:** `task/088-dogfood-bdd-and-migrate-pending-tasks-to-bdd-active`
**Switch/create:** `git checkout -b task/088-dogfood-bdd-and-migrate-pending-tasks-to-bdd-active`
**Make target:** `make branch-task f=TASK-088`

## Acceptance criteria (Gherkin)

- [x] Scenario: This repo's own pyproject.toml depends on pytest-bdd
      Given this repo's `pyproject.toml`
      When its dev dependency group is inspected
      Then `pytest-bdd` is listed

- [x] Scenario: This repo has its own tests/bdd/ scaffold
      Given this repo's working tree
      When `tests/bdd/features/` and `tests/bdd/steps/` are inspected
      Then both directories exist with the example scenario and step file
      And `make bdd` runs and passes the example scenario

- [x] Scenario: TASK-084/TASK-085 scenarios are visibly red without breaking make test/CI
      Given `tests/bdd/features/TASK-084-obsolete-task-status.feature` and
      `tests/bdd/features/TASK-085-mark-butler-sync-deprecated.feature` exist,
      each bound via a `scenarios()`-only step file with no step implementations
      When `make bdd -v` runs
      Then all nine scenarios report `XFAIL` with a "not yet implemented" reason
      And `make test` and `make bdd-missing` both still exit 0 (deliberately-pending
           scenarios, marked `xfail`, are not the same failure class as an
           accidentally-forgotten step binding, so `bdd-missing` — which greps for
           `StepDefinitionNotFoundError` — correctly does not flag them)

- [x] Scenario: TASK-084 and TASK-085 are BDD-ACTIVE with criteria referencing their feature files
      Given `docs/tasks/TASK-084-obsolete-task-status.md` and
      `docs/tasks/TASK-085-mark-butler-sync-deprecated.md`
      When their `**BDD mode:**` field and acceptance criteria are inspected
      Then both show `BDD-ACTIVE`
      And each acceptance criterion references its scenario in the matching `.feature` file instead of inline Given/When/Then

- [x] Scenario: TASK-055 is left unmigrated
      Given `docs/tasks/TASK-055-cli-mcp-version-sync-after-pull.md` has `TBD` acceptance criteria
      When this task's migration runs
      Then TASK-055's `**BDD mode:**` stays `BDD-ABSENT` and no feature file is created for it

## Out of scope
- Writing `@given`/`@when`/`@then` step implementations for TASK-084/TASK-085's scenarios
- Migrating TASK-055 (acceptance criteria still `TBD`)
- Migrating TASK-027/TASK-049 (predate the `**BDD mode:**` field entirely; adding the field where none existed is a different kind of edit than lifting existing Gherkin)
- Any change to `butler_core`, `git_ops.py`, or the Makefile targets themselves (BDD-010/012 already exist per TASK-080)

## Blockers
None

## Completion
**Date:** 2026-08-01
**Summary:** Added `pytest-bdd` to this repo's own dev dependencies and
created `tests/bdd/features/`/`tests/bdd/steps/` with the de-templated
example scenario, so `make bdd`/`make bdd-missing` are meaningful when run
against python-butler itself (BDD-052). Lifted TASK-084's four and
TASK-085's five Gherkin acceptance criteria verbatim into
`tests/bdd/features/TASK-084-obsolete-task-status.feature` and
`tests/bdd/features/TASK-085-mark-butler-sync-deprecated.feature`,
each bound via a `scenarios()`-only step file (BDD-053). Discovered during
implementation that binding via `scenarios()` with no step implementations
makes `make test` fail outright (BDD-011 already collects `tests/bdd/` into
the main suite, and this repo's own CI now dogfoods `make test` per
TASK-078) — asked the user how to resolve this, and per their choice, both
step files carry a module-level `pytest.mark.xfail(reason="... not yet
implemented", strict=False)` so the nine scenarios show as `XFAIL` in
`make bdd -v` (visibly red, satisfying BDD-032(c)) without failing `make
test` or `make bdd-missing` (which only flags accidentally-unbound steps
via `StepDefinitionNotFoundError`, a different, narrower failure class than
a deliberately-pending xfail). Updated TASK-084/TASK-085's `**BDD mode:**`
to `BDD-ACTIVE` with a new `**Feature files:**` field, and replaced each
task's inline Gherkin acceptance criteria with a reference to its scenario
in the matching `.feature` file. TASK-055 (still-`TBD` acceptance criteria)
and TASK-027/TASK-049 (predate the `**BDD mode:**` field) were left
untouched, as scoped.
**Files changed:**
- `pyproject.toml` - modified (`pytest-bdd` dev dependency)
- `tests/bdd/features/example_search.feature` - created
- `tests/bdd/steps/test_example_search_steps.py` - created
- `tests/bdd/features/TASK-084-obsolete-task-status.feature` - created
- `tests/bdd/steps/test_task_084_steps.py` - created
- `tests/bdd/features/TASK-085-mark-butler-sync-deprecated.feature` - created
- `tests/bdd/steps/test_task_085_steps.py` - created
- `docs/tasks/TASK-084-obsolete-task-status.md` - modified (BDD mode, Feature files, acceptance criteria)
- `docs/tasks/TASK-085-mark-butler-sync-deprecated.md` - modified (BDD mode, Feature files, acceptance criteria)
- `docs/tasks/TASK-088-dogfood-bdd-and-migrate-pending-tasks-to-bdd-active.md` - created
- `CHANGELOG.md` - modified
**Branch:** `git checkout task/088-dogfood-bdd-and-migrate-pending-tasks-to-bdd-active`
**Stage:** `pyproject.toml uv.lock tests/bdd/features/example_search.feature tests/bdd/steps/test_example_search_steps.py tests/bdd/features/TASK-084-obsolete-task-status.feature tests/bdd/steps/test_task_084_steps.py tests/bdd/features/TASK-085-mark-butler-sync-deprecated.feature tests/bdd/steps/test_task_085_steps.py docs/tasks/TASK-084-obsolete-task-status.md docs/tasks/TASK-085-mark-butler-sync-deprecated.md docs/tasks/TASK-088-dogfood-bdd-and-migrate-pending-tasks-to-bdd-active.md CHANGELOG.md REQUIREMENTS_BDD.md`
**Commit:** `git commit -m "Dogfood BDD scaffold in python-butler and migrate TASK-084/TASK-085 to BDD-ACTIVE (TASK-088)"`
