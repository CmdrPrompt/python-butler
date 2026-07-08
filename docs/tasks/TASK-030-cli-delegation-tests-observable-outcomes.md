# TASK-030 CLI delegation tests should assert observable outcomes, not mock call args

## Status

todo

## Description

**Test quality improvement:** The 5 tests in `tests/test_cli.py::TestGitDelegation`
(`branch`, `stage`, `commit`, `pr`, `merge`) only assert `mock_x.call_count == 1` and
`mock_x.call_args.args[0].id == "TASK-001"`. This is Mock Tautology Theatre: it verifies
the mock was called with a certain object rather than any externally observable CLI
behaviour, so the tests break on any internal signature refactor even when behaviour is
unchanged, and provide weaker regression protection than an outcome-based assertion would.
**Property:** Maintainable
**Current blended score:** 6.0
**Target score:** 7.5
**Evidence:** `tests/test_cli.py:136-180` (all 5 `TestGitDelegation` tests)

Covers a Test Design Reviewer finding from the TASK-024 (`src/butler_cli/__main__.py`)
review.

## Branch

**Branch name:** `task/030-cli-delegation-tests-observable-outcomes`
**Switch/create:** `git checkout -b task/030-cli-delegation-tests-observable-outcomes`
**Make target:** `make branch-task f=TASK-030`

## Acceptance criteria

- [ ] Identified tests refactored to address the finding
- [ ] Farley Index re-evaluated — blended score for this property does not decrease
- [ ] make lint && make test pass
- [ ] CHANGELOG.md updated

## Completion

**Date:**
**Summary:**
**Files changed:**

- `tests/test_cli.py` — modified

**Branch:** `git checkout task/030-cli-delegation-tests-observable-outcomes`
**Stage:** `git add tests/test_cli.py CHANGELOG.md`
**Commit:** `git commit -m "Assert observable outcomes instead of mock call args in CLI delegation tests"`
