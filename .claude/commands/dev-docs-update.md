---
description: Update development documentation before context compaction or session end
argument-hint: Optional - specific context or tasks to focus on (leave empty for comprehensive update)
---

We're approaching context limits or ending the session. Please update the development documentation to ensure seamless continuation after context reset.

## Required Updates

### 1. Update Active Task Documentation

For each task in `dev/active/`:

**Update `[task-name]-context.md` with:**
- Current implementation state
- Key decisions made this session
- Files modified and why
- Any blockers or issues discovered
- Next immediate steps
- Last Updated timestamp

**Update `[task-name]-tasks.md` with:**
- Mark completed tasks as [x]
- Add any new tasks discovered
- Update in-progress tasks with current status
- Reorder priorities if needed

### 2. Capture Session Context

Include any relevant information about:
- Complex problems solved
- Architectural decisions made
- Tricky bugs found and fixed
- Integration points discovered
- Testing approaches used
- Django-specific patterns established

### 3. Document Django-Specific Progress

Track progress on:
- Models created/modified (migrations needed?)
- Views implemented
- URL patterns added
- Templates created
- Celery tasks defined
- Test coverage status

### 4. Document Unfinished Work

- What was being worked on when context limit approached
- Exact state of any partially completed features
- Commands that need to be run on restart (migrations, tests)
- Any temporary workarounds that need permanent fixes

### 5. Create Handoff Notes

If switching to a new conversation:
- Exact file and line being edited
- The goal of current changes
- Any uncommitted changes that need attention
- Test commands to verify work:
  ```bash
  make test
  make ruff
  make migrations  # Check for missing migrations
  ```

## Additional Context: $ARGUMENTS

**Priority**: Focus on capturing information that would be hard to rediscover or reconstruct from code alone.

**Django-Specific**: Always note if migrations need to be created/applied, and which apps were modified.
