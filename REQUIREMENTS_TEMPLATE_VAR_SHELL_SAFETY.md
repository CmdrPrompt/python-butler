# Requirements: template variable substitution must tolerate shell-special characters

## Context

`generate-pyproject`, `generate-governance-files`, and every other
`generate-*` target build a `sed` command line by letting Make expand
`$(PROJECT_NAME)` / `$(PROJECT_DESCRIPTION)` (and the other template
variables) directly inside a single-quoted `sed -e 's|...|...|g'` argument,
e.g. (`src/butler_core/data/Makefile:84-89`):

```make
@sed \
    -e 's|{{PROJECT_NAME}}|$(PROJECT_NAME)|g' \
    -e 's|{{PROJECT_DESCRIPTION}}|$(PROJECT_DESCRIPTION)|g' \
    ...
    .butler/scaffold/pyproject.toml.tmpl > pyproject.toml
```

Make performs this expansion as plain text substitution before the line is
handed to `/bin/sh -c`. Any single quote (`'`) inside the description text
closes the enclosing `'...'` shell string early; the remainder of the value
is then parsed as shell syntax instead of literal text.

Reproduced 2026-08-02 in `firefly-household-splitter`: running
`make init-project` with the project description `Computes how household
members should split a shared cost base. Reads the CSV/JSON export from
firefly-bills-analyzer, buckets each recurring payment by source account,
and reports each member's monthly transfer to the shared account under
equal-remainder and proportional splits.` (containing `member's`) produced:

```text
/bin/sh: -c: line 0: unexpected EOF while looking for matching `''
/bin/sh: -c: line 1: syntax error: unexpected end of file
make[1]: *** [generate-pyproject] Error 2
```

`generate-pyproject` aborted before writing `pyproject.toml`, with no
indication to the operator that the description text itself was the cause.
The same unescaped-expansion pattern applies everywhere `PROJECT_NAME` /
`PROJECT_DESCRIPTION` (or any other free-text template variable) is
substituted via `sed` inside a Make recipe.

**Re-run with `FORCE=1` is worse than a clean abort.** Because
`init-project`'s recipe body is one continuous `\`-joined shell script that
also invokes `generate-governance-files`, `generate-pyproject`,
`generate-gitignore`, and `generate-pre-commit-config` as nested `$(MAKE)`
calls within that same script, the unterminated quote from the apostrophe
does not stay contained to the one `sed` call that introduced it — it
desynchronizes quote-parsing for the rest of the script. Reproduced
2026-08-02, second attempt, `make init-project FORCE=1`: the run produced
`sed: unescaped newline inside substitute pattern`, then treated leftover
template tokens and substituted values as bare commands
(`{{BUG_TRIAGE_NAME}}: command not found`, `Bug: command not found`,
`Computes: command not found`, `docs/Requirements_Firefly-Household-Splitter.md:
Permission denied`), and ended with `make[2]: *** [help] Broken pipe` /
`make[1]: *** [generate-governance-files] Error 127`. `CLAUDE.md` was still
never created. A previously-tracked root file
(`Requirements_Firefly-Household-Splitter.md`) also ended up deleted from
the working tree, most likely as a side effect of a redirection target
shifting once quote-parsing desynchronized — i.e. the corruption is not
confined to producing wrong/garbled output, it can affect files unrelated to
the ones `generate-*` is supposed to touch.

## Goals

1. A `PROJECT_NAME` or `PROJECT_DESCRIPTION` value containing a single
   quote must not break the shell command that substitutes it.
2. The fix must not require the operator to pre-escape or avoid certain
   punctuation when answering `init-project`'s interactive prompts.

## Non-goals

- Handling arbitrary binary/control characters or multi-line values in
  `PROJECT_NAME`/`PROJECT_DESCRIPTION` — plain punctuation-bearing English
  prose is the bar.
- Changing the `sed`-based substitution mechanism itself, beyond how the
  variable's value is passed into it.

## Requirement 1: Single quotes in template variable values do not break generation

**Description:** WHEN `PROJECT_NAME` or `PROJECT_DESCRIPTION` contains one or
more single-quote (`'`) characters, THEN every `generate-*` target that
substitutes it (`generate-pyproject`, `generate-governance-files`, and any
other target substituting free-text template variables) SHALL complete
successfully and SHALL write the value into the output file verbatim,
including the single quote(s).

**Use case:**

```bash
$ make init-project
Project description [Describe your project here.]: Tracks each member's monthly share.
...
✓ Generated pyproject.toml
$ grep description pyproject.toml
description = "Tracks each member's monthly share."
```

## Acceptance criteria (overall)

- [ ] `make generate-pyproject PROJECT_DESCRIPTION="Tracks each member's
      monthly share."` exits 0 and `pyproject.toml` contains the
      description verbatim, apostrophe included.
- [ ] `make generate-governance-files PROJECT_DESCRIPTION="Tracks each
      member's monthly share."` exits 0 and `CLAUDE.md` /
      `.github/copilot-instructions.md` contain the description verbatim.
- [ ] A `PROJECT_DESCRIPTION` without special characters continues to
      produce byte-identical output to current behavior.
