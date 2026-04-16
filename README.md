# python-commons

Shared infrastructure for Python projects — Makefile targets, and Claude Code agents.

## What's included

- **`Makefile`** — task workflow, linting, testing, and git targets built on [uv](https://github.com/astral-sh/uv)
- **`.claude/agents/`** — Claude Code agents for spec-driven, TDD development

## Adopting in a project

Run all commands from **your project's root**, not from this repo.

### 1. Add as a subtree (one-time)

```bash
cd /path/to/your-project

git subtree add --prefix=.commons \
  https://github.com/CmdrPrompt/python-commons.git main --squash
```

This creates a `.commons/` folder inside your project with all content from this repo committed directly into your history — no submodule setup needed.

### 2. Include the Makefile

In your project's `Makefile`:

```makefile
include .commons/Makefile
```

### 3. Pull updates later

```bash
git subtree pull --prefix=.commons \
  https://github.com/CmdrPrompt/python-commons.git main --squash
```

### 4. Push local changes back to python-commons

If you've improved something in `.commons/` and want to contribute it back:

```bash
git subtree push --prefix=.commons \
  https://github.com/CmdrPrompt/python-commons.git main
```

This extracts all commits that touched `.commons/` and pushes them to python-commons as if they were made there directly.

If you don't have push access, push to a fork and open a pull request against `main` on python-commons instead.

## Agents

The same seven agents are available for both **Claude Code** and **GitHub Copilot**,
generated from shared templates.

### Workflow

```
requirements-drafter → workflow-guardian → implementation-worker → pr-reviewer → merge
                                ↑
              bug-triage ───────┤
    characterization-test-writer┘
              dependency-auditor (run periodically or before releases)
```

### Agents

| Agent | Role in flow | Purpose |
|---|---|---|
| `requirements-drafter` | Before implementation | Turns vague ideas into clear, testable requirements |
| `workflow-guardian` | Gate before coding | Enforces requirements-first flow, task branches, TDD, and commit discipline |
| `implementation-worker` | Coding | Implements approved work inside the correct task branch |
| `pr-reviewer` | Before merge | Reviews PRs for requirements adherence, test quality, and scope creep |
| `bug-triage` | On demand | Hunts for bugs without fixing them, produces prioritised task files |
| `characterization-test-writer` | Before refactoring | Documents existing untested behavior before refactoring |
| `dependency-auditor` | Periodic / pre-release | Audits dependencies for CVEs, outdated packages, and license issues |

| Tool | Format | Location |
|---|---|---|
| Claude Code | `.agent.md` | `.claude/agents/` (committed in repo) |
| GitHub Copilot | `.agent.md` | `.github/agents/` (generated) |

Claude Code agents live in `.claude/agents/` and are committed directly in this repo,
copied into consuming projects via subtree. Copilot agents are generated per project
by `make generate-governance-files` since they may contain project-specific paths.

### How to invoke agents

#### Claude Code

Type `@agent-name` directly in the Claude Code chat. Claude also auto-suggests relevant
agents based on what you describe.

```
> @requirements-drafter I want to add CSV export for the transaction list
> @workflow-guardian TASK-042, requirement confirmed
> @pr-reviewer TASK-042
> @bug-triage focus on src/importers/
> @dependency-auditor
```

#### GitHub Copilot (VS Code 1.101+)

Run `make generate-governance-files` first to generate `.github/agents/`. Then open the
**Copilot Chat panel** in VS Code and use the **dropdown** at the bottom of the panel to
switch to the agent you want before sending your message.

### When to use each agent

**Starting a new feature or change**

Invoke `requirements-drafter` with a rough description of what you want to build.
It asks clarifying questions and writes a confirmed requirement to your requirements doc.
Then invoke `workflow-guardian` with the TASK-ID — it gates on that confirmed requirement,
creates the task file, switches to the task branch, and hands off to `implementation-worker`.

**Implementing**

`implementation-worker` is invoked by `workflow-guardian` automatically after confirmation.
It follows TDD (Red → Green → Refactor), runs `make lint && make test`, updates
`CHANGELOG.md`, and commits via `make commit-current-task`.

**Before merging**

Invoke `pr-reviewer` with the TASK-ID or PR number. It checks scope, acceptance criteria,
test quality, and changelog — and gives a verdict of APPROVE / REQUEST CHANGES / NEEDS DISCUSSION.

**Finding bugs proactively**

Invoke `bug-triage` on a module or the full codebase. It reads the requirements doc,
traces code paths, and presents a prioritised list of confirmed and unconfirmed findings.
You decide which become tasks.

**Before refactoring untested code**

Invoke `characterization-test-writer` on the target module. It documents current behavior
as-is with pytest + Hypothesis tests, presents findings for your review, then commits.
Only after that should `workflow-guardian` + `implementation-worker` do the refactoring.

**Auditing dependencies**

Invoke `dependency-auditor` periodically or before a release. It runs `pip-audit`,
checks for outdated packages, and flags non-permissive licenses. You decide which
findings become tasks.

## Governance Templates

The `templates/` folder contains shared templates for:

- `CLAUDE.md`
- `.github/copilot-instructions.md`
- `.github/agents/*.agent.md` (one per agent, for GitHub Copilot)

Generate all project files from these templates:

```bash
make generate-governance-files
```

Override project-context values when needed:

```bash
make generate-governance-files \
  PROJECT_NAME="your-project" \
  PROJECT_DESCRIPTION="Describe your project context." \
  REQUIREMENTS_PATH="docs/REQUIREMENTS.md" \
  PROJECT_MAKE_TARGET="make web -- start local web server"
```

Generated files include a short header comment showing the template source and generation command.

## Conventions

- Tasks live in `docs/tasks/TASK-<NNN>-short-description.md`
- Every task runs on its own `task/<NNN>-short-description` branch
- Commits via `make commit-current-task` only — never `git commit` directly
- General workflow rules live in `~/.claude/CLAUDE.md`
