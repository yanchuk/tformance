# Copilot Mock Data Generator - Real-World Realism Improvements

**Last Updated: 2026-01-11**

## Executive Summary

The Copilot mock data generator needs improvements to produce realistic data patterns that match real-world GitHub Copilot usage. Additionally, a **critical schema mismatch** was discovered between our mock data format and the official GitHub Copilot Metrics API.

### Goals
1. Fix schema compatibility with official GitHub Copilot Metrics API
2. Calibrate acceptance rates to match real-world benchmarks (~30%)
3. Add temporal patterns (weekday/weekend variance)
4. Implement language-specific acceptance rates
5. Model power user distribution (80/20 rule)
6. Add new team onboarding ramp-up scenario

### Success Criteria
- `parse_metrics_response()` handles both official API and mock formats
- All scenarios produce acceptance rates within real-world ranges
- Weekend data shows 30-40% lower volume with slightly higher acceptance
- Tests pass with updated realistic assertions
- Dashboard displays realistic patterns

---

## Current State Analysis

### What Works Well
- **Reproducibility**: Deterministic RNG with seed parameter
- **Scenario Diversity**: 6 scenarios covering different adoption patterns
- **Test Coverage**: 40+ tests covering schema and constraints
- **Team Scaling**: Proper scaling based on team size

### Critical Issue: API Schema Mismatch

**Official GitHub API** uses nested structure:
```
editors > models > languages > total_code_suggestions
```

**Our mock data** uses flat structure:
```
languages > total_completions (direct)
```

The `parse_metrics_response()` function expects fields that don't exist in the official API:
- `code_completions.total_completions` - Not in official API
- `lang.total_completions` - Official API nests under `editors > models`

### Real-World Benchmarks vs Current Mock

| Metric | Real-World | Current Mock | Target |
|--------|-----------|--------------|--------|
| Average acceptance | ~30-33% | 25-50% | 28-35% |
| High performer | 33-40% | 40-55% | 30-38% |
| Lines acceptance | ~20% | Same as suggestions | 60-70% of suggestion rate |
| Weekend volume | 30-40% lower | Same as weekday | Model reduction |
| User distribution | Power law | Uniform | 80/20 rule |

---

## Implementation Plan

### Phase 0: Fix Schema to Match Official GitHub API (CRITICAL)
**Effort: L** | **Priority: P0** | **Risk: Medium**

> **REVISED**: Per plan review, fix the GENERATOR to produce official schema, NOT the parser to accept legacy format. This eliminates technical debt.

**The Problem**:
- Mock generator produces flat structure with wrong field names
- Parser expects flat structure with wrong field names
- Both are incompatible with real GitHub Copilot API

**Correct Approach** (Clean Break):
1. **Update generator** to produce official nested schema (`editors > models > languages`)
2. **Update field names** to match official API:
   - `total_completions` → `total_code_suggestions`
   - `total_acceptances` → `total_code_acceptances`
3. **Update parser** to aggregate from nested structure
4. **Update ALL test fixtures** (40+ tests) to use official format
5. **Remove legacy format support** (no backward compatibility)

**TDD Workflow**:
1. Write failing test for official API format parsing
2. Write failing test for generator producing official format
3. Update generator `_generate_day()` to produce nested structure
4. Update parser to aggregate across editors/models
5. Update all test fixtures

### Phase 1: Calibrate Acceptance Rates
**Effort: S** | **Priority: P1** | **Risk: Low**

Update scenario configurations to match real-world data.

**Changes**:
- `high_adoption`: (0.40, 0.55) → (0.30, 0.38)
- `mixed_usage`: (0.15, 0.65) → (0.20, 0.40)
- `growth` end rate: 0.70 → 0.38
- `decline` start rate: 0.70 → 0.38
- Lines acceptance: 60-70% of suggestions rate

### Phase 2: Add Temporal Patterns
**Effort: M** | **Priority: P2** | **Risk: Low**

Model weekend/weekday variance in generated data.

**Approach**:
1. Detect weekend via `current_date.weekday() >= 5`
2. Apply modifiers:
   - Completions: 0.60-0.70x on weekends
   - Active users: 0.50-0.65x on weekends
   - Acceptance rate: 1.05-1.10x on weekends
3. Add `model_weekends` parameter (default True)

### Phase 3: Language-Specific Rates
**Effort: S** | **Priority: P2** | **Risk: Low**

Different languages have different acceptance rates.

**Modifiers**:
```python
LANGUAGE_ACCEPTANCE_MODIFIERS = {
    "python": 1.0,        # baseline
    "typescript": 1.05,   # slightly higher
    "javascript": 0.95,   # slightly lower
    "go": 1.0,
    "html": 0.70,         # notably lower
    "css": 0.65,
    "json": 0.60,
    "sql": 0.75,
}
```

### Phase 4: Power User Distribution
**Effort: S** | **Priority: P3** | **Risk: Low**

Replace uniform distribution with power law in seeding.

**Approach**:
```python
user_tier = rng.random()
if user_tier < 0.20:      # Top 20% (power users)
    member_factor = rng.uniform(2.0, 4.0)
elif user_tier < 0.50:    # Middle 30%
    member_factor = rng.uniform(0.8, 1.5)
else:                     # Bottom 50%
    member_factor = rng.uniform(0.1, 0.6)
```

### Phase 5: Onboarding Ramp-Up Scenario
**Effort: M** | **Priority: P3** | **Risk: Low**

New scenario modeling 11-week adoption curve.

**Progression**:
- Week 1-2: 15-20% acceptance, 20% volume
- Week 3-5: 20-25% acceptance, 40% volume
- Week 6-8: 25-30% acceptance, 70% volume
- Week 9-11: 30-35% acceptance, 100% volume

---

## Risk Assessment

| Risk | Likelihood | Impact | Mitigation |
|------|------------|--------|------------|
| Breaking existing tests | High | Medium | Update assertions, run full test suite |
| Schema detection fails | Low | High | Comprehensive format detection logic |
| Dashboard displays incorrectly | Low | Medium | Manual visual verification |
| Backward compatibility issues | Medium | Medium | Support both formats |

---

## Verification Plan

### Automated Tests
```bash
# Run all Copilot-related tests
.venv/bin/pytest apps/integrations/tests/test_copilot*.py -v

# Run with coverage
.venv/bin/pytest apps/integrations/tests/test_copilot*.py --cov=apps/integrations/services
```

### Manual Verification
1. Generate mock data for each scenario
2. Calculate average acceptance rates (should be ~30%)
3. Verify weekend patterns show reduced volume
4. Check language distribution has variance

### Dashboard Check
```bash
# Seed fresh data
.venv/bin/python manage.py seed_copilot_demo --team=demo --scenario=mixed_usage --weeks=8 --clear-existing

# Check dashboard at http://localhost:8000/a/demo/metrics/ai-adoption/
```

---

## Sources

**Official API Documentation:**
- [GitHub Copilot Metrics API](https://docs.github.com/en/rest/copilot/copilot-metrics)

**Real-world benchmarks:**
- [GitHub Copilot Adoption Trends - Opsera](https://opsera.ai/blog/github-copilot-adoption-trends-insights-from-real-data/)
- [Measuring GitHub Copilot's Impact - ACM](https://cacm.acm.org/research/measuring-github-copilots-impact-on-productivity/)
- [GitHub Copilot Research with Accenture](https://github.blog/news-insights/research/research-quantifying-github-copilots-impact-in-the-enterprise-with-accenture/)
