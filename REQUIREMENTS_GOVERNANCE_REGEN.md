# Requirements: `generate-governance-files FORCE=1` must not clobber project identity

## Context

`make generate-governance-files` writes `CLAUDE.md` and
`.github/copilot-instructions.md` from `templates/CLAUDE.md.tmpl` and
`templates/copilot-instructions.md.tmpl`, substituting the `PROJECT_NAME`
and `PROJECT_DESCRIPTION` Make variables
(`src/butler_core/data/Makefile:13-14`). Those variables default to the
placeholders `my-project` and `Describe your project here.` and are only
ever set to the real project's values once, interactively, during
`make init-project`. Nothing persists that answer anywhere on disk — not in
a config file, not read back from the existing `CLAUDE.md`.

`FORCE=1` is the documented, and now the *only* practical, way to refresh an
already-adopted project's governance files after `butler-pull` brings in
template/agent/skill changes (see `REQUIREMENTS_BUTLER_PULL.md`
Requirement 1's use case, and BDD-051). That invocation
(`make generate-governance-files FORCE=1`) never passes `PROJECT_NAME=`/
`PROJECT_DESCRIPTION=`, so the Makefile silently falls back to the
placeholder defaults and overwrites the real project name and description
in `CLAUDE.md` and `.github/copilot-instructions.md` with generic
placeholder text — destroying project-specific content with no warning and
no diff shown. This has been observed in multiple consumer repos (most
recently `firefly-python-api`, 2026-08-02), recovered only because the
previous file content was still visible in `git diff` before commit.

## Goals

1. `make generate-governance-files FORCE=1`, run on a project that already
   has a `CLAUDE.md` from a prior generation, MUST NOT silently replace a
   real project name/description with the placeholder defaults.
2. The fix must work for the common case where the operator does not
   re-pass `PROJECT_NAME=`/`PROJECT_DESCRIPTION=` on every regeneration —
   that is the normal `butler-pull` → `generate-governance-files FORCE=1`
   flow today and MUST keep working without extra required flags.

## Non-goals

- Changing what other template variables `generate-governance-files`
  substitutes, or the substitution mechanism itself.
- Persisting arbitrary CLAUDE.md customizations beyond the project
  name/description line — free-form edits elsewhere in the file are already
  known to be overwritten by regeneration and are out of scope here.
- Changing `init-project`'s interactive prompt flow.

## Requirement 1: Preserve existing project name/description across regeneration

**Description:** WHEN `generate-governance-files` runs with `FORCE=1` AND an
existing `CLAUDE.md` is present AND the caller did not explicitly pass
`PROJECT_NAME=`/`PROJECT_DESCRIPTION=` on the command line, THEN the
generator SHALL extract the current project name and description from the
existing `CLAUDE.md` (its `# <name>` H1 and the paragraph immediately below
it) and use those values instead of the `my-project`/`Describe your project
here.` Makefile defaults.

**Use case:**

```bash
$ cat CLAUDE.md
# firefly-python-api

Python client library for the Firefly III REST API...

$ make generate-governance-files FORCE=1
✓ Generated CLAUDE.md, .github/copilot-instructions.md, .github/agents/, .claude/agents/, and .claude/skills/
$ head -3 CLAUDE.md
# firefly-python-api

Python client library for the Firefly III REST API...
```

## Requirement 2: Explicit override still works

**Description:** WHEN the caller explicitly passes `PROJECT_NAME=`/
`PROJECT_DESCRIPTION=` to `make generate-governance-files FORCE=1`, THEN
those explicit values SHALL take precedence over both the Makefile defaults
and any value extracted from an existing `CLAUDE.md` per Requirement 1.

**Use case:**

```bash
$ make generate-governance-files FORCE=1 PROJECT_NAME="renamed-project" PROJECT_DESCRIPTION="New description."
$ head -3 CLAUDE.md
# renamed-project

New description.
```

## Requirement 3: First-time generation is unaffected

**Description:** WHEN no `CLAUDE.md` exists yet (first-time
`generate-governance-files`, with or without `FORCE=1`), THEN the generator
SHALL behave exactly as it does today — using the `PROJECT_NAME`/
`PROJECT_DESCRIPTION` values passed on the command line (as `init-project`
does), falling back to the Makefile placeholder defaults if none are given.
This requirement is unaffected by Requirement 1, which only applies when an
existing `CLAUDE.md` is present.

## Acceptance criteria (overall)

- [ ] Regenerating governance files with `FORCE=1` and no explicit
      `PROJECT_NAME=`/`PROJECT_DESCRIPTION=`, against a project whose
      `CLAUDE.md` already has a real name/description, leaves that
      name/description unchanged in both `CLAUDE.md` and
      `.github/copilot-instructions.md`.
- [ ] Passing `PROJECT_NAME=`/`PROJECT_DESCRIPTION=` explicitly still
      overrides whatever `CLAUDE.md` currently contains.
- [ ] First-time generation (no prior `CLAUDE.md`) is bit-for-bit unchanged
      from current behavior.
