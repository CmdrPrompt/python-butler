# TASK-014 Fix pyproject.toml scaffold: build-system, src layout, pymarkdownlnt, and .gitignore

## Status
todo

## Description

Three defects were discovered when bootstrapping a new src-layout project with the
butler scaffold (`make init-project` / `make generate-pyproject`):

1. **Wrong pymarkdown package** — `scaffold/pyproject.toml.tmpl` lists `"pymarkdown"`
   which resolves to an ancient Python-2-era package (v0.1.4) that crashes on
   import with `ModuleNotFoundError: No module named 'StringIO'`. The correct
   package is `pymarkdownlnt>=0.9.36`.

2. **Missing `[build-system]`** — without a build-system table the package cannot
   be installed in editable mode (`uv pip install -e .`), so `make test` fails with
   `ModuleNotFoundError: No module named '<package>'` even after `make install`.

3. **Missing `[tool.setuptools.packages.find]`** — projects using a `src/` layout
   need `where = ["src"]` so setuptools discovers the package. Without it the
   package installs but none of its modules are importable.

4. **Missing `.pymarkdown` scaffold file** — new projects have no `.pymarkdown`
   config, so `make lint` fails with
   `Specified configuration file '.pymarkdown' does not exist`.

5. **Incomplete `.gitignore` for complexipy output** — the scaffolded `.gitignore`
   covers `complexipy_results_*.json` (underscore) but not `complexipy-results*.json`
   (hyphen), which is the filename complexipy actually produces.

6. **Numbered lists in agent templates use incrementing numbers** —
   `workflow-guardian.agent.md.tmpl` (and other agent templates) use `2.`, `3.` …
   `10.` in ordered lists. `pymarkdown --fix` rewrites these to `1.` on every item
   (the CommonMark-preferred style), causing `make lint` to flag the generated files
   as dirty on every new project until manually fixed.

## Branch
**Branch name:** `task/014-fix-pyproject-scaffold`
**Switch/create:** `git checkout -b task/014-fix-pyproject-scaffold`
**Make target:** `make branch-task f=TASK-014`

## Acceptance criteria

- [ ] `scaffold/pyproject.toml.tmpl` contains `"pymarkdownlnt>=0.9.36"` instead of
  `"pymarkdown"`
- [ ] `scaffold/pyproject.toml.tmpl` contains a `[build-system]` table:
  ```toml
  [build-system]
  requires = ["setuptools>=68"]
  build-backend = "setuptools.build_meta"
  ```
- [ ] `scaffold/pyproject.toml.tmpl` contains `[tool.setuptools.packages.find]`
  with `where = ["{{SRC_DIR}}"]` (or the resolved value of `SRC_DIR`, defaulting
  to `src`)
- [ ] `scaffold/.pymarkdown.tmpl` (or a static `scaffold/.pymarkdown`) is created
  with the same disabled-rules config used across existing butler-based projects
  (md003, md013, md022, md024, md032, md033, md040, md041)
- [ ] `make generate-pyproject` (or `make init-project`) writes the `.pymarkdown`
  file alongside `pyproject.toml`
- [ ] The scaffolded `.gitignore` includes `complexipy-results*.json` alongside
  the existing `complexipy_results_*.json` entry
- [ ] All ordered lists in agent `.md.tmpl` files use `1.` on every item instead
  of incrementing numbers, so generated files pass `make lint` without modification
- [ ] A fresh project bootstrapped from the updated scaffold passes
  `make lint && make test` without manual intervention
- [ ] `make lint && make test` pass in the butler repo itself

## Completion
**Date:**
**Summary:**
**Files changed:**
**Branch:**
**Stage:**
**Commit:**
