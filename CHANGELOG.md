# Changelog

## [Unreleased]

### Added

- This repo now dogfoods its own BDD scaffold: `pytest-bdd` is a dev
  dependency, and `tests/bdd/features/`/`tests/bdd/steps/` exist with the
  example scenario, so `make bdd`/`make bdd-missing` are meaningful here, not
  only in consumer projects. TASK-084 and TASK-085's existing Gherkin
  acceptance criteria have been lifted into real `.feature` files
  (`BDD mode: BDD-ACTIVE`), bound via `scenarios()`-only step files marked
  `xfail` so their pending (not-yet-implemented) scenarios show as visibly
  red in `make bdd -v` without failing `make test`/CI. (TASK-088)
- The `CLAUDE.md` and Copilot instructions governance templates now include a BDD
  section covering directory layout (`tests/bdd/features/`, `tests/bdd/steps/`),
  feature file naming, declarative scenario style, acceptance-criterion-to-scenario
  mapping, and the outside-in implementation loop. `make init-project` and
  `make generate-governance-files` emit these additions and the `tests/bdd/`
  scaffold by default; pass `ENABLE_BDD=0` to omit them for projects that don't
  want BDD support. Existing projects adopt BDD by regenerating with
  `make generate-governance-files FORCE=1`. (TASK-083)
- Workflow Guardian, Implementation Worker, PR Reviewer, and Characterization Test
  Writer now enforce/support the BDD outside-in workflow: Guardian gates the start
  of implementation on the task's feature files (or inline Gherkin) existing and,
  where `make bdd` is available, showing the task's scenarios failing or unbound
  (red state); Implementation Worker binds step definitions first so scenarios fail
  for the right reason before driving the inner TDD loop, and treats the task
  incomplete until both `make bdd` and `make test` pass; PR Reviewer rejects a PR
  that leaves any acceptance criterion ID uncovered by a passing scenario; and
  Characterization Test Writer prefers Gherkin scenarios for user-facing behavior,
  keeping plain pytest for internal implementation details. (TASK-082)
- The canonical task file template (`task-file-format` skill) now structures acceptance
  criteria as numbered items, each carrying either an inline Gherkin scenario or a reference
  to the `.feature` file and scenario name that covers it, plus a `Feature files:` field for
  BDD-ACTIVE tasks and explicit guidance mapping preconditions/triggers/obligations to
  Given/When/Then. Checkbox markers stay at the start of the line so `butler task check`
  keeps working unchanged. (TASK-081)
- `make bdd` and `make bdd-missing` targets let a project run its BDD scenarios verbosely
  (`uv run pytest tests/bdd/ -v`) or list scenarios missing bound step definitions, exiting
  non-zero on a failure or an unbound step; both degrade gracefully with an adoption hint and
  exit 0 in projects that haven't adopted `tests/bdd/` yet, and `make help` now lists both
  targets. `make test` already collects `tests/bdd/` since it's nested under the project's
  regular test directory. (TASK-080)
- Scaffolded projects (`make init-project` / `make generate-governance-files`) now come with
  `pytest-bdd` support out of the box: `pytest-bdd` is added to the `dev` dependency group,
  `tool.pytest.ini_options.testpaths` collects `tests/bdd/` alongside the project's regular
  test directory, and a new `make generate-bdd-scaffold` target creates `tests/bdd/features/`
  and `tests/bdd/steps/` with a runnable example scenario and step definitions demonstrating
  the Given/When/Then and step-reuse conventions. (TASK-079)
- This repo's own `.github/workflows/ci.yml` now dogfoods the reusable `python-ci.yml` it
  publishes: a new `ci` job calls `./.github/workflows/python-ci.yml` with `make lint`/`make
  test`/`uv run pip-audit`, alongside the existing `validate-agents` job — a lint or test
  failure here is now caught by CI instead of only by whoever happens to run `make lint`/`make
  test` locally. Added `pip-audit` to the `dev` extra so the audit command is runnable. (TASK-078)

- The generated `CLAUDE.md`'s "Task Management" section now states that
  Workflow Guardian's rules apply automatically to task-branch/requirements/
  TDD work, independent of explicit `@`-mention invocation, and that the
  underlying operations may be performed via `make` targets, the `butler`
  CLI, or the `butler-mcp` MCP server interchangeably — the constraint is on
  never bypassing all three with a raw `git`/`gh` command, not on which one
  is used. (TASK-067)
- `make branch-task` now syncs the task's GitHub Projects item to Status
  "In Progress" as soon as the task branch is created or switched to, via a
  new `--stage start` on `butler task sync-project` (alongside the existing
  `draft`/`open`/`merge`/`backfill` stages) — the Project board now reflects
  that implementation has begun instead of staying at its default column
  until the PR is opened or merged. Like the other stages, `--stage start`
  reuses an existing linked item instead of creating a duplicate, and any
  failure (no Project configured, missing "Status"/"In Progress" field, `gh`
  not authenticated, etc.) is a best-effort warning that never blocks branch
  creation. (TASK-065)
- New standalone `make sync-project-draft f=TASK-XXX` and `make
  sync-project-backfill f=TASK-XXX` targets reach the `draft` and `backfill`
  GitHub Projects sync stages, which previously had no `make` entry point
  and were only reachable via the raw `butler task sync-project` CLI call —
  `make` is now a complete interface to all five sync stages. (TASK-069)
