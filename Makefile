.PHONY: all help setup install lint check-agents-sync validate-agents check-butler fix stage branch-task sync-main stage-task commit-task \
        commit-output pr-task merge-pr stage-current-task commit-current-task pr-current-task \
        sync-project-draft sync-project-backfill \
	merge-current-task merge-worktree worktree-clean test clean clean-complexity generate-governance-files \
	generate-pyproject generate-gitignore generate-pre-commit-config generate-pymarkdown \
	generate-bdd-scaffold init-project bdd bdd-missing \
	butler-fetch butler-pull butler-check butler-uninstall

BUTLER_REMOTE ?= https://github.com/CmdrPrompt/python-butler.git
TASKS_DIR ?= docs/tasks
SRC_DIR ?= src
TESTS_DIR ?= tests
PROJECT_NAME ?= my-project
PROJECT_DESCRIPTION ?= Describe your project here.
REQUIREMENTS_PATH ?= docs/REQUIREMENTS.md
WORKFLOW_GUARDIAN_NAME ?= Workflow Guardian
WORKFLOW_GUARDIAN_REF ?= Workflow Guardian agent (`.github/agents/workflow-guardian.agent.md`)
BUG_TRIAGE_NAME ?= Bug Triage
PROJECT_MAKE_TARGET ?= make help
GUIDELINES_TITLE ?= Python Development Guidelines
ENABLE_BDD ?= 1

all: help

## Show this help text
help:
	@echo ""
	@echo "Available commands:"
	@echo ""
	@echo "  Keeping butler up to date:"
	@echo "    make butler-check  -- Check if butler updates are available"
	@echo "    make butler-pull   -- Move .butler's submodule pointer to the latest commit (prints the git add/commit follow-up)"
	@echo "    make butler-fetch  -- Same as butler-pull"
	@echo ""
	@echo "  Removing butler:"
	@echo "    make butler-uninstall CATEGORIES=subtree,makefile,governance  -- Remove butler's footprint (add DRY_RUN=1 or FORCE=1)"
	@echo ""
	@echo "  First time on a new project:"
	@echo "    make init-project  -- Interactively generate CLAUDE.md and governance files"
	@echo ""
	@echo "  First time on a new machine:"
	@echo "    make setup    -- Install uv (if missing)"
	@echo "    make install  -- Create venv, install dependencies and activate pre-commit"
	@echo ""
	@echo "  Daily use:"
	@echo "    make lint     -- Run ruff, mypy, bandit, pymarkdown and complexipy"
	@echo "    make fix      -- Auto-fix ruff and pymarkdown issues"
	@echo "    make stage    -- Auto-fix and re-stage all staged changes"
	@echo "    make test     -- Run pytest with coverage"
	@echo "    make validate-agents  -- Validate agent definitions (frontmatter and tool names)"
	@echo "    make bdd              -- Run BDD scenarios in tests/bdd/ verbosely"
	@echo "    make bdd-missing      -- List BDD scenarios missing bound step definitions"
	@echo ""
	@echo "  Governance templates:"
	@echo "    make generate-governance-files  -- Generate CLAUDE.md, .github/copilot-instructions.md, and .github/chatmodes/"
	@echo "                                       Pass FORCE=1 to regenerate an existing project (also the adoption path for BDD support)"
	@echo "                                       Pass ENABLE_BDD=0 to omit BDD sections and the tests/bdd/ scaffold (default: 1)"
	@echo ""
	@echo "  Task workflow (explicit task ID):"
	@echo "    make branch-task f=TASK-001  -- Create/switch to task branch"
	@echo "    make sync-main               -- Merge main into current task branch"
	@echo "    make stage-task f=TASK-001   -- Fix + stage files listed in task"
	@echo "    make commit-task f=TASK-001  -- Commit with message from task file"
	@echo "    make pr-task f=TASK-001      -- Open PR on GitHub"
	@echo "    make merge-pr f=TASK-001     -- Squash-merge PR, pull main"
	@echo ""
	@echo "  Task workflow (current branch):"
	@echo "    make stage-current-task      -- Fix + stage files for current task"
	@echo "    make commit-current-task     -- Commit for current task"
	@echo "    make pr-current-task         -- Open PR for current task"
	@echo "    make merge-current-task      -- Squash-merge PR, pull main"
	@echo ""
	@echo "  Agent / worktree helpers:"
	@echo "    make sync-main                          -- Merge main into current branch"
	@echo "    make merge-worktree b=<branch>          -- Squash-merge a worktree branch into current branch"
	@echo "    make worktree-clean b=<branch>          -- Remove a merged worktree and its temporary branch"
	@echo "    make commit-output f='files' m='msg'    -- Stage and commit arbitrary files"
	@echo ""

