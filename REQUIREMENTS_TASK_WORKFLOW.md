# Requirements: Task Workflow (`butler task` <-> vendored Makefile)

## Context

python-butler ships two entry points for the task-branch workflow that
CLAUDE.md mandates: the `butler` CLI (`butler task branch|stage|commit|pr|merge`,
backed by `src/butler_core/git_ops.py`) and a set of `make` targets
(`branch-task`, `stage-task`, `commit-task`, `pr-task`, `merge-pr`, and their
`*-current-task` wrappers) defined in this repo's root `Makefile`, which is
vendored unchanged into adopting projects as `.butler/Makefile` via
`git subtree add --prefix=.butler`.

TASK-043 documents a real-world incident in a consumer project
(`firefly-python-api`): running `make branch-task` recursed infinitely, and
a `--tasks-dir` flag the vendored Makefile passed was rejected by the
installed CLI. Investigation traced this to a **stale vendored
`.butler/Makefile` snapshot** in that consumer project, predating the
TASK-022/023 refactor that introduced `src/butler_core/git_ops.py` as the
single, correct implementation of branch/stage/commit/pr/merge logic. This
repo's *current* source was never broken: `git_ops.py` was built from day
one (TASK-023, 2026-07-08) to hold the real implementation, the current root
`Makefile` already calls `butler --tasks-dir $(TASKS_DIR) task <cmd> $(f)`
exactly once with no callback, and the CLI already accepts `--tasks-dir`.
There is no history of a `butler/commands/task.py`-style proxy-to-Makefile
implementation anywhere in this repo.

The real, unresolved problem is that once a consumer project vendors
`.butler/Makefile` via `git subtree add`, nothing keeps that copy in sync
with this repo going forward. A consumer can end up pinned to an old,
structurally-different snapshot indefinitely, with no supported way to
detect or correct the drift short of manually diffing and patching files —
exactly what happened to `firefly-python-api`. This document formalizes the
architecture that already exists here (so it cannot silently regress) and
defines the missing piece: a way for consumer projects to refresh their
vendored Makefile.

## Goals

1. Formalize, via regression tests, that `butler task <cmd>` (backed by
   `butler_core.git_ops`) remains the single source of truth for branch
   create/switch, stage, commit, PR open, and PR merge logic, and that
   `.butler/Makefile` task targets remain thin, non-recursive wrappers.
2. Guard against future flag drift (e.g. `--tasks-dir`) between the vendored
   Makefile and the installed CLI's argument parser.
3. Give consumer projects a command to refresh their vendored
   `.butler/Makefile` to match the currently installed CLI/package version,
   so a project can never again get permanently stuck on a stale, buggy
   snapshot the way `firefly-python-api` did.

## Non-goals

- Fixing this repo's own `butler_core`/`butler_cli`/`Makefile` source code —
  it already implements the correct non-recursive architecture and already
  accepts `--tasks-dir`. No bug fix is needed here; only regression-proofing
  and a distribution-refresh mechanism.
- Fixing already-vendored `.butler/Makefile` copies in existing consumer
  repos (e.g. `firefly-python-api`) directly from this repo — out of scope
  per TASK-043; those projects pick up the fix by running the new refresh
  command (Requirement 3) themselves once it ships.
- Changing the subtree-based adoption mechanism itself (`git subtree add`) —
  only refreshing the Makefile file within an already-adopted project is in
  scope.
- Reading task status, or any other data, back from GitHub Projects into the
  CLI, `git_ops.py`, the Makefile, or any agent's task-file read/write
  behavior. The sync is strictly one-way (task file → Projects item) — see
  Requirement 4.
- Making GitHub Projects a source of truth for task state, or changing how
  Workflow Guardian, Task Drafter, Implementation Worker, or any other agent
  reads or writes `docs/tasks/TASK-XXX-*.md` files.

## Requirement 1: Regression test protecting the non-recursive architecture

**Description:** An automated test MUST exist that fails if the
non-recursive architecture ever regresses: `butler_core.git_ops`'s
branch/stage/commit/pr/merge functions (`branch_for`, `stage_for`,
`commit_for`, `open_pr_for`, `merge_pr_for`) MUST NOT construct a
`subprocess` call whose first argument is `"make"`, and an end-to-end test
running `butler task branch` (and the other four subcommands) in a fixture
project MUST assert the process completes without spawning a nested
`butler` or `make` process. This formalizes and protects behavior that
already exists in this repo's source as of TASK-023 — it is not new
implementation, only new test coverage.

**Use case:**