- The `butler-mcp` MCP server now exposes a `sync_project_task(task_id,
  stage)` tool covering all five GitHub Projects sync stages
  (`open`/`merge`/`draft`/`backfill`/`start`), matching what `butler task
  sync-project --stage <x>` already does via the CLI — an MCP-only agent
  with no shell access can now reach Workflow Guardian's GitHub Projects
  sync gate. Like the CLI, it's best-effort and returns the sync's
  success/message instead of raising. (TASK-068)
- New `butler task set-status <ID> <status>` CLI subcommand, matching what
  `butler-mcp`'s `set_task_status` tool already did — the `butler` CLI can
  now set a task's `## Status` field the same way MCP can, instead of that
  operation only being reachable via MCP or a manual file edit. (TASK-073)
- New `make worktree-clean b=<branch>` target removes a subagent's isolated
  worktree and its temporary branch after `merge-worktree`/
  `commit-current-task` have integrated its changes — previously nothing in
  the documented workflow ever cleaned these up, and stale worktrees
  accumulated indefinitely in `.claude/worktrees/` across sessions. The
  `commit-workflow` skill's "Merging a worktree branch" section now
  documents it as a step run after `commit-current-task` succeeds, kept
  separate from `merge-worktree` itself so a failed commit doesn't lose the
  worker's recoverable commit history. (TASK-074)

### Fixed

- A task file's Completion `**Stage:**` field is now parsed and rendered as a
  plain whitespace-separated list of file paths (`Task.stage_paths`) instead
  of a free-form command string — `butler task stage` (and `make
  stage-current-task`/`stage-task`) now always construct `git add <paths>`
  themselves and never execute the field's text as a shell command. A
  mistakenly-written `make`/`butler` invocation in that field (as happened in
  TASK-069, TASK-082, and TASK-083, each spawning a runaway recursive `make`
  process tree) now fails immediately with a "pathspec did not match any
  files" git error instead of recursing. The `**Commit:**` field already
  worked this way and is unchanged. (TASK-086)
- The reusable `.github/workflows/python-ci.yml`'s checkout step now fetches
  submodules (`submodules: true`), fixing a missing-file failure (e.g.
  `include .butler/Makefile: No such file or directory`) for consumer repos
  whose build depends on a git submodule — found via `firefly-bank-importer`
  PR #38's Lint step after the `uv` fix below let it get that far. (TASK-076)
- The reusable `.github/workflows/python-ci.yml` now sets up `uv` (via
  `astral-sh/setup-uv`) before the Install step, fixing `uv: command not
  found` for consumer repos whose `install-command` is a `uv` invocation —
  found via `firefly-bank-importer`'s first real end-to-end run of this
  workflow after repointing to the renamed repo. (TASK-075)
