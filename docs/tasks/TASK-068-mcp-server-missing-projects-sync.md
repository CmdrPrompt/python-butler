# TASK-068 MCP server has no tools for the GitHub Projects sync

## Status
todo

## Requirements
**Binding:** Requirement 4, Requirement 10 (REQUIREMENTS_TASK_WORKFLOW.md)
**BDD mode:** BDD-ABSENT (parity gap; no new requirement text needed — Requirement 10 already commits to the claim this closes)
**Depends on:** None (TASK-067, which shipped Requirement 10's interchangeability wording, does not block this — it is what surfaced the gap)
**Precedence:** The requirements document is the binding definition of this task.
The story below is derived from it. On any discrepancy, the requirements
document wins. Stop and report discrepancies; do not build from the story.

## Story (context, not binding)
As a maintainer working through the `butler-mcp` MCP server (e.g. from an
MCP-compatible agent that has no shell access to run the `butler` CLI or
`make` directly), I want to sync a task's metadata to its linked GitHub
Projects item (draft/open/merge/backfill/start stages) the same way the CLI
already can, so that Workflow Guardian's mandatory "GitHub Projects draft
sync gate" step is actually reachable from an MCP-only environment instead
of silently unavailable.

## Description
**Gap (found live, 2026-07-31, during a parity audit requested after
TASK-067):** `src/butler_cli/__main__.py` exposes `butler task sync-project
<ID> --stage open|merge|draft|backfill|start`, backed by
`butler_core.projects.sync_on_pr_open/_merge/_draft/_backfill/_start`. The
Makefile wires `--stage start`/`open`/`merge` into `branch-task`/`pr-task`/
`merge-pr` automatically. `mcp/server.py`, however, exposes exactly 10
tools (`list_tasks`, `get_task`, `create_task`,
`check_acceptance_criterion`, `set_task_status`, `branch_task`,
`stage_task`, `commit_task`, `open_pr_for_task`, `merge_task_pr` — matching
`mcp/tests/test_server.py`'s `EXPECTED_TOOL_NAMES` exactly) and none of
them touch `butler_core.projects` at all. There is no MCP path to any of
the five sync stages.

This directly undercuts the wording TASK-067 just shipped in Requirement
10 / the generated `CLAUDE.md`, which states the underlying operations
(explicitly including "task-file sync") "may be performed via the `make`
targets... the installed `butler` CLI directly, or the `butler-mcp` MCP
server ... interchangeably." For GitHub Projects sync specifically, that
claim is false today: only the CLI can do it.

**Proposed fix:** Add MCP tool(s) in `mcp/server.py` wrapping
`butler_core.projects.sync_on_pr_open`/`_merge`/`_draft`/`_backfill`/
`_start`, mirroring the CLI's `--stage` dispatch (either one
`sync_project_task(task_id: str, stage: str)` tool matching the CLI's
single `sync-project --stage <x>` shape, or five separate tools matching
the one-tool-per-git-operation pattern the module's docstring already
states for branch/stage/commit/pr/merge — implementation choice for
whoever picks this up). Update `mcp/tests/test_server.py`'s
`EXPECTED_TOOL_NAMES` set and add coverage for the new tool(s), following
the existing test patterns in that file (fixture task files, `asyncio`
tool invocation).

**Implementation location:** `mcp/server.py`, `mcp/tests/test_server.py`.

## Branch
**Branch name:** `task/068-mcp-server-missing-projects-sync`
**Switch/create:** `git checkout -b task/068-mcp-server-missing-projects-sync`
**Make target:** `make branch-task f=TASK-068`

## Acceptance criteria (Gherkin)

- [ ] Scenario: MCP exposes a way to run every sync-project stage
      Given the MCP server (`mcp/server.py`)
      When its tool list is inspected
      Then a tool (or tools) exist covering all five stages
      (`open`/`merge`/`draft`/`backfill`/`start`) that
      `butler task sync-project --stage <x>` already covers via the CLI

- [ ] Scenario: The new tool(s) return the sync's best-effort result, never raise
      Given a task with no configured GitHub Project (or any other
      best-effort sync failure condition per Requirement 4)
      When the MCP tool is invoked for that task
      Then it returns the sync's warning/result message rather than raising
      an unhandled exception, matching the CLI's `SyncResult` handling

- [ ] `mcp/tests/test_server.py`'s `EXPECTED_TOOL_NAMES` is updated and new
      test coverage exists for the added tool(s)

- [ ] make lint && make test pass (both this repo's own suite and, if the
      MCP package has its own `pytest` run, that one too)

- [ ] CHANGELOG.md updated

## Out of scope
- Changing the CLI's or Makefile's existing sync-project behavior — this
  task only adds the missing MCP surface.
- Fixing the separate Make-side gap (no standalone `make` target for
  `--stage draft`/`--stage backfill`) — tracked as TASK-069.
- Auditing `set_task_status`'s asymmetry (MCP has it, CLI doesn't) or
  `butler sync`'s continued relevance — tracked separately as TASK-070 and
  TASK-071.

## Blockers
None

## Completion
**Date:**
**Summary:**
**Files changed:**
**Branch:** `git checkout task/068-mcp-server-missing-projects-sync`
**Stage:** `git add mcp/server.py mcp/tests/test_server.py CHANGELOG.md docs/tasks/TASK-068-mcp-server-missing-projects-sync.md`
**Commit:** `git commit -m "Add GitHub Projects sync tools to the MCP server"`
