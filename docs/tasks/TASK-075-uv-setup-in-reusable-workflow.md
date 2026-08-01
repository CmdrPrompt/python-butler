# TASK-075 Set up uv before the Install step in the reusable python-ci.yml workflow

## Status
done

## Requirements
**Binding:** Requirement 3 (REQUIREMENTS_REUSABLE_CI.md)
**BDD mode:** BDD-ABSENT
**Depends on:** none
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a consumer repo whose `install-command` is a `uv` invocation, I want the
reusable `python-ci.yml` workflow to set up `uv` before running Install, so
that the Install step doesn't fail with `uv: command not found`.

## Description
`firefly-bank-importer`'s PR #38 — the first real end-to-end run of this
reusable workflow after repointing its `uses:` from the renamed
`python-commons` to `python-butler` (TASK-060) — failed at the Install step
with `uv: command not found` (exit 127). `.github/workflows/python-ci.yml`
sets up Python via `actions/setup-python@v5` but never installs `uv` before
running `${{ inputs.install-command }}`. Add a "Set up uv" step (using
`astral-sh/setup-uv`) between the existing "Set up Python" step and the
"Install" step.

## Branch
**Branch name:** `task/075-uv-setup-in-reusable-workflow`
**Switch/create:** `git checkout -b task/075-uv-setup-in-reusable-workflow`
**Make target:** `make branch-task f=TASK-075`

## Acceptance criteria (Gherkin)

- [ ] Scenario: uv is set up before Install
      Given `.github/workflows/python-ci.yml`'s `ci` job
      When the workflow's steps are inspected
      Then a "Set up uv" step using `astral-sh/setup-uv` appears after "Set up Python" and before "Install"

- [ ] Scenario: uv-based install-command succeeds
      Given a consumer's `install-command` is `uv sync --extra dev`
      When the reusable workflow runs against a real consumer PR
      Then the Install step succeeds instead of failing with `uv: command not found`

## Out of scope
- Pinning a specific `uv` version (use `astral-sh/setup-uv`'s default/latest
  unless a future requirement specifies otherwise).
- Any change to `firefly-bank-importer`'s `ci.yml` (already fixed, TASK-060).

## Blockers
None

## Completion
**Date:** 2026-08-01
**Summary:** Added a "Set up uv" step (`astral-sh/setup-uv@v5`) between "Set up Python" and "Install" in `.github/workflows/python-ci.yml`, so `install-command` (typically `uv sync --extra dev`) no longer fails with `uv: command not found`. Added `test_uv_is_set_up_before_install` to `tests/test_python_ci_workflow.py`, asserting the step's position via `uses: astral-sh/setup-uv@...` between "Set up Python" and "Install". Found via `firefly-bank-importer` PR #38's Install step failing with exit 127.
**Files changed:**
- `.github/workflows/python-ci.yml` - modified
**Branch:** `git checkout task/075-uv-setup-in-reusable-workflow`
**Stage:** `git add .github/workflows/python-ci.yml tests/test_python_ci_workflow.py CHANGELOG.md REQUIREMENTS_REUSABLE_CI.md docs/tasks/TASK-075-uv-setup-in-reusable-workflow.md`
**Commit:** `git commit -m "Set up uv before Install in the reusable python-ci.yml workflow"`
