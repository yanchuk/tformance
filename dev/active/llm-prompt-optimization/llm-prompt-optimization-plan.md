# LLM Prompt Optimization Plan

**Last Updated**: 2026-01-01
**Status**: ✅ COMPLETED
**Prompt Version**: 7.0.0 → 8.0.0

---

## Executive Summary

This plan improved the LLM prompts used for PR analysis, focusing on:
1. **Technology Detection** - Expanded from 9 lines to ~100 lines with structured guidance
2. **Summary Generation** - Added PR type decision tree and quality constraints
3. **Prompt Structure** - Applied OpenAI/Anthropic best practices consistently

**Results**: 100% pass rate (57/57 tests) up from 95.7% baseline (45/47).

---

## Final Results

| Metric | Baseline (v7.0.0) | Final (v8.0.0) | Change |
|--------|-------------------|----------------|--------|
| **Total Tests** | 47 | 57 | +10 new |
| **Passed** | 45 (95.7%) | 57 (100%) | +12 |
| **Failed** | 2 | 0 | Fixed all |
| **Prompt Tokens** | ~1,500 | ~2,100 | +40% |

### Fixed Issues
1. `pos_coderabbit_review` - Now detects CodeRabbit as AI tool
2. `pos_greptile_codebase` - Now detects Greptile as AI tool

### New Test Coverage
- 10 technology detection tests (Rust, Next.js, Terraform, Swift, etc.)
- All pass with 100% accuracy

---

## Implementation Completed

### Phase 1: Baseline Measurement ✅

**Completed**: 2026-01-01

- Ran full promptfoo evaluation with v7.0.0 prompts
- Results: 47 tests, 45 passed, 2 failed
- Output saved to `results/baseline-v7.0.0/`

### Phase 2: Tech Detection Enhancement ✅

**Completed**: 2026-01-01

Enhanced `tech_detection.jinja2` with:
- File extension → language mapping table (22 extensions)
- Framework detection signal table (16 frameworks)
- Category assignment rules with disambiguation
- 5 few-shot examples with reasoning

### Phase 3: Summary Quality Enhancement ✅

**Completed**: 2026-01-01

Created new `summary_guidelines.jinja2` with:
- PR type decision tree (7-step priority order)
- Common classification mistakes section
- Title/description rules
- 5 type examples with reasoning

### Phase 4: Prompt Structure Optimization ✅

**Completed**: 2026-01-01

- Enhanced Identity section in `intro.jinja2`
- Updated PROMPT_VERSION to 8.0.0
- All 57 tests passing

### Phase 5: Langfuse Integration ⏸️

**Status**: Deferred

User decided not to introduce Langfuse at this time. Can be revisited later for:
- Version control without code deploys
- A/B testing via labels
- Non-dev prompt editing
- Cost/latency tracking per version

---

## Files Modified

| File | Change |
|------|--------|
| `apps/metrics/prompts/templates/sections/tech_detection.jinja2` | Expanded from 9 to ~100 lines |
| `apps/metrics/prompts/templates/sections/summary_guidelines.jinja2` | NEW file |
| `apps/metrics/prompts/templates/sections/intro.jinja2` | Enhanced identity |
| `apps/metrics/prompts/templates/system.jinja2` | Added summary_guidelines include |
| `apps/metrics/services/llm_prompts.py` | PROMPT_VERSION = "8.0.0" |
| `apps/metrics/prompts/golden_tests.py` | Added 10 new tests |

---

## Token Cost Analysis

| Section | Before | After | Added |
|---------|--------|-------|-------|
| Tech Detection | ~80 tokens | ~350 tokens | +270 |
| Summary Guidelines | 0 | ~400 tokens | +400 |
| Identity | ~30 tokens | ~50 tokens | +20 |
| Examples | ~0 | ~200 tokens | +200 |
| **Total** | ~1,500 | ~2,100 | **+600** |

**Cost Impact**: ~$0.0002/request increase. Justified by 100% vs 95.7% accuracy.

---

## Verification Commands

```bash
# Run golden tests
DJANGO_SETTINGS_MODULE=tformance.settings .venv/bin/pytest apps/metrics/prompts/tests/ -v

# Export and run promptfoo evaluation
python manage.py export_prompts --output results/verify
cd results/verify && npx promptfoo eval -c promptfoo.yaml
```

---

## Rollback Plan

If v8.0.0 causes issues:

1. Revert PROMPT_VERSION to "7.0.0" in `llm_prompts.py`
2. Remove `{% include 'sections/summary_guidelines.jinja2' %}` from system.jinja2
3. Document issues for next iteration

---

## Lessons Learned

1. **Few-shot examples are powerful** - Adding 5 examples per section dramatically improved accuracy
2. **Decision trees work** - Explicit priority order for PR type classification eliminated ambiguity
3. **Tables > prose** - Mapping tables are easier for LLMs to parse than natural language descriptions
4. **Token cost is acceptable** - 40% increase is worth 100% accuracy
