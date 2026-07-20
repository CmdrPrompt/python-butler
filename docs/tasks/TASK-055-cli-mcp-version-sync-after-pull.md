# TASK-055 Keep installed `butler` CLI/MCP server in sync after a pull

## Status
blocked

## Requirements
**Binding:** TBD — no requirement drafted yet; see Blockers
**BDD mode:** BDD-ABSENT
**Depends on:** TASK-054 (this task's approach assumes `.butler` is a git
submodule with sources that persist after a pull; if TASK-054 is not
confirmed/implemented, this task must be re-scoped for the subtree world
instead)
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a consumer project maintainer who has installed the `butler` CLI/MCP
server into my project's venv, I want it to stay in sync with whatever
`.butler` version `butler-pull` just fetched, so that I never run a stale
CLI against a newer set of butler sources without realizing it.

## Description
This is TASK-039's second, independent problem (its Background item "2.
Stale CLI after pull"), split out on its own because TASK-054 changes the
shape of the best fix for it:

TASK-039 (subtree world) proposed reinstalling the CLI non-editable from
freshly pulled sources inside `butler-pull`, specifically ruling out an
editable install (its R9) because `butler-trim` would delete `.butler`'s
sources right after, leaving an editable install pointing at files that no
longer exist.

If TASK-054 (switch `.butler` to a git submodule and retire `butler-trim`)
is confirmed and implemented, that constraint disappears: `.butler`'s
sources remain on disk permanently, at whatever commit the submodule
pointer currently records. That makes an **editable install**
(`pip install -e .butler/`) a live option — the installed CLI/MCP server
would automatically reflect whatever the submodule pointer currently points
to, with no reinstall step required after `butler-pull` at all, closing the
version-drift gap structurally rather than by remembering to run a command.

This task is to evaluate and, if confirmed, implement whichever fix is
appropriate once TASK-054's outcome is known: an automatic editable-install
switch, a `butler-pull`-triggered reinstall (as TASK-039 originally proposed,
adapted to a submodule where sources persist), or something else.

## Branch
**Branch name:** `task/055-cli-mcp-version-sync-after-pull`
**Switch/create:** `git checkout -b task/055-cli-mcp-version-sync-after-pull`
**Make target:** `make branch-task f=TASK-055`

## Acceptance criteria (Gherkin)
- [ ] TBD — to be written once the requirement is drafted and confirmed, and
      once TASK-054's outcome (submodule vs. subtree, trim retired vs. not)
      is known.

## Out of scope
- TASK-054's own scope (the distribution-mechanism switch itself).
- TBD — to be confirmed alongside the requirement.

## Blockers
- [ ] No requirement exists yet for this change. This task must not be
      implemented, and its Acceptance criteria/Out of scope sections must
      not be filled in, until a requirement is written and confirmed — only
      the user can waive this.
- [ ] Depends on TASK-054's resolution: the correct fix here (editable
      install vs. pull-triggered reinstall) is different depending on
      whether TASK-054 ships. Do not draft the requirement until TASK-054's
      Status leaves `blocked`.

## Completion
**Date:** TBD
**Summary:** TBD
**Files changed:** TBD
**Branch:** `git checkout task/055-cli-mcp-version-sync-after-pull`
**Stage:** TBD
**Commit:** TBD
