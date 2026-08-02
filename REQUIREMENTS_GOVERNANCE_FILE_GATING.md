# Requirements: `generate-governance-files` must gate each output file independently

## Context

`generate-governance-files` (`src/butler_core/data/Makefile:457-498`) starts
with two existence checks before writing anything:

```make
@[ ! -f CLAUDE.md ] || [ "$(FORCE)" = "1" ] || \
    (echo "CLAUDE.md already exists. Run with FORCE=1 to overwrite."; exit 1)
@[ ! -f .github/copilot-instructions.md ] || [ "$(FORCE)" = "1" ] || \
    (echo ".github/copilot-instructions.md already exists. Run with FORCE=1 to overwrite."; exit 1)
```

Both checks must pass before the recipe reaches the line that actually
writes `CLAUDE.md` (`src/butler_core/data/Makefile:468`). If
`.github/copilot-instructions.md` already exists but `CLAUDE.md` does not
(observed 2026-08-02 in `firefly-household-splitter`, after a first
`make init-project` run partially completed — `.github/`,
`.gitignore`, and `.pre-commit-config.yaml` were generated but `CLAUDE.md`
was not, likely from an earlier interrupted or FORCE-less invocation), the
second check aborts the whole recipe with exit code 1 before `CLAUDE.md` is
ever created. Every subsequent run hits the exact same abort: `CLAUDE.md`'s
own check keeps passing (the file still doesn't exist) while
`copilot-instructions.md`'s check keeps failing, so the project is stuck
unable to generate `CLAUDE.md` without also passing `FORCE=1` (which
additionally overwrites `copilot-instructions.md`, `.gitignore`, and
`.pre-commit-config.yaml`, even though only `CLAUDE.md` was actually
missing).

`make init-project` prints a `git add CLAUDE.md ...` follow-up
(`src/butler_core/data/Makefile:378`) regardless of whether generation
actually succeeded, so the operator sees no error until `git add` reports
`pathspec 'CLAUDE.md' did not match any files`.

## Goals

1. A missing output file must be generated even when a sibling output file
   already exists, without requiring `FORCE=1`.
2. `FORCE=1` must remain required to overwrite a file that already exists.
3. The `git add`/commit instructions printed at the end of `init-project`
   must only be shown when generation actually succeeded.

## Non-goals

- Changing what `FORCE=1` overwrites once all guarded files already exist.
- Deduplicating the guard-and-generate pattern across `generate-pyproject`,
  `generate-gitignore`, `generate-pre-commit-config` (each already gates
  independently on its own single file; only the multi-file
  `generate-governance-files` mixes two files behind one shared check).

## Requirement 1: Each guarded output file gates only on its own existence

**Description:** WHEN `generate-governance-files` runs AND one guarded output
file (e.g. `.github/copilot-instructions.md`) already exists on disk without
`FORCE=1`, THEN the generator SHALL still write any other guarded output
file (e.g. `CLAUDE.md`) that does not yet exist, and SHALL only skip/refuse
the file(s) that already exist.

**Use case:**

```bash
$ ls
.github/copilot-instructions.md  .gitignore  .pre-commit-config.yaml
$ make generate-governance-files
.github/copilot-instructions.md already exists. Run with FORCE=1 to overwrite.
✓ Generated CLAUDE.md, .github/agents/, .claude/agents/, and .claude/skills/
$ ls CLAUDE.md
CLAUDE.md
```

## Requirement 2: Existing files are still protected without FORCE=1

**Description:** WHEN a guarded output file already exists AND `FORCE=1` is
not passed, THEN the generator SHALL leave that specific file untouched and
SHALL report that it was skipped, per current behavior for
`generate-pyproject`/`generate-gitignore`/`generate-pre-commit-config`.

**Use case:**

```bash
$ make generate-governance-files
.github/copilot-instructions.md already exists. Run with FORCE=1 to overwrite.
✓ Generated CLAUDE.md, .github/agents/, .claude/agents/, and .claude/skills/
$ diff .github/copilot-instructions.md <(git show HEAD:.github/copilot-instructions.md)
```

(no output — file unchanged)

## Requirement 3: `init-project`'s success message reflects actual outcome

**Description:** WHEN any file `init-project` lists in its final `git add`
instructions was not actually generated (skipped due to an existing-file
guard, or failed), THEN `init-project` SHALL NOT print that file in the
"✓ Done. Stage and commit with" instructions as if it were freshly created.

**Use case:**

```bash
$ make init-project
.github/copilot-instructions.md already exists. Run with FORCE=1 to overwrite.
✓ Generated CLAUDE.md, .github/agents/, .claude/agents/, and .claude/skills/
...
✓ Done. Stage and commit with:

  git add CLAUDE.md .github/ .claude/
  git commit -m "Bootstrap project with python-butler"
```

## Acceptance criteria (overall)

- [ ] Running `generate-governance-files` (no `FORCE=1`) with
      `.github/copilot-instructions.md` present but `CLAUDE.md` absent
      creates `CLAUDE.md` and leaves `copilot-instructions.md` untouched.
- [ ] Running it again afterwards (both files now present) makes no changes
      and reports both as already existing.
- [ ] `init-project`'s final instructions list only files that were
      actually written during that run.
