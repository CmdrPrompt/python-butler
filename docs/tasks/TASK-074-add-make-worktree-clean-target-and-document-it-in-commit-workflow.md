# TASK-074 Add `make worktree-clean` target and document it in commit-workflow

## Status
todo

## Requirements
**Binding:** Requirement 12 (REQUIREMENTS_TASK_WORKFLOW.md)
**BDD mode:** BDD-ABSENT (Makefile target + skill doc change; behavior is
already fully specified by Requirement 12's Description/Use case, and this
task's own Gherkin scenarios below cover it)
**Depends on:** None
**Precedence:** The requirements document is the binding definition of this
task. The story below is derived from it. On any discrepancy, the
requirements document wins. Stop and report discrepancies; do not build
from the story.

## Story (context, not binding)
As Workflow Guardian (or anyone following the `commit-workflow` skill's
worktree-merge procedure), I want a `make worktree-clean b=<branch>`
target to run after a successful `commit-current-task`, so that a
subagent's isolated worktree and its temporary branch are removed instead
of accumulating indefinitely in `.claude/worktrees/` — confirmed live in
this repo, which had 11 stale worktrees left over from past sessions with
no cleanup step ever run.

## Description
**Implementation:** Add a `worktree-clean` target to the Makefile:

```makefile
worktree-clean:
	@[ -n "$(b)" ] || (echo "Usage: make worktree-clean b=<branch-name>"; exit 1)
	@path=$$(git worktree list --porcelain | awk -v b="refs/heads/$(b)" '/^worktree /{p=$$2} /^branch /{if ($$2==b){print p; exit}}'); \
	if [ -z "$$path" ]; then echo "No worktree found for branch $(b)"; exit 1; fi; \
	git worktree remove --force "$$path" && git branch -D $(b)
```

Resolves the worktree path for `<branch>` from `git worktree list
--porcelain` (matching on `refs/heads/<branch>`, since `--porcelain` prints
worktree/branch pairs in adjacent `worktree <path>`/`branch
refs/heads/<name>` lines), then removes the worktree and deletes the
branch. `--force` on `git worktree remove` is safe here since the
branch's content was already squash-merged into the current branch's
staging area by the prior `merge-worktree` step — nothing of value is lost.
Add `worktree-clean` to `.PHONY` and the `make help` listing.

**Documentation:** Update `.claude/skills/commit-workflow/SKILL.md`'s
"Merging a worktree branch" section to add a step 3: run `make
worktree-clean b=<branch>` after `commit-current-task` succeeds. Per
Requirement 12, this step MUST NOT be folded into `merge-worktree` itself
(preserves the recovery path if the squash or commit step fails).

**Implementation location:** `Makefile`,
`.claude/skills/commit-workflow/SKILL.md`,
`templates/commit-workflow/SKILL.md.tmpl` if a separate template copy
exists (check `.claude/skills/` vs `templates/` sync convention used by
prior skill changes, e.g. TASK-050/TASK-051), `tests/test_worktree_clean.py`.

## Branch
**Branch name:** `task/074-add-make-worktree-clean-target-and-document-it-in-commit-workflow`
**Switch/create:** `git checkout -b task/074-add-make-worktree-clean-target-and-document-it-in-commit-workflow`
**Make target:** `make branch-task f=TASK-074`

## Acceptance criteria (Gherkin)

- [ ] Scenario: `make worktree-clean` removes a real worktree and its branch
      Given a git repository with a worktree checked out on branch
      `worktree-agent-test` (via `git worktree add`)
      When `make worktree-clean b=worktree-agent-test` is run from the
      repository root
      Then `git worktree list` no longer lists that worktree's path, and
      `git branch` no longer lists `worktree-agent-test`

- [ ] Scenario: A missing `b=` argument fails with a usage message
      Given no `b=` argument is supplied
      When `make worktree-clean` is run
      Then it fails with a "Usage: make worktree-clean b=&lt;branch-name&gt;"
      message, matching every other `b=`/`f=`-argument target's pattern
      (e.g. `merge-worktree`)

- [ ] Scenario: `worktree-clean` is documented as a separate post-commit step
      Given `.claude/skills/commit-workflow/SKILL.md`'s "Merging a worktree
      branch" section
      When it is read
      Then it lists `make worktree-clean b=<branch>` as a step run after
      `make commit-current-task` succeeds, not folded into `merge-worktree`

- [ ] `make lint && make test` pass, with coverage not below the
      task-start baseline

- [ ] CHANGELOG.md updated

## Out of scope
- Actually cleaning up the 11 stale worktrees already present in this
  repo's `.claude/worktrees/` — a one-off manual cleanup, not part of this
  task's automated behavior (may be done separately, with explicit
  confirmation, since it's a destructive operation on existing state).
- Automatically running `worktree-clean` as part of `merge-worktree` or
  any other existing target — Requirement 12 explicitly requires it stay a
  separate, manually-sequenced step.
- Any change to how subagents are spawned (`isolation: "worktree"`) or how
  `merge-worktree`'s squash-merge itself works.

## Blockers
None

## Completion
**Date:**
**Summary:**
**Files changed:**
**Branch:** `git checkout task/074-add-make-worktree-clean-target-and-document-it-in-commit-workflow`
**Stage:** `git add Makefile .claude/skills/commit-workflow/SKILL.md tests/test_worktree_clean.py REQUIREMENTS_TASK_WORKFLOW.md CHANGELOG.md docs/tasks/TASK-074-add-make-worktree-clean-target-and-document-it-in-commit-workflow.md`
**Commit:** `git commit -m "Add make worktree-clean target and document it in commit-workflow"`
