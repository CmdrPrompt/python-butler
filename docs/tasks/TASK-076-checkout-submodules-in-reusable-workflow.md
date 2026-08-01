# TASK-076 Check out consumer submodules in the reusable python-ci.yml workflow

## Status
in-progress

## Requirements
**Binding:** Requirement 4 (REQUIREMENTS_REUSABLE_CI.md)
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-075
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a consumer repo with a git submodule dependency (e.g. `firefly-bank-importer`'s
`.butler`), I want the reusable `python-ci.yml` workflow's checkout step to
fetch submodules, so that Lint/Test/Audit steps that depend on submodule
content (e.g. `include .butler/Makefile`) don't fail with missing files.

## Description
`firefly-bank-importer`'s PR #38, after TASK-075's `uv` fix, progressed past
Install and failed at Lint with `Makefile:1: .butler/Makefile: No such file
or directory` — `actions/checkout@v4` in `.github/workflows/python-ci.yml`
doesn't set `submodules:`, so it defaults to not fetching them, leaving
`.butler` an empty directory. Add `submodules: true` to the existing
checkout step.

## Branch
**Branch name:** `task/076-checkout-submodules-in-reusable-workflow`
**Switch/create:** `git checkout -b task/076-checkout-submodules-in-reusable-workflow`
**Make target:** `make branch-task f=TASK-076`

## Acceptance criteria (Gherkin)

- [ ] Scenario: Checkout step fetches submodules
      Given `.github/workflows/python-ci.yml`'s `ci` job's `actions/checkout@v4` step
      When the workflow's steps are inspected
      Then the checkout step's `with:` sets `submodules: true`

- [ ] Scenario: Consumer submodule content is present for Lint
      Given a consumer's `lint-command` depends on a git submodule (e.g. `include .butler/Makefile`)
      When the reusable workflow runs against a real consumer PR
      Then the checkout step populates the submodule and the Lint step no longer fails with a missing-file error

## Out of scope
- Any change to `firefly-bank-importer`'s `ci.yml` or `.butler` submodule
  itself.
- `fetch-depth`, `lfs`, or other `actions/checkout` inputs not needed to
  populate submodules.

## Blockers
None

## Completion
**Date:** 2026-08-01
**Summary:** Added `with: submodules: true` to the `actions/checkout@v4` step in `.github/workflows/python-ci.yml`, so a consumer whose build depends on a git submodule (e.g. `.butler`) has it populated before Lint/Test run. Added `test_checkout_fetches_submodules` to `tests/test_python_ci_workflow.py`. Found via `firefly-bank-importer` PR #38's Lint step failing with `Makefile:1: .butler/Makefile: No such file or directory` after TASK-075's uv fix let it get that far.
**Files changed:**
- `.github/workflows/python-ci.yml` - modified
**Branch:** `git checkout task/076-checkout-submodules-in-reusable-workflow`
**Stage:** `git add .github/workflows/python-ci.yml tests/test_python_ci_workflow.py CHANGELOG.md REQUIREMENTS_REUSABLE_CI.md docs/tasks/TASK-076-checkout-submodules-in-reusable-workflow.md`
**Commit:** `git commit -m "Check out consumer submodules in the reusable python-ci.yml workflow"`
