# Unified PR Timeline - Tasks

Last Updated: 2025-12-25 05:15 UTC

## Phase 1: Core Timeline Builder (TDD) ✅ COMPLETE

### RED Phase - Write Failing Tests ✅
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

### GREEN Phase - Make Tests Pass ✅
- [x] Add TimelineEvent dataclass to llm_prompts.py
- [x] Add build_timeline() function
- [x] Add format_timeline() function
- [x] Verify all 10 tests PASS

### REFACTOR Phase - Improve Code ✅
- [x] Extract _get_member_display_name() helper
- [x] Extract _collect_timeline_events() helper
- [x] Verify tests still pass

## Phase 2: Template Integration ✅ COMPLETE

- [x] Add timeline parameter to user.jinja2
- [x] Add Timeline section template
- [x] Update render.py to accept timeline param
- [x] Update intro.jinja2 with timeline docs
- [x] Update PR_ANALYSIS_SYSTEM_PROMPT to v6.3.0
- [x] Hide comment count when timeline provided

## Phase 3: Commit ✅ COMPLETE

- [x] Run all tests (247 passed)
- [x] Commit: 1a8c637

## Phase 4: A/B Validation ✅ COMPLETE

### Create A/B Test Infrastructure ✅
- [x] Create v6.2-no-timeline.txt (control - without timeline section)
- [x] Create v6.3-with-timeline.txt (treatment - current prompt)
- [x] Create ab-timeline-comparison.yaml promptfoo config
- [x] Create health-ground-truth.json with 45 labeled PRs

### Dataset Categories (34 tests in yaml) ✅
- [x] 6 PRs: Fast merge, no rework → low friction, low risk
- [x] 6 PRs: Multiple review rounds → high friction
- [x] 6 PRs: Long gaps between events → high risk (blockers)
- [x] 6 PRs: Quick response to review → low friction
- [x] 10 PRs: Hotfix with fast turnaround → high risk, low friction

### Run Evaluation ✅
- [x] Run A/B comparison with promptfoo
- [x] Analyze HEALTH assessment accuracy
- [x] Document findings

### Results Summary
- Control (v6.2 no timeline): 47.1% accuracy
- Treatment (v6.3 with timeline): 52.9% accuracy
- **Timeline improves accuracy by +5.8 percentage points**

## Phase 5: Finalize

- [x] Update context.md with A/B results
- [ ] Move task to dev/completed/

## Quick Commands

```bash
# Run A/B comparison
cd dev/active/ai-detection-pr-descriptions/experiments
GROQ_API_KEY=$GROQ_API_KEY npx promptfoo eval -c ab-timeline-comparison.yaml

# View results
npx promptfoo view
```