```python
def test_git_ops_never_shells_out_to_make():
    """Regression test for TASK-043: butler_core.git_ops must never proxy
    back to `make` for branch/stage/commit/pr/merge operations, and the
    vendored Makefile must never be able to recurse into itself through
    the CLI."""
    ...
```

## Requirement 2: Guard against `--tasks-dir` (and future flag) drift

**Description:** A dedicated automated test MUST parse the `butler ...`
invocations in the root `Makefile` and cross-check every flag they pass
(currently `--tasks-dir`) against the CLI's argparse definition
(`src/butler_cli/__main__.py`), failing if any flag the Makefile passes is
not accepted by the installed CLI. This test MUST run as part of
`make test`. This already holds today — the requirement is to keep it
enforced automatically going forward, so a future change to the CLI's
task-directory configuration mechanism (e.g. a move to a config file) cannot
ship without a matching update to the vendored Makefile's `butler`
invocations in the same commit/PR, or without a documented deprecation
window if the old flag is kept for compatibility.

**Use case:**

```bash
make test
# includes a dedicated test that parses every `butler ...` invocation in
# the root Makefile, extracts the flags passed, and asserts each flag is
# accepted by src/butler_cli/__main__.py's argparse definition; fails the
# build if a flag is dropped from one side without the other being
# updated in the same change.
```

## Requirement 3: `butler` command to refresh a consumer project's vendored Makefile

**Description:** A CLI command, `butler sync`, MUST be able to overwrite a
consumer project's `.butler/Makefile` with the version bundled in the
currently installed `butler` package, so that a consumer project can correct
drift between its vendored Makefile and the installed CLI (such as the
stale snapshot `firefly-python-api` was pinned to) without manually diffing
and patching files by hand. `butler sync --dry-run` MUST compare the actual
content (e.g. hash or diff) of the local `.butler/Makefile` against the
bundled version and report a needed change only if they actually differ —
it MUST NOT unconditionally report "would overwrite" regardless of content.
The command MUST refuse to run on a dirty working tree unless `--force` is
passed (consistent with `REQUIREMENTS_UNINSTALL.md` Requirement 3), and MUST
support `--dry-run`.

**Use case:**

```bash
butler sync --dry-run
# Compares the content (hash/diff) of the local .butler/Makefile against
# the version bundled in the installed butler package.
# If they differ:
#   would overwrite .butler/Makefile (local hash abc123 != bundled hash def456)
# If they are identical:
#   .butler/Makefile is already up to date; nothing to do

butler sync
# overwrites .butler/Makefile with the version bundled in the installed
# butler package, only if its content differs from the bundled version;
# leaves other vendored files (governance docs, agents) untouched
```

## Requirement 4: Best-effort one-way sync of task metadata to a linked GitHub Projects item

**Description:** The task workflow MUST support an optional, additive
one-way mirror of task metadata (TASK-ID, title, status) from the task file
in `docs/tasks/TASK-XXX-*.md` to a GitHub Projects (v2) item linked to the
task's PR. `docs/tasks/TASK-XXX-*.md` remains the sole source of truth;
nothing from GitHub Projects is ever read back into the CLI, `git_ops.py`,
the Makefile, or any agent's (Workflow Guardian, Task Drafter,
Implementation Worker, etc.) read/write behavior against task files, which
MUST NOT change as part of this requirement.

The sync MUST be implemented as a single, separate, encapsulated entry
point (e.g. a `butler task sync-project` command or an equivalent standalone
script invoked via a dedicated `make` target such as `sync-project-item`) —
not inlined into `git_ops.py`'s branch/stage/commit/pr/merge functions —
so that a future, heavier integration (e.g. Projects as source of truth)
can replace or extend this entry point without requiring changes to the
existing branch/stage/commit/pr/merge call sites.

The sync MUST be invoked as an added step in the existing flow:

- `make pr-current-task` (and `make pr-task`) MUST, after the PR is opened,
  attempt to create or link a GitHub Projects item for that PR and set its
  TASK-ID/title fields from the task file. "Link" means the sync MUST FIRST
  look up whether a Project item already exists for the task (matching on
  the task's TASK-ID title prefix, the same lookup already used to update
  status) and reuse that item; a new item MUST be created only when no
  existing item matches. This applies across every sync stage
  (`draft`/`open`/`merge`/`backfill`) so that running more than one stage
  for the same task never produces more than one Project item.
- `make merge-current-task` (and `make merge-pr`) MUST, after the PR is
  merged, attempt to update the linked Projects item's status field to
  reflect completion.

The sync MUST use the `gh` CLI (e.g. `gh project item-add`) or the GitHub
GraphQL API.

