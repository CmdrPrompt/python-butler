# Requirements: `CLAUDE.md.tmpl` routes to skills instead of restating them

## Context

`templates/CLAUDE.md.tmpl` renders to a 122-line `CLAUDE.md` in every
consumer project (`clean-firefly-bank-importer`, `firefly-bills-analyzer`,
`firefly-household-balancer`, `firefly-python-api`). Since
`REQUIREMENTS_AGENT_SKILLS.md`, the same projects also ship the shared
procedures as skills under `.claude/skills/` (`commit-workflow`,
`task-file-format`, `tdd-cycle`, `changelog`, `characterization-tests`).
The template still restates much of that skill content in full — the task
workflow command block, changelog style rules, the coverage baseline — so
every session loads it twice (once from `CLAUDE.md`, once on skill load), and
the two copies drift:

- The template's "Branch sync" line says `git merge main`; the
  `commit-workflow` skill and every consumer's `.butler/Makefile` use
  `make sync-main`.
- The template points to `.github/agents/<name>.agent.md`, which is the
  Copilot copy; Claude Code loads agents from `.claude/agents/`, and
  python-butler itself has no `.github/agents/` at all.
- The "Bug Discovery" section repeats what the Bug Triage agent's own
  description already puts in every session's agent list.

python-butler itself has no `CLAUDE.md`. Its rules have instead lived in the
user's global `~/.claude/CLAUDE.md`, an older hand-copied variant of the
template, which is therefore also loaded in every consumer session (on top of
the consumer's own `CLAUDE.md`) and in unrelated non-butler projects.

Skill descriptions are loaded into every session's context. The five shipped
skills' descriptions are 260–370 characters each, mostly keyword lists that
repeat words already in the description.

## Goals

1. A generated `CLAUDE.md` states each rule that no shipped skill owns, and
   for everything a skill owns it names the skill instead of restating it.
2. Generated `CLAUDE.md` content is correct for the files and targets a
   generated project actually has.
3. python-butler has its own tracked `CLAUDE.md` generated from the same
   template, so the user's global `~/.claude/CLAUDE.md` no longer needs to
   carry butler rules.
4. Shipped skill descriptions are short enough to be cheap to preload while
   still triggering on the same situations.
5. Consumer projects adopt all of this through the existing
   `make butler-pull` → `make generate-governance-files FORCE=1` flow, with
   no new variables, targets or manual edits.

## Non-goals

- Changing `templates/copilot-instructions.md.tmpl` or `.github/agents/`.
  Copilot has no skills, so it keeps the full text. BDD-041 stays satisfied
  because the BDD conventions themselves do not change, only their wording
  in the Claude template.
- Changing the `generate-governance-files` recipe, its variables, or the
  project-identity preservation from `REQUIREMENTS_GOVERNANCE_REGEN.md`.
- Changing agent files or what any skill's body says.
- Editing consumer repos. Each one regenerates on its own schedule through
  its own task flow.
- Editing the user's global `~/.claude/CLAUDE.md` (outside this repo; done
  separately after this lands).
- Changing the section headings that other requirements refer to
  (BDD-040, `REQUIREMENTS_CROSS_WORKSPACE.md` Requirement 1,
  `REQUIREMENTS_TASK_WORKFLOW.md` Requirement 10). Those requirements stay
  satisfied unchanged.

## Requirement 1: Template routes to skills for skill-owned content

**Description:** `templates/CLAUDE.md.tmpl` SHALL NOT restate content that a
shipped skill owns. Where that content is relevant, the template SHALL name
the skill instead:

- the task workflow command block and stage/commit/PR/merge mechanics →
  `commit-workflow` (the template MAY keep a single-line ordered list of the
  `make *-current-task` targets);
- the task file format → `task-file-format`;
- the red-green-refactor mechanics and coverage baseline → `tdd-cycle`;
- the changelog style rules → `changelog`.

The template SHALL drop the "Bug Discovery" section.

The template SHALL keep every rule that no skill owns:

- the spec-first gate (update `{{REQUIREMENTS_PATH}}`, present, ask
  "Is this what you intended?", wait for explicit confirmation; no
  requirement + use case → no implementation);
- `{{WORKFLOW_GUARDIAN_NAME}}`'s rules applying automatically, and the
  three equivalent interfaces (`make`, `butler` CLI, `butler-mcp`) with the
  ban on bypassing all three (`REQUIREMENTS_TASK_WORKFLOW.md`
  Requirement 10), in the "Task Management" section;
- branch policy (one `task/<NNN>-short-description` branch per task, never
  implement on `main`);
