# TASK-073 Add `butler task set-status` CLI subcommand

## Status
todo

## Requirements
**Binding:** Requirement 4, Requirement 6 (REQUIREMENTS_MCP.md, as amended
2026-08-01 to add `butler task set-status TASK-015 done` to Requirement 6's
example command list)
**BDD mode:** BDD-ABSENT (parity fix following an already-confirmed
requirement amendment; no new Gherkin scenario needed beyond this task's
own acceptance criteria)
**Depends on:** TASK-070 (investigation that produced this requirement
amendment and its confirmation)
**Precedence:** The requirements document is the binding definition of this
task. The story below is derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build
from the story.

## Story (context, not binding)
As a developer or Workflow Guardian using the `butler` CLI directly (no MCP
client available), I want a `task set-status` subcommand equivalent to
`butler-mcp`'s existing `set_task_status` tool, so that a Status transition
can be performed the same way through either interface instead of only
being reachable via MCP or a manual file edit.

## Description
**Background (TASK-070):** `butler_core.tasks.set_status()` has existed
since the shared task-core module was introduced (REQUIREMENTS_MCP.md
Requirement 4) and is already exposed as `mcp/server.py`'s
`set_task_status(task_id, status)` tool (Requirement 7). The CLI
(`src/butler_cli/__main__.py`) never gained a matching subcommand —
Requirement 6's example list simply omitted it, confirmed (TASK-070) to be
a spec oversight rather than an intentional restriction. The user confirmed
the fix: add CLI parity.

**Implementation:** Add a `task set-status <ID> <status>` subparser to
`_build_parser()` in `src/butler_cli/__main__.py`, following `task check`'s
existing pattern (positional `task_id`, plus the new value), backed by a
`_cmd_set_status` handler calling the already-tested
`butler_core.tasks.set_status(task_id, status, tasks_dir=...)` — no new
`butler_core` logic needed, `set_status` already validates against
`VALID_STATUSES` and raises `ValueError` for an invalid one. Register the
handler in `_TASK_HANDLERS`.

**Implementation location:** `src/butler_cli/__main__.py`,
`tests/test_cli.py`.

## Branch
**Branch name:** `task/073-add-butler-task-set-status-cli-subcommand`
**Switch/create:** `git checkout -b task/073-add-butler-task-set-status-cli-subcommand`
**Make target:** `make branch-task f=TASK-073`

## Acceptance criteria (Gherkin)

- [ ] Scenario: `butler task set-status` updates the task file's Status field
      Given a task file with `## Status\ntodo`
      When `butler task set-status TASK-015 done` is run
      Then the task file's `## Status` field reads `done`, matching what
      `butler-mcp`'s `set_task_status` tool already does for the same input

- [ ] Scenario: An invalid status value is rejected
      Given a task file with `## Status\ntodo`
      When `butler task set-status TASK-015 bogus` is run
      Then the command fails with the same `ValueError` message
      `butler_core.tasks.set_status` already raises for an invalid status,
      matching the MCP tool's behavior for the same input

- [ ] `make lint && make test` pass, with coverage not below the task-start
      baseline

- [ ] CHANGELOG.md updated

## Out of scope
- Adding a `make set-status-task f=TASK-XXX` Makefile target — not
  requested by TASK-070's recommendation or Requirement 6, and Status
  transitions during the normal workflow continue to happen via a task-file
  edit committed through `stage-current-task`/`commit-current-task` as
  today; this task only closes the CLI-vs-MCP tool gap.
- Any change to `mcp/server.py`'s `set_task_status` tool — it already works
  correctly and is the parity target, not the thing being fixed.
- Any gating/verification logic (e.g. requiring acceptance criteria to be
  checked before allowing `done`) — TASK-070 concluded the gate is
  procedural (Workflow Guardian's own diligence) on every interface today,
  and changing that would be a separate, explicitly-scoped decision.

## Blockers
None

## Completion
**Date:**
**Summary:**
**Files changed:**
**Branch:** `git checkout task/073-add-butler-task-set-status-cli-subcommand`
**Stage:** `git add src/butler_cli/__main__.py tests/test_cli.py REQUIREMENTS_MCP.md CHANGELOG.md docs/tasks/TASK-073-add-butler-task-set-status-cli-subcommand.md`
**Commit:** `git commit -m "Add butler task set-status CLI subcommand"`
