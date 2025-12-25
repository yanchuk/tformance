# Unified PR Timeline - Context

Last Updated: 2025-12-25 05:30 UTC

## Current State: A/B VALIDATION COMPLETE

Timeline feature implemented and committed (1a8c637). A/B evaluation completed.

## Completed Work

### Commit 1a8c637: Add unified PR timeline to LLM prompt (v6.3.0)

**Files Modified:**
- `apps/metrics/services/llm_prompts.py` - TimelineEvent, build_timeline(), format_timeline()
- `apps/metrics/tests/test_llm_prompts.py` - 10 TDD tests
- `apps/metrics/prompts/templates/user.jinja2` - Timeline section
- `apps/metrics/prompts/templates/sections/intro.jinja2` - Timeline docs
- `apps/metrics/prompts/render.py` - Timeline parameter

**TDD Cycle Completed:**
- RED: 10 failing tests written
- GREEN: All tests passing (247 total)
- REFACTOR: Extracted helpers (_get_member_display_name, _collect_timeline_events)

## Timeline Format

```
Timeline:
- [+0.5h] COMMIT: Add notification models
- [+48.0h] REVIEW [CHANGES_REQUESTED]: Sarah: Need rate limiting
- [+52.0h] COMMIT: Fix review feedback
- [+72.0h] REVIEW [APPROVED]: Bob: LGTM
- [+96.0h] MERGED
```

## Key Decisions Made

1. **Baseline**: `pr_created_at` (not `first_review_at`)
2. **Event limit**: 15 max
3. **MERGED event**: Included to show completion
4. **Comments count**: Hidden when timeline provided (redundant)
5. **No CI/CD**: Excluded per user request

## A/B Validation Results

### Summary

| Variant | Passed | Failed | Accuracy |
|---------|--------|--------|----------|
| Control (v6.2 no timeline) | 8 | 9 | 47.1% |
| Treatment (v6.3 with timeline) | 9 | 8 | **52.9%** |

**Result: Timeline provides modest improvement (+5.8 percentage points)**

### Key Findings

1. **Timeline helps with blocker detection**
   - Infrastructure migration: Control=medium risk, Treatment=**high risk** (correct)
   - GDPR compliance: Control=medium friction, Treatment=**high friction** (correct)
   - The timeline's long gaps (168h+) help LLM understand blockers

2. **Scope detection needs calibration**
   - LLM consistently underestimates scope (returns "medium" for 600+ lines)
   - Need to adjust prompt thresholds or ground truth expectations

3. **Hotfix risk not recognized**
   - LLM returns "medium" risk for hotfixes instead of "high"
   - "Hotfix: Yes" flag not a strong enough signal
   - May need explicit hotfix handling in prompt

### Test Cases

34 total test cases across 5 categories:
- 6 low friction PRs (3 control, 3 treatment)
- 6 high friction PRs (3 control, 3 treatment)
- 6 blocker PRs (3 control, 3 treatment)
- 6 quick response PRs (3 control, 3 treatment)
- 10 hotfix PRs (5 control, 5 treatment)

## Commands

```bash
# Run A/B evaluation
cd dev/active/ai-detection-pr-descriptions/experiments
GROQ_API_KEY=$GROQ_API_KEY npx promptfoo eval -c ab-timeline-comparison.yaml

# Run all timeline tests
.venv/bin/pytest apps/metrics/tests/test_llm_prompts.py -k timeline -v
```

## Files for A/B Testing

| File | Purpose |
|------|---------|
| `experiments/prompts/v6.2-no-timeline.txt` | Control (no timeline) |
| `experiments/prompts/v6.3-with-timeline.txt` | Treatment (with timeline) |
| `experiments/ab-timeline-comparison.yaml` | Promptfoo A/B config |
| `experiments/health-ground-truth.json` | Labeled test cases |