The sync MUST be best-effort: if no GitHub Project is configured for the
repository, if `gh` lacks the required permissions, if `gh` is not
installed/authenticated, or if the sync otherwise fails for any reason, the
failure MUST be reported as a warning (non-zero exit from the sync step MUST
NOT propagate as a failure of `pr-task`/`pr-current-task`/`merge-pr`/
`merge-current-task`) and MUST NOT block PR creation or merge. PR creation
and merge MUST succeed identically whether or not the Projects sync
succeeds.

When the warning is specifically "no GitHub Project is configured"
(the `BUTLER_GITHUB_PROJECT` environment variable is unset), the warning
MUST additionally suggest, in the same message or an immediately following
line, the concrete commands needed to create a Project and configure the
variable, with the owner and repository name filled in from the current
repository rather than left as a placeholder. The owner/repository name
MUST be derived at runtime (e.g. via `gh repo view --json owner,name` or by
parsing the `origin` remote URL) so the suggestion is directly copy-pasteable
for whichever repository the sync runs in. If the owner/repository name
cannot be determined (e.g. `gh` is not installed/authenticated, or there is
no `origin` remote), the sync MUST fall back to the existing generic warning
without a concrete example rather than failing or raising.

**Use case:**

```bash
make pr-current-task
# ... existing behavior: branch pushed, PR opened using task file metadata ...
# additionally attempts to sync task metadata to a linked GitHub Projects
# item:
#   Synced TASK-012 "Add dark mode toggle" to GitHub Project item (status: In Progress)
# if no Project is configured, and owner/repo can be determined (e.g. this
# repo, CmdrPrompt/python-butler):
#   Warning: could not sync TASK-012 to GitHub Projects (no project configured for this repo) - continuing
#   To configure one:
#     gh project create --owner CmdrPrompt --title "python-butler"
#     export BUTLER_GITHUB_PROJECT=<number from the command above>
# if owner/repo cannot be determined (e.g. gh not authenticated):
#   Warning: could not sync TASK-012 to GitHub Projects (no project configured for this repo) - continuing
# if gh lacks permission or another failure occurs:
#   Warning: could not sync TASK-012 to GitHub Projects (no project configured for this repo) - continuing
# PR creation succeeds either way; make pr-current-task exits 0

make merge-current-task
# ... existing behavior: PR squash-merged, main pulled ...
# additionally attempts to update the linked Projects item's status:
#   Updated GitHub Project item for TASK-012 to status: Done
# if the sync fails for any reason:
#   Warning: could not update GitHub Project item for TASK-012 (gh: not authenticated) - continuing
# merge succeeds either way; make merge-current-task exits 0
```

## Requirement 5: Correct GitHub Projects v2 node-ID resolution for item creation and status updates

**Description:** `BUTLER_GITHUB_PROJECT` holds the human-facing project
*number* (e.g. `2`, as shown in the Project's URL and by `gh project list`).
The GitHub Projects v2 GraphQL API that `gh project item-edit` calls
requires the project's **node ID** (e.g. `PVT_kwHOAAnLPc4BfBkx`) for
`--project-id`, the target field's **node ID** (e.g.
`PVTSSF_lAHOAAnLPc4BfBkxzhZXgzs`) for `--field-id`, and the target
single-select option's **node ID** (e.g. `98236657`) for
`--single-select-option-id` — none of these accept the plain project number
or human-readable names ("Status", "Done"). `_sync()` in
`butler_core/projects.py` currently passes the raw project number straight
through as `--project-id` and hardcodes the literal strings `"Status"` and
`"Done"` for `--field-id`/`--single-select-option-id`, so the `--stage
merge` status update MUST fail against any real GitHub Projects v2 board
with a GraphQL "Could not resolve to a node" error — confirmed live against
the `CmdrPrompt/python-butler` Project on 2026-07-31 while completing
TASK-058. The `--stage open` item-create call is unaffected, since `gh
project item-create` already accepts the plain project number.

