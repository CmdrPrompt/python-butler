# TASK-095 Correct the unverified Bash-pipe rationale in the agent definitions

## Status
done

## Requirements
**Binding:** Requirement 2 (REQUIREMENTS_AGENT_SKILLS.md)
**BDD mode:** BDD-PLANNED
**Depends on:** TASK-094
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a maintainer, I want the agent definitions to justify their rules with
claims that have actually been observed, so that a rule nobody can verify does
not silently constrain every future decision built on top of it.

## Description
The Implementation Worker's Tool usage section states that piping command
output through `| tail`/`| head`/`| grep` may fall outside the pre-approved
Bash allowlist and "silently stall your turn with no result". The rule was
added 2026-07-09 in commit `9832126` ("Enhance agent documentation with tool
usage guidelines"), with no recorded incident behind it.

Measured 2026-08-03: a general-purpose subagent was instructed to run exactly
`make test | tail -5` in a single Bash call, with explicit instructions not to
substitute, retry unpiped, or use a quiet flag instead. The command ran. No
permission prompt, no stall, no error. It returned the expected five lines:

```text
src/butler_core/tasks.py         143      2    99%   92, 243
src/butler_core/uninstall.py      76      0   100%
------------------------------------------------------------
TOTAL                            815      9    99%
================= 385 passed, 9 xfailed, 2 warnings in 29.05s ==================
```

The stated mechanism therefore does not hold under the current configuration.
The likely origin is a misattribution: the symptom the rule describes (a
subagent turn ending with no usable result) matches the "narrated tool calls"
failure mode that `.claude/hooks/subagent_toolcheck.py` was built for
(TASK-025/TASK-034/TASK-038), which is a model-behavior problem, not a
permission problem.

This does not invalidate TASK-094. The quiet targets remain the right tool:
they work regardless of permission configuration, they need no allowlist
entries, they behave identically in CI, and they help humans too. Only the
*justification* is wrong, and it has since been copied into a requirement and
pinned by a test.

The unverified claim currently appears in:

- `claude-agents/implementation-worker.agent.md` (and its `.claude/agents/`
  mirror) — the pipe prohibition itself, plus the same "silently stall" claim
  on the Read/Grep/Glob bullet
- `claude-agents/test-writer.agent.md` (and mirror) — the "silently stall"
  claim on its Read/Grep/Glob bullet
- `REQUIREMENTS_AGENT_SKILLS.md` Requirement 2, first sentence
- `tests/test_quiet_check_targets.py` — asserts the literal `| tail`,
  `| head` and `| grep` tokens are still present in the agent file

What survives, on its own merits and with a rationale that is actually true:

- Preferring `Read`/`Grep`/`Glob` over Bash `cat`/`find`/`ls`, because
  dedicated read tools return bounded, structured results and do not depend on
  shell quoting or allowlist shape.
- Preferring the quiet Makefile targets over ad-hoc pipes, because the target
  is the single source of truth for what a check prints, so agent, human and
  CI runs stay consistent.
- Reporting the exact command when a Bash call is blocked or interrupted
  (Implementation Worker, Test Writer, PR Reviewer). Cheap, and the only thing
  that makes a future permission failure diagnosable at all. Keep verbatim.

The pipe rule becomes a preference rather than a prohibition. An agent that
pipes is not doing something forbidden, it is just doing something the quiet
targets already do better.

## Branch
**Branch name:** `task/095-correct-unverified-bash-pipe-rationale`
**Switch/create:** `git checkout -b task/095-correct-unverified-bash-pipe-rationale`
**Make target:** `make branch-task f=TASK-095`

## Acceptance criteria (Gherkin)
**Feature files:** None

- [x] 1. Scenario: The requirement no longer justifies itself with the stall claim
      Given `REQUIREMENTS_AGENT_SKILLS.md` Requirement 2
      When its Description is read
      Then it contains no claim that a piped command stalls a subagent's turn
      And it contains no claim that piping puts a command outside the allowlist
      And its obligations on the quiet targets are otherwise unchanged
- [x] 2. Scenario: The pipe rule is a preference, not a prohibition
      Given `claude-agents/implementation-worker.agent.md`
      When its Tool usage section is read
      Then it directs the agent to prefer the quiet Makefile targets over ad-hoc pipes
      And it gives single-source-of-truth consistency as the reason
      And it does not forbid piping
- [x] 3. Scenario: The false rationale is gone from every agent that carried it
      Given `claude-agents/implementation-worker.agent.md` and `claude-agents/test-writer.agent.md`
      When each is read
      Then neither claims a Bash call outside the allowlist will silently stall the turn
      And each still directs the agent to use `Read`/`Grep`/`Glob` over Bash `cat`/`find`/`ls`
- [x] 4. Scenario: The blocked-command reporting rule is untouched
      Given the Implementation Worker, Test Writer and PR Reviewer definitions
      When each Tool usage section is read
      Then each still instructs the agent to state the exact blocked command
      instead of ending its turn silently
- [x] 5. Scenario: The test pins the new rule rather than the old tokens
      Given `tests/test_quiet_check_targets.py`
      When its Implementation Worker assertions run
      Then they no longer require the literal `| tail`, `| head` and `| grep` tokens
      And they assert that the quiet targets are named as the preferred path
      And `make verify` and `make test-quiet` are still asserted as before
- [x] 6. Scenario: The mirrors and validators stay green
      Given the edited agent definitions
      When `make verify` runs
      Then it exits 0
      And `make check-agents-sync` reports no drift between `claude-agents/` and `.claude/agents/`
      And `scripts/validate_agents.py` reports all agent definitions valid
- [x] 7. Scenario: The measurement is recorded where the claim used to live
      Given `REQUIREMENTS_AGENT_SKILLS.md`
      When Requirement 2 is read
      Then it records that the pipe prohibition's stated mechanism was tested on
      2026-08-03 and not reproduced, so that this is not rediscovered from scratch

## Out of scope
- Rewriting `docs/tasks/TASK-094-quiet-check-targets-for-agent-context.md`.
  It is a completed task file and a historical record of what was believed at
  the time; correcting it retroactively would erase the very trail that made
  this task findable.
- Removing or weakening the quiet targets, `make verify`, or any of TASK-094's
  Makefile work. Only the justification changes, not the mechanism.
- The `.claude/hooks/subagent_toolcheck.py` narration gate and the
  TASK-025/034/038 failure mode it detects. Naming it as the likely true origin
  is not a claim that it needs changing.
- Adding `head`/`tail`/`grep` to `.claude/settings.local.json`. The quiet
  targets make the allowlist question moot; broadening permissions to enable a
  path we no longer recommend is the wrong direction.
- Auditing every other unverified rationale across the ten agent definitions.
  Worth doing, but as its own task with its own evidence.

## Blockers
None

## Completion
**Date:** 2026-08-03
**Summary:** Reworded the pipe-prohibition rule in the Implementation Worker
and Test Writer agent definitions, and in `REQUIREMENTS_AGENT_SKILLS.md`
Requirement 2, from a forbidden-because-it-stalls rule to a
preferred-because-of-consistency one, and recorded the 2026-08-03
measurement that the stall/allowlist mechanism did not reproduce. Updated
`tests/test_quiet_check_targets.py` to pin the new preference wording
instead of the literal `| tail`/`| head`/`| grep` tokens. Blocked-command
reporting and the Read/Grep/Glob-over-Bash rule are untouched. `make
verify`, `make check-agents-sync` and `scripts/validate_agents.py` all pass.
**Files changed:**
- `REQUIREMENTS_AGENT_SKILLS.md` - modified
- `claude-agents/implementation-worker.agent.md` - modified
- `.claude/agents/implementation-worker.agent.md` - modified
- `claude-agents/test-writer.agent.md` - modified
- `.claude/agents/test-writer.agent.md` - modified
- `tests/test_quiet_check_targets.py` - modified
- `CHANGELOG.md` - modified
- `docs/tasks/TASK-095-correct-unverified-bash-pipe-rationale.md` - modified
**Branch:** `git checkout task/095-correct-unverified-bash-pipe-rationale`
**Stage:** `claude-agents/implementation-worker.agent.md .claude/agents/implementation-worker.agent.md claude-agents/test-writer.agent.md .claude/agents/test-writer.agent.md REQUIREMENTS_AGENT_SKILLS.md tests/test_quiet_check_targets.py CHANGELOG.md docs/tasks/TASK-095-correct-unverified-bash-pipe-rationale.md`
**Commit:** `git commit -m "Correct the unverified Bash-pipe rationale in the agent definitions (TASK-095)"`
