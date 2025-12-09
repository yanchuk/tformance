# Claude Code Infrastructure Guide

This guide documents the Claude Code infrastructure set up for tformance and how to use it effectively.

## Best Practices Compliance Review

| Best Practice | Status | Implementation |
|--------------|--------|----------------|
| CLAUDE.md file | ✅ | Comprehensive project docs, commands, TDD, coding guidelines |
| Tuned instructions | ✅ | Django-specific patterns, emphasized TDD requirements |
| Tool allowlist | ⚠️ | Default settings - customize via `/permissions` as needed |
| gh CLI usage | ✅ | Documented in CLAUDE.md, Claude can use for PR/issues |
| Bash tools | ✅ | Makefile commands documented (make test, ruff, migrations) |
| MCP servers | ⚠️ | Not configured - add if needed for specific integrations |
| Custom slash commands | ✅ | `/dev-docs`, `/dev-docs-update` |
| TDD workflow | ✅ | Full skill + 3 agents for Red-Green-Refactor |
| Context persistence | ✅ | Dev docs pattern with plan/context/tasks files |
| Code quality hooks | ✅ | Stop hook runs ruff + migration check |

### Gaps to Consider

1. **MCP Servers**: Consider adding for Puppeteer (screenshots), Sentry (error tracking), or database inspection
2. **Tool Allowlist**: Add frequently-used tools to reduce permission prompts
3. **Pre-commit Hooks**: Could add git hooks for additional validation

---

## Infrastructure Overview

```
.claude/
├── settings.json           # Hook configuration
├── settings.local.json     # Local overrides (gitignored)
├── hooks/
│   ├── skill-activation-prompt.ts   # Skill trigger logic
│   ├── skill-activation-prompt.sh   # Shell wrapper
│   ├── post-tool-use-tracker.sh     # Tracks modified files
│   └── stop-validation.sh           # Quality checks on stop
├── skills/
│   ├── skill-rules.json             # Activation triggers
│   ├── tdd-integration/             # TDD workflow
│   ├── django-dev-guidelines/       # Django patterns
│   └── htmx-alpine-flowbite-guidelines/  # Frontend patterns
├── agents/
│   ├── tdd-test-writer.md           # RED phase
│   ├── tdd-implementer.md           # GREEN phase
│   ├── tdd-refactorer.md            # REFACTOR phase
│   ├── code-architecture-reviewer.md
│   ├── refactor-planner.md
│   ├── plan-reviewer.md
│   └── documentation-architect.md
└── commands/
    ├── dev-docs.md                  # Create task documentation
    └── dev-docs-update.md           # Update before context reset
```

---

## Hooks System

### 1. Skill Activation (UserPromptSubmit)

**Triggers**: Every prompt you send

**What it does**: Analyzes your prompt against `skill-rules.json` and suggests relevant skills

**Example output**:
```
💡 Relevant skills detected:
   • tdd-integration - TDD Red-Green-Refactor workflow for Django
   • django-dev-guidelines - Django development patterns
```

**Trigger patterns** (from skill-rules.json):
- "implement", "add feature", "build" → tdd-integration
- "django", "view", "model", "serializer" → django-dev-guidelines
- "htmx", "alpine", "template", "component" → htmx-alpine-flowbite-guidelines

### 2. Post-Tool-Use Tracker (Edit/Write)

**Triggers**: After any file edit or write

**What it does**: Tracks which Django apps were modified during the session

**Output location**: `.claude/cache/[session-id]/affected-apps.txt`

### 3. Stop Validation (Stop)

**Triggers**: When Claude finishes a task

**What it does**:
1. Runs `make ruff-format` (code formatting)
2. Runs `make ruff-lint` (linting)
3. Checks for missing migrations

**Sample output**:
```
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━
🔍 CODE VALIDATION CHECK
━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━━

📝 Checking code formatting (ruff)...
✅ Code formatted

🔎 Checking code quality (ruff lint)...
✅ No lint issues

🗃️  Checking for missing migrations...
✅ No missing migrations
```

---

## Skills System

### How Skills Work

1. **Prompt triggers**: Keywords or intent patterns in your message
2. **File triggers**: Path patterns when working with specific files
3. **Content triggers**: Patterns detected in file content

### Available Skills

#### tdd-integration
**Purpose**: Enforces Test-Driven Development workflow

**Triggers**:
- Keywords: "implement", "add feature", "build", "create functionality"
- Files: `apps/**/views.py`, `apps/**/models.py`, etc.

