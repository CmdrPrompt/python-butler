# TASK-070 Investigate the `set_task_status` MCP/CLI asymmetry

## Status
todo

## Requirements
**Binding:** Requirement 10 (REQUIREMENTS_TASK_WORKFLOW.md)
**BDD mode:** BDD-ABSENT (investigation task — no requirement text confirmed yet, see below)
**Depends on:** None
**Precedence:** The requirements document is the binding definition of what the
task workflow's interfaces currently do. This task does NOT add or change
any requirement text itself — its job is to investigate and produce a
recommendation. Any resulting behavior change MUST go through a
Requirements Drafter round and explicit user confirmation before
implementation, per CLAUDE.md's spec-driven development rule. Do not build
production code from this task file alone.

## Story (context, not binding)
As a maintainer relying on `task-file-format`'s rule that only Workflow
Guardian transitions a task's Status between `in-progress`/`done`, I want
to know whether the MCP server's `set_task_status` tool — which has no CLI
equivalent — is an intentional convenience for Guardian-driven MCP usage or
an unreviewed governance gap that lets any MCP client bypass the intended
gate, so the asymmetry can be resolved deliberately instead of left
unexamined.

## Description
**Finding (observed live, 2026-07-31, during a parity audit requested
after TASK-067):** `mcp/server.py`'s `set_task_status(task_id, status)`
tool calls `butler_core.tasks.set_status()` directly, letting any MCP
client set a task's Status field to any value with no gating. The `butler`
CLI (`src/butler_cli/__main__.py`) has no equivalent `task set-status`
subcommand — `butler_core.tasks.set_status()` exists in `butler_core` but
is only reachable today through the MCP tool, not through the CLI's
argparse surface at all.

Per `.claude/skills/task-file-format/SKILL.md`'s "Status transitions and
role boundaries" section: "The Workflow Guardian owns the `in-progress`
and `done` transitions and is the only role that edits Status and
Completion on an existing task." An ungated `set_task_status` MCP tool
appears to let any MCP-connected agent perform that transition directly,
bypassing whatever verification Workflow Guardian's own procedure (task
metadata gate, acceptance-criteria gate, etc.) would otherwise require
before flipping Status to `done`.

**What this task must produce:** a recommendation (not necessarily code)
choosing between:

1. **Add a matching CLI subcommand** (`butler task set-status <ID>
   <status>`), treating the MCP tool as intentional and just closing the
   CLI-side asymmetry — no governance change, purely an interface-parity
   fix.
2. **Remove or gate the MCP tool**, if the asymmetry is judged to be an
   unreviewed governance gap rather than an intentional convenience — e.g.
   requiring the caller to independently confirm the same checks Workflow
   Guardian's own procedure runs (acceptance criteria checked, tests
   passing, etc.) before allowing the transition, or removing the tool
   entirely and requiring Status transitions to go through
   `commit_task`/task-file edits instead.
3. **Leave it as-is**, if investigation concludes the current asymmetry is
   low-risk (e.g. because in practice only a Workflow-Guardian-following
   agent would call it, and the real gate is procedural/social rather than
   technical) — with an explicit rationale recorded, not silence.

Investigate: when/why `set_task_status` was added (`git log`/`git blame`
on `mcp/server.py`), whether any existing task file's Completion notes
document an intended use for it, and whether Workflow Guardian's own
documented procedure (`.claude/agents/workflow-guardian.agent.md`) ever
calls it out as its intended mechanism for status transitions when
operating over MCP. Then present the recommendation, its tradeoffs, and
(if applicable) a proposed requirement-text draft to the user for
confirmation, following the same pattern TASK-064 used for its own
investigation-then-recommendation task.

**Implementation location (for whichever follow-up is confirmed, not this
task):** `mcp/server.py` and/or `src/butler_cli/__main__.py`,
`.claude/agents/workflow-guardian.agent.md` if the gate needs explicit
documentation, `REQUIREMENTS_TASK_WORKFLOW.md` (new/amended requirement,
pending Requirements Drafter + user confirmation).

## Branch
**Branch name:** `task/070-investigate-set-task-status-asymmetry`
**Switch/create:** `git checkout -b task/070-investigate-set-task-status-asymmetry`
**Make target:** `make branch-task f=TASK-070`

## Acceptance criteria (Gherkin)

- [ ] Scenario: The origin and intended use of `set_task_status` is established
      Given `mcp/server.py`'s `set_task_status` tool
      When this task is worked
      Then its git history/commit message and any related task file's
      Completion notes are checked, and the intended use (if any) is
      recorded, rather than assumed

- [ ] Scenario: A recommendation is presented for user confirmation before any requirement text is written
      Given the three candidate directions described above
      When the findings are ready
      Then the user is presented with a clear recommendation and tradeoffs,
      and asked to confirm before a Requirements Drafter round drafts any
      new/changed requirement text

## Out of scope
- Actually implementing any of the three candidate directions — this task
  produces a recommendation and, if the user confirms, hands off to a
  Requirements Drafter round and a normal implementation task.
- The separate MCP/Make sync-project parity gaps — tracked as TASK-068 and
  TASK-069.
- The separate `butler sync` relevance question — tracked as TASK-071.

## Blockers
None

## Completion
**Date:**
**Summary:**
**Files changed:**
**Branch:** `git checkout task/070-investigate-set-task-status-asymmetry`
**Stage:** `git add docs/tasks/TASK-070-investigate-set-task-status-asymmetry.md`
**Commit:** `git commit -m "Investigate the set_task_status MCP/CLI asymmetry"`
