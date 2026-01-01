# Dashboard Insight LLM Testing and Prompt Evaluation - Plan

**Last Updated**: 2025-12-31
**Status**: In Progress
**Branch**: `main` (integrated into existing dashboard-insights feature)

## Executive Summary

This plan covers the testing and evaluation framework for the LLM-powered dashboard insights feature. The goal is to ensure that the LLM prompt produces high-quality, CTO-relevant insights that correctly prioritize and interpret engineering metrics data.

## Current State Analysis

### Completed Work
- **Dashboard Insights Feature** (Phase 1-5): Fully implemented with 96 tests
- **Model Configuration**: Updated from deprecated `deepseek-r1-distill-qwen-32b` to `openai/gpt-oss-20b`
- **JSON Schema Validation**: Strict schema with `additionalProperties: false`
- **Fallback Strategy**: Two-pass model fallback (primary → fallback → rule-based)
- **Golden Tests**: 16 test scenarios created in `insight_golden_tests.py`
- **Promptfoo Config**: 8 tests configured in `insight_promptfoo.yaml`

### Key Files
| File | Purpose |
|------|---------|
| `apps/metrics/services/insight_llm.py` | LLM service with model config, schema, and system prompt |
| `apps/metrics/prompts/templates/insight/user.jinja2` | User prompt template (metrics data) |
| `apps/metrics/prompts/insight_golden_tests.py` | 16 golden test scenarios |
| `apps/metrics/prompts/insight_promptfoo.yaml` | Promptfoo evaluation config |

### Model Configuration
```python
INSIGHT_MODEL = "openai/gpt-oss-20b"        # Primary: fast, cheap, good JSON
INSIGHT_FALLBACK_MODEL = "llama-3.3-70b-versatile"  # Fallback: reliable reasoning
```

## Proposed Future State

### Target Outcomes
1. **100% golden test pass rate** on primary model
2. **Prompt versioning** for tracking changes
3. **Automated evaluation** in CI/CD pipeline
4. **Time range adaptation** (weekly vs monthly language)
5. **Model comparison** dashboards

### Priority Order for Headlines
The system prompt enforces this priority for CTO-relevant insights:
1. Quality crisis (revert_rate > 8%)
2. AI impact significant (adoption > 40% AND |cycle_time_diff| > 25%)
3. Severe slowdown (cycle_time pct_change > 50%)
4. Major throughput change (|pct_change| > 30%)
5. Bottleneck detected
6. Bus factor risk (top_contributor_pct > 50%)
7. Otherwise: Summarize notable change

## Implementation Phases

### Phase 1: Golden Test Framework (COMPLETED)
- [x] Create `InsightGoldenTest` dataclass
- [x] Define 16 test scenarios covering all priority categories
- [x] Implement `get_insight_test_data()` helper
- [x] Add `to_promptfoo_test()` converter

### Phase 2: Promptfoo Integration (IN PROGRESS)
- [x] Create `insight_promptfoo.yaml` configuration
- [x] Configure GPT-OSS-20B as primary provider
- [x] Configure Llama-3.3-70B as fallback provider
- [ ] Fix JavaScript assertion syntax issues
- [ ] Achieve 100% pass rate on primary model

### Phase 3: Prompt Versioning (PENDING)
- [ ] Add PROMPT_VERSION constant to insight_llm.py
- [ ] Track prompt changes in version control
- [ ] Create prompt changelog

### Phase 4: CI/CD Integration (PENDING)
- [ ] Add promptfoo eval to GitHub Actions
- [ ] Set pass rate threshold (e.g., 80%)
- [ ] Generate evaluation reports

### Phase 5: Advanced Evaluation (FUTURE)
- [ ] Add model comparison (OSS-20B vs OSS-120B)
- [ ] Test with real production data samples
- [ ] Create evaluation dashboard

## Detailed Tasks

### Task 1: Fix Promptfoo Assertions
**Effort**: S | **Priority**: P1 | **Status**: In Progress

**Current Issue**: JavaScript assertions are failing due to syntax issues.

**Acceptance Criteria**:
- All 8 promptfoo tests pass on GPT-OSS-20B
- Assertions use single-line JavaScript syntax
- Error handling for JSON parse failures

**Implementation**:
```yaml
assert:
  - type: javascript
    value: "JSON.parse(output).headline.toLowerCase().includes('revert')"
```

### Task 2: Add Prompt Version Tracking
**Effort**: S | **Priority**: P2 | **Status**: Pending

**Acceptance Criteria**:
- PROMPT_VERSION constant in insight_llm.py (e.g., "1.0.0")
- Version included in promptfoo config
- Version logged with each insight generation

### Task 3: Expand Golden Test Coverage
**Effort**: M | **Priority**: P2 | **Status**: Pending

**Acceptance Criteria**:
- Add edge cases: zero AI adoption, zero throughput change
- Add time range variations (7, 14, 30, 90 days)
- Add multi-bottleneck scenarios

### Task 4: CI/CD Evaluation Pipeline
**Effort**: L | **Priority**: P3 | **Status**: Pending

**Acceptance Criteria**:
- GitHub Action runs `npx promptfoo eval` on PR
- Fail if pass rate < 80%
- Cache API responses to reduce costs
- Generate markdown report artifact

## Risk Assessment

| Risk | Impact | Likelihood | Mitigation |
|------|--------|------------|------------|
| Model deprecation | High | Medium | Two-pass fallback, monitor Groq announcements |
| Prompt regression | Medium | Medium | Golden tests catch regressions |
| Rate limiting | Low | Low | Request caching, backoff |
| Cost overrun | Low | Low | OSS-20B is $0.04/1M tokens |

## Success Metrics

| Metric | Target | Current |
|--------|--------|---------|
| Golden test pass rate (Python) | 100% | 100% (16/16) |
| Promptfoo pass rate (GPT-OSS-20B) | 100% | 25% (4/16) |
| Promptfoo pass rate (Llama-3.3) | 80% | 50% |
| Prompt version tracking | Yes | No |
| CI/CD integration | Yes | No |

## Required Resources

### Dependencies
- `groq` Python SDK (installed)
- `npx promptfoo` (installed via npm)
- GROQ_API_KEY environment variable

### Estimated Effort
- Phase 2 completion: 2-4 hours
- Phase 3: 1-2 hours
- Phase 4: 4-6 hours
- Phase 5: 8-12 hours

## Commands

```bash
# Run golden tests with live LLM
GROQ_API_KEY=$GROQ_API_KEY .venv/bin/python -c "
from apps.metrics.prompts.insight_golden_tests import INSIGHT_GOLDEN_TESTS, get_insight_test_data
from apps.metrics.services.insight_llm import generate_insight
for test in INSIGHT_GOLDEN_TESTS:
    result = generate_insight(get_insight_test_data(test))
    print(f'{test.id}: {result.get(\"headline\", \"\")[:60]}...')
"

# Run promptfoo evaluation
npx promptfoo eval -c apps/metrics/prompts/insight_promptfoo.yaml

# View promptfoo results
npx promptfoo view
```