The sync MUST resolve the project's node ID (e.g. via `gh project view
<number> --owner <owner> --format json --jq .id`) and the "Status" field's
node ID plus its "Done" option's node ID (e.g. via `gh project field-list
<number> --owner <owner> --format json`, matching the field named `Status`
and the option named `Done`) at sync time, and use those resolved IDs for
`--project-id`, `--field-id`, and `--single-select-option-id` respectively.
If the "Status" field or "Done" option cannot be found on the configured
Project (e.g. the board doesn't have that column/option), the sync MUST
fail as an ordinary best-effort warning per Requirement 4 — it MUST NOT
raise or block PR merge.

**Use case:**

```bash
export BUTLER_GITHUB_PROJECT=2
make merge-current-task
# ... existing behavior: PR squash-merged, main pulled ...
# resolves project 2's node ID, the "Status" field's node ID, and the
# "Done" option's node ID via `gh project view`/`gh project field-list`,
# then updates the linked item's Status to Done using those resolved IDs:
#   Updated GitHub Project item for TASK-012 to status: Done
# if the configured Project has no "Status" field or no "Done" option:
#   Warning: could not update GitHub Project item for TASK-012 (no "Status"/"Done" field on this Project) - continuing
# merge succeeds either way; make merge-current-task exits 0
```

## Requirement 6: Repo-local Project configuration and a draft-stage sync triggered by Workflow Guardian

**Description:** `BUTLER_GITHUB_PROJECT` (Requirement 4) is read from the
*invoking process's* environment, which does not identify which local repo
a task file was written into. When an agent runs in one workspace but
writes a task file into a different local repo (e.g. Task Drafter spawned
against a target repo other than its own working directory), the project
number MUST be resolvable from the **target repo** itself, not from
whatever environment variable the invoking process happens to have set.

A repo-local config file, `.butler-project`, at the target repo's root MUST
hold the plain GitHub Project number (the same value `BUTLER_GITHUB_PROJECT`
holds today) as its entire contents. The sync's project-number resolution
MUST check `.butler-project` in the target repo first and fall back to the
`BUTLER_GITHUB_PROJECT` environment variable only if the file is absent —
this keeps Requirement 4's existing environment-variable-only behavior
working unchanged for repos that have not adopted the config file. The "no
project configured" warning's setup suggestion (Requirement 4) MUST be
extended to offer creating `.butler-project` as an alternative to `export
BUTLER_GITHUB_PROJECT=...`.

A new sync stage, `--stage draft`, MUST exist alongside the existing `open`
and `merge` stages, creating/linking a Project item the same way `--stage
open` does (item status left at the Project's default, e.g. "Todo"/"In
Progress" — no requirement here to force a specific default status).

Task Drafter (`.claude/agents/task-drafter.agent.md` /
`claude-agents/task-drafter.agent.md`) itself is NOT changed to gain Bash or
any GitHub-interaction capability — it stays a pure Read/Grep/Glob/Write
agent. Instead, the Workflow Guardian agent, which already has Bash and
already merges Task Drafter's worktree branch (per the `commit-workflow`
skill's worktree section), MUST run `butler task sync-project <id> --stage
draft` for every new or modified task file immediately after merging Task
Drafter's branch, resolving the target repo's `.butler-project` /
`BUTLER_GITHUB_PROJECT` as described above. This sync step follows the same
best-effort contract as Requirement 4: a failure MUST produce a warning and
MUST NOT block the merge of Task Drafter's branch or fail Workflow
Guardian's run.

A standalone `make sync-project-draft f=<TASK-ID>` target MUST also exist as
a thin wrapper around `butler --tasks-dir $(TASKS_DIR) task sync-project
$(f) --stage draft` (same `f=`-argument and `check-butler` convention as
`stage-task`/`commit-task`), so that Workflow Guardian's draft-stage step
above, and any maintainer running the workflow entirely through `make`, has
a `make` entry point for this stage — mirroring the wiring Requirement 9
already mandates for `--stage start`, except invoked standalone (via `f=`)
rather than as an automatic added step of an existing target, since
`--stage draft` runs before a task branch exists and has no existing `make`
target to attach to. Like every other sync invocation, this stays a direct,
single `butler` call in the target's recipe — it MUST NOT call back into
`make` itself, preserving Requirement 1's non-recursive architecture.

**Use case:**

```bash
# In target-repo/.butler-project:
2

# Task Drafter (running in a different workspace) writes
# target-repo/docs/tasks/TASK-012-add-dark-mode-toggle.md, commits it to
# its worktree branch, and hands off to Workflow Guardian.

