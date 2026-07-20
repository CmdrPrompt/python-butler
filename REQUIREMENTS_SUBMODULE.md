# Requirements: Switch `.butler` distribution from git subtree to git submodule

## Status

Confirmed — implemented by TASK-054.

## Context

python-butler is currently distributed into a consumer project via
`git subtree add --prefix=.butler ...`, followed by `make butler-trim`, which
deletes everything under `.butler/` except `Makefile`. Because a subtree
merges butler's full upstream tree into the consumer's own git history on
every `butler-pull`, and the trim has already deleted files a later pull
tries to modify, `git subtree pull` structurally produces modify/delete merge
conflicts — not an edge case, but the expected outcome of trimming at all.
TASK-048, TASK-051, and TASK-053 hardened the trim/pull guard logic around
this so it at least never silently destroys un-regenerated content, but none
of that prevents the conflict itself; the consumer still has to hand-resolve
or abort the merge (reproduced again in `firefly-bills-analyzer`,
2026-07-20).

A git submodule stores `.butler` as a single pointer (a commit hash recorded
in `.gitmodules`/the gitlink tree entry) to the python-butler repo, rather
than merging its content into the consumer's own history. Updating means
moving that pointer and committing a one-line change in the superproject —
there is no tree merge against the consumer's own history, so the
modify/delete conflict class described above cannot occur structurally.

This document defines the requirements for that switch. It supersedes the
subtree-specific requirements below, which describe behavior that stops
applying once `.butler` is a submodule.

## Goals

1. Adopt `.butler` as a git submodule pointing at the python-butler repo,
   replacing `git subtree add`.
2. Replace `butler-fetch`/`butler-pull`/`butler-check`'s subtree-based
   implementation with submodule-native equivalents that move and commit the
   pointer, with no tree merge into the consumer's history.
