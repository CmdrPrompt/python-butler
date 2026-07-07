# TASK-026 Makefile refactor

## Status

todo

## Description

Refactor the existing Makefile targets (`branch-task`, `stage-task`,
`commit-task`, `pr-task`, `merge-pr` and their `-current-task` variants) to
delegate to `butler-cli` instead of inlining `grep`/`sed` parsing.

Covers Requirement 8 from REQUIREMENTS_MCP.md.

Target names, arguments (`f=TASK-XXX`), and all observable behavior must
remain identical. If `butler-cli` is not installed, targets must fail with a
clear error message pointing at how to install it — not a cryptic Python
traceback.

**Depends on:** TASK-024 (butler-cli fully implemented)

## Branch

**Branch name:** `task/026-makefile-refactor`
**Switch/create:** `git checkout -b task/026-makefile-refactor`
**Make target:** `make branch-task f=TASK-026`

## Acceptance criteria

- [ ] `make branch-task f=TASK-021` delegates to `butler task branch TASK-021`
- [ ] `make stage-task f=TASK-021` delegates to `butler task stage TASK-021`
- [ ] `make commit-task f=TASK-021` delegates to `butler task commit TASK-021`
- [ ] `make pr-task f=TASK-021` delegates to `butler task pr TASK-021`
- [ ] `make merge-pr f=TASK-021` delegates to `butler task merge TASK-021`
- [ ] All `-current-task` variants still derive TASK-NNN from branch name and delegate correctly
- [ ] When `butler-cli` is not installed, each target prints a clear install instruction and exits 1
- [ ] `make lint && make test` pass

## Completion

**Date:**
**Summary:**
**Files changed:**

- `Makefile` — modified

**Branch:** `git checkout task/026-makefile-refactor`
**Stage:** `git add Makefile CHANGELOG.md docs/tasks/TASK-026-makefile-refactor.md`
**Commit:** `git commit -m "Refactor Makefile task targets to delegate to butler-cli"`