- GitHub Projects items created by `butler task sync-project` (`draft`/`open`/
  `start`/`backfill` stages) now get a populated body instead of an empty
  one — built from the task file's `## Story` and `## Acceptance criteria`
  sections plus a link back to the task file (and, once one exists, a link
  to the task's PR), so a converted-to-Issue item is useful on its own
  instead of a bare placeholder. The body deliberately excludes the task
  file's `## Description` section, which stays reserved for the PR body.
  (TASK-066)
- The GitHub Projects sync (`butler task sync-project`, all stages —
  `draft`/`open`/`merge`/`backfill`) now looks up whether a Project item already
  exists for the task (matching on its TASK-ID title prefix) before creating one,
  and reuses that item instead of creating a duplicate — previously, running more
  than one sync stage for the same task (the normal `draft` → `open` → `merge`
  sequence) created a new Project item on every call. The item-lookup callers that
  update an item's status (`--stage merge`/`--stage backfill`) also now take only
  the first matching item ID instead of assuming exactly one line of output; a
  stale multi-match no longer gets concatenated into a single malformed `--id`
  value passed to `gh project item-edit`, which previously made the merge-stage
  status update fail outright with a GraphQL error whenever a task already had more
  than one linked item. (TASK-063)
- `butler task show`, `butler-mcp`'s `get_task`/`list_tasks`, and any other
  reader of `Task.acceptance_criteria` now correctly find a task's
  acceptance criteria when the section is headed `## Acceptance criteria
  (Gherkin)` — the heading every task file has used since TASK-043. The
  parser's heading matcher previously required the heading line to be
  exactly `## Acceptance criteria` with nothing but whitespace after it, so
  it silently returned an empty list for every current-format task file,
  even though the checkboxes were present and `butler task check`/the
  GitHub Projects item body (both of which read the file differently)
  worked correctly. (TASK-072)

### Changed

- The reusable `.github/workflows/python-ci.yml` now runs Install, Lint, Test, and Audit as
  separate `needs`-chained jobs instead of steps within one `ci` job, so a consumer PR's checks
  list shows each stage as its own entry (e.g. "lint" failing red at a glance) instead of a single
  combined "ci / ci" check that has to be opened to see which step failed. Each job re-runs
  `install-command`, made fast by `astral-sh/setup-uv`'s `enable-cache: true` restoring the
  resolved packages. The `workflow_call` input contract is unchanged, so no consumer `ci.yml`
  needs edits. (TASK-077)
- `butler task pr` (`make pr-task`/`pr-current-task`) no longer switches the working tree to
  `main` after opening the PR — it now leaves you on the task branch, so `make
  merge-current-task` can run immediately afterward without a manual `git checkout
  task/<NNN>-...` first, and the Projects `--stage open`/`--stage draft` sync step that
  immediately follows no longer spuriously fails with "No task file found" (the task file only
  exists on the task branch, not yet on `main`, until the PR is merged). To keep starting a new
  task safe now that a leftover task branch can be left checked out, `butler task branch` (`make
  branch-task`), when creating a brand-new branch, now fetches and bases it on `origin/main`
  instead of on whatever branch is currently checked out; switching to an already-existing task
  branch is unchanged. (TASK-061)

- `.butler` is now distributed as a git submodule instead of a git subtree. Adoption uses
  `git submodule add <remote> .butler` in place of `git subtree add --prefix=.butler ... --squash`;
  `make butler-fetch`/`make butler-pull` now move `.butler`'s submodule pointer to the latest
  remote commit and print the `git add .butler` / `git commit` follow-up instead of merging
  butler's tree into the consumer project's own history and auto-committing, so a pull can no
  longer produce the modify/delete merge conflicts that repeatedly hit subtree consumers (e.g.
  `firefly-bills-analyzer`); `make butler-check` compares the submodule's recorded commit against
  the remote's tracked branch instead of a `.butler-version` file. `make butler-trim` and its
  un-regenerated-content guard (TASK-048, TASK-051, TASK-053) are removed outright -- `.butler`
  stays a full, untrimmed submodule checkout at all times, since a submodule pointer move has no
  tree-merge step to guard. `make butler-uninstall CATEGORIES=subtree,...` now removes the
  submodule cleanly (`git submodule deinit -f .butler` + `git rm -f .butler`, plus the
  `.gitmodules` entry and any leftover `.git/modules/.butler` metadata) instead of a plain
  `rm -rf .butler`. `README.md` documents a manual migration path for existing subtree-based
  consumer projects to convert to the submodule layout without rewriting their git history.
  `REQUIREMENTS_BUTLER_PULL.md` is superseded in full by `REQUIREMENTS_SUBMODULE.md`; its
  `claude-skills`/`claude-agents` copy-symmetry requirement carries forward unchanged, and
  `generate-governance-files`'s copy behavior is otherwise untouched. (TASK-054)
- The "no project configured for this repo" warning printed by the GitHub Projects sync now
  includes a concrete, copy-pasteable setup suggestion (`gh project create --owner <owner> --title
  <repo>` followed by `export BUTLER_GITHUB_PROJECT=<number from the command above>`) with the
  owner and repository name filled in from the current repository, derived at runtime via
  `gh repo view --json owner,name` or by parsing the `origin` remote URL. If the owner/repository
  cannot be determined (e.g. `gh` is not installed/authenticated, or there is no `origin` remote),
  the sync falls back to the previous generic warning with no example. (TASK-057)

### Fixed

- The GitHub Projects sync's merge-stage status update (`sync_on_pr_merge` /
  `butler task sync-project <id> --stage merge`) now resolves the actual GraphQL node
  IDs for the Project, its "Status" field, and the "Done" option (via `gh project
  view`/`gh project field-list`) before calling `gh project item-edit`, instead of
  passing the plain `BUTLER_GITHUB_PROJECT` number and the literal strings
  "Status"/"Done" directly — which GitHub's API always rejected with a "could not
  resolve to a node" error, so the merge-stage status update had never actually
  succeeded against a real Projects v2 board. A Project missing a "Status" field or a
  "Done" option now produces the existing best-effort warning instead of failing the
  same way. (TASK-059)

### Added

- `butler task sync-project <task_id> --stage backfill` is a new sync stage for historical tasks
  (e.g. TASK-001 through TASK-059) completed before the Projects sync existed: it creates/links a
  Project item and sets its Status to match the task file's own `## Status` (generalizing the
  previous "Done"-only resolution to match any status option by name, case-insensitively, treating
  `-` as a space, e.g. `in-progress` matches an option named "In Progress"), sets a "Created" date
  field (if the Project has one) to the git commit date the task file was first added, and -- when
  the task's status is `done` -- sets a "Closed" date field (if present) to the task's own
  `## Completion` date, falling back to the file's most recent commit date when the Completion date
  is missing or unparseable. A Project missing the "Created" or "Closed" field is silently skipped
  (each is opportunistic, not required); a missing "Status" field/option still produces the existing
  best-effort warning. (TASK-062)
- The GitHub Projects sync now resolves its target Project from a repo-local `.butler-project`
  file (plain text, contents = the Project number) in the target repo's root, checked before
  falling back to the `BUTLER_GITHUB_PROJECT` environment variable — so which Project a task
  syncs to no longer depends on the invoking shell's environment, which broke down when an agent
  (e.g. Task Drafter) writes a task file into a different local repo than the one it's running
  in. The "no project configured" warning now offers creating `.butler-project` alongside
  `export BUTLER_GITHUB_PROJECT=...`. `butler task sync-project <id> --stage draft` is a new
  stage (behaving like `--stage open`) that Workflow Guardian now runs immediately after merging
  Task Drafter's worktree branch, best-effort, so a task shows up on the Project board as soon as
  it's drafted rather than only once its PR is opened; Task Drafter's own tool set is unchanged
  (still no `gh`/GitHub access). (TASK-060)