3. Retire `butler-trim`. Its sole purpose was to keep the subtree-merged
   file tree out of the consumer's own git history and avoid the resulting
   modify/delete conflicts on the next pull — both are solved structurally
   by the submodule mechanism itself (the superproject only ever records a
   gitlink + `.gitmodules` entry, never butler's file tree). The remaining
   effect of trim, a smaller `.butler/` working-tree footprint, is a minor,
   separate disk-space concern not worth a bespoke rm-based script; if it
   ever matters, the correct tool is a submodule sparse-checkout, not a
   revival of `butler-trim`.
4. Give existing subtree-based consumer projects (e.g.
   `firefly-bills-analyzer`) a documented, one-time migration path to
   submodule.
5. Update `README.md`'s adoption and "keeping butler up to date" instructions
   to the submodule-based commands.

## Non-goals

- Auto-migrating existing subtree-based consumers unattended. Whether a
  migration script is provided at all, or only documented manual steps, is
  TBD (see TASK-054 Out of scope).
- Continuing to support subtree mode indefinitely alongside submodule. TBD
  whether subtree support is removed outright or kept as a legacy path (see
  TASK-054 Out of scope).
- Changing what `generate-governance-files` reads from or how it substitutes
  template variables — unaffected by the distribution mechanism.
- CLI/MCP server reinstall-from-pulled-sources behavior (TASK-039 R7–R10).
  This is a distinct concern from the distribution-mechanism switch and is
  tracked separately in TASK-055, not resolved by this document.

## Deprecations

Switching to submodule invalidates or requires revision of requirements
written specifically for subtree's failure modes. Recorded here so nothing
is silently left in an inconsistent state:

- **`REQUIREMENTS_BUTLER_PULL.md` — superseded in full.** Its four
  requirements (change-detection before an automatic trim, `make help`
  wording, `claude-skills`/`claude-agents` copy symmetry, and the
  `butler-trim` un-regenerated-content guard) all exist to manage the
  subtree-pull → trim → next-subtree-pull conflict cycle. A submodule update
  is a pointer move with no merge step, so there is no "trim ran before
  regeneration" race and no "modify/delete conflict recovery path" to guard.
  Requirement 3's `generate-governance-files` copy behavior
  (`.butler/claude-skills/*/SKILL.md` → `.claude/skills/`) is the only part
  that is mechanism-independent and must be preserved — carried forward here
  as Requirement 5.
- **TASK-039 (`docs/tasks/TASK-039-conflict-free-butler-pull.md`, Status:
  Draft) — superseded, not deleted.** Its restore-before-pull /
  CLI-reinstall approach solves the same subtree modify/delete conflict by
  working around it; a submodule has no such conflict class, making TASK-039's
  entire approach unnecessary if this task ships. Its R7–R10 (CLI reinstall
  from pulled sources after a pull) are the one part not specific to subtree
  and are tracked separately in TASK-055, not resolved by this document.
  Recommend the Workflow Guardian re-file TASK-039's Status as
  `blocked`/superseded-pending-TASK-054 rather than leaving it `Draft`, since
  only the Guardian owns Status transitions.
- **`REQUIREMENTS_UNINSTALL.md` Requirement 1 — not superseded, but its
  `subtree` category is now inaccurate and must be updated**, not deprecated:
  the category currently documents removal as "the `.butler/` directory"
  (`rm -rf .butler`); under a submodule this must become `git submodule
  deinit -f .butler`, removing the `.gitmodules` entry and the
  `.git/modules/.butler` metadata, then `git rm -f .butler` — a plain `rm -rf
  .butler` leaves `.gitmodules` and submodule metadata behind. Whether the
  category keeps the name `subtree` (for backward CLI/script compatibility)
  or is renamed `submodule` is TBD — flagged for user decision, not resolved
  by this document.

## Requirement 1: Adoption uses `git submodule add`

**Description:** The README's "Adding butler to a new project" and "Adding
butler to an existing project" sections MUST replace
`git subtree add --prefix=.butler <remote> main --squash` with
`git submodule add <remote> .butler`, and the subsequent
`make butler-trim FORCE=1` step MUST be replaced per Requirement 3 below.

## Requirement 2: `butler-fetch`/`butler-pull`/`butler-check` become pointer-move operations

**Description:** `butler-fetch` and `butler-pull` MUST update `.butler` by
advancing the submodule pointer (`git submodule update --remote .butler` or
equivalent), rather than running `git subtree pull --squash`. Neither target
commits the resulting gitlink change automatically — consistent with every
other Makefile target that changes tracked state (e.g. `butler-trim` today),
the target prints the exact `git add .butler` / `git commit` follow-up and
leaves committing to the user. `butler-check` MUST compare
the submodule's currently-recorded commit against the latest commit on the
tracked branch of the python-butler remote (instead of comparing
`.butler-version` against `git ls-remote`, which may become redundant once
the submodule pointer itself is the version record — TBD whether
`.butler-version` is kept for backward compatibility or retired in favor of
`git submodule status`).

**Use case:**

```bash
$ make butler-check
Checking for butler updates...
Updates available.
  Current: <submodule pointer commit>
  Latest:  <remote main HEAD>
  Run: make butler-pull

$ make butler-pull
Updating .butler submodule pointer ...
✓ .butler now at <new commit>. Commit this pointer change:
  git add .butler
  git commit -m "chore: update butler submodule"
```

## Requirement 3: `butler-trim` is retired

**Description:** `make butler-trim` and its guard logic (TASK-048, TASK-051,
TASK-053) MUST be removed. A consumer project's working tree keeps the full
`.butler` checkout as an ordinary submodule — `Makefile`, `templates/`,
`claude-agents/`, `claude-skills/`, and any other butler sources — with no
deletion step after adoption or after a pull.

The `.butler/templates/`, `.butler/claude-agents/`, and
`.butler/claude-skills/` change-detection and `generate-governance-files`
invocation described in Requirement 5 still apply: those consumer-facing
files must still be read and copied out into the consumer's own governance
files after a `butler-pull` moves the pointer, since they remain the
mechanism by which butler's templates/agents/skills reach a consumer's
`CLAUDE.md`/`.github/agents/`/`.claude/agents/`/`.claude/skills/`. What
changes is only that this can now happen at any time after a pull, on the
consumer's own schedule — there is no trim step racing to delete the source
content first.

## Requirement 4: Migration path for existing subtree consumers

**Description:** A documented (manual, per Non-goals) procedure MUST exist
for a consumer project currently using the subtree layout (e.g.
`firefly-bills-analyzer`) to convert to the submodule layout without losing
its own project history. At minimum this covers: removing the subtree's
merged history is out of scope (git history is append-only and not rewritten
by this task — see Non-goals), but converting the *current* `.butler`
working-tree state to a submodule pointer, updating the `Makefile`'s
`include .butler/Makefile` line if its path changes, and re-running
`generate-governance-files` if needed.

CLI/MCP server version-sync (TASK-039 R7–R10) is explicitly out of scope
here (see Non-goals) and tracked as its own task, TASK-055, since it is
orthogonal to the distribution-mechanism switch and submodule changes the
shape of its best fix (an editable install becomes viable once `.butler`'s
sources are no longer trimmed away, which TASK-039 R9 had ruled out for
exactly the opposite reason).

## Requirement 5: `claude-skills`/`claude-agents` generation is preserved, mechanism-independent

**Description:** Carried forward unchanged from
`REQUIREMENTS_BUTLER_PULL.md` Requirement 3, since it is not
subtree-specific: `generate-governance-files` MUST copy
`.butler/claude-skills/*/SKILL.md` into a consumer project's
`.claude/skills/`, mirroring the existing
`cp .butler/claude-agents/*.agent.md .claude/agents/` step, regardless of
whether `.butler` is a subtree or a submodule.

## Requirement 6: `REQUIREMENTS_UNINSTALL.md`'s `subtree` category is corrected

**Description:** `make butler-uninstall CATEGORIES=subtree,...` (or its
renamed equivalent, per the Deprecations section) MUST remove the submodule
correctly: `git submodule deinit -f .butler`, then `git rm -f .butler`, then
remove the corresponding entry from `.gitmodules` (and `.gitmodules` itself
if it becomes empty) — not a plain `rm -rf .butler`, which leaves
`.gitmodules` and `.git/modules/.butler` metadata behind.

## Acceptance criteria (overall)

- [x] Confirmed by the user (TASK-054).
- [x] `README.md`'s adoption sections use `git submodule add`.
- [x] `butler-fetch`/`butler-pull`/`butler-check` operate on the submodule
      pointer with no subtree merge.
- [x] `butler-trim` and its guard logic are removed; `.butler` is left as a
      full, untrimmed submodule checkout after adoption and after every
      pull.
- [x] A documented migration procedure exists for subtree → submodule
      conversion in an existing consumer project.
- [x] `generate-governance-files` still copies `.butler/claude-skills/*/SKILL.md`
      into `.claude/skills/`.
- [x] `make butler-uninstall` removes the submodule cleanly (`.gitmodules`
      and `.git/modules/.butler` included), not just `.butler/`.
- [x] `REQUIREMENTS_BUTLER_PULL.md` is marked superseded (not deleted) and
      points here.
- [ ] TASK-039's status is revisited by the Workflow Guardian in light of
      this document. (Not implementation-worker's to change — flagged for
      the Guardian; see the note added to `TASK-039-conflict-free-butler-pull.md`.)
- [x] `CHANGELOG.md` updated with a behavior-first entry.
- [x] `make lint && make test` pass.