# Workflow Guardian merges the worktree branch, then:
butler task sync-project TASK-012 --stage draft
# Resolves target-repo/.butler-project (falling back to
# $BUTLER_GITHUB_PROJECT if absent), creates/links a Project item for
# TASK-012, and reports:
#   Synced TASK-012 "Add dark mode toggle" to GitHub Project item (status: In Progress)
# On failure (no .butler-project/env var, gh not authenticated, etc.):
#   Warning: could not sync TASK-012 to GitHub Projects (no project configured for this repo) - continuing
#   To configure one:
#     gh project create --owner CmdrPrompt --title "python-butler"
#     echo <number from the command above> > .butler-project
#     (or) export BUTLER_GITHUB_PROJECT=<number from the command above>
# Workflow Guardian's merge of Task Drafter's branch succeeds either way.
```

## Requirement 7: Stay on the task branch after opening a PR

**Description:** `open_pr_for` (backing `butler task pr` / `make
pr-task`/`pr-current-task`) currently ends with `git checkout main`,
switching the working tree off the task branch immediately after the PR is
created. This was observed, three times in one session while completing
TASK-058/059/060, to cause two concrete problems: (1) the very next
Makefile line in `pr-task` (`butler task sync-project $(f) --stage open`)
runs against `main`, where the just-created task file does not yet exist
(it is only on the task branch, pending merge), so the draft/open-stage
Projects sync spuriously fails with "No task file found"; and (2) merging
the task immediately after opening its PR — the common case — requires a
manual `git checkout task/<NNN>-...` first, since `merge-pr`/
`merge-current-task` (and the `sync-project --stage merge` step that
follows a successful merge) both depend on being run from the task branch.

`open_pr_for` MUST NOT switch the working tree away from the task branch
after creating the PR; it leaves the caller on the task branch it was
invoked from. `merge_pr_for` is unaffected by this change — it already
determines the target branch from the task object (via `gh pr list --head
<branch>`), not from the currently checked-out branch, and already ends by
checking out and pulling `main` once the merge succeeds.

To avoid a new branch inadvertently forking off a leftover task branch
instead of `main` (now that `open_pr_for` no longer returns the caller to
`main`), `branch_for` MUST, when creating a **new** task branch (one that
does not already exist locally), first fetch and base the new branch on
`origin/main` rather than on whatever branch happens to be currently
checked out. `branch_for` switching to an **existing** task branch is
unaffected — that path already does not depend on the starting branch.

**Use case:**

```bash
make branch-task f=TASK-061
# ... implement, test, stage, commit ...
make pr-current-task
# opens the PR; the shell remains on task/061-... (no more manual
# `git checkout task/061-...` needed before merging)
make merge-current-task
# squash-merges immediately, no branch switch required first

# Starting a fresh task right after, without manually returning to main:
make branch-task f=TASK-062
# branch_for fetches and bases task/062-... on origin/main, not on
# whatever branch (e.g. an already-merged task/061-...) was left checked
# out -- so the new branch never accidentally carries task/061's commits
```

## Requirement 8: Backfill sync for historical tasks (`--stage backfill`)

**Description:** Tasks completed before Requirement 6's draft-stage sync
existed (e.g. TASK-001 through TASK-059) have no corresponding GitHub
Projects item, or one whose Status/date fields don't reflect the task's
actual history — `sync-project` has only ever run at present-day
open/draft/merge time, so a backfilled item would otherwise carry today's
date and whatever Status the default `gh project item-create` leaves it at,
not the task's real completion history.

A new sync stage, `--stage backfill`, MUST exist alongside `open`/`draft`/
`merge`. Given a single task ID, it MUST:

1. Create/link a Project item for the task (same as `--stage open`/`draft`).
2. Set the item's "Status" field to match the task file's own `## Status`
   value (e.g. `todo`, `in-progress`, `done`), generalizing the existing
   Done-only resolution (`_resolve_status_done_field_ids`) to resolve any
   status option by name (case-insensitively, `-` treated as a space, e.g.
   `in-progress` matches an option named "In Progress") instead of
   hardcoding "Done".
3. If the configured Project has a "Created" date field, set it to the git
   commit date the task file was first added (earliest commit touching the
   file, `git log --diff-filter=A --follow`).