**Workflow**:
1. 🔴 RED - `tdd-test-writer` agent creates failing test
2. 🟢 GREEN - `tdd-implementer` agent writes minimum code to pass
3. 🔵 REFACTOR - `tdd-refactorer` agent improves code quality

**Example prompt**: "Implement a GitHub webhook endpoint for the integrations app"

#### django-dev-guidelines
**Purpose**: Django development patterns and best practices

**Triggers**:
- Keywords: "django", "view", "model", "serializer", "celery", "task"
- Files: `apps/**/*.py`

**Resources**:
- [models-guide.md](skills/django-dev-guidelines/resources/models-guide.md) - BaseModel, BaseTeamModel, managers
- [views-guide.md](skills/django-dev-guidelines/resources/views-guide.md) - Function-based views, decorators
- [drf-guide.md](skills/django-dev-guidelines/resources/drf-guide.md) - Django REST Framework patterns
- [celery-guide.md](skills/django-dev-guidelines/resources/celery-guide.md) - Background tasks
- [teams-guide.md](skills/django-dev-guidelines/resources/teams-guide.md) - Multi-tenancy

#### htmx-alpine-flowbite-guidelines
**Purpose**: Frontend development patterns

**Triggers**:
- Keywords: "htmx", "alpine", "flowbite", "daisyui", "template", "component"
- Files: `templates/**/*.html`, `assets/**/*.js`

**Resources**:
- [htmx-patterns.md](skills/htmx-alpine-flowbite-guidelines/resources/htmx-patterns.md)
- [alpine-patterns.md](skills/htmx-alpine-flowbite-guidelines/resources/alpine-patterns.md)

---

## Agents System

Agents are specialized subagents Claude can delegate to for complex tasks.

### TDD Agents

| Agent | Phase | Purpose |
|-------|-------|---------|
| `tdd-test-writer` | 🔴 RED | Write failing tests following Django conventions |
| `tdd-implementer` | 🟢 GREEN | Write minimum code to pass tests |
| `tdd-refactorer` | 🔵 REFACTOR | Improve code while keeping tests green |

### Code Quality Agents

| Agent | Purpose |
|-------|---------|
| `code-architecture-reviewer` | Review code for Django patterns, security, performance |
| `refactor-planner` | Plan refactoring with impact analysis |
| `plan-reviewer` | Review technical plans for completeness |
| `documentation-architect` | Generate comprehensive documentation |

---

## Slash Commands

### /dev-docs [task description]

**Purpose**: Create structured development documentation for a task

**Creates**:
```
dev/active/[task-name]/
├── [task-name]-plan.md      # Comprehensive implementation plan
├── [task-name]-context.md   # Key files, decisions, dependencies
└── [task-name]-tasks.md     # Checklist for tracking progress
```

**Example**:
```
/dev-docs implement GitHub integration for syncing commits and PRs
```

**When to use**:
- Starting a new feature
- Complex multi-step implementations
- When you need to persist context across sessions

### /dev-docs-update [optional focus]

**Purpose**: Update documentation before context limit or session end

**Updates**:
- Marks completed tasks
- Captures current state
- Documents unfinished work
- Creates handoff notes

**Example**:
```
/dev-docs-update focusing on the API endpoint implementation
```

**When to use**:
- When you see context limit warnings
- Before ending a long session
- When switching tasks

---

## Recommended Workflows

### 1. Explore, Plan, Code, Commit

Best for: New features, complex tasks

```
1. Ask Claude to explore the codebase (use "ultrathink" for deep analysis)
2. /dev-docs [feature] to create persistent documentation
3. Follow TDD cycle for implementation
4. Ask Claude to commit and create PR
```

### 2. TDD Workflow (Automatic)

Best for: Any new functionality

When you say "implement [feature]", the skill system automatically:
1. Triggers `tdd-integration` skill
2. Delegates to appropriate agents
3. Ensures tests pass before completing

```
User: "Implement a webhook handler for GitHub events"

Claude:
🔴 RED PHASE: Delegating to tdd-test-writer...
[Test written, confirmed failing]

🟢 GREEN PHASE: Delegating to tdd-implementer...
[Implementation written, tests pass]

🔵 REFACTOR PHASE: Delegating to tdd-refactorer...
[Code improved, tests still pass]

✅ TDD cycle complete
```

### 3. Long Session with Context Persistence

Best for: Multi-day features

```
Session 1:
1. /dev-docs [feature] - Create documentation
2. Work on implementation
3. /dev-docs-update - Save state before ending

Session 2:
1. Read dev/active/[task]/ files
2. Continue from where you left off
3. /dev-docs-update when done
```

