# TASK-015 Add butler-trim, butler-add, and butler-pull targets

## Status
done

## Description

When a project adopts python-butler via `git subtree add --prefix=.butler`, the
entire butler repo lands in `.butler/`. That includes files that only exist to
manage the butler project itself — docs, changelog, .gitignore, .claude/ — none
of which serve any purpose in an adopting project. Committing them is unnecessary
noise in the adopting repo's history.

This task adds three Makefile targets so adopters can keep `.butler/` lean:

- **`butler-trim`** — removes butler-internal files from `.butler/` using
  `git rm -r --ignore-unmatch`, leaving only what is functionally required.
- **`butler-add`** — convenience wrapper: runs `git subtree add` followed by
  `butler-trim`, then prints suggested staging/commit commands.
- **`butler-pull`** — convenience wrapper: runs `git subtree pull` followed by
  `butler-trim`, then prints suggested staging/commit commands.

Files removed by `butler-trim`:
- `.butler/.claude/` — butler's dev-agent definitions and local settings
- `.butler/.gitignore` — butler's own gitignore (can conflict with project's)
- `.butler/CHANGELOG.md` — butler's release notes
- `.butler/docs/` — butler's tasks and internal documentation
- `.butler/README.md` — butler's README

Files kept in `.butler/` (functionally required):
- `.butler/Makefile`
- `.butler/templates/`
- `.butler/scaffold/`

## Branch
**Branch name:** `task/015-butler-trim-target`
**Switch/create:** `git checkout -b task/015-butler-trim-target`
**Make target:** `make branch-task f=TASK-015`

## Acceptance criteria

- [ ] `make butler-trim` removes `.butler/.claude/`, `.butler/.gitignore`,
  `.butler/CHANGELOG.md`, `.butler/docs/`, `.butler/README.md` via
  `git rm -r --ignore-unmatch` (idempotent: safe to run twice)
- [ ] `make butler-add` runs `git subtree add --prefix=.butler $(BUTLER_REMOTE) main --squash`
  then calls `butler-trim` and prints suggested git commands
- [ ] `make butler-pull` runs `git subtree pull --prefix=.butler $(BUTLER_REMOTE) main --squash`
  then calls `butler-trim` and prints suggested git commands
- [ ] `BUTLER_REMOTE` defaults to `https://github.com/CmdrPrompt/python-butler.git`
  and can be overridden by the caller
- [ ] README adoption guide is updated to show `make butler-add` instead of the
  manual `git subtree add` command, with a note about `make butler-pull` for updates
- [ ] `make lint && make test` pass in the butler repo

## Completion
**Date:** 2026-04-30
**Summary:** Added `butler-trim` and `butler-pull` targets to Makefile. Moved Claude Code agent source files from `.claude/agents/` to `claude-agents/` so `.claude/` can be safely trimmed. Updated `generate-governance-files` to use new path. Updated README adoption guide and CHANGELOG.
**Files changed:** `Makefile`, `claude-agents/` (new directory, 7 files), `README.md`, `CHANGELOG.md`, `docs/tasks/TASK-015-butler-trim-target.md`
**Branch:** `task/015-butler-trim-target`
**Stage:** `git add Makefile claude-agents/ README.md CHANGELOG.md docs/tasks/TASK-015-butler-trim-target.md`
**Commit:** `git commit -m "Add butler-trim and butler-pull targets; move Claude agents to claude-agents/ (TASK-015)"`
