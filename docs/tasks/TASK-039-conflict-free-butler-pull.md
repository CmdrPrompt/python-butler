# TASK-039: Conflict-free butler-pull

## Status

Draft

## Background

`make butler-trim` deletes everything in `.butler/` except `Makefile`. When upstream
python-butler later modifies any of the trimmed files, `make butler-pull` runs
`git subtree pull --squash` against a working tree where those files no longer exist.
Git reports modify/delete conflicts, the merge fails, and the user must resolve it
manually:

```
Automatic merge failed; fix conflicts and then commit the result.
make: *** [butler-pull] Error 1
```

This is structural, not incidental. Every consumer project that has trimmed will hit
it on every update that touches a trimmed file.

## Goal

`make butler-pull` shall complete without merge conflicts in a project that has
previously run `make butler-trim`, provided the user has not made local edits
inside `.butler/`.

## Approach

Restore trimmed files before pulling, so the working tree matches the subtree
history and the merge applies cleanly:

1. Locate the most recent subtree squash commit for prefix `.butler`
   (e.g. `git log --grep='git-subtree-dir: .butler' -1 --format=%H`).
2. Restore `.butler/` from that commit and commit the restore
   (skip the commit if nothing changed).
3. Run `git subtree pull --prefix=.butler <BUTLER_REPO_URL> <BUTLER_BRANCH> --squash`.
4. Run the existing trim logic (reuse `butler-trim`).
5. Update `.butler-version` as today.

Reuse: `butler-fetch` already restores butler sources. Extract the restore step into
a shared internal target (e.g. `_butler-restore`) used by both `butler-fetch` and
`butler-pull`.

## Requirements

- R1: When `.butler/` has been trimmed and upstream has modified trimmed files,
  `make butler-pull` shall complete with exit code 0 and no merge conflicts.
- R2: After `make butler-pull`, `.butler/` shall contain only `Makefile`
  (trimmed state), and `.butler-version` shall contain the new upstream version.
- R3: If the user has uncommitted changes inside `.butler/`, `butler-pull` shall
  abort with a clear error message before touching the working tree.
- R4: If no prior subtree squash commit for `.butler` exists, `butler-pull` shall
  abort with an error instructing the user to run `git subtree add` first.
- R5: The restore step shall not modify any files outside `.butler/`.
- R6: `butler-fetch` behavior shall remain unchanged from the user's perspective.

## Acceptance criteria

- AC1: In a test repo: subtree add, trim, commit. Simulate an upstream change to a
  trimmed file (e.g. a template). Run `make butler-pull`. Expect: exit 0, no
  conflict markers, `.butler/` trimmed, `.butler-version` updated.
- AC2: Run `make butler-pull` twice in a row. Second run reports "already up to
  date" (or equivalent) and exits 0 without creating empty commits.
- AC3: Dirty `.butler/Makefile` in working tree, run `make butler-pull`. Expect:
  non-zero exit and an error message naming the dirty path, working tree untouched.
- AC4: Fresh repo without any subtree history, run `make butler-pull`. Expect:
  non-zero exit with guidance to run `git subtree add`.
- AC5: `make butler-check` still works unchanged after the refactor.

## Out of scope

- Auto-resolving genuine content conflicts caused by local edits to `.butler/`
  files (R3 makes these fail fast instead).
- Migrating away from git subtree.

## Notes

- Test setup can use a local bare repo as upstream to avoid network access in tests.
- Update `README.md` section "Keeping butler up to date" if the user-facing
  workflow changes (it should not, per R6/Goal).
- Add a CHANGELOG.md entry.