# Dashboard Insight LLM Testing - Tasks

**Last Updated**: 2025-12-31

## Phase 1: Golden Test Framework ✅ COMPLETED

- [x] Create `InsightGoldenTest` dataclass
- [x] Define 16 test scenarios covering all priority categories
- [x] Implement `get_insight_test_data()` helper
- [x] Add `to_promptfoo_test()` converter
- [x] Validate all 16 tests pass with live LLM (100% pass rate)

## Phase 2: Promptfoo Integration 🔄 IN PROGRESS

- [x] Create `insight_promptfoo.yaml` configuration
- [x] Configure GPT-OSS-20B as primary provider
- [x] Configure Llama-3.3-70B as fallback provider
- [x] Fix JavaScript assertion syntax (single-line format)
- [ ] **Refine assertions for higher pass rate**
  - Current: 4/16 passing (25%)
  - Target: 16/16 passing (100%)
- [ ] Test with different assertion strategies:
  - [ ] Looser keyword matching (synonyms)
  - [ ] Focus on priority/sentiment instead of headline
  - [ ] Use `contains-json` with partial matching

## Phase 3: Prompt Versioning ⏳ PENDING

- [ ] Add `PROMPT_VERSION` constant to `insight_llm.py`
- [ ] Include version in promptfoo config metadata
- [ ] Add version logging to insight generation
- [ ] Create CHANGELOG.md for prompt changes

## Phase 4: CI/CD Integration ⏳ PENDING

- [ ] Create GitHub Action workflow file
- [ ] Configure `npx promptfoo eval` command
- [ ] Set pass rate threshold (80%)
- [ ] Add caching for API responses
- [ ] Generate markdown report artifact
- [ ] Add PR comment with results summary

## Phase 5: Advanced Evaluation ⏳ FUTURE

- [ ] Add model comparison (OSS-20B vs OSS-120B)
- [ ] Test with real production data samples
- [ ] Create evaluation dashboard
- [ ] Add A/B testing capability for prompts

---

## Quick Commands

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

# View promptfoo results in browser
npx promptfoo view
```

---

## Success Metrics

| Metric | Target | Current | Status |
|--------|--------|---------|--------|
| Golden test pass rate (Python) | 100% | 100% | ✅ |
| Promptfoo pass rate (GPT-OSS-20B) | 100% | 25% | 🔄 |
| Promptfoo pass rate (Llama-3.3) | 80% | 50% | 🔄 |
| Prompt version tracking | Yes | No | ⏳ |
| CI/CD integration | Yes | No | ⏳ |

---

## Notes

- **Assertion strategy**: Current assertions expect specific keywords in headlines. Model outputs vary - consider checking `priority` and `sentiment` fields instead which are more deterministic.
- **Model behavior**: GPT-OSS-20B tends to use different vocabulary than Llama-3.3-70B. May need model-specific assertion tuning.
- **Time ranges**: Tests validated that model correctly adapts language for weekly (7d) vs monthly (30d) data.
