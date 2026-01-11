# Copilot Mock Data Realism - Tasks

**Last Updated: 2026-01-11**

## Progress Overview

| Phase | Status | Progress |
|-------|--------|----------|
| Phase 0: Schema Fix | Not Started | 0/8 |
| Phase 1: Acceptance Rates | Not Started | 0/4 |
| Phase 2: Temporal Patterns | Not Started | 0/4 |
| Phase 3: Language Rates | Not Started | 0/3 |
| Phase 4: Power Users | Not Started | 0/3 |
| Phase 5: Onboarding Scenario | Not Started | 0/3 |

---

## Phase 0: Fix Schema to Match Official GitHub API (CRITICAL)

> **Goal**: Generator produces official GitHub API format, parser aggregates correctly

### 0.1 Generator Schema Fix

- [ ] **0.1.1** Write failing test: `test_generator_produces_official_nested_schema`
  - Test that `_generate_day()` output has `editors > models > languages` structure
  - Verify field names are `total_code_suggestions`, `total_code_acceptances`
  - **File**: `apps/integrations/tests/test_copilot_mock_data.py`

- [ ] **0.1.2** Update `_generate_editors()` to include `models` array
  - Each editor should have a `models` array with at least one model
  - Model should contain `languages` array with completion data
  - **File**: `apps/integrations/services/copilot_mock_data.py`

- [ ] **0.1.3** Rename fields to match official API
  - `total_completions` → `total_code_suggestions`
  - `total_acceptances` → `total_code_acceptances`
  - `total_lines_suggested` → `total_code_lines_suggested`
  - `total_lines_accepted` → `total_code_lines_accepted`
  - **File**: `apps/integrations/services/copilot_mock_data.py`

- [ ] **0.1.4** Remove top-level `total_completions` from `copilot_ide_code_completions`
  - Official API doesn't have aggregate totals at top level
  - Move completion data ONLY into `editors > models > languages`
  - **File**: `apps/integrations/services/copilot_mock_data.py`

### 0.2 Parser Aggregation Fix

- [ ] **0.2.1** Write failing test: `test_parse_aggregates_from_nested_structure`
  - Test with official format input
  - Verify totals are summed across all editors/models
  - **File**: `apps/integrations/tests/test_copilot_metrics.py`

- [ ] **0.2.2** Update `parse_metrics_response()` to aggregate from nested structure
  - Loop through `editors > models > languages`
  - Sum `total_code_suggestions` across all nested languages
  - Use correct field names for mapping
  - **File**: `apps/integrations/services/copilot_metrics.py`

### 0.3 Test Fixture Updates

- [ ] **0.3.1** Update all mock data test fixtures to official format
  - Update ~40 tests in `test_copilot_mock_data.py`
  - Update fixtures in `test_copilot_metrics.py`
  - Update any other test files using mock Copilot data
  - **Files**: `apps/integrations/tests/test_copilot_*.py`

- [ ] **0.3.2** Run full test suite and fix any remaining failures
  - `make test ARGS='apps.integrations'`
  - Fix any edge cases or missed field mappings

---

## Phase 1: Calibrate Acceptance Rates

> **Goal**: Align acceptance rates with real-world ~30% average

- [ ] **1.1** Update `SCENARIO_CONFIGS` with realistic rates
  - `high_adoption`: (0.40, 0.55) → (0.30, 0.38)
  - `mixed_usage`: (0.15, 0.65) → (0.20, 0.40)
  - `growth`: end_rate 0.70 → 0.38
  - `decline`: start_rate 0.70 → 0.38
  - **File**: `apps/integrations/services/copilot_mock_data.py:54-88`

- [ ] **1.2** Fix lines acceptance rate to be lower than suggestions
  - Lines acceptance = 60-70% of suggestions acceptance
  - Update `_generate_day()` lines calculation
  - **File**: `apps/integrations/services/copilot_mock_data.py:246-248`

- [ ] **1.3** Update test assertions for new rate ranges
  - Update `test_high_adoption_scenario` assertions
  - Update `test_mixed_usage_scenario` assertions
  - Update `test_growth_scenario_weekly_progression` assertions
  - **File**: `apps/integrations/tests/test_copilot_mock_data.py`

- [ ] **1.4** Verify all scenarios with manual check
  - Generate data for each scenario
  - Calculate average acceptance rates
  - Confirm ~30% average

---

## Phase 2: Add Temporal Patterns (Weekend/Weekday)

> **Goal**: Model realistic weekday/weekend variance

- [ ] **2.1** Write failing test: `test_weekend_has_lower_volume`
  - Generate 2 weeks of data
  - Verify weekend days have 30-40% lower completions
  - **File**: `apps/integrations/tests/test_copilot_mock_data.py`