- Hypothesis for all parsing and data transformation functions;
- the Cross-Workspace Boundary section (`REQUIREMENTS_CROSS_WORKSPACE.md`
  Requirement 1), with all four rules;
- the BDD section (BDD-040), inside the existing `<!--BDD:START-->` /
  `<!--BDD:END-->` markers;
- the "Running the Application" section with `{{PROJECT_MAKE_TARGET}}`;
- "What NOT to Do": never commit code failing `make lint` or `make test`,
  no new dependencies without a requirement, no `# type: ignore` without an
  explanation, no raw `git commit`.

**Use case:**

```text
A consumer runs `make butler-pull` and
`make generate-governance-files FORCE=1`. The regenerated CLAUDE.md keeps the
project's real name and description, still tells the assistant to confirm
requirements first, apply Workflow Guardian's rules automatically, respect
the cross-workspace boundary and follow the BDD conventions, and says "see
skill `changelog`" instead of listing the changelog rules. When the assistant
later writes a changelog entry it loads the `changelog` skill and reads the
rules once, from one source.
```

## Requirement 2: Generated `CLAUDE.md` stays short

**Description:** `CLAUDE.md` rendered from the template with `ENABLE_BDD=1`
SHALL be at most 70 lines, excluding the H1 and the description paragraph.

**Use case:**

```bash
$ make generate-governance-files FORCE=1
$ wc -l CLAUDE.md
      66 CLAUDE.md        # was 122
```

## Requirement 3: Generated references match what the project has

**Description:** The template's branch-sync instruction SHALL say
`make sync-main` (not `git merge main`). Any agent file path the template
names SHALL be under `.claude/agents/`, which `generate-governance-files`
populates in every generated project.

**Use case:**

```text
A task branch is behind main. The assistant follows CLAUDE.md, runs
`make sync-main`, and gets the same behavior the `commit-workflow` skill
describes, instead of a raw `git merge main` that bypasses the make targets.
```

## Requirement 4: python-butler dogfoods its own template

**Description:** python-butler SHALL track a root `CLAUDE.md` whose content
equals `templates/CLAUDE.md.tmpl` rendered with `ENABLE_BDD=1`,
`PROJECT_NAME=python-butler`, python-butler's one-line description, and
`REQUIREMENTS_PATH` set to the root `REQUIREMENTS_*.md` files. A test SHALL
fail when the tracked file and the rendered template differ, and its failure
message SHALL say how to regenerate the file.

**Use case:**

```text
A later task edits templates/CLAUDE.md.tmpl but forgets python-butler's own
CLAUDE.md. `make test` fails, naming the drift and the command that
regenerates it. Once regenerated, sessions in python-butler load the same
rules consumers get, with nothing needed in ~/.claude/CLAUDE.md.
```

## Requirement 5: Short skill descriptions

**Description:** The `description:` of each shipped skill (`changelog`,
`characterization-tests`, `commit-workflow`, `task-file-format`,
`tdd-cycle`) SHALL be at most 200 characters, SHALL still state when to use
the skill, and SHALL still name the situations it currently triggers on.
`claude-skills/` and `.claude/skills/` stay byte-identical
(`make check-skills-sync`).

**Use case:**

```text
A session starts in a consumer project. The skill list costs about half the
characters it did, and asking the assistant to "commit TASK-012" still loads
`commit-workflow`.
```

## Acceptance criteria (overall)

- [ ] `templates/CLAUDE.md.tmpl` contains no task workflow code block, no
      changelog rule list, no coverage-baseline rule and no "Bug Discovery"
      section, and names `commit-workflow`, `task-file-format`, `tdd-cycle`
      and `changelog`.
- [ ] The template keeps the spec-first gate, the Workflow Guardian
      auto-apply and three-interface statements in "Task Management", the
      branch policy, the Hypothesis rule, the Cross-Workspace Boundary
      section, the BDD section and the What NOT to Do rules listed in
      Requirement 1.
- [ ] Rendered with `ENABLE_BDD=1`, `CLAUDE.md` is at most 70 lines
      excluding the H1 and the description.
- [ ] The template says `make sync-main`, not `git merge main`, and names no
      `.github/agents/` path.
- [ ] Existing tests for BDD-040, project-identity preservation, file
      gating and template variable shell safety pass unchanged.
- [ ] python-butler tracks a root `CLAUDE.md` and a test fails on drift
      from the rendered template.
- [ ] Each shipped skill description is at most 200 characters, and
      `make check-skills-sync` passes.
- [ ] `CHANGELOG.md` updated with a behavior-first entry.
- [ ] `make lint && make test` pass.