### 4. Code Review Workflow

Best for: Before merging PRs

```
1. Ask Claude to review changes: "Review the code in apps/integrations/"
2. Claude triggers code-architecture-reviewer agent
3. Get feedback on patterns, security, performance
4. Address issues before creating PR
```

---

## Common Commands Reference

### Development
```bash
make dev              # Start development server
make shell            # Django shell
make dbshell          # PostgreSQL shell
make manage ARGS='command'  # Any Django command
```

### Testing
```bash
make test             # Run all tests
make test ARGS='apps.myapp.tests'  # Run specific tests
make test ARGS='apps.myapp.tests::TestClass::test_method'  # Single test
```

### Code Quality
```bash
make ruff             # Format + lint
make ruff-format      # Format only
make ruff-lint        # Lint only
```

### Database
```bash
make migrations       # Create migrations
make migrate          # Apply migrations
```

### New Code
```bash
make uv run 'pegasus startapp <app_name> <Model1> <Model2>'  # New Django app
```

---

## Tips for Best Results

### 1. Be Specific in Instructions

```
❌ "Add tests for the integration"
✅ "Write tests for the GitHub webhook handler in apps/integrations,
    covering the cases: valid payload, invalid signature, missing event type"
```

### 2. Use Extended Thinking

```
"Think hard about how to structure the GitHub integration"
"Ultrathink about the data model for storing metrics"
```

Thinking levels: "think" < "think hard" < "think harder" < "ultrathink"

### 3. Use /clear Between Tasks

Clear context when switching between unrelated tasks to improve performance.

### 4. Course Correct Early

- Press **Escape** to interrupt if going wrong direction
- Double-tap **Escape** to edit previous prompt
- Ask "undo changes and try a different approach"

### 5. Reference Files Directly

Use tab-completion to reference files:
```
"Look at apps/integrations/views.py and add error handling"
```

### 6. Give Claude Images

Drag and drop mockups, screenshots, or diagrams for UI work.

---

## Troubleshooting

### Hooks Not Running

1. Check npm dependencies:
   ```bash
   cd .claude/hooks && npm install
   ```

2. Verify scripts are executable:
   ```bash
   chmod +x .claude/hooks/*.sh
   ```

3. Check settings.json syntax:
   ```bash
   cat .claude/settings.json | python -m json.tool
   ```

### Skill Not Activating

1. Check skill-rules.json for matching keywords/patterns
2. Verify skill SKILL.md file exists
3. Check TypeScript hook for errors:
   ```bash
   cd .claude/hooks && npx tsx skill-activation-prompt.ts
   ```

### TDD Workflow Skipped

The TDD skill doesn't trigger for:
- Bug fixes
- Documentation changes
- Configuration changes

If you want TDD for these, explicitly say "use TDD workflow"

### Stop Validation Failing

The stop hook is informational (exit 0) so it won't block. If you see warnings:
```bash
make ruff          # Fix formatting/linting
make migrations    # Create missing migrations
```

---

## Extending the Infrastructure

### Adding a New Skill

1. Create directory: `.claude/skills/[skill-name]/`
2. Create `SKILL.md` with frontmatter and content (< 500 lines)
3. Add resource files for detailed info
4. Register in `skill-rules.json`

### Adding a New Agent

1. Create `.claude/agents/[agent-name].md`
2. Define: Purpose, Capabilities, Input/Output format
3. Reference in skills or use directly via Task tool

### Adding a New Command

1. Create `.claude/commands/[command-name].md`
2. Add frontmatter with description and argument-hint
3. Use `$ARGUMENTS` placeholder for parameters
4. Available as `/project:[command-name]`

### Adding a New Hook

1. Create script in `.claude/hooks/`
2. Register in `settings.json` under appropriate event
3. Available events: `UserPromptSubmit`, `PostToolUse`, `Stop`, etc.

---

## Quick Reference Card

| Task | Command/Action |
|------|----------------|
| Start new feature | `/dev-docs [feature description]` |
| Update docs before context limit | `/dev-docs-update` |
| Run tests | `make test` |
| Format code | `make ruff` |
| Create migrations | `make migrations` |
| Apply migrations | `make migrate` |
| Start dev server | `make dev` |
| Clear context | `/clear` |
| See available commands | Type `/` |
| Trigger deep thinking | Add "ultrathink" to prompt |
| Request TDD | Say "implement [feature]" |
| Request code review | Say "review the code in [path]" |
