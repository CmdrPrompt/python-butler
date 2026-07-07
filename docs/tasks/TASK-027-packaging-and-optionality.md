# TASK-027 Packaging and optionality

## Status

todo

## Description

Finalize packaging so that `butler_core` and `butler_cli` are installable via
`uv tool install` / `pip install`, while remaining fully optional for projects
that only adopt butler's Makefile.

Covers Requirement 9 from REQUIREMENTS_MCP.md.

The MCP server has its own `mcp/pyproject.toml` (already created in TASK-025)
so its MCP SDK dependency does not leak. This task verifies the full adoption
matrix: Makefile-only, CLI-only, and CLI+MCP all work correctly.

Also update README to document CLI and MCP server installation and usage as
optional additions, separate from the base Makefile adoption flow.

**Depends on:** TASK-024 (CLI), TASK-025 (MCP), TASK-026 (Makefile refactor)

## Branch

**Branch name:** `task/027-packaging-and-optionality`
**Switch/create:** `git checkout -b task/027-packaging-and-optionality`
**Make target:** `make branch-task f=TASK-027`

## Acceptance criteria

- [ ] `uv tool install .` (from repo root) installs the `butler` CLI entry point
- [ ] A project that only includes `.butler/Makefile` (no Python package installed) still has fully working `make branch-task`, `stage-task`, `commit-task`, `pr-task`, `merge-pr` targets (falls back gracefully or the Makefile-only path is preserved)
- [ ] `mcp/pyproject.toml` is independently installable and does not pull in `butler_core`'s dev dependencies
- [ ] README has a section documenting CLI installation (`uv tool install`) and a section documenting MCP server setup, both clearly marked as optional
- [ ] `make lint && make test` pass

## Completion

**Date:**
**Summary:**
**Files changed:**

- `pyproject.toml` — modified (finalize entry points)
- `README.md` — modified (CLI and MCP server sections)

**Branch:** `git checkout task/027-packaging-and-optionality`
**Stage:** `git add pyproject.toml README.md CHANGELOG.md docs/tasks/TASK-027-packaging-and-optionality.md`
**Commit:** `git commit -m "Finalize packaging and document CLI and MCP server as optional additions"`
