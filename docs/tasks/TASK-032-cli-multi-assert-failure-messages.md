# TASK-032 Add assertion messages to multi-assert CLI tests

## Status

todo

## Description

**Test quality improvement:** Four tests in `tests/test_cli.py` make multiple assertions
with no failure message, so a failure does not immediately state which field diverged
without reading the test body: `test_prints_structured_task_data` (4 asserts),
`test_prints_checked_and_unchecked_acceptance_criteria` (2 asserts),
`test_prints_completion_date_and_summary_when_present` (2 asserts), and
`test_creates_new_task_file_and_prints_id` (2 asserts). Add an assertion message to each
`assert` in these tests stating what was expected.
**Property:** Understandable
**Current blended score:** 8.4
**Target score:** 9.0
**Evidence:** `tests/test_cli.py:49-52`, `tests/test_cli.py:68-69`,
`tests/test_cli.py:83-84`, `tests/test_cli.py:116-117`

Covers a Test Design Reviewer finding from the TASK-024 (`src/butler_cli/__main__.py`)
review.

## Branch

**Branch name:** `task/032-cli-multi-assert-failure-messages`
**Switch/create:** `git checkout -b task/032-cli-multi-assert-failure-messages`
**Make target:** `make branch-task f=TASK-032`

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

**Branch:** `git checkout task/032-cli-multi-assert-failure-messages`
**Stage:** `git add tests/test_cli.py CHANGELOG.md`
**Commit:** `git commit -m "Add assertion messages to multi-assert CLI tests"`
