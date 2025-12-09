# Dev Docs Pattern

A methodology for maintaining project context across Claude Code sessions and context resets.

## The Problem

**Context resets lose everything:**
- Implementation decisions
- Key files and their purposes
- Task progress
- Technical constraints
- Why certain approaches were chosen

**After a reset, Claude has to rediscover everything.**

## The Solution: Persistent Dev Docs

A three-file structure that captures everything needed to resume work:

```
dev/active/[task-name]/
├── [task-name]-plan.md      # Strategic plan
├── [task-name]-context.md   # Key decisions & files
└── [task-name]-tasks.md     # Checklist format
```

**These files survive context resets** - Claude reads them to get back up to speed instantly.

## Three-File Structure

### 1. [task-name]-plan.md

**Purpose:** Strategic plan for the implementation

**Contains:**
- Executive summary
- Current state analysis
- Proposed future state
- Implementation phases
- Detailed tasks with acceptance criteria
- Risk assessment
- Success metrics

### 2. [task-name]-context.md

**Purpose:** Key information for resuming work

**Contains:**
- SESSION PROGRESS section (updated frequently!)
- What's completed vs in-progress
- Key files and their purposes
- Important decisions made
- Technical constraints discovered
- Quick resume instructions

**CRITICAL:** Update the SESSION PROGRESS section every time significant work is done!

### 3. [task-name]-tasks.md

**Purpose:** Checklist for tracking progress

**Contains:**
- Phases broken down by logical sections
- Tasks in checkbox format
- Status indicators
- Acceptance criteria

## Usage

### Starting a New Task

Use the `/dev-docs` slash command:
```
/dev-docs implement GitHub integration
```

This creates:
- `dev/active/github-integration/`
  - github-integration-plan.md
  - github-integration-context.md
  - github-integration-tasks.md

### Before Context Reset

Use the `/dev-docs-update` slash command:
```
/dev-docs-update
```

This updates all files with current progress and state.

### Resuming After Reset

Simply tell Claude:
> "Continue working on [task-name]. Check dev/active/[task-name]/ for context."

Claude reads the files and resumes exactly where you left off.

## File Organization

```
dev/
├── README.md              # This file
├── active/                # Current work
│   ├── github-integration/
│   │   ├── github-integration-plan.md
│   │   ├── github-integration-context.md
│   │   └── github-integration-tasks.md
│   └── jira-sync/
│       └── ...
└── archive/               # Completed work (optional)
    └── completed-task/
        └── ...
```

## When to Use

**Use for:**
- Complex multi-session tasks
- Features with many moving parts
- Work likely to span multiple sessions
- Implementation phases from PRD

**Skip for:**
- Simple bug fixes
- Single-file changes
- Quick updates

**Rule of thumb:** If it takes more than 2 hours or spans multiple sessions, use dev docs.

## Django-Specific Tips

When documenting Django tasks, always note:
- Which apps are being modified
- Migration status (pending/applied)
- Test coverage status
- URL patterns (team vs non-team)
- Celery tasks if applicable