4. If the configured Project has a "Closed" date field and the task's
   status is `done`, set it to the task file's own Completion date (`##
   Completion` / `**Date:**`) when present and parseable as a date;
   otherwise fall back to the git commit date of the task file's most
   recent commit. If the status is not `done`, the "Closed" field MUST be
   left unset.

A missing "Created" or "Closed" field on the configured Project MUST NOT
fail the sync — each is set independently and silently skipped if the
field doesn't exist, since backfill date-enrichment is opportunistic, not
required. A missing "Status" field/option, and complete Project-resolution
failure, continue to follow Requirement 4's best-effort warning contract
(warn, never raise, never block).

Backfill is invoked per task ID, the same way `open`/`draft`/`merge` are —
looping over every file in `docs/tasks/` to backfill a whole repo's history
in one command is out of scope for this requirement; a maintainer (or an
external one-off script) calls it once per historical task ID.

A standalone `make sync-project-backfill f=<TASK-ID>` target MUST also
exist, as a thin wrapper around `butler --tasks-dir $(TASKS_DIR) task
sync-project $(f) --stage backfill` (same `f=`-argument and `check-butler`
convention as `stage-task`/`commit-task`), so a maintainer backfilling
historical tasks (or scripting a one-off loop over several) can do so
through `make` alone rather than only the raw CLI. As with every other
sync-stage target, this is a single, direct `butler` call in the target's
recipe with no call back into `make`, preserving Requirement 1's
non-recursive architecture.

**Use case:**

```bash
butler task sync-project TASK-012 --stage backfill
# Resolves the Project (.butler-project / BUTLER_GITHUB_PROJECT), creates/
# links a Project item, sets Status to whatever TASK-012's ## Status
# section says, sets "Created" to the date TASK-012's task file was first
# committed, and -- since TASK-012's status is done -- sets "Closed" to its
# Completion date:
#   Synced TASK-012 "Add dark mode toggle" to GitHub Project item (status: Done, created: 2026-03-02, closed: 2026-03-05)
# If the Project has no "Created"/"Closed" date fields, those are silently
# skipped and only Status is set:
#   Synced TASK-012 "Add dark mode toggle" to GitHub Project item (status: Done)
```

## Requirement 9: Start-of-implementation sync sets Status to "In Progress" (`--stage start`)

**Description:** A task's linked GitHub Projects item currently only moves
past the Project's default column at `--stage merge` (Status -> Done) or via
a one-off `--stage backfill` run. Between `--stage draft`/`--stage open` and
the merge, the item sits at whatever the Project's default Status option is
(e.g. "Todo"), even while a maintainer has already started implementing the
task on its branch — the Project board does not reflect that work is
actually in progress until it is finished.

A new sync stage, `--stage start`, MUST exist alongside `draft`/`open`/
`merge`/`backfill`. It MUST create/link a Project item for the task (same
lookup-then-reuse behavior as the other stages, per Requirement 4's "link"
clarification) and set the item's "Status" field to the option matching
"In Progress", using the same generalized status-option resolution
`--stage backfill` already uses (`_resolve_status_option_field_ids`) rather
than a new hardcoded lookup. A missing "Status" field or "In Progress"
option on the configured Project MUST follow Requirement 4's best-effort
warning contract (warn, never raise, never block).

`make branch-task` MUST invoke `--stage start` as an added step immediately
after `butler task branch` creates or switches to the task branch,
mirroring how `--stage open`/`--stage merge` are already invoked as added
`make` steps from `pr-task`/`merge-pr` rather than being inlined into
`git_ops.py`'s `branch_for`/`open_pr_for`/`merge_pr_for` functions
themselves (per Requirement 4's encapsulation constraint). As with every
other sync stage, a sync failure MUST NOT block the branch creation/switch
itself (`-butler ...` in the Makefile, matching the existing `-`-prefixed
sync lines for `pr-task`/`merge-pr`). There is no `branch-current-task`
target to also update — unlike `pr`/`merge`, branch creation has no
"current task" to resolve from, since the branch does not exist yet.

**Use case:**

```bash
make branch-task f=TASK-012
# ... existing behavior: branch task/012-add-dark-mode-toggle created/
# switched to, based on origin/main ...
# additionally attempts to sync the task to GitHub Projects:
#   Synced TASK-012 "Add dark mode toggle" to GitHub Project item (status: In Progress)
# if the Project has no "Status" field or "In Progress" option:
#   Warning: could not sync TASK-012 to GitHub Projects (no "Status"/"In Progress" field on this Project) - continuing
# branch creation succeeds either way; make branch-task exits 0
```

## Requirement 10: `CLAUDE.md.tmpl` instructs automatic self-application of Workflow Guardian's rules

**Description:** `templates/CLAUDE.md.tmpl`'s "Task Management" section
currently only points to the `{{WORKFLOW_GUARDIAN_NAME}}` agent's file as
the source of the task-file format and workflow enforcement. It does not
state that an assistant operating in a project generated from this
template MUST apply that agent's gates (requirements-first, task-drafting,
branch discipline, TDD, commit discipline, etc.) automatically whenever
doing task-branch/requirements/TDD work in the repository, regardless of
whether the agent is explicitly invoked by name (e.g. `@workflow-guardian`).
Without this, an assistant may treat the referenced gates as optional
guidance to consult on demand rather than a standing constraint, and skip
steps (e.g. committing with a raw `git commit`, or skipping the GitHub
Projects draft-stage sync) that the agent file itself mandates.

The generated `Task Management` section MUST state explicitly that
`{{WORKFLOW_GUARDIAN_NAME}}`'s rules apply automatically to any
task-branch/requirements/TDD work, independent of explicit invocation. It
MUST also state that the underlying operations (branch/stage/commit/pr/
merge, task-file sync) may be performed via **any** of the three
equivalent interfaces this project ships — the vendored `make` targets,
the installed `butler` CLI directly, or the optional `butler-mcp` MCP
server — rather than mandating `make` specifically; the gate is on *never
bypassing all three* with a raw `git`/`gh` command, not on which of the
three is used.

**Use case:**

```text
A consumer project generates its CLAUDE.md from this template. An assistant
working in that project is asked to "start TASK-005" without any
@-mention of the Workflow Guardian agent. Because the generated CLAUDE.md
states the agent's rules apply automatically, the assistant runs the full
gated flow (requirements confirmation, task drafting, branch creation,
TDD, draft-stage Projects sync, commit discipline, etc.) without being
separately asked to invoke the agent by name — using make targets, the
`butler` CLI, or the `butler-mcp` MCP server, whichever is available/
configured in that environment, instead of raw `git`/`gh` commands.
```

## Requirement 11: Project item body sourced from the task file's Story and Acceptance criteria (extends Requirement 4)

**Description:** Requirement 4 scopes the synced Project item metadata to
"TASK-ID, title, status." This requirement extends that scope to include a
body. `_create_item()` in `src/butler_core/projects.py` currently calls `gh
project item-create` with `--title` only; no `--body` is ever passed, so
every Project item it creates (via `sync_on_pr_draft`, `sync_on_pr_open`,
`sync_on_pr_backfill`, and `_start`/`sync_on_pr_start`) has an empty body —
confirmed live against the `CmdrPrompt/python-butler` Project on
2026-07-31, where issues #65-#72 (converted from Project items) all carry
empty bodies.

When creating a new Project item, `_create_item()` MUST pass a `--body`
argument built from the task file located via `tasks_dir` (already
available to its caller, `_sync()`, and used elsewhere in the module by
`_task_file_path()`/`_git_log_dates()`). The body MUST consist of exactly:

1. The task file's `## Story` section, verbatim.
2. The task file's `## Acceptance criteria` section, verbatim.
3. A link back to the task file itself (its `docs/tasks/TASK-XXX-*.md` path
   or a GitHub blob URL), and, once a PR exists for the task, a link to
   that PR.

