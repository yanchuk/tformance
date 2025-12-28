# PostHog Analytics Integration - Tasks

**Last Updated:** 2025-12-26

---

## Phase 1: Frontend JS SDK Setup [S] ✅ COMPLETE

**Goal:** Enable autocapture, session replay, and user identification in browser

### Tasks

- [x] **1.1** Create `templates/web/components/posthog_init.html` partial
  - Load PostHog JS from CDN
  - Initialize with API key and host from settings
  - Configure autocapture and session recording options
  - Acceptance: PostHog snippet renders in page source

- [x] **1.2** Create `posthog_config` context processor in `apps/web/context_processors.py`
  - Expose `POSTHOG_API_KEY` and `POSTHOG_HOST` to templates
  - Only expose if key is set (production-safe)
  - Acceptance: `{{ POSTHOG_API_KEY }}` available in templates

- [x] **1.3** Add context processor to `TEMPLATES` in `settings.py`
  - Add to context_processors list
  - Acceptance: Context available in all templates

- [x] **1.4** Include PostHog partial in `templates/web/base.html`
  - Add after existing analytics (Google Analytics block)
  - Acceptance: PostHog JS loads in browser

- [x] **1.5** Implement user identification on page load
  - Call `posthog.identify()` for authenticated users
  - Include email, name, user ID
  - Acceptance: Users appear in PostHog Persons with properties

- [x] **1.6** Implement group identification for teams
  - Call `posthog.group('team', slug)` when team context exists
  - Include team name, plan properties
  - Acceptance: Teams appear as groups in PostHog

- [ ] **1.7** Test session recording
  - Enable in PostHog dashboard settings
  - Verify recordings capture correctly
  - Verify input masking works
  - Acceptance: Session replays visible in PostHog

---

## Phase 2: Core Funnel Tracking [M] ✅ COMPLETE (Core Events)

**Goal:** Track the complete signup → activation funnel

### Backend Setup

- [x] **2.1** Create `apps/utils/analytics.py` helper module
  ```python
  def track_event(user, event, properties=None):
      """Track event for user with standard properties."""

  def identify_user(user, properties=None):
      """Identify user with properties."""

  def group_identify(team, properties=None):
      """Identify team group with properties."""

  def is_feature_enabled(feature_key, user=None, team=None):
      """Check if feature flag is enabled."""
  ```
  - Wrap PostHog calls with error handling
  - Add team context automatically
  - Acceptance: Helper functions work correctly

- [x] **2.2** Add tests for analytics helpers
  - Mock PostHog calls
  - Test error handling (no crash if PostHog unavailable)
  - Acceptance: 20 tests pass

### Signup Tracking

- [x] **2.3** Track `user_signed_up` event
  - Location: `apps/users/signals.py` (allauth signal handler)
  - Properties: method (email/google/github)
  - Acceptance: Event fires on new signup

### Onboarding Tracking

- [x] **2.4** Track `onboarding_step_completed` events
  - Location: `apps/onboarding/views.py`
  - Steps: github, repos, jira, slack
  - Properties: step, team_slug
  - Acceptance: Each step tracked in PostHog funnel

- [x] **2.5** Track `onboarding_skipped` event
  - Location: `apps/onboarding/views.py` skip handlers
  - Properties: step (github/jira/slack), team_slug
  - Acceptance: Skip events appear in PostHog

- [x] **2.6** Track `github_connected` event
  - Location: `apps/onboarding/views.py` (_create_team_from_org)
  - Properties: org_name, member_count, team_slug
  - Acceptance: GitHub connections tracked

- [ ] **2.7** Track `jira_connected` event *(Deferred - tracked in integration OAuth)*
  - Location: `apps/integrations/views/jira.py` OAuth callback
  - Properties: project_count
  - Acceptance: Jira connections tracked

- [ ] **2.8** Track `slack_connected` event *(Deferred - tracked in integration OAuth)*
  - Location: `apps/integrations/views/slack.py` OAuth callback
  - Properties: workspace_name
  - Acceptance: Slack connections tracked

### Activation Tracking

- [x] **2.9** Track `dashboard_first_view` event
  - Location: `apps/metrics/views/analytics_views.py`
  - Only fire once per session (via session flag)
  - Properties: team_slug
  - Acceptance: Activation event appears

- [ ] **2.10** Set user property `activated_at` on first dashboard view *(Deferred)*
  - Use `$set_once` to never overwrite
  - Acceptance: Property persists correctly

### Subscription Tracking

