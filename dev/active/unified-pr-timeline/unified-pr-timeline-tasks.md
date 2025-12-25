# Unified PR Timeline - Tasks

Last Updated: 2025-12-25

## Phase 1: Core Timeline Builder (TDD)

### RED Phase - Write Failing Tests
- [x] Write test for TimelineEvent dataclass creation
- [x] Write test for TimelineEvent field types
- [x] Write test for build_timeline with commits only
- [x] Write test for build_timeline with reviews only
- [x] Write test for build_timeline with comments only
- [x] Write test for build_timeline mixed events sorted
- [x] Write test for build_timeline empty PR
- [x] Write test for format_timeline basic output
- [x] Write test for format_timeline 15 event limit
- [x] Write test for format_timeline empty list
- [x] Verify all 10 tests FAIL with ImportError

### GREEN Phase - Make Tests Pass
- [ ] Add TimelineEvent dataclass to llm_prompts.py
- [ ] Add build_timeline() function
  - [ ] Collect commits with committed_at
  - [ ] Collect reviews with submitted_at
  - [ ] Collect comments with comment_created_at
  - [ ] Add MERGED event if merged_at exists
  - [ ] Sort by timestamp ascending
  - [ ] Return list[TimelineEvent]
- [ ] Add format_timeline() function
  - [ ] Format each event as [+X.Xh] EVENT_TYPE: content
  - [ ] Special format for REVIEW with state
  - [ ] Limit to 15 events
  - [ ] Return "Timeline:\n" + events
- [ ] Verify all 10 tests PASS

### REFACTOR Phase - Improve Code
- [ ] Review code for duplication
- [ ] Consolidate with existing timestamp helpers
- [ ] Improve readability if needed
- [ ] Verify tests still pass

## Phase 2: Template Integration

### Jinja Template Updates
- [ ] Add timeline parameter to user.jinja2
- [ ] Add Timeline section template
- [ ] Remove separate commits/reviews/comments sections
- [ ] Update render.py to accept timeline param

### System Prompt Updates
- [ ] Update intro.jinja2 with timeline docs
- [ ] Explain event types (COMMIT, REVIEW, COMMENT, MERGED)
- [ ] Show example timeline interpretation
- [ ] Explain cause-effect analysis

### Python Function Updates
- [ ] Update get_user_prompt() to accept timeline
- [ ] Update build_llm_pr_context() to call build_timeline()
- [ ] Ensure Jinja and Python output match

## Phase 3: Golden Tests & Verification

### Update Golden Tests
- [ ] Add timeline field to GoldenTest dataclass
- [ ] Update health_slow_review with timeline
- [ ] Update health_fast_small with timeline
- [ ] Update health_hotfix_revert with timeline
- [ ] Update health_draft_wip with timeline

### Verification
- [ ] Run all prompts tests: `.venv/bin/pytest apps/metrics/prompts/tests/ -v`
- [ ] Verify template equivalence test passes
- [ ] Export promptfoo config
- [ ] Run promptfoo eval (target: 90%+ pass rate)

## Phase 4: Finalize

- [ ] Update context.md with final state
- [ ] Commit all changes with descriptive message
- [ ] Move task to dev/completed/

## Quick Commands

```bash
# Run failing tests (RED)
.venv/bin/pytest apps/metrics/tests/test_llm_prompts.py -k timeline -v

# Run all llm_prompts tests
.venv/bin/pytest apps/metrics/tests/test_llm_prompts.py -v

# Run prompt template tests
.venv/bin/pytest apps/metrics/prompts/tests/ -v

# Export promptfoo
.venv/bin/python manage.py export_prompts --output dev/active/ai-detection-pr-descriptions/experiments/

# Run promptfoo eval
cd dev/active/ai-detection-pr-descriptions/experiments && npx promptfoo eval
```

## Event Format Reference

```
Timeline:
- [+0.5h] COMMIT: Add notification models
- [+4.0h] COMMIT: Implement WebSocket consumer
- [+48.0h] REVIEW [CHANGES_REQUESTED]: Sarah Tech Lead: Need rate limiting
- [+48.5h] COMMENT: Sarah Tech Lead: Can you also add tests?
- [+52.0h] COMMIT: Fix review feedback
- [+72.0h] REVIEW [APPROVED]: Bob Backend: LGTM
- [+96.0h] MERGED
```
