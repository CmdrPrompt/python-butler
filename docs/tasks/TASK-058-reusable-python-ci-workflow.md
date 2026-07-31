# TASK-058 Add reusable python-ci.yml workflow for consumer repos

## Status
done

## Requirements
**Binding:** Requirement 1, 2 (REQUIREMENTS_REUSABLE_CI.md)
**BDD mode:** BDD-ABSENT
**Depends on:** none
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer of a consumer repo (e.g. `firefly-bank-importer`), I want a reusable `python-ci.yml` workflow in `python-butler` with the same input contract my `ci.yml` already assumes, so that repointing my `uses:` line from the renamed `python-commons` repo restores real CI enforcement (lint/test/audit) on my pull requests.

## Description
`firefly-bank-importer`'s `.github/workflows/ci.yml` calls
`CmdrPrompt/python-commons/.github/workflows/python-ci.yml@main` with inputs
`python-version`, `install-command`, `lint-command`, `test-command`,
`audit-command`. That repo was renamed to `python-butler`, and no
`python-ci.yml` file has ever existed in either repo's history — every
consumer PR has been failing instantly ("workflow file issue") since at
least TASK-050 (2026-05), meaning lint/test/audit have never actually run
in CI for that consumer.

This task adds `.github/workflows/python-ci.yml` to `python-butler` as a
`workflow_call` reusable workflow matching that exact input contract, so
consumer repos can point at
`CmdrPrompt/python-butler/.github/workflows/python-ci.yml@main` with no
changes to their `with:` block.

**Implementation location:** new file
`.github/workflows/python-ci.yml` in this repo. Does not touch the
existing `.github/workflows/ci.yml` (`validate-agents` job).

## Branch
**Branch name:** `task/058-reusable-python-ci-workflow`
**Switch/create:** `git checkout -b task/058-reusable-python-ci-workflow`
**Make target:** `make branch-task f=TASK-058`

## Acceptance criteria (Gherkin)

- [x] Scenario: Reusable workflow accepts the existing consumer input contract
      Given a consumer repo's workflow calls `uses: CmdrPrompt/python-butler/.github/workflows/python-ci.yml@main`
      And passes `python-version`, `install-command`, `lint-command`, `test-command`, and `audit-command` under `with:`
      When the calling workflow runs
      Then the reusable workflow checks out the caller's repo, sets up the given Python version, and runs install, lint, test, and audit commands in order as separate steps

- [x] Scenario: A failing step fails the calling PR's check
      Given a consumer's `lint-command` (or `test-command`, or `audit-command`) exits non-zero
      When the reusable workflow runs that step
      Then the job fails, the calling PR's required check shows as failed, and the Actions log attributes the failure to that specific step (not install or an unrelated step)

- [x] Scenario: Omitted audit-command skips the audit step
      Given a caller's `with:` block does not set `audit-command`
      When the reusable workflow runs
      Then the audit step is skipped and the job does not fail solely because `audit-command` was absent

## Out of scope
- Updating `firefly-bank-importer`'s `.github/workflows/ci.yml` to point at
  the new location — that happens in that repo, after this workflow is
  merged here.
- Changes to the existing `validate-agents` job/workflow.
- Matrix Python versions, dependency caching, or non-`uv` install flows.

## Blockers
None

## Completion
**Date:** 2026-07-31
**Summary:** Added `.github/workflows/python-ci.yml` as a `workflow_call` reusable
workflow with the five inputs (`python-version`, `install-command`,
`lint-command`, `test-command` required; `audit-command` optional). The job
checks out the caller's repo, sets up Python via `actions/setup-python@v5`,
then runs install, lint, test as separate named `run:` steps (each failing
the job on non-zero exit, no `||` swallowing), and a conditional Audit step
(`if: inputs.audit-command != ''`) so an omitted `audit-command` is skipped
without failing the job. Added `tests/test_python_ci_workflow.py` to
statically verify the input contract, step ordering, and failure semantics
(the true end-to-end run against a real consumer PR is out of scope here,
per the task's Out of scope section, and happens once
`firefly-bank-importer` repoints its `uses:` line). No changes to the
existing `.github/workflows/ci.yml`/`validate-agents` job.
**Files changed:**
- `.github/workflows/python-ci.yml` - created
- `tests/test_python_ci_workflow.py` - created
- `CHANGELOG.md` - modified
- `REQUIREMENTS_REUSABLE_CI.md` - created (requirements doc, confirmed with user before implementation)
- `docs/tasks/TASK-058-reusable-python-ci-workflow.md` - modified
**Branch:** `git checkout task/058-reusable-python-ci-workflow`
**Stage:** `git add .github/workflows/python-ci.yml tests/test_python_ci_workflow.py CHANGELOG.md REQUIREMENTS_REUSABLE_CI.md docs/tasks/TASK-058-reusable-python-ci-workflow.md`
**Commit:** `git commit -m "Add reusable python-ci.yml workflow for consumer repos"`
