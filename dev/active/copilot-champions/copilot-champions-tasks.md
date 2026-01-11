# Copilot Champions - Tasks

Last Updated: 2026-01-11

## Phase 1: Service Layer (TDD)

### 1.1 Create Test File (RED)
- [ ] Create `apps/metrics/tests/test_copilot_champions.py`
- [ ] Write test for `get_copilot_champions()` with valid data
- [ ] Write test for empty team (no champions)
- [ ] Write test for members below threshold
- [ ] Write test for tie-breaking (deterministic order)
- [ ] Write test for TEAM001 compliance
- [ ] Verify all tests FAIL (no implementation yet)

### 1.2 Implement Core Service (GREEN)
- [ ] Create `apps/metrics/services/copilot_champions.py`
- [ ] Implement `_get_copilot_usage_by_member()` - aggregate AIUsageDaily
- [ ] Implement `_get_pr_metrics_by_member()` - aggregate PullRequest
- [ ] Implement `_calculate_percentile_scores()` - percentile-based scoring
- [ ] Implement `get_copilot_champions()` - main entry point
- [ ] Verify all tests PASS

### 1.3 Edge Case Tests (RED-GREEN)
- [ ] Test: Member with Copilot usage but 0 PRs
- [ ] Test: Member with PRs but no Copilot
- [ ] Test: All members below qualification threshold
- [ ] Test: Large team performance (mock 100+ members)
- [ ] Test: Date range edge cases

### 1.4 Refactor
- [ ] Review code for simplification opportunities
- [ ] Add docstrings and type hints
- [ ] Run code simplifier if beneficial

---

## Phase 2: LLM Integration

### 2.1 Add Champions to Prompt Data (TDD)
- [ ] Write test for `get_copilot_metrics_for_prompt()` including champions
- [ ] Modify `apps/integrations/services/copilot_metrics_prompt.py`
- [ ] Add `champions` field to return dict
- [ ] Verify test passes

### 2.2 Update User Prompt Template
- [ ] Get user approval for template change
- [ ] Modify `apps/metrics/prompts/templates/sections/copilot_metrics.jinja2`
- [ ] Add champions section with @mentions
- [ ] Bump PROMPT_VERSION

### 2.3 Update System Prompt Guidance
- [ ] Add champion mentoring guidance to system prompt
- [ ] Add "Only mention if team has champions AND struggling users" rule
- [ ] Test with demo teams

---

## Phase 3: Dashboard UI

### 3.1 Add View Context (TDD)
- [ ] Write test for `ai_adoption` view including champions
- [ ] Modify `apps/metrics/views/analytics_views.py`
- [ ] Pass champions to template context
- [ ] Verify test passes

### 3.2 Add Champions Card
- [ ] Modify `templates/metrics/analytics/ai_adoption.html`
- [ ] Add Champions card component
- [ ] Style with DaisyUI semantic colors
- [ ] Test responsive layout

### 3.3 Visual Verification
- [ ] Navigate to AI Adoption tab in browser
- [ ] Verify Champions card displays correctly
- [ ] Test with different team scenarios

---

## Phase 4: Feature Flag & Rollout

### 4.1 Add Feature Flag
- [ ] Add `copilot_champions` flag to waffle
- [ ] Gate champions display in view
- [ ] Gate champions in LLM prompt

### 4.2 Verification
- [ ] Generate insights for demo teams
- [ ] Verify champions mentioned when appropriate
- [ ] Verify champions NOT mentioned when no struggling users

---

## Phase 5: Final Testing & Commit

### 5.1 Run Full Test Suite
- [ ] `make test ARGS='apps.metrics.tests.test_copilot_champions'`
- [ ] `make test` (full suite)
- [ ] `make lint-team-isolation`

### 5.2 Manual Verification
- [ ] Test with langchain-demo (inactive_licenses)
- [ ] Test with vercel-demo (high_adoption)
- [ ] Test with dify-demo (growth)

### 5.3 Commit
- [ ] Stage relevant files
- [ ] Create descriptive commit message
- [ ] Verify pre-commit hooks pass

---

## Acceptance Criteria

- [ ] Top 3 champions correctly identified per team
- [ ] Scoring uses team-relative percentiles
- [ ] Champions display on AI Adoption dashboard
- [ ] Champions mentioned in LLM insights when appropriate
- [ ] All tests pass
- [ ] No TEAM001 violations
- [ ] Feature flag controls visibility