- A reusable `.github/workflows/python-ci.yml` (`workflow_call`) now exists in this repo, accepting
  the `python-version`, `install-command`, `lint-command`, `test-command`, and optional
  `audit-command` inputs that consumer repos (e.g. `firefly-bank-importer`) already pass. Consumer
  workflows can repoint their `uses:` from the renamed `python-commons` repo to
  `CmdrPrompt/python-butler/.github/workflows/python-ci.yml@main` with no changes to their `with:`
  block, restoring real lint/test/audit enforcement on their pull requests, which had been failing
  instantly since the file never existed in either repo. (TASK-058)
- Added a best-effort, one-way sync of task metadata to a linked GitHub Projects (v2) item: a new
  `butler task sync-project <task_id> --stage open|merge` command (backed by `butler_core.projects`,
  kept separate from `git_ops.py`) creates or links a Project item populated with the TASK-ID and
  title when a PR is opened, and moves the item's status to "Done" when the PR is merged. The
  target Project is configured via the `BUTLER_GITHUB_PROJECT` environment variable; `pr-task` and
  `merge-pr` now invoke the sync step as a non-blocking addition after opening/merging the PR, so a
  missing Project, an unauthenticated or missing `gh` CLI, or any other sync failure only prints a
  warning and never fails PR creation or merge. (TASK-056)
- Added five shared skills (`commit-workflow`, `task-file-format`, `tdd-cycle`, `changelog`,
  `characterization-tests`) under `.claude/skills/` (mirrored in `claude-skills/`) so procedures
  previously duplicated across every agent definition now live in one place; all agents now load
  them via the `Skill` tool instead of restating the text inline. Added a `check-skills-sync`
  `make lint` target that fails the build if the two skill directories drift apart, mirroring the
  existing `check-agents-sync` check. (TASK-050)
- Added a `butler sync` CLI command that refreshes a consumer project's vendored
  `.butler/Makefile` to match the version bundled in the currently installed `butler` package,
  comparing content by hash so it only overwrites when the files actually differ (`--dry-run` to
  preview, `--force` to override the dirty-working-tree guard). Consumer projects that end up
  pinned to a stale vendored Makefile snapshot -- as `firefly-python-api` was before TASK-043 --
  now have a supported way to correct the drift without manually diffing and patching files by
  hand. (TASK-045)
- Added a `task-drafter` agent (Claude Code and GitHub Copilot flavors) that turns confirmed
  requirements into INVEST-compliant task files with Gherkin acceptance criteria, splitting this
  responsibility out of `requirements-drafter`. `workflow-guardian` now delegates task-file
  drafting to it and gates implementation on the task's Status not being `blocked`. (TASK-042)
- Added regression tests (`tests/test_no_make_recursion.py`) protecting the non-recursive
  `butler task <cmd>` <-> vendored Makefile architecture: a static/AST scan asserts
  `butler_core.git_ops`'s `branch_for`, `stage_for`, `commit_for`, `open_pr_for`, and
  `merge_pr_for` never construct a `subprocess` call whose first argument is `"make"`, and
  end-to-end tests assert `butler task branch|stage|commit|pr|merge` complete without spawning a
  nested `butler` or `make` process. No production code changed; this formalizes behavior that
  already existed as of TASK-023 so it cannot silently regress. (TASK-043)
- Added a test (`tests/test_makefile_cli_flag_drift.py`) that parses every `butler ...` invocation
  in the root `Makefile`, extracts the flags they pass (currently `--tasks-dir`), and cross-checks
  them against the CLI's argparse definition in `src/butler_cli/__main__.py`, failing `make test`
  if the Makefile ever passes a flag the installed CLI no longer accepts. No production code
  changed; this guards against silent drift going forward. (TASK-044)

### Changed

- `REQUIREMENTS_BUTLER_PULL.md` now defines the set of consumer-facing content
  paths (`templates/`, `claude-agents/`, `claude-skills/`) once, under a
  "Scoped paths" section, instead of re-enumerating them in Requirement 1,
  Requirement 3, Requirement 4, and the overall acceptance criteria — closing
  the drift risk where adding a new content type or requirement could leave
  one of those spots out of sync with the others. No behavior change. (TASK-052)

### Fixed

