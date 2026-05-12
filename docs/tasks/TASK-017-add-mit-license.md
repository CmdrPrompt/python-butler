# TASK-017 Add MIT license to python-butler

## Status

in progress

## Description

`python-butler` is a public repository with no declared license. Without a
license, the default copyright applies and downstream projects have no explicit
permission to use, copy, or modify the code. Adding an MIT license clarifies
the terms for all current and future adopters, including `python-butler-cli`.

## Acceptance criteria

- [ ] `LICENSE` file exists in the repository root with standard MIT license
  text, copyright holder Thomas Lindqvist, year 2026
- [ ] `README.md` includes a license section referencing the MIT license
- [ ] No other files are modified

## Branch

**Switch/create:** `git checkout -b task/017-add-mit-license`

## Completion

**Stage:** `git add LICENSE README.md docs/tasks/TASK-017-add-mit-license.md`
**Commit:** `git commit -m "Add MIT license"`
