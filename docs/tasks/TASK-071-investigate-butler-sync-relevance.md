# TASK-071 Investigate whether `butler sync` (Requirement 3) is still relevant post-submodule migration

## Status
todo

## Requirements
**Binding:** Requirement 3 (REQUIREMENTS_TASK_WORKFLOW.md); related to REQUIREMENTS_SUBMODULE.md Requirements 1-2
**BDD mode:** BDD-ABSENT (investigation task — no requirement text confirmed yet, see below)
**Depends on:** None
**Precedence:** The requirements document is the binding definition of what
`butler sync` currently does and why. This task does NOT add or change any
requirement text itself — its job is to investigate and produce a
recommendation. Any resulting behavior change (deprecation, doc update, or
keeping it as-is) MUST go through a Requirements Drafter round and explicit
user confirmation before implementation, per CLAUDE.md's spec-driven
development rule. Do not build production code from this task file alone.

## Story (context, not binding)
As a maintainer relying on the generated `CLAUDE.md`'s new claim (TASK-067,
Requirement 10) that `make`, the `butler` CLI, and `butler-mcp` are
interchangeable interfaces to "the underlying operations," I want to know
whether `butler sync` (Requirement 3: refreshes a consumer project's
vendored `.butler/Makefile` to match the installed CLI, for `git
subtree`-based installs) is still a real, needed operation that `make`/MCP
should also expose, or whether it was superseded by the `git submodule`
based distribution model and should be documented as legacy/deprecated
instead — so effort isn't spent building parity for a dead code path.

## Description
**Finding (observed live, 2026-07-31, during a parity audit requested
after TASK-067):** `butler sync --dry-run|--force` (CLI-only,
`src/butler_core/sync.py`'s `sync_makefile`) exists per
REQUIREMENTS_TASK_WORKFLOW.md's Requirement 3, written for a `git subtree
add --prefix=.butler` distribution model — it compares a consumer
project's vendored `.butler/Makefile` content against the version bundled
in the installed `butler` package and overwrites it if they differ,
addressing the `firefly-python-api` stale-snapshot incident (TASK-043).

REQUIREMENTS_SUBMODULE.md's Requirements 1-2 (referenced by this repo's
own recent history, e.g. TASK-054 "Switch `.butler` distribution from git
subtree to git submodule") describe a different, apparently *later*
distribution mechanism: `git submodule add`, with `butler-fetch`/
`butler-pull`/`butler-check` (all present in this repo's own `Makefile`,
lines ~364-390) as "pointer-move operations" — moving `.butler`'s
submodule commit pointer forward, not diffing/overwriting file content the
way `butler sync` does.

Neither `make` nor `mcp/server.py` expose `butler sync` today. Before
filing that as a parity gap to close (the way TASK-068/TASK-069 do for the
GitHub-Projects-sync gaps), it needs to be established whether `butler
sync` is:

1. **Still relevant** for consumer projects that adopted via the older
   subtree mechanism and haven't migrated (REQUIREMENTS_SUBMODULE.md
   Requirement 4, "Migration path for existing subtree consumers," implies
   such projects may still exist) — in which case it's a real gap and
   TASK-068/069-style follow-ups (add `make`/MCP wrappers) are warranted.
2. **Superseded/legacy** for submodule-based installs (the now-default
   mechanism), in which case the right fix is documentation (mark
   Requirement 3 as legacy/subtree-only in REQUIREMENTS_TASK_WORKFLOW.md,
   note it in `butler sync --help`/its docstring) rather than building
   `make`/MCP parity for a path new projects don't use.

Investigate: read REQUIREMENTS_SUBMODULE.md in full (especially
Requirement 4's migration path and whether it references `butler sync` at
all), check whether `sync_makefile`'s implementation or tests assume a
subtree layout that a submodule install wouldn't have, and check whether
any consumer-facing docs (README.md) already describe `butler sync` as
subtree-specific or submodule-compatible. Then present the recommendation
and tradeoffs to the user for confirmation, following the same
investigate-then-recommend pattern TASK-064 used.

**Implementation location (for whichever follow-up is confirmed, not this
task):** `REQUIREMENTS_TASK_WORKFLOW.md` (Requirement 3, possibly marked
legacy or amended), `src/butler_core/sync.py`/`src/butler_cli/__main__.py`
docstrings, `README.md`, or (if still relevant) `Makefile`/`mcp/server.py`
parity additions mirroring TASK-068/TASK-069.

## Branch
**Branch name:** `task/071-investigate-butler-sync-relevance`
**Switch/create:** `git checkout -b task/071-investigate-butler-sync-relevance`
**Make target:** `make branch-task f=TASK-071`

## Acceptance criteria (Gherkin)

- [ ] Scenario: `butler sync`'s relevance under the submodule distribution model is established
      Given REQUIREMENTS_SUBMODULE.md's Requirements 1-2 (submodule
      adoption) and Requirement 4 (migration path for existing subtree
      consumers)
      When this task is worked
      Then it is determined and recorded whether `butler sync` still
      serves live (subtree-based) consumer projects, or is superseded by
      `butler-fetch`/`butler-pull`/`butler-check` for submodule-based ones

- [ ] Scenario: A recommendation is presented for user confirmation before any requirement text is written
      Given the two candidate directions described above (still-relevant
      vs. legacy/superseded)
      When the findings are ready
      Then the user is presented with a clear recommendation and
      tradeoffs, and asked to confirm before a Requirements Drafter round
      drafts any new/changed requirement text

## Out of scope
- Actually implementing either direction (adding `make`/MCP parity, or
  marking Requirement 3 legacy) — this task produces a recommendation and,
  if the user confirms, hands off to a Requirements Drafter round and a
  normal implementation/documentation task.
- The separate GitHub-Projects-sync parity gaps (TASK-068, TASK-069) and
  the `set_task_status` asymmetry (TASK-070).

## Blockers
None

## Completion
**Date:**
**Summary:**
**Files changed:**
**Branch:** `git checkout task/071-investigate-butler-sync-relevance`
**Stage:** `git add docs/tasks/TASK-071-investigate-butler-sync-relevance.md`
**Commit:** `git commit -m "Investigate whether butler sync is still relevant post-submodule migration"`
