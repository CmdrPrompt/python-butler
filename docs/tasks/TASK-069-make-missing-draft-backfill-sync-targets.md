# TASK-069 No standalone `make` target reaches `--stage draft`/`--stage backfill`

## Status
todo

## Requirements
**Binding:** Requirement 4, Requirement 6, Requirement 8, Requirement 10 (REQUIREMENTS_TASK_WORKFLOW.md)
**BDD mode:** BDD-ABSENT (parity gap; no new requirement text needed — Requirement 10 already commits to the claim this closes)
**Depends on:** None
**Precedence:** The requirements document is the binding definition of this task.
The story below is derived from it. On any discrepancy, the requirements
document wins. Stop and report discrepancies; do not build from the story.

## Story (context, not binding)
As a maintainer who only wants to use `make` (never invoking the `butler`
CLI directly), I want a `make` target for the GitHub Projects draft-stage
sync (mandatory per Workflow Guardian's "GitHub Projects draft sync gate"
right after committing a new task file) and for the backfill-stage sync
(Requirement 8, for historical tasks), so that `make` alone is a complete
interface to the task workflow instead of silently missing two of its five
sync stages.

## Description
**Gap (found live, 2026-07-31, during a parity audit requested after
TASK-067):** The root `Makefile` wires exactly three of the five
`sync-project` stages into existing targets as automatic added steps:

- `branch-task` -> `--stage start` (line ~214)
- `pr-task`/`pr-current-task` -> `--stage open` (line ~258)
- `merge-pr`/`merge-current-task` -> `--stage merge` (line ~271)

There is no target anywhere in the Makefile that runs `--stage draft` or
`--stage backfill`. Both are only reachable via the raw CLI invocation:
`butler --tasks-dir docs/tasks task sync-project TASK-XXX --stage draft`
(mandated by `.claude/agents/workflow-guardian.agent.md`'s "GitHub
Projects draft sync gate", run immediately after committing a
Task-Drafter-produced task file, before any task branch/`make branch-task`
call exists to piggyback on) or `--stage backfill` (Requirement 8, a
one-off historical-task sync with no natural `make branch-task`/`pr-task`/
`merge-pr` call site to attach to either).

This directly undercuts the wording TASK-067 just shipped in Requirement
10 / the generated `CLAUDE.md`, which states the underlying operations
(explicitly including "task-file sync") "may be performed via the `make`
targets... interchangeably" with the CLI/MCP. For the draft and backfill
stages specifically, that claim is false today: `make` alone cannot do
them.

**Proposed fix:** Add two standalone `make` targets, e.g. `sync-project-draft
f=<TASK-ID>` and `sync-project-backfill f=<TASK-ID>`, each a thin wrapper
around `butler --tasks-dir $(TASKS_DIR) task sync-project $(f) --stage
draft`/`--stage backfill` (matching the existing `stage-task`/`commit-task`
`f=`-argument convention and their `check-butler` dependency). Naming and
whether to also add `*-current-task` auto-detecting variants (matching
`stage-current-task`/`commit-current-task`'s branch-name-parsing pattern)
is an implementation decision for whoever picks this up — `--stage draft`
in particular runs before a task branch exists, so a `-current-task`
variant may not make sense for it the way it does for the branch-scoped
stages.

**Implementation location:** `Makefile` (new targets near `stage-task`/
`commit-task`, lines ~223-231), `README.md` if it documents the sync
stages' invocation, `tests/test_projects_makefile_integration.py` (existing
test file already asserts Makefile/CLI flag parity for other stages — add
coverage for the new targets there).

## Branch
**Branch name:** `task/069-make-missing-draft-backfill-sync-targets`
**Switch/create:** `git checkout -b task/069-make-missing-draft-backfill-sync-targets`
**Make target:** `make branch-task f=TASK-069`

## Acceptance criteria (Gherkin)

- [ ] Scenario: A standalone `make` target runs the draft-stage sync
      Given a task file with no linked Project item yet
      When `make sync-project-draft f=TASK-XXX` runs
      Then it invokes `butler task sync-project TASK-XXX --stage draft`
      and reports the same result the equivalent raw CLI call would

- [ ] Scenario: A standalone `make` target runs the backfill-stage sync
      Given a historical task file
      When `make sync-project-backfill f=TASK-XXX` runs
      Then it invokes `butler task sync-project TASK-XXX --stage backfill`
      and reports the same result the equivalent raw CLI call would

- [ ] `tests/test_projects_makefile_integration.py` covers the new targets
      the same way it already covers the existing sync-stage Makefile
      wiring

- [ ] make lint && make test pass

- [ ] CHANGELOG.md updated

## Out of scope
- Changing the CLI's or existing Makefile targets' (`branch-task`/
  `pr-task`/`merge-pr`) existing automatic sync wiring for
  `start`/`open`/`merge`.
- Fixing the separate MCP-side gap (no MCP tools for any sync-project
  stage) — tracked as TASK-068.
- Auditing `set_task_status`'s asymmetry or `butler sync`'s continued
  relevance — tracked separately as TASK-070 and TASK-071.

## Blockers
None

## Completion
**Date:**
**Summary:**
**Files changed:**
**Branch:** `git checkout task/069-make-missing-draft-backfill-sync-targets`
**Stage:** `git add Makefile tests/test_projects_makefile_integration.py CHANGELOG.md docs/tasks/TASK-069-make-missing-draft-backfill-sync-targets.md`
**Commit:** `git commit -m "Add standalone make targets for the draft and backfill GitHub Projects sync stages"`
