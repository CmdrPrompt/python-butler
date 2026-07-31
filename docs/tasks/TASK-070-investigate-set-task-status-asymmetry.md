# TASK-070 Investigate the `set_task_status` MCP/CLI asymmetry

## Status
done

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

**Investigation findings (2026-08-01):**

- **Origin:** `set_task_status` was not added separately or later — it
  shipped with the very first MCP server implementation (TASK-025,
  commit `d682e2b`, 2026-07-08), as one of the 10 tools REQUIREMENTS_MCP.md
  Requirement 7 explicitly lists (`set_task_status(task_id, status)`).
  TASK-025's own Completion notes give no rationale beyond "implement all
  10 required tools" — no gating or governance discussion.
- **The asymmetry is baked into the requirements document itself, not code
  drift:** REQUIREMENTS_MCP.md's Requirement 4 defines `check_criterion`
  and `set_status` together as one pair of `butler_core` functions.
  Requirement 6 (CLI)'s example command list includes `task check` (the
  first of the pair) but omits a `task set-status` equivalent; Requirement
  7 (MCP)'s tool list includes both `check_acceptance_criterion` and
  `set_task_status`. This looks like an oversight in Requirement 6's
  example rather than an intentional decision — nothing in the spec
  explains why the CLI would deliberately exclude just one half of
  Requirement 4's pair.
- **Workflow Guardian's own docs never reference the tool:** neither
  `.claude/agents/workflow-guardian.agent.md` nor
  `templates/workflow-guardian.agent.md.tmpl` mentions `set_task_status`
  (or `set-status`) anywhere. Guardian's documented procedure — "At task
  start, set task Status to `in-progress`... At completion, set Status to
  `done`" — predates the MCP server (present in the template since the
  initial commit, 2026-04-16) and was written assuming direct file edits,
  not a dedicated command on any interface.
- **The `make`/CLI path has no Status-transition command either — it's a
  hand-edit today:** confirmed against this repo's own recent history
  (TASK-069's Status flip to `done` was a hand-edit to the task file,
  included in the same commit as the implementation, committed via `make
  commit-current-task` like any other file change — not a dedicated
  command). So the real comparison isn't "MCP has an ungated shortcut the
  CLI lacks" — it's "MCP has a *structured tool* for an edit that, on
  every interface including MCP, has always been technically ungated
  (nothing anywhere verifies acceptance criteria or tests before a Status
  edit is written and committed)." The gate has always been procedural
  (Workflow Guardian's own diligence before it writes/commits that line),
  not technical, on any of the three interfaces.
- **Requirement 10 (TASK-067)'s interchangeability claim doesn't strictly
  cover this:** its text lists "branch/stage/commit/pr/merge, task-file
  sync" as the operations guaranteed across all three interfaces — a
  Status transition isn't literally named. So this asymmetry isn't a
  violation of Requirement 10's letter, even though it is in tension with
  its spirit (the three interfaces being otherwise-equivalent).

**Recommendation: Option 1 (add CLI parity), not Option 2 or 3.** Reasoning:
removing/gating the MCP tool (Option 2) wouldn't add any real safety, since
the same ungated edit is already possible today via a plain file edit on
the make/CLI path — there is nothing to "close" there that isn't already
open elsewhere. Leaving it as-is (Option 3) would let a known spec
inconsistency (Requirement 6 vs. Requirement 4/7) stand unremarked. Adding
a `butler task set-status <ID> <status>` CLI subcommand — a thin wrapper
over the already-existing, already-tested `butler_core.tasks.set_status`,
mirroring `task check`'s existing pattern — closes the parity gap the same
way TASK-068 closed the GitHub-Projects-sync one, and incidentally also
gives `make` a symmetric target opportunity. This needs a small
Requirements Drafter round to add `task set-status` to REQUIREMENTS_MCP.md
Requirement 6's example list before implementation, per CLAUDE.md's
spec-driven rule — not done in this investigation task.

## Branch
**Branch name:** `task/070-investigate-set-task-status-asymmetry`
**Switch/create:** `git checkout -b task/070-investigate-set-task-status-asymmetry`
**Make target:** `make branch-task f=TASK-070`

## Acceptance criteria (Gherkin)

- [x] Scenario: The origin and intended use of `set_task_status` is established
      Given `mcp/server.py`'s `set_task_status` tool
      When this task is worked
      Then its git history/commit message and any related task file's
      Completion notes are checked, and the intended use (if any) is
      recorded, rather than assumed

- [x] Scenario: A recommendation is presented for user confirmation before any requirement text is written
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
**Date:** 2026-08-01
**Summary:** Investigated `set_task_status`'s origin (shipped with the
original MCP server, TASK-025, per REQUIREMENTS_MCP.md Requirement 7's
tool list) and found the CLI-side gap traces back to Requirement 6's
example command list omitting `task set-status` while Requirement 4 defines
`check_criterion`/`set_status` as a pair and Requirement 7 (MCP) includes
both — a spec inconsistency, not a deliberate governance decision.
Confirmed Workflow Guardian's own docs never reference the tool, and that
the `make`/CLI path has no Status-transition command either (it's always
been a hand-edit to the task file, committed normally) — so the technical
gate on Status transitions is equally absent on every interface today;
only Guardian's own procedural diligence gates it anywhere. Presented three
options to the user; **confirmed: add CLI parity** (`butler task set-status
<ID> <status>`, thin wrapper over the existing `butler_core.tasks.set_status`).
Per CLAUDE.md's spec-driven rule, implementation is a separate follow-up
task, gated on a Requirements Drafter round adding `task set-status` to
REQUIREMENTS_MCP.md Requirement 6's example list first.
**Files changed:**
- `docs/tasks/TASK-070-investigate-set-task-status-asymmetry.md` - findings, recommendation, completion
**Branch:** `git checkout task/070-investigate-set-task-status-asymmetry`
**Stage:** `git add docs/tasks/TASK-070-investigate-set-task-status-asymmetry.md`
**Commit:** `git commit -m "Investigate the set_task_status MCP/CLI asymmetry"`
