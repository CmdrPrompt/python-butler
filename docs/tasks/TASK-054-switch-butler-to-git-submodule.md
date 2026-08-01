# TASK-054 Switch `.butler` distribution from git subtree to git submodule

## Status
done

## Requirements
**Binding:** Requirements 1-6 (REQUIREMENTS_SUBMODULE.md)
**BDD mode:** BDD-PLANNED
**Depends on:** none
**Precedence:** The requirements above are the binding definition of this task.
The story and scenarios below are derived from them. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build from
the story.

## Story (context, not binding)
As a consumer project maintainer, I want `.butler` distributed as a git
submodule instead of a git subtree, so that pulling butler updates can never
produce a merge conflict in my own project's git history.

## Description
`git subtree pull` merges butler's full upstream content into the consumer
project's own history on every pull, then `butler-trim` deletes everything
but `Makefile` to keep the working tree clean (TASK-039, TASK-048, TASK-051).
This structurally conflicts whenever a pull touches a path a prior trim
already deleted locally — not a rare edge case, but the expected outcome of
trimming at all. TASK-053 added a guard so `butler-trim` won't silently
destroy un-regenerated content when this happens, but it does not prevent the
conflict itself; the consumer still has to run `git merge --abort` or
hand-resolve it (reproduced in `firefly-bills-analyzer`, 2026-07-20).

A git submodule stores `.butler` as a pointer (commit hash) to the
python-butler repo rather than merging its content into the consumer's
history. Updating means moving the pointer and committing that one-line
change — there is no tree merge against the consumer's own history, so this
class of conflict cannot occur.

Per `REQUIREMENTS_SUBMODULE.md`: adoption switches to `git submodule add`
(Requirement 1); `butler-fetch`/`butler-pull`/`butler-check` become
pointer-move operations with no subtree merge (Requirement 2);
`butler-trim` and its guard logic (TASK-048, TASK-051, TASK-053) are
retired outright — `.butler` stays a full, untrimmed submodule checkout
(Requirement 3); a documented manual migration path is provided for
existing subtree-based consumers, e.g. `firefly-bills-analyzer`
(Requirement 4); `generate-governance-files`'s `claude-skills`/`claude-agents`
copy behavior is preserved unchanged (Requirement 5); and
`butler-uninstall`'s `subtree` category is corrected to properly
`git submodule deinit`/`git rm` instead of a plain `rm -rf .butler`
(Requirement 6).

`REQUIREMENTS_BUTLER_PULL.md` is superseded in full by this switch (its
trim-guard/change-detection requirements manage a conflict class that no
longer exists); TASK-039 ("Conflict-free butler-pull with CLI upgrade",
Draft) is superseded for the same reason, except its CLI/MCP
version-sync concern (R7-R10), which is unrelated to the merge-conflict
problem and is tracked separately as TASK-055 (blocked on this task's
resolution).

## Branch
**Branch name:** `task/054-switch-butler-to-git-submodule`
**Switch/create:** `git checkout -b task/054-switch-butler-to-git-submodule`
**Make target:** `make branch-task f=TASK-054`

## Acceptance criteria (Gherkin)

- [ ] Scenario: adoption uses git submodule instead of git subtree
      Given a new or existing project adopting python-butler for the first
      time
      When following `README.md`'s adoption instructions
      Then the command run is `git submodule add <remote> .butler` (not
      `git subtree add`), and no `make butler-trim FORCE=1` step follows
- [ ] Scenario: butler-fetch/butler-pull move the submodule pointer, no merge
      Given a project with `.butler` already added as a git submodule
      When `make butler-fetch` or `make butler-pull` runs
      Then `.butler`'s submodule pointer advances to the latest commit on
      the tracked branch of the python-butler remote, no `git subtree pull`
      or tree-merge step runs, and the target prints the exact
      `git add .butler` / `git commit` follow-up instead of committing
      automatically
- [ ] Scenario: butler-check compares the submodule pointer, not .butler-version
      Given a project with `.butler` added as a git submodule
      When `make butler-check` runs
      Then it reports up-to-date or available-update status by comparing
      the submodule's currently-recorded commit against the latest commit
      on the remote's tracked branch
- [ ] Scenario: butler-trim and its guard logic are removed
      Given `.butler` is a git submodule
      When a project adopts butler or runs `make butler-pull`
      Then no trim step runs at any point, `.butler/templates/`,
      `.butler/claude-agents/`, and `.butler/claude-skills/` remain present
      in the working tree, and `make butler-trim` is no longer a defined
      Makefile target