## Generate pyproject.toml and .pymarkdown from templates if missing
generate-pyproject:
	@[ ! -f pyproject.toml ] || [ "$(FORCE)" = "1" ] || \
		(echo "pyproject.toml already exists. Run with FORCE=1 to overwrite."; exit 1)
	@sed \
		-e 's|{{PROJECT_NAME}}|$(PROJECT_NAME)|g' \
		-e 's|{{PROJECT_DESCRIPTION}}|$(PROJECT_DESCRIPTION)|g' \
		-e 's|{{TESTS_DIR}}|$(TESTS_DIR)|g' \
		-e 's|{{SRC_DIR}}|$(SRC_DIR)|g' \
		.butler/scaffold/pyproject.toml.tmpl > pyproject.toml
	@echo "✓ Generated pyproject.toml"
	@$(MAKE) generate-pymarkdown FORCE=$(FORCE)

## Generate .pymarkdown config from scaffold
generate-pymarkdown:
	@[ ! -f .pymarkdown ] || [ "$(FORCE)" = "1" ] || \
		(echo ".pymarkdown already exists. Run with FORCE=1 to overwrite."; exit 1)
	@cp .butler/scaffold/.pymarkdown .pymarkdown
	@echo "✓ Generated .pymarkdown"

## Generate .gitignore from scaffold template
generate-gitignore:
	@[ ! -f .gitignore ] || [ "$(FORCE)" = "1" ] || \
		(echo ".gitignore already exists. Run with FORCE=1 to overwrite."; exit 1)
	@cp .butler/scaffold/.gitignore.tmpl .gitignore
	@echo "✓ Generated .gitignore"

## Generate .pre-commit-config.yaml from scaffold template
generate-pre-commit-config:
	@[ ! -f .pre-commit-config.yaml ] || [ "$(FORCE)" = "1" ] || \
		(echo ".pre-commit-config.yaml already exists. Run with FORCE=1 to overwrite."; exit 1)
	@cp .butler/scaffold/.pre-commit-config.yaml.tmpl .pre-commit-config.yaml
	@echo "✓ Generated .pre-commit-config.yaml"

## Generate the tests/bdd/ directory skeleton with example feature/step files
generate-bdd-scaffold:
	@mkdir -p $(TESTS_DIR)/bdd/features $(TESTS_DIR)/bdd/steps
	@[ ! -f $(TESTS_DIR)/bdd/features/example_search.feature ] || [ "$(FORCE)" = "1" ] || \
		(echo "$(TESTS_DIR)/bdd/features/example_search.feature already exists. Run with FORCE=1 to overwrite."; exit 1)
	@cp .butler/scaffold/tests/bdd/features/example_search.feature.tmpl \
		$(TESTS_DIR)/bdd/features/example_search.feature
	@[ ! -f $(TESTS_DIR)/bdd/steps/test_example_search_steps.py ] || [ "$(FORCE)" = "1" ] || \
		(echo "$(TESTS_DIR)/bdd/steps/test_example_search_steps.py already exists. Run with FORCE=1 to overwrite."; exit 1)
	@cp .butler/scaffold/tests/bdd/steps/test_example_search_steps.py.tmpl \
		$(TESTS_DIR)/bdd/steps/test_example_search_steps.py
	@echo "✓ Generated $(TESTS_DIR)/bdd/ skeleton with example feature and step files"

