# TASK-077 Split the reusable python-ci.yml into separate needs-chained jobs

## Status
in-progress

## Requirements
**Binding:** Requirement 1 (REQUIREMENTS_REUSABLE_CI.md)
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-076
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer watching a consumer PR's checks list, I want Install, Lint,
Test, and Audit to show as separate checks, so that I can see which stage
failed at a glance instead of opening a single combined "ci / ci" job's log.

## Description
`.github/workflows/python-ci.yml` currently runs Checkout → Set up Python →
Set up uv → Install → Lint → Test → Audit as steps inside one `ci` job, so
GitHub's PR checks list shows a single "ci / ci" entry. Restructure into
four `needs`-chained jobs (`install`, `lint`, `test`, `audit`), each
checking out (with `submodules: true`) and setting up Python/`uv`
(`astral-sh/setup-uv` with `enable-cache: true`) before re-running
`install-command` and then that job's own command. `audit` keeps its
existing `if: inputs.audit-command != ''` conditional. The
`workflow_call` input contract is unchanged, so no consumer `ci.yml` needs
edits.

## Branch
**Branch name:** `task/077-split-reusable-workflow-into-jobs`
**Switch/create:** `git checkout -b task/077-split-reusable-workflow-into-jobs`
**Make target:** `make branch-task f=TASK-077`

## Acceptance criteria (Gherkin)

- [ ] Scenario: Install, Lint, Test, Audit are separate needs-chained jobs
      Given `.github/workflows/python-ci.yml`
      When the workflow's `jobs` are inspected
      Then `install`, `lint`, `test`, `audit` each exist as top-level jobs, with `lint` needing `install`, `test` needing `lint`, and `audit` needing `test`

- [ ] Scenario: Each job checks out submodules and sets up uv before its command
      Given any of the `lint`/`test`/`audit` jobs
      When its steps are inspected
      Then it checks out with `submodules: true`, sets up `uv` via `astral-sh/setup-uv` with caching enabled, re-runs `install-command`, then runs its own command

- [ ] Scenario: Audit remains conditional
      Given the `audit` job
      When `audit-command` is omitted by the caller
      Then the job (or its command step) does not run and does not fail the workflow

## Out of scope
- Any change to the `workflow_call` input contract or consumer `ci.yml`
  files.
- Parallelizing lint/test/audit (explicitly sequential per the confirmed
  requirement).

## Blockers
None

## Completion
**Date:** 2026-08-01
**Summary:** Restructured `.github/workflows/python-ci.yml` from one `ci` job with sequential steps into four `needs`-chained jobs (`install` → `lint` → `test` → `audit`). Each job checks out with `submodules: true`, sets up Python and `uv` (`astral-sh/setup-uv` with `enable-cache: true`), re-runs `install-command`, then its own command. `audit` keeps its `if: inputs.audit-command != ''` conditional. Rewrote `tests/test_python_ci_workflow.py` for the new job structure (job set, `needs` chain, per-job checkout/uv/install, per-job command assertions). `workflow_call` input contract unchanged — no consumer `ci.yml` edits needed.
**Files changed:**
- `.github/workflows/python-ci.yml` - modified
**Branch:** `git checkout task/077-split-reusable-workflow-into-jobs`
**Stage:** `git add .github/workflows/python-ci.yml tests/test_python_ci_workflow.py CHANGELOG.md REQUIREMENTS_REUSABLE_CI.md docs/tasks/TASK-077-split-reusable-workflow-into-jobs.md`
**Commit:** `git commit -m "Split the reusable python-ci.yml into separate needs-chained jobs"`