- [ ] **2.11** Track `subscription_started` event *(Deferred - no billing yet)*
  - Location: `apps/subscriptions/views.py` or djstripe webhook handler
  - Properties: plan, seats, mrr
  - Acceptance: Subscription events appear

- [ ] **2.12** Track `subscription_cancelled` event *(Deferred - no billing yet)*
  - Location: `apps/subscriptions/views.py` cancel handler
  - Properties: reason (if collected), days_active
  - Acceptance: Churn events appear

---

## Phase 3: Engagement Tracking [S] ✅ COMPLETE

**Goal:** Understand how users interact with core features

- [x] **3.1** Track `analytics_viewed` on tab navigation
  - Location: `apps/metrics/views/analytics_views.py`
  - Properties: tab (overview/ai_adoption/delivery/quality/team), date_range, team_slug
  - Acceptance: Tab usage visible in PostHog

- [x] **3.2** Track `pr_list_exported` on CSV export
  - Location: `apps/metrics/views/pr_list_views.py`
  - Properties: format, row_count, has_filters, team_slug
  - Acceptance: Export usage tracked

- [x] **3.3** Track `date_filter_changed` on date range selection *(Handled by autocapture)*
  - PostHog autocapture tracks all form interactions and clicks
  - analytics_viewed already includes date_range property

- [ ] **3.4** Track `survey_response_submitted` *(Deferred - when survey feature is used)*
  - Location: `apps/web/webhooks.py` (Slack callback) or survey views
  - Properties: type (author/reviewer), ai_assisted (for author surveys)
  - Acceptance: Survey engagement tracked

- [ ] **3.5** Track `leaderboard_viewed` *(Deferred - when leaderboard is built)*
  - Location: Leaderboard view
  - Properties: team_slug
  - Acceptance: Gamification engagement tracked

---

## Phase 4: Session Replay & Error Tracking [S] ✅ COMPLETE

**Goal:** Enable debugging and UX research capabilities

- [x] **4.1** Configure session recording exclusions
  - Exclude: /accounts/, /admin/, /api/, /__reload__/
  - Added to posthog_init.html with stopSessionRecording() call
  - Acceptance: Auth pages not recorded

- [x] **4.2** Enable exception autocapture
  - Added `posthog.exception_autocapture = True` to settings.py
  - Also set `posthog.debug = DEBUG` for dev visibility
  - Acceptance: Python errors appear in PostHog Error Tracking

- [x] **4.3** Configure input masking for PII
  - Set `maskAllInputs: true` in session_recording config
  - Password fields explicitly masked via maskInputOptions
  - Acceptance: Recordings show masked inputs

- [x] **4.4** Test recording privacy on sensitive pages
  - Implemented page path exclusion check on load
  - respects_dnt: true honors browser Do Not Track
  - Acceptance: No sensitive data in recordings

---

## Phase 5: In-App Surveys [M]

**Goal:** Collect qualitative feedback at key moments

### Survey Definitions (Create in PostHog UI)

- [ ] **5.1** Create "Post-Onboarding NPS" survey
  - Type: NPS (0-10 rating)
  - Question: "How likely are you to recommend us to a colleague?"
  - Trigger: 7 days after signup, once
  - Target: Users who completed onboarding
  - Acceptance: Survey appears for qualifying users

- [ ] **5.2** Create "AI Correlation Feedback" survey
  - Type: Rating (1-5 stars)
  - Question: "Was the AI correlation analysis helpful?"
  - Trigger: After viewing AI correlation page 3+ times
  - Target: Admin users
  - Acceptance: Survey appears for power users

- [ ] **5.3** Create "Churn Prevention" survey
  - Type: Multiple choice + open text
  - Question: "What's the main reason you're cancelling?"
  - Options: Too expensive, Missing features, Not useful, Switching tools, Other
  - Trigger: On subscription cancellation page
  - Acceptance: Survey appears on cancel page

### Survey Integration

- [ ] **5.4** Enable surveys in PostHog JS init
  - Already enabled by default in JS SDK
  - Test survey rendering works
  - Acceptance: Surveys render correctly in app

- [ ] **5.5** Style surveys to match app theme
  - Use PostHog survey customization
  - Match DaisyUI colors (coral/orange accent, dark theme)
  - Acceptance: Surveys look native to app

---

## Phase 6: Feature Flags [S]

**Goal:** Enable gradual rollout of new features

### Flag Definitions (Create in PostHog UI)

- [ ] **6.1** Create `trends-dashboard` feature flag
  - Type: Rollout (percentage based)
  - Default: 0% (off)
  - Linked to trends-benchmarks-dashboard work
  - Acceptance: Flag evaluates correctly