- [ ] Scenario: generate-governance-files still copies claude-skills content
      Given `.butler/claude-skills/<name>/SKILL.md` exists (via the
      submodule checkout)
      When `make generate-governance-files FORCE=1` runs
      Then `.claude/skills/<name>/SKILL.md` is created, mirroring the
      existing `claude-agents/` → `.claude/agents/` copy, unchanged from
      today's subtree-based behavior
- [ ] Scenario: a documented migration path exists for subtree-based consumers
      Given a consumer project (e.g. `firefly-bills-analyzer`) currently
      using the subtree layout
      When following `README.md`'s migration section
      Then the documented manual steps convert `.butler` to a submodule
      pointer without rewriting the project's own git history, and update
      the `Makefile`'s `include .butler/Makefile` line if its path changed
- [ ] Scenario: butler-uninstall removes the submodule cleanly
      Given a project with `.butler` added as a git submodule
      When `make butler-uninstall CATEGORIES=subtree,...` runs
      Then `.butler` is removed via `git submodule deinit -f .butler` +
      `git rm -f .butler`, the corresponding `.gitmodules` entry is removed
      (and the file itself if it becomes empty), and no `.git/modules/.butler`
      metadata is left behind — not just a plain `rm -rf .butler`

## Out of scope

- Auto-migrating existing subtree-based consumer projects unattended — the
  migration path (Requirement 4 / the scenario above) is manual and
  documented, not scripted.
- Continuing to support git-subtree adoption as a documented, ongoing option
  alongside submodule — `README.md`'s adoption instructions are replaced,
  not duplicated; existing subtree consumers migrate via the documented
  path instead.
- CLI/MCP server reinstall-from-pulled-sources behavior — tracked
  separately in TASK-055 (blocked on this task's resolution).
- Rewriting or squashing the git history a prior `git subtree` merge already
  created in a consumer project.

## Blockers

- None

## Completion
**Date:** 2026-07-20
**Summary:** Switched `.butler` distribution from a `git subtree` to a `git submodule`.
`butler-fetch`/`butler-pull` now move `.butler`'s submodule pointer to the latest remote commit and
print the `git add .butler` / `git commit` follow-up instead of running `git subtree pull --squash`
and auto-committing; `butler-check` compares the submodule's recorded commit against the remote's
tracked branch instead of a `.butler-version` file. `butler-trim` and its TASK-048/051/053 guard
logic are removed entirely, along with the now-obsolete characterization tests that exercised them
(the retained `TestGenerateGovernanceFilesCopiesSkills` test in the same file still covers the
mechanism-independent `claude-skills` copy behavior). `butler-uninstall`'s `subtree` category now
runs `git submodule deinit -f .butler` + `git rm -f .butler`, removes any leftover
`.git/modules/.butler` metadata, and drops the `.gitmodules` entry (falling back to a plain
directory removal when `.butler` is not a registered submodule). `README.md`'s adoption,
update, and uninstall sections are updated accordingly, and a new manual migration section
documents converting an existing subtree-based consumer (e.g. `firefly-bills-analyzer`) to the
submodule layout. `REQUIREMENTS_BUTLER_PULL.md`'s supersession note is finalized (no longer
"pending confirmation").
**Files changed:** `Makefile`, `src/butler_core/data/Makefile`, `src/butler_core/uninstall.py`,
`README.md`, `REQUIREMENTS_SUBMODULE.md`, `REQUIREMENTS_BUTLER_PULL.md`, `CHANGELOG.md`,
`tests/test_butler_submodule.py`, `tests/test_uninstall.py`,
`tests/test_butler_pull_governance_regen.py`,
`docs/tasks/TASK-039-conflict-free-butler-pull.md`,
`docs/tasks/TASK-054-switch-butler-to-git-submodule.md`,
`docs/tasks/TASK-055-cli-mcp-version-sync-after-pull.md`
**Branch:** `git checkout task/054-switch-butler-to-git-submodule`
**Stage:** `Makefile src/butler_core/data/Makefile src/butler_core/uninstall.py README.md REQUIREMENTS_SUBMODULE.md REQUIREMENTS_BUTLER_PULL.md CHANGELOG.md tests/test_butler_submodule.py tests/test_uninstall.py tests/test_butler_pull_governance_regen.py docs/tasks/TASK-039-conflict-free-butler-pull.md docs/tasks/TASK-054-switch-butler-to-git-submodule.md docs/tasks/TASK-055-cli-mcp-version-sync-after-pull.md`
**Commit:** `fix(TASK-054): switch .butler distribution from git subtree to git submodule`
