# TASK-021 Package scaffolding

## Status

todo

## Description

Set up `python-butler` as a proper Python project: create `pyproject.toml`,
`src/butler_core/`, `src/butler_cli/` package skeletons, `mcp/` directory
skeleton, and `tests/` directory. This is the prerequisite for all subsequent
butler_core implementation tasks.

Includes installing dev dependencies so `make lint && make test` pass on the
empty package.

## Branch

**Branch name:** `task/021-package-scaffolding`
**Switch/create:** `git checkout -b task/021-package-scaffolding`
**Make target:** `make branch-task f=TASK-021`

## Acceptance criteria

- [ ] `pyproject.toml` exists and declares `butler_core` and `butler_cli` as packages under `src/`
- [ ] `src/butler_core/__init__.py` and `src/butler_cli/__init__.py` exist
- [ ] `mcp/` directory exists with a placeholder `server.py`
- [ ] `tests/` directory exists with a placeholder test
- [ ] `make install` succeeds (uv sync + pre-commit install)
- [ ] `make lint && make test` pass on the empty skeleton

## Completion

**Date:**
**Summary:**
**Files changed:**

- `pyproject.toml` — created
- `src/butler_core/__init__.py` — created
- `src/butler_cli/__init__.py` — created
- `mcp/__init__.py` — created
- `mcp/server.py` — created
- `tests/__init__.py` — created
- `tests/test_placeholder.py` — created

**Branch:** `git checkout task/021-package-scaffolding`
**Stage:** `git add pyproject.toml src/ mcp/ tests/ CHANGELOG.md docs/tasks/TASK-021-package-scaffolding.md`
**Commit:** `git commit -m "Scaffold butler_core, butler_cli, and mcp package structure"`
