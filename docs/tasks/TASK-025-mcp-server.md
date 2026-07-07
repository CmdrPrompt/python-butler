# TASK-025 MCP server

## Status

todo

## Description

Implement `mcp/server.py` as a thin wrapper over `butler_core`, exposing all
task and git/gh operations as MCP tools over stdio transport.

Covers Requirement 7 from REQUIREMENTS_MCP.md.

The MCP server lives in its own `mcp/pyproject.toml` so its dependency on the
MCP SDK does not leak into projects that don't use it. Each tool maps 1:1 to
a `butler_core` function — no implicit batching of multiple git operations.

**Depends on:** TASK-022 and TASK-023 (butler_core modules)

## Branch

**Branch name:** `task/025-mcp-server`
**Switch/create:** `git checkout -b task/025-mcp-server`
**Make target:** `make branch-task f=TASK-025`

## Acceptance criteria

- [ ] `mcp/server.py` implements `list_tasks`, `get_task`, `create_task`, `check_acceptance_criterion`, `set_task_status` tools
- [ ] `mcp/server.py` implements `branch_task`, `stage_task`, `commit_task`, `open_pr_for_task`, `merge_task_pr` tools
- [ ] Each action tool (branch/stage/commit/pr/merge) performs exactly one git operation per call
- [ ] `mcp/pyproject.toml` exists and declares the MCP SDK as a dependency, separate from main `pyproject.toml`
- [ ] Server runs over stdio transport (invocable via `python -m mcp.server` or `uv run mcp/server.py`)
- [ ] Manually verified: Claude Code can connect and call `list_tasks` against this repo's `docs/tasks/`
- [ ] `make lint && make test` pass

## Completion

**Date:**
**Summary:**
**Files changed:**

- `mcp/server.py` — created/updated
- `mcp/pyproject.toml` — created

**Branch:** `git checkout task/025-mcp-server`
**Stage:** `git add mcp/server.py mcp/pyproject.toml CHANGELOG.md docs/tasks/TASK-025-mcp-server.md`
**Commit:** `git commit -m "Implement MCP server exposing butler_core operations over stdio"`