- [ ] **2.2** Add weekend detection in `_generate_day()`
  - Check `current_date.weekday() >= 5`
  - Apply volume reduction (0.60-0.70x)
  - Apply slight acceptance rate increase (1.05-1.10x)
  - **File**: `apps/integrations/services/copilot_mock_data.py`

- [ ] **2.3** Add `model_weekends` parameter to `generate()`
  - Default to `True` for realistic behavior
  - Allow `False` for backward compatibility in tests
  - **File**: `apps/integrations/services/copilot_mock_data.py`

- [ ] **2.4** Update tests to verify weekend patterns
  - Add assertions for weekend volume reduction
  - Verify acceptance rate is slightly higher on weekends
  - **File**: `apps/integrations/tests/test_copilot_mock_data.py`

---

## Phase 3: Language-Specific Acceptance Rates

> **Goal**: Different languages have different acceptance rates

- [ ] **3.1** Define `LANGUAGE_ACCEPTANCE_MODIFIERS` constant
  ```python
  LANGUAGE_ACCEPTANCE_MODIFIERS = {
      "python": 1.0,
      "typescript": 1.05,
      "javascript": 0.95,
      "go": 1.0,
      "html": 0.70,
      "css": 0.65,
      "json": 0.60,
      "sql": 0.75,
  }
  ```
  - **File**: `apps/integrations/services/copilot_mock_data.py`

- [ ] **3.2** Update `_generate_model_languages()` to apply modifiers
  - Multiply base acceptance rate by language modifier
  - Expand `LANGUAGES` list to include more languages
  - **File**: `apps/integrations/services/copilot_mock_data.py`

- [ ] **3.3** Add test for language variance
  - Verify Python has higher acceptance than HTML
  - **File**: `apps/integrations/tests/test_copilot_mock_data.py`

---

## Phase 4: Power User Distribution

> **Goal**: 20% of users generate 80% of completions

- [ ] **4.1** Write failing test: `test_power_user_distribution`
  - Seed data for team with 10+ members
  - Verify top 20% generate ~80% of completions
  - **File**: `apps/metrics/tests/test_seed_copilot_demo.py` (create if needed)

- [ ] **4.2** Replace uniform distribution with power law
  ```python
  user_tier = rng.random()
  if user_tier < 0.20:      # Power users
      member_factor = rng.uniform(2.0, 4.0)
  elif user_tier < 0.50:    # Middle tier
      member_factor = rng.uniform(0.8, 1.5)
  else:                     # Low usage
      member_factor = rng.uniform(0.1, 0.6)
  ```
  - **File**: `apps/metrics/management/commands/seed_copilot_demo.py:159-163`

- [ ] **4.3** Update seeding tests to verify distribution
  - **File**: `apps/metrics/tests/test_seed_copilot_demo.py`

---

## Phase 5: New Team Onboarding Scenario

> **Goal**: Model 11-week adoption curve

- [ ] **5.1** Add `NEW_TEAM_ONBOARDING` to `CopilotScenario` enum
  - **File**: `apps/integrations/services/copilot_mock_data.py:16-24`

- [ ] **5.2** Add scenario config with progressive rates
  ```python
  CopilotScenario.NEW_TEAM_ONBOARDING.value: ScenarioConfig(
      start_acceptance_rate=0.15,
      end_acceptance_rate=0.35,
      active_users_range=(5, 25),
      completions_range=(50, 2000),
      ramp_up_weeks=11,  # New field
  ),
  ```
  - **File**: `apps/integrations/services/copilot_mock_data.py`

- [ ] **5.3** Add test for onboarding progression
  - Verify week 1-2: 15-20% acceptance, low volume
  - Verify week 9-11: 30-35% acceptance, full volume
  - **File**: `apps/integrations/tests/test_copilot_mock_data.py`

---

## Verification Checklist

- [ ] All tests pass: `make test ARGS='apps.integrations'`
- [ ] Generator produces official GitHub API format
- [ ] Parser correctly aggregates nested data
- [ ] Acceptance rates average ~30%
- [ ] Weekend data shows reduced volume
- [ ] Dashboard displays correctly after re-seeding
- [ ] No regressions in AI Adoption dashboard

---

## Commands Reference

```bash
# Run Copilot tests
.venv/bin/pytest apps/integrations/tests/test_copilot*.py -v

# Reseed demo data
.venv/bin/python manage.py seed_copilot_demo --team=demo --scenario=mixed_usage --weeks=8 --clear-existing

# Quick acceptance rate check
.venv/bin/python -c "
from apps.integrations.services.copilot_mock_data import CopilotMockDataGenerator
gen = CopilotMockDataGenerator(seed=42)
data = gen.generate('2025-01-01', '2025-01-07', scenario='high_adoption')
for d in data:
    # After schema fix, need to aggregate from nested structure
    print(d['date'])
"
```
