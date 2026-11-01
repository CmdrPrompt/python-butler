# TASK-098 Upgrade vulnerable locked dependencies

## Status
todo

## Requirements
**Binding:** Requirement 6 (REQUIREMENTS_REUSABLE_CI.md)
**BDD mode:** BDD-ACTIVE
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer of python-butler and its consumer projects, I want every
locked dependency to pass the CI security audit, so that unrelated pull
requests are no longer blocked by advisories against versions already in
the lockfile.

## Description
`ci / audit` fails on `main` and on PR #103 with "Found 34 known
vulnerabilities in 5 packages": `virtualenv` 21.6.0 (19), `filelock` 3.29.6
(9), `urllib3` 2.7.0 (3), `certifi` 2026.7.22 (2) and `msgpack` 1.2.1 (1).
All five are transitive development dependencies pulled in by `pre-commit`
and `pip-audit`. The "butler-core (0.1.0) Dependency not found on PyPI" line
is informational only and is not the cause.

Upgrade only the affected packages in `uv.lock` with `uv lock
--upgrade-package virtualenv --upgrade-package filelock --upgrade-package
urllib3 --upgrade-package certifi --upgrade-package msgpack`. A dry run
resolves to virtualenv 21.15.2, filelock 4.2.6, urllib3 2.8.0, certifi
2026.10.23 and msgpack 1.2.4. The dry run also moves two transitive
dependencies, `python-discovery` 1.4.3 to 1.9.0 and `packaging` 26.2 to
26.3; these are expected required updates and are allowed.

Risk: filelock 4.x is a major version bump. All nine filelock advisories
are fixed only in 4.x (4.0.9 / 4.2.1), so staying on 3.x is not an option.
If 4.x breaks `make lint`, `make test`, `make bdd` or the pre-commit hooks,
stop and mark the task blocked; do not pin filelock below 4. Only
`uv.lock` changes; `pyproject.toml` stays untouched.

Do not change the CI workflow, do not run an unscoped `uv lock --upgrade`,
and do not add advisory ignore entries to silence the audit. Requirement 6
is met only when the audit passes against the locked versions.

## Branch
**Branch name:** `task/098-upgrade-vulnerable-locked-dependencies`
**Switch/create:** `git checkout -b task/098-upgrade-vulnerable-locked-dependencies`
**Make target:** `make branch-task f=TASK-098`

## Acceptance criteria (Gherkin)
**Feature files:** tests/bdd/features/TASK-098-upgrade-vulnerable-locked-dependencies.feature

- [ ] 1. See `tests/bdd/features/TASK-098-upgrade-vulnerable-locked-dependencies.feature`: Scenario "Locked dependencies report no known vulnerabilities" (@AC-1)
- [ ] 2. See `tests/bdd/features/TASK-098-upgrade-vulnerable-locked-dependencies.feature`: Scenario "Only the local package is skipped" (@AC-2)
- [ ] 3. See `tests/bdd/features/TASK-098-upgrade-vulnerable-locked-dependencies.feature`: Scenario "Quality gates still pass after the upgrade" (@AC-3)
- [ ] 4. See `tests/bdd/features/TASK-098-upgrade-vulnerable-locked-dependencies.feature`: Scenario "Only affected packages change in the lockfile" (@AC-4)

## Out of scope
- Dependabot or Renovate automation for dependency updates.
- Changing `.github/workflows/python-ci.yml` or any other CI workflow.
- Upgrading packages that are not in the audit findings, and any unscoped whole-lockfile upgrade.
- Adding advisory ignore entries to the audit configuration.
- Changing `REQUIREMENTS_REUSABLE_CI.md` or any other requirements document.

## Blockers
None

## Completion
**Date:** YYYY-MM-DD
**Summary:** What was done, any decisions made, and what was left out and why.
**Files changed:**
- `path/to/file` - created / modified
**Branch:** `git checkout task/098-upgrade-vulnerable-locked-dependencies`
**Stage:** `uv.lock CHANGELOG.md docs/tasks/TASK-098-upgrade-vulnerable-locked-dependencies.md tests/bdd/features/TASK-098-upgrade-vulnerable-locked-dependencies.feature tests/bdd/steps/test_task_098_steps.py`
**Commit:** `git commit -m "Upgrade locked dev dependencies with known vulnerabilities (TASK-098)"`
