# TASK-078 Dogfood the reusable python-ci.yml in this repo's own ci.yml

## Status
in-progress

## Requirements
**Binding:** Requirement 5 (REQUIREMENTS_REUSABLE_CI.md)
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-077
**Precedence:** The requirements document is the binding definition of this task.
The story and scenarios below are derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer of this repo, I want its own PR checks to run `make lint`/
`make test`/`pip-audit` via the reusable workflow it publishes for other
repos, so that a lint or test failure here is caught by CI instead of only
being caught when someone happens to run `make lint`/`make test` locally.

## Description
`.github/workflows/ci.yml` currently only runs `validate-agents`; nothing in
GitHub Actions runs this repo's own `make lint`/`make test`. Add a `ci` job
that calls `./.github/workflows/python-ci.yml` (same-repo relative
reference) with `install-command: "uv sync --extra dev"`,
`lint-command: "make lint"`, `test-command: "make test"`,
`audit-command: "uv run pip-audit --progress-spinner=off"`. Add `pip-audit`
to `pyproject.toml`'s `dev` extra (mirrors the fix already applied to
`firefly-bank-importer`, TASK-061) so the audit command is runnable.

## Branch
**Branch name:** `task/078-dogfood-reusable-ci-workflow`
**Switch/create:** `git checkout -b task/078-dogfood-reusable-ci-workflow`
**Make target:** `make branch-task f=TASK-078`

## Acceptance criteria (Gherkin)

- [ ] Scenario: ci.yml calls the reusable workflow with this repo's commands
      Given `.github/workflows/ci.yml`
      When its `jobs` are inspected
      Then a `ci` job exists with `uses: ./.github/workflows/python-ci.yml` and `with:` values `install-command: "uv sync --extra dev"`, `lint-command: "make lint"`, `test-command: "make test"`, `audit-command: "uv run pip-audit --progress-spinner=off"`, alongside the existing `validate-agents` job

- [ ] Scenario: pip-audit is installed and runs clean
      Given `pyproject.toml`'s `dev` extra
      When `uv sync --extra dev` then `uv run pip-audit --progress-spinner=off` run
      Then `pip-audit` is found and reports no known vulnerabilities

## Out of scope
- Changing `validate-agents` itself.
- Vulnerability remediation beyond what's needed to make `pip-audit` pass
  cleanly today.

## Blockers
None

## Completion
**Date:** 2026-08-01
**Summary:** Added a `ci` job to `.github/workflows/ci.yml` that calls `./.github/workflows/python-ci.yml` (same-repo relative reference) with `install-command: "uv sync --extra dev"`, `lint-command: "make lint"`, `test-command: "make test"`, `audit-command: "uv run pip-audit --progress-spinner=off"`, alongside the existing `validate-agents` job. Added `pip-audit` to `pyproject.toml`'s `dev` extra; `uv run pip-audit` reports no known vulnerabilities. Added `tests/test_ci_workflow.py` asserting `validate-agents` is unchanged and the new `ci` job's `uses`/`with` match. `make lint` and full suite (324 passed) both pass.

Also fixed, while investigating why TASK-075/076/077 never appeared on the GitHub Project board: the globally installed `butler` CLI (`uv tool install`) predated the `sync-project`/`set-status` subcommands, so every `make branch-task`/`pr-current-task`/`merge-current-task` sync step had been silently no-op'ing all session. Reinstalled via `uv tool install --force .`, backfilled TASK-075/076/077 to the Project board, and set their task-file Status to `done` (separate `chore:` commit directly on `main`, since it's metadata bookkeeping unrelated to this task's scope).
**Files changed:**
- `.github/workflows/ci.yml` - modified
- `pyproject.toml` - modified
**Branch:** `git checkout task/078-dogfood-reusable-ci-workflow`
**Stage:** `git add .github/workflows/ci.yml pyproject.toml uv.lock CHANGELOG.md REQUIREMENTS_REUSABLE_CI.md docs/tasks/TASK-078-dogfood-reusable-ci-workflow.md`
**Commit:** `git commit -m "Dogfood the reusable python-ci.yml in this repo's own ci.yml"`
