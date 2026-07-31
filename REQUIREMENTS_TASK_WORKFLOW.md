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
  TASK-ID/title fields from the task file.
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