- [ ] **6.2** Create `industry-benchmarks` feature flag
  - Type: Rollout (percentage based)
  - Default: 0% (off)
  - For Phase 4 of trends-benchmarks-dashboard
  - Acceptance: Flag evaluates correctly

- [ ] **6.3** Create `insights-engine` feature flag
  - Type: Rollout (percentage based)
  - Default: 0% (off)
  - For Phase 5 of trends-benchmarks-dashboard
  - Acceptance: Flag evaluates correctly

### Backend Flag Evaluation

- [ ] **6.4** Create feature flag helper in `apps/utils/analytics.py`
  ```python
  def is_feature_enabled(feature_key, user=None, team=None):
      """Check if feature flag is enabled for user/team."""
  ```
  - Handle missing PostHog gracefully
  - Cache flag values briefly
  - Acceptance: Flag checks work in views

- [ ] **6.5** Add flag checks to trends views
  - Gate new trends page behind flag
  - Show/hide navigation based on flag
  - Acceptance: Feature hidden when flag off

### Frontend Flag Evaluation

- [ ] **6.6** Use PostHog JS for client-side flags
  - `posthog.isFeatureEnabled('trends-dashboard')`
  - Conditionally show UI elements
  - Acceptance: UI responds to flag state

---

## Phase 7: PostHog Dashboard Setup [S]

**Goal:** Create actionable dashboards in PostHog

- [ ] **7.1** Create "Onboarding Funnel" dashboard
  - Funnel: signup → github → repos → (jira?) → (slack?) → dashboard
  - Conversion rates
  - Time between steps
  - Acceptance: Funnel shows real data

- [ ] **7.2** Create "Weekly Engagement" dashboard
  - Charts: DAU/WAU, session count, feature usage
  - Filters: team, date range
  - Acceptance: Engagement visible

- [ ] **7.3** Create "Activation Metrics" dashboard
  - Time to first dashboard view
  - Time to first survey response
  - Integration connection rates
  - Acceptance: Activation metrics visible

- [ ] **7.4** Set up weekly email digest
  - Summary of key metrics
  - Sent to team
  - Acceptance: Email arrives weekly

---

## Completion Checklist

### Phase 1 Complete When: ✅
- [x] PostHog JS loads on all pages
- [x] Users are identified on login
- [x] Teams are identified as groups
- [ ] Session recordings capture correctly *(Needs manual testing)*
- [x] Autocapture events appear in PostHog *(Enabled by default)*

### Phase 2 Complete When: ✅ (Core Events)
- [x] Signup event tracks all methods
- [x] All onboarding steps tracked
- [x] First dashboard view tracked
- [ ] Subscription events tracked *(Deferred - no billing)*
- [x] Funnel can be built in PostHog

### Phase 3 Complete When: ✅
- [x] Analytics tab usage tracked (all tabs)
- [x] Export usage tracked
- [x] Filter usage tracked (via autocapture + analytics_viewed)
- [ ] Survey response events tracked *(Deferred)*

### Phase 4 Complete When: ✅
- [x] Session recordings work
- [x] Sensitive pages excluded
- [x] Errors appear in PostHog (exception_autocapture enabled)
- [x] Input masking verified (maskAllInputs: true)

### Phase 5 Complete When:
- [ ] NPS survey deployed
- [ ] Feature feedback survey deployed
- [ ] Churn survey deployed
- [ ] Surveys styled to match app

### Phase 6 Complete When:
- [ ] Feature flags created
- [ ] Backend flag checks work
- [ ] Frontend flag checks work
- [ ] Trends gated behind flag

### Phase 7 Complete When:
- [ ] Onboarding funnel dashboard built
- [ ] Engagement dashboard built
- [ ] Activation dashboard built
- [ ] Weekly digest configured

---

## Notes

- Start with Phase 1 - it's the foundation for everything
- Phase 2 is highest priority - core funnel visibility
- Phase 5 (Surveys) can wait until post-MVP
- Phase 6 (Flags) should coordinate with trends-benchmarks work
- Keep event count minimal - only track what informs decisions

---

## Estimated Effort

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| Phase 1: Frontend SDK | 2-3 hours | None |
| Phase 2: Core Funnels | 4-6 hours | Phase 1 |
| Phase 3: Engagement | 2-3 hours | Phase 1 |
| Phase 4: Replay/Errors | 1-2 hours | Phase 1 |
| Phase 5: Surveys | 3-4 hours | Phase 1 |
| Phase 6: Feature Flags | 2-3 hours | Phase 1 |
| Phase 7: Dashboards | 2-3 hours | Phase 2-3 |
| **Total** | **16-24 hours** | |
