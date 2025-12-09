---
description: Create comprehensive development documentation for a task with plan, context, and tasks files
argument-hint: Describe the task (e.g., "implement GitHub integration", "add Jira sync")
---

You are an elite strategic planning specialist for Django/Python projects. Create a comprehensive, actionable plan for: $ARGUMENTS

## Instructions

1. **Analyze the request** and determine the scope of planning needed
2. **Examine relevant files** in the codebase to understand current state:
   - Check `prd/` for product requirements
   - Check `apps/` for existing Django apps
   - Check `CLAUDE.md` for coding guidelines
3. **Create a structured plan** with:
   - Executive Summary
   - Current State Analysis
   - Proposed Future State
   - Implementation Phases (broken into sections)
   - Detailed Tasks (actionable items with clear acceptance criteria)
   - Risk Assessment and Mitigation Strategies
   - Success Metrics
   - Required Resources and Dependencies

4. **Task Breakdown Structure**:
   - Each major section represents a phase or component
   - Number and prioritize tasks within sections
   - Include clear acceptance criteria for each task
   - Specify dependencies between tasks
   - Estimate effort levels (S/M/L/XL)

5. **Create task management structure**:
   - Create directory: `dev/active/[task-name]/` (relative to project root)
   - Generate three files:
     - `[task-name]-plan.md` - The comprehensive plan
     - `[task-name]-context.md` - Key files, decisions, dependencies
     - `[task-name]-tasks.md` - Checklist format for tracking progress
   - Include "Last Updated: YYYY-MM-DD" in each file

## Django-Specific Considerations

When planning, consider:
- Which Django apps will be created/modified
- Model changes and migrations needed
- View structure (function-based preferred, per CLAUDE.md)
- URL patterns (team_urlpatterns vs urlpatterns)
- Template structure
- Celery tasks for async operations
- Test coverage requirements (TDD workflow)

## Quality Standards

- Plans must be self-contained with all necessary context
- Use clear, actionable language
- Include specific technical details
- Consider both technical and business perspectives
- Account for potential risks and edge cases
- Follow project conventions from CLAUDE.md

## Context References

- Check `prd/` for product requirements and implementation phases
- Check `CLAUDE.md` for coding guidelines
- Check existing apps in `apps/` for patterns to follow
- Reference `apps/teams/` for team-scoped functionality patterns

**Note**: This command is ideal to use AFTER discussing requirements when you have a clear vision of what needs to be done. It creates persistent task structure that survives context resets.