- `make butler-trim` now refuses to delete `.butler/templates/`, `.butler/claude-agents/`, or
  `.butler/claude-skills/` while any of them are non-empty, unless `FORCE=1` is passed -- closing
  a gap where `butler-pull`'s change-detection guard (TASK-048/051) only protected the automatic
  trim inside a *successful* pull, leaving the conflict-recovery path (`git subtree pull` fails,
  the user resolves the conflict by hand, then runs `make butler-trim` directly per
  `butler-pull`'s own failure message) and any other direct invocation completely unguarded. The
  README's adoption steps, its "Keeping butler up to date" and "Regenerating governance files"
  sections now pass `FORCE=1` where a manual `butler-trim` follows a regen, and document the
  `git subtree pull` conflict-recovery path explicitly. (TASK-053)
- `make butler-pull`'s change-detection and `generate-governance-files` now treat
  `.butler/claude-skills/` the same as `.butler/claude-agents/`: a pull that only changes skills
  now defers the automatic trim and prints the same warning, and `generate-governance-files`
  copies every `.butler/claude-skills/*/SKILL.md` into `.claude/skills/<name>/SKILL.md`. Skill
  updates were previously silently deleted by the automatic trim, with no supported way — manual
  or automatic — for a consumer project to ever receive them. (TASK-051)
- `make butler-pull` no longer deletes `.butler/templates/` or `.butler/claude-agents/` before a
  consumer project can regenerate governance files against newly-pulled content: it now compares
  those two paths before and after the subtree pull and, if either changed, prints the changed
  files plus the exact follow-up commands (`make generate-governance-files FORCE=1` then
  `make butler-trim`) and skips the automatic trim for that run instead of deleting the new content
  immediately. When neither path changed, `butler-pull` still fetches and trims in one step as
  before. A failed subtree pull (e.g. a merge conflict) also no longer runs `butler-trim` on top of
  the unresolved merge. `make help` and the README's update instructions now describe this
  conditional behavior instead of implying `butler-pull` is always a complete update path.
  (TASK-048)
- `check-agents-sync` (`Makefile` and the vendored `src/butler_core/data/Makefile`, wired into
  `make lint`) now exits 0 with no output when a project has no `claude-agents/` directory,
  instead of hitting bash's non-`nullglob` behavior and reporting a nonsensical false-positive diff
  against a literal `*.agent.md` filename. This previously made `make lint` permanently and
  unfixably broken for every `butler`-adopting project that keeps its agent definitions only in
  `.claude/agents/` (reproduced in `firefly-bills-analyzer`) -- python-butler's own repo, which
  does keep `claude-agents/` and `.claude/agents/` in sync, is unaffected: existing drift-detection
  behavior there is unchanged. (TASK-047)
- `pymarkdown ... fix` invocations (in `make fix`, `make stage`/`make stage-current-task`, and
  `butler_core.git_ops.stage_for()`) now pass `--return-code-scheme minimal`, so successfully
  fixing a markdown file (previously exit code 3 under pymarkdown's default scheme) no longer
  aborts the recipe or raises `CalledProcessError` -- genuine pymarkdown errors (e.g. a bad
  `--config` path) still fail loudly. (TASK-046)
- `make validate-agents` now flags an `.agent.md` file with a missing `tools:` key as an error
  (`missing required key 'tools'`), the same as an empty `tools: []` list -- previously a fully
  absent `tools:` key silently passed validation even though it produces the identical "subagent
  has no tools" runtime failure the validator exists to catch. (TASK-036)
- Fixed invalid `tools:` frontmatter in all nine `.claude/agents/*.agent.md` definitions (and
  their `claude-agents/` sources): the generic names `read, search, edit, write, execute, todo,
  agent` are not Claude Code tool names and were silently dropped, leaving every subagent with an
  empty tool set. Affected subagents (Test Writer, PR Reviewer, Implementation Worker) narrated
  tool calls as plain text instead of executing them and stalled with zero tool uses, the failure
  mode previously documented in TASK-025. Replaced with the real names (`Read`, `Grep`, `Glob`,
  `Edit`, `Write`, `Bash`, `TodoWrite`, `Task`) and updated the prose in the Tool usage sections
  to match. (TASK-035)
- `make merge-pr`/`make merge-current-task` now read the task branch name from the task file's
  `**Branch name:**` line instead of recomputing it from the filename, fixing a mismatch
  (`task/task-<NNN>-<slug>` vs. the real `task/<NNN>-<slug>` convention) that made these targets
  always fail with "No open PR for branch ..." even when a valid, mergeable PR existed. (TASK-033)
- Pinned the `ruff-pre-commit` hook to `v0.15.20`, matching the project's `ruff` dev dependency,
  and re-sorted `mcp/server.py`'s imports accordingly — the two had drifted apart (`v0.11.0` vs.
  latest), so a commit that passed the pre-commit hook could still fail a plain `make lint`.
  (TASK-033)

- Subagent failure markers older than 60 minutes are no longer reported as gate trip
  conditions. Markers in `.claude/state/agent-failures/` are project-global state shared
  across concurrent sessions; a stale marker from one task could confuse another task's
  session. Stale markers are still consumed (deleted) on read, but are excluded from the
  hard-gate escalation message and exit code. If all found markers are stale, the gate
  exits silently with 0 (matching "no markers found" behavior). Markers with missing or
  unparseable `detected_at` timestamps are treated as fresh (fail toward reporting).
  (TASK-037)
- The subagent zero-tool-call hard gate no longer fires on legitimately tool-free work: a
  marker is now only written when zero tool calls coincide with corroborating evidence of
  the real "narrated tool calls" failure (a tool-narration text pattern, or a coordinator
  follow-up event in the transcript), so a long free-text report with zero tool calls (e.g.
  Test Design Reviewer briefed to work entirely from pasted content) no longer trips the
  gate. Agents whose task is genuinely text-in/text-out can also opt out entirely with a new
  `allow-tool-free: true` frontmatter key (`make validate-agents` validates it as boolean);
  `test-design-reviewer.agent.md` now declares it. Failure markers also carry a `session_id`,
  and `agent_result_gate.py` only treats markers from its own session as candidates to
  trigger, leaving other sessions' markers untouched (previously any marker in any session
  could spuriously trip the gate) while still pruning any marker older than 24 hours
  regardless of session. The gate's stderr directive no longer unconditionally claims a
  frontmatter configuration error: when `validate-agents` passes, it now states that the
  configuration is valid and points at the transcript and marker diagnosis for further
  investigation instead. (TASK-038)

