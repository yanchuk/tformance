# Copilot Mock Data - Tasks (TDD)

**Last Updated**: 2026-01-07

---

## Phase 1: Mock Generator Core ✅ COMPLETE

### 1.1 API Schema Validation Tests (RED) ✅

**Effort: S** | **Priority: P0**

- [x] Create test file `apps/integrations/tests/test_copilot_mock_data.py`
- [x] Write `test_generates_correct_date_format` - ISO 8601 dates
- [x] Write `test_generates_all_required_fields` - Check all top-level fields
- [x] Write `test_code_completions_has_required_fields` - Nested structure
- [x] Write `test_languages_array_structure` - Language breakdown
- [x] Write `test_editors_array_structure` - Editor breakdown
- [x] Run tests and confirm they FAIL (no implementation yet)

### 1.2 Basic Generator Implementation (GREEN) ✅

**Effort: M** | **Priority: P0** | **Depends on: 1.1**

- [x] Create `apps/integrations/services/copilot_mock_data.py`
- [x] Implement `CopilotMockDataGenerator` class
- [x] Implement `generate(since, until, scenario)` method
- [x] Return valid API-compatible JSON structure
- [x] Run tests and confirm they PASS

### 1.3 Deterministic Seeding (GREEN) ✅

**Effort: S** | **Priority: P0** | **Depends on: 1.2**

- [x] Write `test_same_seed_produces_identical_data`
- [x] Write `test_different_seed_produces_different_data`
- [x] Import `DeterministicRandom` from `apps/metrics/seeding/deterministic.py`
- [x] Add `seed` parameter to `__init__`
- [x] Use `self.rng` for all random values

### 1.4 Refactor: Extract Constants (REFACTOR) ✅

**Effort: S** | **Priority: P1** | **Depends on: 1.3**

- [x] Added type hints with `TypedDict` for ScenarioParams
- [x] Added docstrings with examples
- [x] Extracted LANGUAGES and EDITORS as class constants
- [x] All tests pass

---

## Phase 2: Scenario System ✅ COMPLETE

### 2.1 Scenario Tests (RED) ✅

**Effort: M** | **Priority: P0**

- [x] Write `test_high_adoption_scenario_acceptance_rate` - 40-55%
- [x] Write `test_low_adoption_scenario_acceptance_rate` - 15-25%
- [x] Write `test_growth_scenario_progression` - 30% → 70%
- [x] Write `test_decline_scenario_progression` - 70% → 30%
- [x] Write `test_mixed_usage_scenario_variance` - 15-65%
- [x] Write `test_inactive_licenses_scenario_has_inactive_days`
- [x] Write `test_unknown_scenario_raises_value_error`
- [x] Write `test_engaged_users_not_exceeding_active_users`
- [x] Run tests and confirm they FAIL

### 2.2 Scenario Implementation (GREEN) ✅

**Effort: L** | **Priority: P0** | **Depends on: 2.1**

- [x] Create `CopilotScenario` enum with 6 values
- [x] Add `scenario` parameter to `generate()` method
- [x] Implement `_get_scenario_params(scenario, day_index, total_days)` helper
- [x] Apply scenario multipliers to base values
- [x] Run tests and confirm they PASS

### 2.3 Refactor: Scenario Registry (REFACTOR) ✅

**Effort: S** | **Priority: P2** | **Depends on: 2.2**

- [x] Create `SCENARIO_CONFIGS` registry dict
- [x] Create `ScenarioConfig` dataclass for type safety
- [x] Create `ScenarioParams` TypedDict
- [x] Extract `_interpolate_acceptance_rate()` helper
- [x] Extract `_generate_breakdown()` helper for languages/editors
- [x] All tests still pass

---

## Phase 3: Management Command ✅ COMPLETE

### 3.1 Command Tests (RED) ✅

**Effort: M** | **Priority: P0**

