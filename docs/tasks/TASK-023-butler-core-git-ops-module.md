# TASK-023 butler_core git_ops module

## Status

todo

## Description

Implement `src/butler_core/git_ops.py` extracting the logic currently inlined
in Makefile targets into Python functions: `branch_for(task)`, `stage_for(task)`,
`commit_for(task)`, `open_pr_for(task)`, `merge_pr_for(task)`.

Covers Requirement 5 from REQUIREMENTS_MCP.md.

Behavior must match the current Makefile exactly, including error messages
(e.g. "No task file found matching '...'") so existing CI scripts are not broken.

**Depends on:** TASK-022 (butler_core tasks module)

## Branch

**Branch name:** `task/023-butler-core-git-ops-module`
**Switch/create:** `git checkout -b task/023-butler-core-git-ops-module`
**Make target:** `make branch-task f=TASK-023`

## Acceptance criteria

- [ ] `branch_for(task)` creates or switches to the task branch (matching Makefile `branch-task` behavior)
- [ ] `stage_for(task)` runs ruff fix, ruff format, pymarkdown fix, then `git add` per task's Stage command
- [ ] `commit_for(task)` commits with message from task's Commit field
- [ ] `open_pr_for(task)` pushes branch and runs `gh pr create` with title and body from task
- [ ] `merge_pr_for(task)` squash-merges the open PR and pulls main
- [ ] Error messages match current Makefile (e.g. "No task file found matching '...'")
- [ ] Unit tests cover branch-already-exists path and missing-task-file error path
- [ ] `make lint && make test` pass

## Completion

**Date:**
**Summary:**
**Files changed:**

- `src/butler_core/git_ops.py` — created
- `tests/test_git_ops.py` — created

**Branch:** `git checkout task/023-butler-core-git-ops-module`
**Stage:** `git add src/butler_core/git_ops.py tests/test_git_ops.py CHANGELOG.md docs/tasks/TASK-023-butler-core-git-ops-module.md`
**Commit:** `git commit -m "Implement butler_core git_ops module matching Makefile target behavior"`
