# TASK-024 butler-cli

## Status

todo

## Description

Implement `src/butler_cli/__main__.py` as a thin wrapper over `butler_core`,
exposing all task and git/gh operations as CLI subcommands under `butler task`.

Covers Requirement 6 from REQUIREMENTS_MCP.md.

The CLI entry point is registered in `pyproject.toml` as `butler-cli` (or
`butler`). It must be installable via `uv tool install` and work in terminals
including GitHub Codespaces.

**Depends on:** TASK-022 and TASK-023 (butler_core modules)

## Branch

**Branch name:** `task/024-butler-cli`
**Switch/create:** `git checkout -b task/024-butler-cli`
**Make target:** `make branch-task f=TASK-024`

## Acceptance criteria

- [ ] `butler task list [--status todo|in-progress|done]` prints matching tasks
- [ ] `butler task show TASK-015` prints structured task data
- [ ] `butler task create --title "..." --description "..."` creates a new task file
- [ ] `butler task check TASK-015 --criterion 2` checks the specified criterion
- [ ] `butler task branch TASK-015` delegates to `git_ops.branch_for`
- [ ] `butler task stage TASK-015` delegates to `git_ops.stage_for`
- [ ] `butler task commit TASK-015` delegates to `git_ops.commit_for`
- [ ] `butler task pr TASK-015` delegates to `git_ops.open_pr_for`
- [ ] `butler task merge TASK-015` delegates to `git_ops.merge_pr_for`
- [ ] CLI entry point declared in `pyproject.toml` and installable via `uv tool install`
- [ ] `make lint && make test` pass

## Completion

**Date:**
**Summary:**
**Files changed:**

- `src/butler_cli/__main__.py` — created
- `tests/test_cli.py` — created

**Branch:** `git checkout task/024-butler-cli`
**Stage:** `git add src/butler_cli/__main__.py tests/test_cli.py pyproject.toml CHANGELOG.md docs/tasks/TASK-024-butler-cli.md`
**Commit:** `git commit -m "Implement butler-cli exposing all butler_core operations as subcommands"`