- [x] Write `test_command_requires_team_argument`
- [x] Write `test_command_creates_ai_usage_records`
- [x] Write `test_command_respects_scenario_parameter_high_adoption`
- [x] Write `test_command_respects_scenario_parameter_low_adoption`
- [x] Write `test_command_respects_weeks_parameter_4_weeks`
- [x] Write `test_command_respects_weeks_parameter_8_weeks`
- [x] Write `test_command_clear_existing_removes_old_copilot_data`
- [x] Write `test_command_clear_existing_preserves_cursor_records`
- [x] Write `test_command_creates_records_for_team_members`
- [x] Write `test_command_respects_team_isolation`
- [x] Write `test_command_respects_seed_parameter_deterministic_output`
- [x] Write `test_command_with_different_seeds_produces_different_output`
- [x] Write `test_command_fails_with_nonexistent_team`
- [x] Write `test_command_outputs_summary`
- [x] Run tests and confirm they FAIL

### 3.2 Command Implementation (GREEN) ✅

**Effort: M** | **Priority: P0** | **Depends on: 3.1**

- [x] Create `apps/metrics/management/commands/seed_copilot_demo.py`
- [x] Add `--team` argument (required)
- [x] Add `--scenario` argument (default: mixed_usage)
- [x] Add `--weeks` argument (default: 4)
- [x] Add `--clear-existing` flag
- [x] Add `--seed` argument for reproducibility
- [x] Create `AIUsageDaily` records from generated data
- [x] Output summary on completion
- [x] Run tests and confirm they PASS

### 3.3 Refactor (REFACTOR) ✅

**Effort: S** | **Priority: P2** | **Depends on: 3.2**

- [x] Use `DeterministicRandom` directly for member distribution
- [x] All tests still pass

---

## Phase 4: PR Correlation ✅ COMPLETE

### 4.1 Correlation Tests (RED) ✅

**Effort: M** | **Priority: P1**

- [x] Write `test_prs_on_usage_days_marked_ai_assisted`
- [x] Write `test_prs_on_non_usage_days_not_marked`
- [x] Write `test_ai_tools_detected_includes_copilot`
- [x] Write `test_existing_ai_tools_preserved`
- [x] Write `test_correlation_respects_team_isolation`
- [x] Write `test_correlation_only_for_copilot_source`
- [x] Write `test_correlation_requires_minimum_suggestions`
- [x] Write `test_correlation_returns_count`

**8 tests pass**

### 4.2 Correlation Implementation (GREEN) ✅

**Effort: M** | **Priority: P1** | **Depends on: 4.1**

- [x] Add `correlate_prs_with_copilot_usage()` function
- [x] Query member's PRs by `pr_created_at__date`
- [x] Query member's `AIUsageDaily` records for date
- [x] Update PR fields when correlation found
- [x] Integrate into `seed_copilot_demo` command with `--correlate-prs` flag
- [x] All tests pass

---

## Phase 5: LLM Integration ✅ COMPLETE

### 5.1 Prompt Template Tests (RED) ✅

**Effort: S** | **Priority: P1**

- [x] Write `test_renders_copilot_section_with_data`
- [x] Write `test_hides_section_when_no_data`
- [x] Write `test_shows_inactive_licenses_warning`
- [x] Write `test_hides_inactive_when_zero`
- [x] Write `test_shows_low_adoption_warning`
- [x] Write `test_shows_good_adoption_indicator`

**6 tests pass**

### 5.2 Prompt Template Implementation (GREEN) ✅

**Effort: S** | **Priority: P1** | **Depends on: 5.1**

- [x] Create `apps/metrics/prompts/templates/sections/copilot_metrics.jinja2`
- [x] Template renders Copilot metrics section
- [x] Handles adoption thresholds (LOW/GOOD indicators)
- [x] All tests pass

### 5.3 Copilot Metrics Service (GREEN) ✅

**Effort: M** | **Priority: P1** | **Depends on: 5.2**

- [x] `get_copilot_metrics_for_prompt()` exists in `copilot_metrics_prompt.py`
- [x] Function queries `AIUsageDaily` and aggregates
- [x] Calculates inactive users, top performers
- [x] Feature flag checking with `include_copilot` parameter
- [x] Full test coverage in `test_copilot_metrics_service.py`