The body MUST NOT include the task file's `## Description` section. This is
a deliberate exclusion: the Project item's body MUST remain distinct from
`_pr_body()` in `src/butler_core/git_ops.py`, which extracts `##
Description` (implementation-heavy detail intended for PR reviewers) for PR
bodies. `_pr_body()`'s extraction logic MUST NOT be reused or duplicated
for the Project item body; a separate, dedicated extraction (e.g. a
`_project_item_body()` helper) MUST be used instead.

If `tasks_dir` cannot be resolved, or no task file can be located for the
task, `_create_item()` MUST fall back to today's `--title`-only item
creation. This is a best-effort fallback consistent with Requirement 4's
warning contract: a missing task file MUST NOT block item creation.

This requirement applies only to item *creation*. It does not require
updating the body of a Project item that already exists.

**Use case:**

```bash
butler task sync-project TASK-012 --stage draft
# TASK-012's task file has:
#   ## Story
#   As a maintainer, I want to see the task's context on the Project board
#   so that ...
#   ## Acceptance criteria (Gherkin)
#   - [ ] Scenario: ...
# Creates a new Project item with:
#   --title "TASK-012 Add dark mode toggle"
#   --body "<## Story content>\n\n<## Acceptance criteria content>\n\nTask file: docs/tasks/TASK-012-add-dark-mode-toggle.md"
# (a PR link is appended once one exists, e.g. by --stage open once the PR
# has been created)
# The body does NOT contain TASK-012's ## Description section.

butler task sync-project TASK-099 --stage draft
# tasks_dir is unset, or no task file can be found for TASK-099:
# Falls back to title-only item creation (today's behavior); item creation
# still succeeds, consistent with Requirement 4's best-effort contract.
```

## Acceptance criteria (overall)

- [ ] A regression test exists asserting `butler_core.git_ops` never shells
      out to `make`, and that `butler task <cmd>` end-to-end does not spawn
      a nested `butler`/`make` process.
- [ ] A dedicated automated test exists (run in `make test`) that parses
      every `butler` flag used in the root Makefile and asserts it is
      accepted by the CLI's argparse definition, failing the build on
      drift.
- [ ] `butler sync` can refresh a consumer project's `.butler/Makefile` to
      match the installed CLI version, comparing content (hash/diff) to
      decide whether a change is needed, gated by a clean-working-tree
      check (`--force` to override), and supporting `--dry-run`.
