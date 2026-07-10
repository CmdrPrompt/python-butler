# TASK-041: Cross-workspace boundary and task-dependency guidelines

## Status

Draft

## Background

While working across `firefly-bills-analyzer` and its sibling dependency
`firefly-python-api` (both scaffolded from python-butler), Claude edited a
requirements document in the sibling repo — from within the consumer
project's workspace — before the user had approved doing so. The user then
asked for `firefly-bills-analyzer/CLAUDE.md` to be amended by hand with a
"Cross-Workspace Boundary" section stating: code must never be developed in
another workspace from the current one, and task files / requirements-doc
edits in another repo are only allowed after the user's explicit prior
approval (ask first, then edit — not edit then ask).

Separately, that same project maintains a `docs/tasks/README.md` task index
that encodes execution order and a dependency graph between tasks (numeric
task IDs are not execution order; each task lists `Depends on` and, where
relevant, a `Condition` noting a dependency living in another repo). This
index was written by hand for that one project; python-butler's scaffolding
has no equivalent template today, so every consumer project that wants
ordered/dependent tasks (or cross-repo dependencies) has to invent this
convention itself.

**No requirements for this task have been written yet.** Unlike most
python-butler tasks, there is no existing `REQUIREMENTS_*.md` entry to point
to — drafting the requirement(s) and use case(s) for this feature, per
python-butler's own spec-driven-development flow, is in scope for this task,
not a prerequisite already done. A new `REQUIREMENTS_*.md` file (or a section
in an existing one — TBD during requirements drafting) must be created and
confirmed with the user before any template/agent changes are implemented.

## Goal

Make the cross-workspace boundary rule and task-dependency/ordering pattern
first-class, reusable parts of python-butler's scaffolding, so new and
existing consumer projects get both without hand-authoring them per-project.

## Approach (tentative — subject to change during requirements drafting)

1. Draft requirements: define what "workspace" means for python-butler's
   purposes, what triggers the boundary rule (sibling repos, monorepo
   packages, vendored/stale `lib/` copies, etc.), and what the task-dependency
   index should guarantee (ordering, `Depends on`, cross-repo `Condition`
   notes). Present to the user and get explicit confirmation before coding.
2. Add a "Cross-Workspace Boundary" section to `templates/CLAUDE.md.tmpl`
   (mirroring the one manually added to `firefly-bills-analyzer/CLAUDE.md`),
   parameterized where needed (e.g. `{{WORKFLOW_GUARDIAN_NAME}}` style
   placeholders already used elsewhere in the template).
3. Extend `templates/workflow-guardian.agent.md.tmpl` with an enforcement gate
   for the boundary rule (never write code in another workspace; task/spec
   edits elsewhere require prior explicit user approval) and, if requirements
   confirm it, a gate for consulting a task-dependency index before starting
   work.
4. Evaluate whether a `docs/tasks/README.md`-style task index template
   (execution order table + dependency graph, as seen in
   `firefly-bills-analyzer/docs/tasks/README.md`) should be added as an
   optional scaffold artifact, and if so add it under `scaffold/` /
   `templates/` with its own governance rules (keep in sync with task files,
   update in the same commit as status changes, etc.).
5. Update README/docs describing scaffolded output to mention the new
   section(s).

## Requirements

To be drafted as part of this task (see Background). Do not implement
template/agent changes until requirements are written and the user has
confirmed them.

## Acceptance criteria

- [ ] Requirements drafted in a new or existing `REQUIREMENTS_*.md`, presented
      to the user, and explicitly confirmed ("Is this what you intended?")
      before implementation begins.
- [ ] `templates/CLAUDE.md.tmpl` includes a cross-workspace boundary section
      consistent with the confirmed requirements.
- [ ] `templates/workflow-guardian.agent.md.tmpl` enforces the boundary rule
      as a mandatory gate.
- [ ] Decision recorded (in the task file) on whether a task-dependency-index
      template is added in this task or split into a follow-up task.
- [ ] `CHANGELOG.md` updated with a behavior-first entry.
- [ ] `make lint && make test` pass.

## Out of scope

- Retroactively rewriting `firefly-bills-analyzer/CLAUDE.md` or
  `firefly-python-api`'s docs — those already have the manually-added
  section; this task only affects python-butler's scaffolding for future/
  other consumer projects.
- Automated tooling that enforces the boundary rule at the OS/filesystem
  level (e.g. sandboxing) — this task is documentation/prompt-level guidance
  for the agents only.

## Notes

- Source context: the manually-added section in
  `firefly-bills-analyzer/CLAUDE.md` (see that repo's git history around
  2026-07-10) is a useful starting draft for the boundary language, but was
  written ad hoc for one project and should be generalized during
  requirements drafting, not copied verbatim.
- Update CHANGELOG.md.