### Added

- Generated `CLAUDE.md` and Workflow Guardian agent definitions now include a Cross-Workspace
  Boundary section/gate: code must never be written in a sibling or dependency repo from the
  current workspace, and task-file/requirements-doc edits in another workspace require the
  user's explicit prior approval before editing. (TASK-041)
- Added `make validate-agents` (`scripts/validate_agents.py`, stdlib-only): validates the YAML
  frontmatter of every `.claude/agents/*.agent.md`: required keys present, `tools:` non-empty and
  containing only real Claude Code tool names (with did-you-mean hints for case errors, and
  `mcp__server__tool` names allowed by pattern). Wired into pre-commit and CI so a broken agent
  definition can never reach `main`. (TASK-035)
- Added a runtime hard gate against silent subagent failure, registered in `.claude/settings.json`:
  `.claude/hooks/subagent_toolcheck.py` (SubagentStop) detects any subagent turn that ends with
  zero `tool_use` blocks and writes a failure marker, and `.claude/hooks/agent_result_gate.py`
  (PostToolUse on `Agent|Task`) picks the marker up in the coordinator's session, runs the
  validator, and exits 2 with a directive to treat the failure as a configuration error and stop
  instead of retrying a subagent that has no tools and cannot comply. (TASK-035)
- Added `make butler-uninstall CATEGORIES=subtree,makefile,governance` to remove butler's
  footprint from an adopting project (the `.butler/` subtree, the Makefile `include` line, and/or
  generated governance files) — supports `DRY_RUN=1` to preview changes and requires a clean
  working tree unless `FORCE=1` is passed. `docs/tasks/` is never touched. Implemented in plain
  shell so it works even in legacy projects with no `butler_core`/`butler-cli` installed. An
  equivalent `butler uninstall --categories ... [--dry-run] [--force]` CLI subcommand is available
  as an optional alternative for projects that already have the CLI installed. (TASK-034)
- README now documents the `butler` CLI (`uv tool install .` or a Git URL) and the standalone MCP
  server (`cd mcp && uv sync`) as optional additions to the base Makefile adoption flow, and a
  new test suite (`tests/test_packaging.py`) locks in the packaging isolation this depends on: the
  MCP server's distribution name can't collide with the `mcp` SDK it depends on, its
  `pyproject.toml` can't pull in `butler_core`'s dev dependencies, and `make check-butler` still
  fails with a clear message (not a traceback) when the CLI isn't installed. (TASK-027)
- A standalone MCP server (`mcp/server.py`, its own `mcp/pyproject.toml`) exposes `list_tasks`,
  `get_task`, `create_task`, `check_acceptance_criterion`, `set_task_status`, `branch_task`,
  `stage_task`, `commit_task`, `open_pr_for_task`, and `merge_task_pr` as MCP tools over stdio,
  each a thin one-to-one wrapper over `butler_core.tasks`/`butler_core.git_ops` with no implicit
  batching of git operations, so Claude Code or any MCP-compatible agent can drive the task
  workflow directly instead of shelling out to `make` or the CLI. The MCP SDK dependency stays
  isolated to `mcp/`'s own environment and does not affect the base package. (TASK-025)
- The `butler` CLI (`src/butler_cli/__main__.py`) now exposes `butler task list [--status ...]`,
  `show`, `create --title --description`, `check --criterion N` (1-based), `branch`, `stage`,
  `commit`, `pr`, and `merge` as thin subcommand wrappers over `butler_core.tasks` and
  `butler_core.git_ops`, so a developer in a terminal (including GitHub Codespaces) can drive
  the full task workflow without `make`. (TASK-024)