## Install uv if missing (run once per machine)
setup:
	@which uv > /dev/null 2>&1 && echo "✓ uv already installed" || \
		(curl -LsSf https://astral.sh/uv/install.sh | sh && echo "✓ uv installed")

## Create virtual environment and install dependencies
install:
	@[ -f pyproject.toml ] || $(MAKE) generate-pyproject
	@[ -f .gitignore ] || $(MAKE) generate-gitignore
	@[ -f .pre-commit-config.yaml ] || $(MAKE) generate-pre-commit-config
	@[ -f .pymarkdown ] || $(MAKE) generate-pymarkdown
	uv sync --extra dev
	uv run pre-commit install
	@[ -f CLAUDE.md ] || $(MAKE) generate-governance-files
	@echo "✓ Environment ready"

## Fail if claude-agents/ and .claude/agents/ have drifted apart
check-agents-sync:
	@[ -d claude-agents ] || exit 0; \
	status=0; \
	for f in claude-agents/*.agent.md; do \
		base=$$(basename "$$f"); \
		other=".claude/agents/$$base"; \
		if [ ! -f "$$other" ]; then \
			echo "check-agents-sync: '$$base' exists in claude-agents/ but not in .claude/agents/"; \
			status=1; \
		elif ! diff -q "$$f" "$$other" > /dev/null 2>&1; then \
			echo "check-agents-sync: '$$base' differs between claude-agents/ and .claude/agents/"; \
			status=1; \
		fi; \
	done; \
	for f in .claude/agents/*.agent.md; do \
		base=$$(basename "$$f"); \
		[ -f "claude-agents/$$base" ] || { \
			echo "check-agents-sync: '$$base' exists in .claude/agents/ but not in claude-agents/"; \
			status=1; \
		}; \
	done; \
	if [ "$$status" -ne 0 ]; then \
		echo "claude-agents/ and .claude/agents/ must stay identical — sync the files above."; \
		exit 1; \
	fi

## Fail if claude-skills/ and .claude/skills/ have drifted apart
check-skills-sync:
	@[ -d claude-skills ] || exit 0; \
	status=0; \
	for f in claude-skills/*/SKILL.md; do \
		name=$$(basename "$$(dirname "$$f")"); \
		other=".claude/skills/$$name/SKILL.md"; \
		if [ ! -f "$$other" ]; then \
			echo "check-skills-sync: '$$name' exists in claude-skills/ but not in .claude/skills/"; \
			status=1; \
		elif ! diff -q "$$f" "$$other" > /dev/null 2>&1; then \
			echo "check-skills-sync: '$$name' differs between claude-skills/ and .claude/skills/"; \
			status=1; \
		fi; \
	done; \
	for f in .claude/skills/*/SKILL.md; do \
		name=$$(basename "$$(dirname "$$f")"); \
		[ -f "claude-skills/$$name/SKILL.md" ] || { \
			echo "check-skills-sync: '$$name' exists in .claude/skills/ but not in claude-skills/"; \
			status=1; \
		}; \
	done; \
	if [ "$$status" -ne 0 ]; then \
		echo "claude-skills/ and .claude/skills/ must stay identical - sync the files above."; \
		exit 1; \
	fi

## Run linters
lint: check-agents-sync check-skills-sync
	uv run ruff check .
	uv run ruff format --check .
	uv run mypy $(SRC_DIR)/
	uv run bandit -r $(SRC_DIR)/ -c pyproject.toml
	uv run pymarkdown --config .pymarkdown scan \
		$(shell find . -name "*.md" -not -path "./.venv/*" -not -path "./.github/*" -not -path "./.butler/.github/*" -not -path "./libs/*" -not -path "./.claude/*")
	uv run complexipy $(SRC_DIR)/ -mx 15 -s desc -j || \
		([ -f scripts/explain_complexipy_failures.py ] && \
			uv run python scripts/explain_complexipy_failures.py --max 15; exit 1)

## Auto-fix ruff and pymarkdown issues
fix:
	uv run ruff check --fix .
	uv run ruff format .
	uv run pymarkdown --config .pymarkdown --return-code-scheme minimal fix \
		$(shell find . -name "*.md" -not -path "./.venv/*" -not -path "./.github/*" -not -path "./.butler/.github/*" -not -path "./libs/*" -not -path "./.claude/*")

## Auto-fix and re-stage already-staged files (run before git commit)
stage:
	@STAGED=$$(git diff --name-only --cached); \
	uv run ruff check --fix .; \
	uv run ruff format .; \
	uv run pymarkdown --config .pymarkdown --return-code-scheme minimal fix \
		$$(find . -name "*.md" -not -path "./.venv/*" -not -path "./.butler/.github/*" -not -path "./libs/*" -not -path "./.claude/*"); \
	[ -n "$$STAGED" ] && echo "$$STAGED" | xargs git add -- || true; \
	git update-index -q --refresh

## Fail with a clear message if butler-cli is not installed
check-butler:
	@command -v butler > /dev/null 2>&1 || \
		(echo "butler-cli is not installed. Install it with: uv pip install -e . (see README for details)"; exit 1)

## Create/switch task branch from task file: make branch-task f=TASK-001
branch-task: check-butler
	@[ -n "$(f)" ] || (echo "Usage: make branch-task f=<task-id>"; exit 1)
	butler --tasks-dir $(TASKS_DIR) task branch $(f)
	-butler --tasks-dir $(TASKS_DIR) task sync-project $(f) --stage start

## Merge main into the current task branch (sync before coding)
sync-main:
	@BRANCH=$$(git branch --show-current); \
	[ "$$BRANCH" != "main" ] || (echo "Already on main — switch to a task branch first"; exit 1)
	git merge main

## Auto-fix and stage files listed in a task file: make stage-task f=TASK-001
stage-task: check-butler
	@[ -n "$(f)" ] || (echo "Usage: make stage-task f=<task-id>"; exit 1)
	butler --tasks-dir $(TASKS_DIR) task stage $(f)

## Commit using message from task file: make commit-task f=TASK-001
commit-task: check-butler
	@[ -n "$(f)" ] || (echo "Usage: make commit-task f=<task-id>"; exit 1)
	butler --tasks-dir $(TASKS_DIR) task commit $(f)

## Sync a task to its GitHub Projects item at the draft stage: make sync-project-draft f=TASK-001
sync-project-draft: check-butler
	@[ -n "$(f)" ] || (echo "Usage: make sync-project-draft f=<task-id>"; exit 1)
	-butler --tasks-dir $(TASKS_DIR) task sync-project $(f) --stage draft

## Sync a historical task to its GitHub Projects item, backfilling status/dates: make sync-project-backfill f=TASK-001
sync-project-backfill: check-butler
	@[ -n "$(f)" ] || (echo "Usage: make sync-project-backfill f=<task-id>"; exit 1)
	-butler --tasks-dir $(TASKS_DIR) task sync-project $(f) --stage backfill

## Auto-fix and stage files for the current task branch
stage-current-task:
	@BRANCH=$$(git branch --show-current); \
	NUM=$$(echo "$$BRANCH" | sed -n 's#^task/\([0-9][0-9][0-9]\)-.*#\1#p'); \
	[ -n "$$NUM" ] || (echo "Not on a task branch (expected task/<NNN>-...)"; exit 1); \
	$(MAKE) stage-task f=TASK-$$NUM

## Commit using task file metadata for the current task branch
commit-current-task:
	@BRANCH=$$(git branch --show-current); \
	NUM=$$(echo "$$BRANCH" | sed -n 's#^task/\([0-9][0-9][0-9]\)-.*#\1#p'); \
	[ -n "$$NUM" ] || (echo "Not on a task branch (expected task/<NNN>-...)"; exit 1); \
	$(MAKE) commit-task f=TASK-$$NUM

## Stage and commit arbitrary files with a given message (for agents not on a task branch)
commit-output:
	@[ -n "$(f)" ] || (echo "Usage: make commit-output f='file1 file2' m='commit message'"; exit 1)
	@[ -n "$(m)" ] || (echo "Usage: make commit-output f='file1 file2' m='commit message'"; exit 1)
	git add -- $(f)
	git commit -m "$(m)"

## Open a GitHub PR using task title and description: make pr-task f=TASK-001
pr-task: check-butler
	@[ -n "$(f)" ] || (echo "Usage: make pr-task f=<task-id>"; exit 1)
	butler --tasks-dir $(TASKS_DIR) task branch $(f)
	butler --tasks-dir $(TASKS_DIR) task pr $(f)
	-butler --tasks-dir $(TASKS_DIR) task sync-project $(f) --stage open

## Open PR using task file metadata for the current task branch
pr-current-task:
	@BRANCH=$$(git branch --show-current); \
	NUM=$$(echo "$$BRANCH" | sed -n 's#^task/\([0-9][0-9][0-9]\)-.*#\1#p'); \
	[ -n "$$NUM" ] || (echo "Not on a task branch (expected task/<NNN>-...)"; exit 1); \
	$(MAKE) pr-task f=TASK-$$NUM

## Squash-merge the open PR for a task branch: make merge-pr f=TASK-001
merge-pr: check-butler
	@[ -n "$(f)" ] || (echo "Usage: make merge-pr f=<task-id>"; exit 1)
	butler --tasks-dir $(TASKS_DIR) task merge $(f)
	-butler --tasks-dir $(TASKS_DIR) task sync-project $(f) --stage merge

## Squash-merge the open PR for the current task branch, then pull main
merge-current-task:
	@BRANCH=$$(git branch --show-current); \
	NUM=$$(echo "$$BRANCH" | sed -n 's#^task/\([0-9][0-9][0-9]\)-.*#\1#p'); \
	[ -n "$$NUM" ] || (echo "Not on a task branch (expected task/<NNN>-...)"; exit 1); \
	$(MAKE) merge-pr f=TASK-$$NUM

## Squash a worktree sub-agent branch's commit(s) into staged changes on the current branch
merge-worktree:
	@[ -n "$(b)" ] || (echo "Usage: make merge-worktree b=<branch-name>"; exit 1)
	git merge --squash $(b)

## Remove a subagent's isolated worktree and its temporary branch after merging: make worktree-clean b=<branch>
worktree-clean:
	@[ -n "$(b)" ] || (echo "Usage: make worktree-clean b=<branch-name>"; exit 1)
	@path=$$(git worktree list --porcelain | awk -v b="refs/heads/$(b)" '/^worktree /{p=$$2} /^branch /{if ($$2==b){print p; exit}}'); \
	if [ -z "$$path" ]; then echo "No worktree found for branch $(b)"; exit 1; fi; \
	git worktree remove --force "$$path" && git branch -D $(b)

## Run tests with coverage
test:
	uv run pytest $(TESTS_DIR)/ --cov=$(SRC_DIR) --cov-report=term-missing

## Run BDD scenarios verbosely; degrades gracefully if tests/bdd/ is absent
bdd:
	@if [ ! -d $(TESTS_DIR)/bdd ]; then \
		echo "No $(TESTS_DIR)/bdd/ directory found — nothing to run. Adopt BDD with 'make generate-bdd-scaffold'."; \
		exit 0; \
	fi; \
	uv run pytest $(TESTS_DIR)/bdd/ -v

## List BDD scenarios without bound step definitions; degrades gracefully if tests/bdd/ is absent
bdd-missing:
	@if [ ! -d $(TESTS_DIR)/bdd ]; then \
		echo "No $(TESTS_DIR)/bdd/ directory found — nothing to check. Adopt BDD with 'make generate-bdd-scaffold'."; \
		exit 0; \
	fi; \
	OUTPUT=$$(uv run pytest $(TESTS_DIR)/bdd/ -q 2>&1); \
	if echo "$$OUTPUT" | grep -q "StepDefinitionNotFoundError"; then \
		echo "$$OUTPUT" | grep -B5 "StepDefinitionNotFoundError"; \
		echo ""; \
		echo "Scenarios above are missing bound step definitions."; \
		exit 1; \
	else \
		echo "✓ All BDD scenarios have bound step definitions"; \
	fi

## Interactively prompt for project values and generate governance files
init-project:
	@echo "Initialising project governance files."
	@echo "Press Enter to accept the default shown in brackets."
	@echo ""
	@read -p "Project name [$(notdir $(CURDIR))]: " pname; \
	pname=$${pname:-$(notdir $(CURDIR))}; \
	read -p "Project description [$(PROJECT_DESCRIPTION)]: " pdesc; \
	pdesc=$${pdesc:-$(PROJECT_DESCRIPTION)}; \
	read -p "Requirements path [$(REQUIREMENTS_PATH)]: " rpath; \
	rpath=$${rpath:-$(REQUIREMENTS_PATH)}; \
	read -p "Run command [$(PROJECT_MAKE_TARGET)]: " ptarget; \
	ptarget=$${ptarget:-$(PROJECT_MAKE_TARGET)}; \
	echo ""; \
	$(MAKE) generate-governance-files FORCE=$(FORCE) ENABLE_BDD=$(ENABLE_BDD) \
		PROJECT_NAME="$$pname" \
		PROJECT_DESCRIPTION="$$pdesc" \
		REQUIREMENTS_PATH="$$rpath" \
		PROJECT_MAKE_TARGET="$$ptarget"; \
	$(MAKE) generate-pyproject FORCE=$(FORCE) \
		PROJECT_NAME="$$pname" \
		PROJECT_DESCRIPTION="$$pdesc"; \
	$(MAKE) generate-gitignore FORCE=$(FORCE); \
	$(MAKE) generate-pre-commit-config FORCE=$(FORCE); \
	echo ""; \
	echo "✓ Done. Stage and commit with:"; \
	echo ""; \
	echo "  git add CLAUDE.md pyproject.toml .gitignore .pre-commit-config.yaml .github/ .claude/"; \
	echo "  git commit -m \"Bootstrap project with python-butler\""

## Remove butler's footprint from this project. Never touches docs/tasks/.
## Usage: make butler-uninstall CATEGORIES=subtree,makefile,governance [DRY_RUN=1] [FORCE=1]
## Pure shell (grep/sed/rm) so it works even without butler_core/butler-cli installed
## (e.g. a legacy project that adopted butler before the CLI existed).
butler-uninstall:
	@[ -n "$(CATEGORIES)" ] || (echo "Usage: make butler-uninstall CATEGORIES=subtree,makefile,governance [DRY_RUN=1] [FORCE=1]"; exit 1)
	@if [ -z "$(FORCE)" ] && [ -n "$$(git status --porcelain)" ]; then \
		echo "Error: working tree has uncommitted changes. Commit/stash first, or pass FORCE=1."; \
		exit 1; \
	fi
	@WANT_SUBTREE=$$(echo "$(CATEGORIES)" | tr ',' '\n' | grep -qx subtree && echo 1 || echo ""); \
	WANT_MAKEFILE=$$(echo "$(CATEGORIES)" | tr ',' '\n' | grep -qx makefile && echo 1 || echo ""); \
	WANT_GOVERNANCE=$$(echo "$(CATEGORIES)" | tr ',' '\n' | grep -qx governance && echo 1 || echo ""); \
	if [ -n "$$WANT_SUBTREE" ] && [ -d .butler ]; then \
		if [ -n "$(DRY_RUN)" ]; then \
			echo "Would run: git submodule deinit -f .butler"; \
			echo "Would run: git rm -f .butler"; \
			echo "Would remove the .gitmodules entry for .butler (and .gitmodules itself if empty)"; \
		else \
			git submodule deinit -f .butler > /dev/null 2>&1 || true; \
			git rm -rf .butler > /dev/null 2>&1 || rm -rf .butler; \
			rm -rf .git/modules/.butler; \
			if [ -f .gitmodules ] && [ ! -s .gitmodules ]; then \
				git rm -f .gitmodules > /dev/null 2>&1 || rm -f .gitmodules; \
			fi; \
			echo "Removed .butler/ (git submodule deinit + git rm)"; \
		fi; \
	fi; \
	if [ -n "$$WANT_MAKEFILE" ] && [ -f Makefile ] && grep -q '^include \.butler/Makefile$$' Makefile; then \
		if [ -n "$(DRY_RUN)" ]; then echo "Would remove 'include .butler/Makefile' line from Makefile"; \
		else \
			grep -v '^include \.butler/Makefile$$' Makefile > Makefile.tmp && mv Makefile.tmp Makefile; \
			echo "Removed 'include .butler/Makefile' line from Makefile"; \
		fi; \
	fi; \
	if [ -n "$$WANT_GOVERNANCE" ]; then \
		for p in CLAUDE.md .github/copilot-instructions.md .github/agents .claude/agents; do \
			if [ -e "$$p" ]; then \
				if [ -n "$(DRY_RUN)" ]; then echo "Would remove $$p"; \
				else rm -rf "$$p"; echo "Removed $$p"; fi; \
			fi; \
		done; \
	fi
	@echo ""
	@echo "docs/tasks/ was not touched."

## Check if butler updates are available (compares .butler's submodule pointer against the remote)
butler-check:
	@CURRENT=$$(git -C .butler rev-parse HEAD 2>/dev/null); \
	echo "Checking for butler updates..."; \
	LATEST=$$(git ls-remote $(BUTLER_REMOTE) refs/heads/main | cut -f1); \
	[ -n "$$LATEST" ] || (echo "Could not reach $(BUTLER_REMOTE)"; exit 1); \
	if [ -z "$$CURRENT" ]; then \
		echo "Could not determine .butler's current submodule commit — is .butler a submodule?"; \
		exit 1; \
	elif [ "$$CURRENT" = "$$LATEST" ]; then \
		echo "✓ butler is up to date ($$CURRENT)"; \
	else \
		echo "Updates available."; \
		echo "  Current: $$CURRENT"; \
		echo "  Latest:  $$LATEST"; \
		echo "  Run: make butler-pull"; \
	fi

## Move .butler's submodule pointer to the latest commit on the tracked branch; prints the git add/commit follow-up
butler-fetch:
	@echo "Updating .butler submodule pointer ..."
	@git submodule update --init --remote .butler
	@echo "✓ .butler now at $$(git -C .butler rev-parse HEAD). Commit this pointer change:"
	@echo "  git add .butler"
	@echo "  git commit -m \"chore: update butler submodule\""

## Same as butler-fetch — move .butler's submodule pointer to the latest commit (no automatic commit)
butler-pull: butler-fetch

## Generate project governance files from .butler templates
generate-governance-files:
	@[ ! -f CLAUDE.md ] || [ "$(FORCE)" = "1" ] || \
		(echo "CLAUDE.md already exists. Run with FORCE=1 to overwrite."; exit 1)
	@[ ! -f .github/copilot-instructions.md ] || [ "$(FORCE)" = "1" ] || \
		(echo ".github/copilot-instructions.md already exists. Run with FORCE=1 to overwrite."; exit 1)
	@mkdir -p .github .github/agents
	@if [ "$(ENABLE_BDD)" = "0" ]; then \
		BDD_FILTER="sed -e /<!--BDD:START-->/,/<!--BDD:END-->/d"; \
	else \
		BDD_FILTER="sed -e /<!--BDD:START-->/d -e /<!--BDD:END-->/d"; \
	fi; \
	$$BDD_FILTER .butler/templates/CLAUDE.md.tmpl | sed \
		-e 's|{{PROJECT_NAME}}|$(PROJECT_NAME)|g' \
		-e 's|{{PROJECT_DESCRIPTION}}|$(PROJECT_DESCRIPTION)|g' \
		-e 's|{{REQUIREMENTS_PATH}}|$(REQUIREMENTS_PATH)|g' \
		-e 's|{{WORKFLOW_GUARDIAN_NAME}}|$(WORKFLOW_GUARDIAN_NAME)|g' \
		-e 's|{{BUG_TRIAGE_NAME}}|$(BUG_TRIAGE_NAME)|g' \
		-e 's|{{PROJECT_MAKE_TARGET}}|$(PROJECT_MAKE_TARGET)|g' \
		> CLAUDE.md; \
	$$BDD_FILTER .butler/templates/copilot-instructions.md.tmpl | sed \
		-e 's|{{GUIDELINES_TITLE}}|$(GUIDELINES_TITLE)|g' \
		-e 's|{{PROJECT_DESCRIPTION}}|$(PROJECT_DESCRIPTION)|g' \
		-e 's|{{REQUIREMENTS_PATH}}|$(REQUIREMENTS_PATH)|g' \
		-e 's|{{WORKFLOW_GUARDIAN_REF}}|$(WORKFLOW_GUARDIAN_REF)|g' \
		-e 's|{{BUG_TRIAGE_NAME}}|$(BUG_TRIAGE_NAME)|g' \
		> .github/copilot-instructions.md
	@for agent in workflow-guardian implementation-worker bug-triage characterization-test-writer requirements-drafter task-drafter pr-reviewer dependency-auditor test-design-reviewer test-writer; do \
		sed \
			-e 's|{{REQUIREMENTS_PATH}}|$(REQUIREMENTS_PATH)|g' \
			.butler/templates/$$agent.agent.md.tmpl > .github/agents/$$agent.agent.md; \
	done
	@mkdir -p .claude/agents
	@cp .butler/claude-agents/*.agent.md .claude/agents/
	@mkdir -p .claude/skills
	@[ -d .butler/claude-skills ] && for dir in .butler/claude-skills/*/; do \
		[ -d "$$dir" ] || continue; \
		name=$$(basename "$$dir"); \
		mkdir -p ".claude/skills/$$name"; \
		cp "$$dir/SKILL.md" ".claude/skills/$$name/SKILL.md"; \
	done; true
	@[ "$(ENABLE_BDD)" = "0" ] || $(MAKE) generate-bdd-scaffold FORCE=$(FORCE)
	@echo "✓ Generated CLAUDE.md, .github/copilot-instructions.md, .github/agents/, .claude/agents/, and .claude/skills/"

## Remove generated complexipy artifacts
clean-complexity:
	rm -rf .complexipy_cache
	rm -f complexipy_results_*.json
	@echo "✓ Removed complexipy artifacts"

## Remove venv and cache
clean:
	$(MAKE) clean-complexity
	rm -rf .venv
	find . -type d \( -name "__pycache__" -o -name ".mypy_cache" \
		-o -name ".ruff_cache" -o -name ".pytest_cache" -o -name "*.egg-info" \) \
		-exec rm -rf {} +
	@echo "✓ Done"

## Validate agent logs
validate-agents:
	@python3 scripts/validate_agents.py .claude/agents