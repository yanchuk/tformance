# DX Features - Task Checklist

**Last Updated:** 2025-01-25

## Progress Tracking

| Phase | Status | Progress |
|-------|--------|----------|
| P0: Copilot Engagement | 🔴 Not Started | 0/8 |
| P0: Cost Visibility | 🔴 Not Started | 0/6 |
| P1: Review Experience | 🔴 Not Started | 0/9 |
| P2: Team Health | 🔴 Not Started | 0/7 |
| E2E Testing | 🔴 Not Started | 0/5 |
| Mock Data | 🔴 Not Started | 0/3 |

---

## Phase 1: P0 - Copilot Engagement Dashboard

### 1.1 RED Phase - Write Failing Tests
- [ ] **Task 1.1.1** Create test file `apps/metrics/tests/services/dashboard/test_copilot_engagement.py`
  - Acceptance: File exists with TestCase class
  - Effort: S
- [ ] **Task 1.1.2** Write test `test_returns_expected_keys`
  - Acceptance: Test fails (function doesn't exist)
  - Effort: S
- [ ] **Task 1.1.3** Write test `test_handles_zero_copilot_users`
  - Acceptance: Test fails, checks division by zero handling
  - Effort: S
- [ ] **Task 1.1.4** Write test `test_sample_sufficient_when_enough_prs`
  - Acceptance: Test fails, checks sample_sufficient=True when >= 10 PRs
  - Effort: S
- [ ] **Task 1.1.5** Write test `test_sample_insufficient_when_few_prs`
  - Acceptance: Test fails, checks sample_sufficient=False when < 10 PRs
  - Effort: S

### 1.2 GREEN Phase - Implement Service
- [ ] **Task 1.2.1** Implement `get_copilot_engagement_summary()` in `copilot_metrics.py`
  - Acceptance: All tests pass
  - Effort: M
  - Depends: 1.1.1-1.1.5
- [ ] **Task 1.2.2** Export function in `__init__.py`
  - Acceptance: Can import from `apps.metrics.services.dashboard`
  - Effort: S
  - Depends: 1.2.1

### 1.3 REFACTOR Phase
- [ ] **Task 1.3.1** Review for N+1 queries, optimize if needed
  - Acceptance: Single query per model, <100ms response
  - Effort: S
  - Depends: 1.2.1

---

## Phase 2: P0 - Cost Visibility Dashboard

### 2.1 Model Change
- [ ] **Task 2.1.1** Add `copilot_price_tier` field to Team model
  - Acceptance: Field with choices (individual/business/enterprise), default=business
  - Effort: S
- [ ] **Task 2.1.2** Create migration `add_copilot_price_tier`
  - Acceptance: Migration file exists and runs cleanly
  - Effort: S
  - Depends: 2.1.1
- [ ] **Task 2.1.3** Run migration
  - Acceptance: `migrate` succeeds
  - Effort: S
  - Depends: 2.1.2

### 2.2 Update CopilotSeatSnapshot
- [ ] **Task 2.2.1** Create `get_copilot_seat_price(team)` helper function
  - Acceptance: Returns Decimal based on team.copilot_price_tier
  - Effort: S
- [ ] **Task 2.2.2** Update `CopilotSeatSnapshot.monthly_cost` to use helper
  - Acceptance: Cost varies by tier ($10, $19, $39)
  - Effort: S
  - Depends: 2.2.1
- [ ] **Task 2.2.3** Write tests for tier pricing in `test_cost_visibility.py`
  - Acceptance: Tests verify $10, $19, $39 calculations
  - Effort: S

---

## Phase 3: P1 - Review Experience Survey

### 3.1 Model Extension
- [ ] **Task 3.1.1** Add `FEEDBACK_CLARITY_CHOICES` constant (1-5)
  - Acceptance: Choices defined in surveys.py
  - Effort: S
- [ ] **Task 3.1.2** Add `REVIEW_BURDEN_CHOICES` constant (1-5)
  - Acceptance: Choices defined in surveys.py
  - Effort: S
- [ ] **Task 3.1.3** Add `feedback_clarity` field to PRSurveyReview
  - Acceptance: IntegerField, choices, null=True
  - Effort: S
  - Depends: 3.1.1
- [ ] **Task 3.1.4** Add `review_burden` field to PRSurveyReview
  - Acceptance: IntegerField, choices, null=True
  - Effort: S
  - Depends: 3.1.2
- [ ] **Task 3.1.5** Create migration `add_review_experience_fields`
  - Acceptance: Migration file exists
  - Effort: S
  - Depends: 3.1.3, 3.1.4

### 3.2 Sampling Logic
- [ ] **Task 3.2.1** Implement `should_show_extended_survey()` function
  - Acceptance: Returns True ~25% of the time
  - Effort: S
- [ ] **Task 3.2.2** Write test for sampling distribution (1000 iterations)
  - Acceptance: 20-30% True results
  - Effort: S
  - Depends: 3.2.1

### 3.3 Survey Handler Updates
- [ ] **Task 3.3.1** Update Slack survey handler to include new questions when sampled
  - Acceptance: Questions appear 25% of time in Slack
  - Effort: M
  - Depends: 3.1.5, 3.2.1
- [ ] **Task 3.3.2** Update web survey form to include new questions when sampled
  - Acceptance: Questions appear 25% of time in web form
  - Effort: M
  - Depends: 3.1.5, 3.2.1

---

## Phase 4: P2 - Team Health Indicators

### 4.1 RED Phase - Write Failing Tests
- [ ] **Task 4.1.1** Create test file `test_team_health_indicators.py`
  - Acceptance: File exists with TestCase class
  - Effort: S
- [ ] **Task 4.1.2** Write test for each indicator (throughput, cycle_time, quality, bottleneck, ai_adoption)
  - Acceptance: 5 tests that fail
  - Effort: M
- [ ] **Task 4.1.3** Write test for status thresholds (green/yellow/red)
  - Acceptance: Tests fail, verify threshold logic
  - Effort: S

### 4.2 GREEN Phase - Implement Service
- [ ] **Task 4.2.1** Implement `get_team_health_indicators()` in `velocity_metrics.py`
  - Acceptance: All indicator tests pass
  - Effort: L
  - Depends: 4.1.1-4.1.3
- [ ] **Task 4.2.2** Export function in `__init__.py`
  - Acceptance: Can import from dashboard services
  - Effort: S
  - Depends: 4.2.1

### 4.3 View & Template
- [ ] **Task 4.3.1** Create view `team_health_indicators_card()`
  - Acceptance: HTMX partial renders
  - Effort: S
  - Depends: 4.2.1
- [ ] **Task 4.3.2** Create template `team_health_indicators.html` with traffic lights
  - Acceptance: Shows 5 indicators with badges
  - Effort: M
  - Depends: 4.3.1

---

## Phase 5: E2E Testing with Playwright

### 5.1 E2E Test File
- [ ] **Task 5.1.1** Create `tests/e2e/dx-features.spec.ts`
  - Acceptance: File exists with test.describe block
  - Effort: S
- [ ] **Task 5.1.2** Write test for Copilot engagement card
  - Acceptance: Test verifies numeric values, confidence indicator
  - Effort: M
- [ ] **Task 5.1.3** Write test for cost visibility with tier
  - Acceptance: Test verifies cost changes with tier
  - Effort: M
- [ ] **Task 5.1.4** Write test for team health indicators
  - Acceptance: Test verifies 5 traffic lights visible
  - Effort: M
- [ ] **Task 5.1.5** Update existing `copilot.spec.ts` for new features
  - Acceptance: Existing tests still pass
  - Effort: S

---

## Phase 6: Mock Data Updates

### 6.1 Factory Updates
- [ ] **Task 6.1.1** Add `CopilotSeatSnapshotFactory` to factories.py
  - Acceptance: Factory creates valid records
  - Effort: S
- [ ] **Task 6.1.2** Update `seed_copilot_demo.py` to ensure `lines_accepted` populated
  - Acceptance: CopilotLanguageDaily records have lines_accepted > 0
  - Effort: S

### 6.2 Verify Mock Data
- [ ] **Task 6.2.1** Run seed command and verify all new features work
  - Acceptance: Dashboard shows engagement and health metrics
  - Effort: S
  - Depends: All above

---

## Verification Checklist

### Before PR
- [ ] All unit tests pass: `make test`
- [ ] All E2E tests pass: `make e2e`
- [ ] No linting errors: `make ruff`
- [ ] Manual verification in browser
- [ ] Playwright screenshot confirms UI

### Manual Verification Steps
1. [ ] Login as admin
2. [ ] Navigate to `/app/metrics/overview/`
3. [ ] Verify Copilot engagement card shows numeric values
4. [ ] Verify sample_sufficient indicator (if applicable)
5. [ ] Navigate to team settings
6. [ ] Change Copilot tier
7. [ ] Verify cost updates
8. [ ] Submit a survey (if available)
9. [ ] Verify extended questions appear ~25% of time
10. [ ] Verify team health indicators show 5 traffic lights

---

## Notes

### TDD Workflow Reminder
1. **RED:** Write failing test first
2. **GREEN:** Write minimum code to pass
3. **REFACTOR:** Clean up while tests stay green

### Playwright Verification
After each UI change:
```bash
# Take screenshot
npx playwright test dx-features.spec.ts --update-snapshots

# Visual check
npx playwright test dx-features.spec.ts --ui
```

### Command Reference
```bash
# Run specific test file
.venv/bin/pytest apps/metrics/tests/services/dashboard/test_copilot_engagement.py -v

# Run with coverage
.venv/bin/pytest apps/metrics/tests/services/dashboard/ --cov=apps/metrics/services/dashboard

# E2E single test
npx playwright test dx-features.spec.ts --grep "engagement"
```