- `make merge-worktree` now squash-merges (`git merge --squash`) instead of a plain merge, so
  Workflow Guardian creates the single real commit itself after a worktree sub-agent's work is
  brought in; Implementation Worker now commits from an isolated worktree with
  `make commit-output` (its branch does not match `task/<NNN>-...`, so `stage-current-task`/
  `commit-current-task` aren't available there) instead of leaving edits uncommitted, so its
  work reliably survives worktree cleanup. Workflow Guardian now also reads test/production
  file content itself and pastes it inline into the Test Design Reviewer prompt instead of
  having the reviewer read files independently, and independently re-verifies every
  Implementation Worker / Test Design Reviewer report (file contents, test counts, commit
  hashes, coverage) against ground truth before trusting it. (TASK-029)
- `butler_core.git_ops` provides `branch_for`, `stage_for`, `commit_for`, `open_pr_for`, and
  `merge_pr_for`, extracting the git/`gh` workflow logic previously inlined in the `Makefile`'s
  `branch-task`, `stage-task`, `commit-task`, `pr-task`, and `merge-pr` targets into reusable,
  testable Python operations on the `Task` dataclass, matching the Makefile's behavior and
  error messages exactly. (TASK-023)
- `butler_core.tasks` reads, lists, creates, and updates `docs/tasks/TASK-*.md` files as
  structured `Task` data — `read_task`, `list_tasks`, `create_task`, `check_criterion`,
  `set_status` — while staying byte-compatible with the `grep`/`sed` parsing in `Makefile`
  targets like `branch-task`, `stage-task`, and `commit-task`. (TASK-022)
- `make check-agents-sync` fails `make lint` if `claude-agents/` (the distributable agent
  sources) and `.claude/agents/` (the in-repo copy) have drifted apart, catching missing or
  differing `.agent.md` files before merge instead of silently. (TASK-028)
- Workflow Guardian now requires a Test Design Reviewer pass over a task's tests, checked
  against Dave Farley's 8 Properties of Good Tests, before `make stage-current-task`/
  `stage-task` — real findings must be addressed before staging. (TASK-028)

### Changed

- `make branch-task`, `stage-task`, `commit-task`, `pr-task`, and `merge-pr` (and their
  `-current-task` variants) now delegate to the `butler` CLI instead of inlining `grep`/`sed`
  parsing of task files; target names, `f=TASK-XXX` arguments, and observable behavior are
  unchanged. If `butler-cli` is not installed, these targets now fail with a clear install
  instruction instead of a cryptic `grep`/`sed` error. (TASK-026)
- `tests/test_cli.py::TestGitDelegation` now mocks `subprocess.run` at the real git/`gh`
  process boundary instead of the CLI's internal `git_ops` collaborator functions, so the
  five delegation tests (branch/stage/commit/pr/merge) assert on the actual external command
  the full CLI pipeline would run (and the CLI's exit code) instead of only that an internal
  function was called with a given object — regression protection now survives internal
  signature refactors. (TASK-030)
- `tests/test_cli.py` test names each now state a single behaviour claim: names containing
  "and" were either split into two independent tests (creating a task file vs. printing its
  id, since they're observed through different mechanisms and don't imply one another) or
  renamed to a single unifying name where the two facts were one cohesive behaviour (e.g.
  "prints an error and exits 1" -> "fails cleanly"). (TASK-031)
- `tests/test_cli.py` multi-assert tests (`test_prints_structured_task_data`,
  `test_prints_acceptance_criteria_with_check_marks`, `test_prints_completion_info_when_present`,
  `test_creates_task_file_with_correct_metadata`) now carry a failure message on every `assert`
  stating what was expected, so a failure pinpoints the diverging field without reading the
  test body. (TASK-032)

### Fixed

- `templates/` (the Copilot-facing `.tmpl` counterparts rendered into an adopting project's
  `.github/agents/`) was missing `test-design-reviewer.agent.md.tmpl` and
  `test-writer.agent.md.tmpl`, and `generate-governance-files`'s agent loop didn't generate
  them either; both agents are now templated and included in generation, matching
  `.claude/agents/`. (TASK-029)
- `claude-agents/` was missing `test-design-reviewer.agent.md` and `test-writer.agent.md`,
  and its `workflow-guardian.agent.md` was stale relative to `.claude/agents/`; both
  directories are now identical. (TASK-028)

- Python package skeleton (`pyproject.toml`, `src/butler_core/`, `src/butler_cli/`, `mcp/`,
  `tests/`) and dev dependencies (`ruff`, `mypy`, `bandit`, `pytest`, `hypothesis`) so
  subsequent tasks can implement and test real code. (TASK-021)
- `make sync-main` merges `main` into the current task branch — replaces the previous
  instruction to run `git merge main` directly. (TASK-021)
- `make merge-worktree b=<branch>` merges a worktree sub-agent branch back into the
  current branch after the agent finishes. (TASK-021)
- `make commit-output f="..." m="..."` stages and commits arbitrary files with a given
  message, for agents that operate outside a task branch. (TASK-021)
- Agent files (`implementation-worker`, `requirements-drafter`, `characterization-test-writer`,
  `test-writer`, `bug-triage`, `dependency-auditor`, `test-design-reviewer`) updated with
  `write` tool access, worktree execution context, and a rule to use `make` targets for all
  git operations instead of direct `git` commands. (TASK-021)
- New agent files `test-writer.agent.md` and `test-design-reviewer.agent.md` added to
  `.claude/agents/`. (TASK-021)

### Fixed

- `make pr-task` and `make branch-task` no longer print `fatal: a branch named
  '...' already exists` when the task branch already exists; they now check with
  `git show-ref` and choose the correct `checkout` form silently. (TASK-019)

- `butler-trim` now removes all files and directories under `.butler/` except
  `Makefile` dynamically, replacing a hardcoded list that silently left behind
  any file added to python-butler after the list was written (e.g. `LICENSE`).
  (TASK-018)

- `butler-trim` now records the remote HEAD SHA via `git ls-remote` instead of
  extracting from the squash-merge commit message, which did not reliably match
  the branch tip. `butler-check` now correctly reports "up to date" after a pull.
  (TASK-016)

- `scaffold/pyproject.toml.tmpl`: replaced `"pymarkdown"` with `"pymarkdownlnt>=0.9.36"`,
  added `[build-system]` table, and added `[tool.setuptools.packages.find]` for src-layout
  projects. (TASK-014)
- `scaffold/.gitignore.tmpl`: added `complexipy-results*.json` (hyphen variant) alongside
  the existing `complexipy_results_*.json` entry. (TASK-014)
- Agent `.md.tmpl` files: all ordered-list items now use `1.` so generated files pass
  `pymarkdown --fix` without modification. (TASK-014)

### Added

- `make butler-check` compares the butler commit SHA in `.butler-version` against
  the remote HEAD and reports whether the project is up to date or suggests
  `make butler-pull`. (TASK-016)
- `make butler-trim` now writes `.butler-version` to the project root with the full
  butler commit SHA; `make butler-pull` keeps it current automatically. (TASK-016)

- `scaffold/.pymarkdown` and `make generate-pymarkdown` target: new projects now get a
  `.pymarkdown` config with the standard disabled rules (md003, md013, md022, md024, md032,
  md033, md040, md041). Generated automatically by `make generate-pyproject` and
  `make install`. (TASK-014)

- `make butler-trim` strips `.butler/` down to just `Makefile` after `make init-project`
  has applied all templates and scaffold files; adopting projects no longer commit
  sources that have no ongoing function. (TASK-015)
- `make butler-fetch` pulls the latest butler without trimming, restoring `templates/`,
  `scaffold/`, and `claude-agents/` when governance files need to be regenerated. (TASK-015)
- `make butler-pull` pulls the latest butler and immediately trims — for keeping
  `.butler/Makefile` up to date without regenerating anything. (TASK-015)
- Claude Code agent source files moved to `claude-agents/` (previously `.claude/agents/`);
  `generate-governance-files` updated accordingly. (TASK-015)

### Fixed

- README "Adopting in an existing project": replaced macOS-incompatible `sed -i`
  with a portable `printf | cat` pattern. (TASK-013)
- README "What's included": scaffold description now lists all generated files. (TASK-013)
- README "Governance files": lists all files generated by `init-project`. (TASK-013)
- README "Adopting in an existing project": added commit and push steps. (TASK-013)

### Added

- README "Adopting in a new project" now includes the commit and push steps
  after `make install`. (TASK-012)

- `make init-project` now generates `.gitignore` from `scaffold/.gitignore.tmpl`;
  `make install` also auto-generates it if missing. (TASK-010)
- `make init-project` now generates `.pre-commit-config.yaml` from scaffold with
  ruff hooks; `make install` also auto-generates it if missing, eliminating the
  "No .pre-commit-config.yaml file was found" warning on first commit. (TASK-011)

### Changed

- Scaffold `pyproject.toml.tmpl` now sets ruff `line-length = 100` instead of 88. (TASK-008)
- `make init-project` now prints the suggested `git add` and `git commit` commands
  after successful generation so the user can copy-paste them. (TASK-009)

### Added

- `make init-project` interactively prompts for project name, description, requirements
  path, and run command, then delegates to `generate-governance-files`; keeps
  `generate-governance-files` CI-safe while giving humans a guided entry point. (TASK-002)
- `make init-project` now defaults the project name prompt to the current directory
  name instead of the static `my-project` placeholder. (TASK-007)
- README now has separate step-by-step adoption flows for new and existing projects,
  prerequisites section, and explicit ordering (subtree → include → init-project). (TASK-003)
- README adoption guide clarifies that an initial empty commit is required only when
  the repo was created locally with `git init`, not when cloned from GitHub. (TASK-004)

### Fixed

- `make init-project` now generates `pyproject.toml` with the collected project name
  and description; previously `make install` would generate it with default values
  (`my-project`, `Describe your project here.`). (TASK-005)
- `generate-pyproject` now guards against overwriting an existing `pyproject.toml`
  unless `FORCE=1` is passed. (TASK-005)

### Changed

- `TESTS_DIR ?= tests` added to Makefile alongside `SRC_DIR`; `test` target now passes
  `$(TESTS_DIR)/` explicitly to pytest; `scaffold/pyproject.toml.tmpl` uses `{{TESTS_DIR}}`
  placeholder for `testpaths` instead of hardcoded `tests`. (TASK-006)

- `templates/CLAUDE.md.tmpl` is now a proper project-scoped CLAUDE.md template with all
  supported placeholders (`{{PROJECT_NAME}}`, `{{PROJECT_DESCRIPTION}}`, `{{REQUIREMENTS_PATH}}`,
  `{{WORKFLOW_GUARDIAN_NAME}}`, `{{BUG_TRIAGE_NAME}}`, `{{PROJECT_MAKE_TARGET}}`); previously
  contained the python-butler README. (TASK-001)
- `generate-governance-files` now guards against overwriting an existing `CLAUDE.md` or
  `.github/copilot-instructions.md` unless `FORCE=1` is passed. (TASK-001)