- [ ] A separate, encapsulated sync entry point exists for mirroring task
      metadata (TASK-ID, title, status) to a linked GitHub Projects item,
      invoked as an added step from `pr-task`/`pr-current-task` (on PR open)
      and `merge-pr`/`merge-current-task` (on merge).
- [ ] The sync is one-way only: nothing is read back from GitHub Projects
      into the task workflow, and no existing agent's task-file read/write
      behavior changes.
- [ ] The sync is best-effort: failures (missing Project, missing `gh`
      permissions, `gh` not installed/authenticated, etc.) produce a warning
      and do not cause `pr-task`, `pr-current-task`, `merge-pr`, or
      `merge-current-task` to fail or block.
- [ ] The "no Project configured" warning includes a concrete,
      copy-pasteable suggestion (`gh project create --owner <owner> --title
      <repo>` and `export BUTLER_GITHUB_PROJECT=...`) with the owner and
      repository name filled in from the current repository when they can
      be determined at runtime, falling back to the existing generic
      warning (no example) when they cannot.
- [ ] `CHANGELOG.md` updated with a behavior-first entry.
- [ ] `make lint && make test` pass.
- [ ] The `--stage merge` status update resolves the Project's node ID and
      the "Status" field's/"Done" option's node IDs at sync time instead of
      passing the raw project number or literal field/option names to `gh
      project item-edit`, and succeeds against a real GitHub Projects v2
      board.
- [ ] A missing "Status" field or "Done" option on the configured Project
      produces a best-effort warning (per Requirement 4), not a raised
      exception or a blocked merge.
- [ ] Project-number resolution checks a `.butler-project` file at the
      target repo's root first, falling back to `BUTLER_GITHUB_PROJECT` only
      when the file is absent.
- [ ] A `--stage draft` option exists on the sync entry point and
      creates/links a Project item the same way `--stage open` does.
- [ ] Workflow Guardian runs the draft-stage sync for every new/modified
      task file immediately after merging Task Drafter's worktree branch;
      Task Drafter's own tool set is unchanged (no Bash, no GitHub
      interaction).
- [ ] The draft-stage sync is best-effort: failures warn and never block
      Workflow Guardian's merge of Task Drafter's branch.
- [ ] The "no Project configured" warning additionally offers creating
      `.butler-project` as a setup option alongside `export
      BUTLER_GITHUB_PROJECT=...`.
- [ ] `open_pr_for` no longer switches to `main` after creating the PR; the
      working tree stays on the task branch.
- [ ] `branch_for`, when creating a new task branch, fetches and bases it on
      `origin/main` rather than on the currently checked-out branch.
- [ ] A `--stage backfill` option exists on the sync entry point: it
      creates/links a Project item, sets Status to the task file's own `##
      Status` value (any status option, not just Done), sets a "Created"
      date field (if present on the Project) to the task file's first-commit
      date, and sets a "Closed" date field (if present and the task is done)
      to the task's Completion date, falling back to the file's most recent
      commit date when the Completion date is absent/unparseable.
- [ ] Missing "Created"/"Closed" date fields on the Project are silently
      skipped by `--stage backfill` without producing a warning; a missing
      "Status" field/option still follows Requirement 4's warning contract.
      Switching to an existing task branch is unaffected.
- [ ] A `--stage start` option exists on the sync entry point: it
      creates/links a Project item (reusing an existing one per Requirement
      4) and sets its "Status" field to the option matching "In Progress",
      via the same generalized status-option resolution `--stage backfill`
      uses.
- [ ] `make branch-task` invokes `--stage start` as an added Makefile step
      immediately after `butler task branch`, the same way `--stage open`/
      `--stage merge` are added steps in `pr-task`/`merge-pr` (not inlined
      into `branch_for` in `git_ops.py`); a sync failure is a best-effort
      warning and never blocks the branch creation/switch.
- [ ] `templates/CLAUDE.md.tmpl`'s "Task Management" section states that
      `{{WORKFLOW_GUARDIAN_NAME}}`'s rules apply automatically to any
      task-branch/requirements/TDD work, independent of explicit
      invocation.
- [ ] The same section states that the underlying operations may be
      performed via the `make` targets, the `butler` CLI, or the
      `butler-mcp` MCP server interchangeably, and that a raw `git`/`gh`
      command bypassing all three is what is disallowed — not `make`
      specifically.
- [ ] A newly created Project item's `--body` is built from the task file's
      `## Story` and `## Acceptance criteria` sections plus a link to the
      task file (and the PR, once one exists) — never the `##
      Description` section, and never `_pr_body()`'s extraction logic.
- [ ] A missing/unresolvable task file falls back to today's `--title`-only
      item creation without blocking or raising.
</content>