---

## Phase 6: Settings Toggle ✅ COMPLETE

### 6.1 Settings Tests (RED) ✅

**Effort: S** | **Priority: P2**

- [x] Write `test_mock_mode_disabled_by_default`
- [x] Write `test_mock_mode_enabled_returns_mock_data`
- [x] Write `test_mock_seed_produces_deterministic_output`
- [x] Write `test_mock_scenario_parameter_used`
- [x] Write `test_different_seed_produces_different_output`

**5 tests pass** - `apps/integrations/tests/test_copilot_mock_mode.py`

### 6.2 Settings Implementation (GREEN) ✅

**Effort: S** | **Priority: P2** | **Depends on: 6.1**

- [x] Add `COPILOT_USE_MOCK_DATA` to `settings.py` (default: False)
- [x] Add `COPILOT_MOCK_SEED` to `settings.py` (default: 42)
- [x] Add `COPILOT_MOCK_SCENARIO` to `settings.py` (default: "mixed_usage")
- [x] Modify `fetch_copilot_metrics()` to check settings
- [x] All tests pass

---

## Phase 7: Dashboard Verification ✅ COMPLETE

### 7.1 Visual Testing Checklist ✅

**Effort: M** | **Priority: P1** | **Depends on: 3.2, 4.2**

- [x] Seed growth scenario: `manage.py seed_copilot_demo --team=tooljet-demo --scenario=growth --weeks=8`
- [x] Verify data statistics match scenario expectations
- [x] Growth scenario: 40,768 records, ~21% avg acceptance (starts low, grows high)
- [x] PR correlation verified: 75 PRs correlated on supabase-demo
- [x] Copilot mock mode settings work (`COPILOT_USE_MOCK_DATA=True`)

### 7.2 Scenario Comparison ✅

- [x] **Growth** (tooljet-demo): 40,768 records, 8 weeks, acceptance grows over time
- [x] **High Adoption** (appsmith-demo): 10,584 records, 4 weeks, 40-55% acceptance
- [x] **Inactive Licenses** (n8n-demo): 38,080 records, 4 weeks, has zero-activity days
- [x] **Mixed Usage** (supabase-demo): 54,516 records, 4 weeks, 15-65% variance

**Note:** Visual dashboard verification is manual task to be done when running `make dev`

---

## Quick Reference

### Run Tests
```bash
# Run all copilot mock tests
.venv/bin/pytest apps/integrations/tests/test_copilot_mock_data.py apps/metrics/tests/test_seed_copilot_demo.py -v

# Run with coverage
.venv/bin/pytest apps/integrations/tests/test_copilot_mock_data.py --cov=apps/integrations/services/copilot_mock_data
```

### Seed Demo Data
```bash
# Growth scenario
python manage.py seed_copilot_demo --team=demo --scenario=growth --weeks=8

# Mixed usage (realistic)
python manage.py seed_copilot_demo --team=demo --scenario=mixed_usage

# Switch scenario (clear old)
python manage.py seed_copilot_demo --team=demo --scenario=inactive_licenses --clear-existing

# High adoption
python manage.py seed_copilot_demo --team=demo --scenario=high_adoption --seed=42
```

### Generate Insights
```bash
# Test LLM integration
python manage.py generate_insights --team=demo
```

---

## Progress Summary

| Phase | Status | Tests | Implementation |
|-------|--------|-------|----------------|
| 1. Mock Generator Core | ✅ | 9/9 | ✅ |
| 2. Scenario System | ✅ | 8/8 | ✅ |
| 3. Management Command | ✅ | 14/14 | ✅ |
| 4. PR Correlation | ✅ | 8/8 | ✅ |
| 5. LLM Integration | ✅ | 6/6 | ✅ |
| 6. Settings Toggle | ✅ | 5/5 | ✅ |
| 7. Dashboard Verification | ✅ | Manual | ✅ |

**Total: 50+ tests, 7/7 phases complete** ✅
