# TASK-022 butler_core tasks module

## Status

todo

## Description

Implement `src/butler_core/tasks.py` providing a `Task` dataclass and all task
file operations: `read_task`, `list_tasks`, `create_task`, `check_criterion`,
`set_status`.

Covers Requirements 1–4 from REQUIREMENTS_MCP.md.

The parser must round-trip existing task files in `docs/tasks/` without
altering unrelated content. The writer must produce output compatible with the
existing `grep`/`sed` parsing in the Makefile (so `make branch-task`,
`stage-task`, `commit-task` keep working on tasks created via this module).

Tests must use Hypothesis for parsing edge cases as specified in the overall
acceptance criteria.

**Depends on:** TASK-021 (package scaffolding)

## Branch

**Branch name:** `task/022-butler-core-tasks-module`
**Switch/create:** `git checkout -b task/022-butler-core-tasks-module`
**Make target:** `make branch-task f=TASK-022`

## Acceptance criteria

- [ ] `Task` dataclass has all fields from Req 1: `id`, `title`, `status`, `description`, `branch_name`, `switch_create_cmd`, `stage_cmd`, `commit_message`, `acceptance_criteria`, `completion`
- [ ] `read_task("TASK-015", tasks_dir="docs/tasks")` returns correct structured data for an existing task file
- [ ] `list_tasks(tasks_dir="docs/tasks", status="todo")` returns only tasks matching the filter
- [ ] `create_task(title, description, tasks_dir)` allocates the next TASK-NNN number, writes a correctly formatted file
- [ ] Files created by `create_task` work with `make branch-task`, `make stage-task`, `make commit-task`
- [ ] `check_criterion("TASK-021", index=0, tasks_dir="docs/tasks")` toggles the checkbox
- [ ] `set_status("TASK-021", "done", tasks_dir="docs/tasks")` updates the Status section
- [ ] Hypothesis-based round-trip tests pass (parse → write → parse produces identical data)
- [ ] `make lint && make test` pass

## Completion

**Date:**
**Summary:**
**Files changed:**

- `src/butler_core/tasks.py` — created
- `tests/test_tasks.py` — created

**Branch:** `git checkout task/022-butler-core-tasks-module`
**Stage:** `git add src/butler_core/tasks.py tests/test_tasks.py CHANGELOG.md docs/tasks/TASK-022-butler-core-tasks-module.md`
**Commit:** `git commit -m "Implement butler_core tasks module with parse, list, create, and update operations"`
