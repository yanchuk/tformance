# User Stories: Public OSS Analytics Page Improvements

**Project**: Tformance Public OSS Analytics
**Feature**: Org Detail Page Enhancements (e.g., /open-source/posthog/)
**Date**: 2026-02-15
**Author**: Senior Product Manager

## Context

These user stories support the public OSS analytics initiative to showcase Tformance's capabilities and convert visitors to paying customers. The improvements enhance the org detail page with better visual storytelling, more comprehensive data, and improved user experience.

**Current State**:
- 100 public orgs, 121 repos, ~23K PRs total
- ~110 new merged PRs/day
- Pages show: hero stats, charts, recent PRs, team breakdown, quality indicators, reviewers, AI tools, insights

**Goals**:
- Showcase Tformance's analytical depth
- Build trust through transparency (repos tracked, methodology)
- Increase conversion to trial/paid accounts
- Improve SEO/discoverability

---

## Story #1: Repository List

**Title**: Display Tracked Repositories per Organization

**User Story**:
As a **visitor evaluating an OSS organization**, I want to **see exactly which repositories Tformance is analyzing** so that **I understand the scope of coverage and can verify data completeness**.

**Priority**: P0 (Critical for transparency)

**Dependencies**: None

**Acceptance Criteria**:
- [ ] Section appears at bottom of page above "Related Organizations"
- [ ] Section title: "Tracked Repositories" with count badge (e.g., "Tracked Repositories (12)")
- [ ] Each repo displays:
  - [ ] Repository name as clickable link to GitHub
  - [ ] Format: `owner/repo-name` (e.g., `posthog/posthog`)
  - [ ] Link opens in new tab with `rel="noopener noreferrer"`
  - [ ] PR count for that repo (e.g., "1,234 PRs analyzed")
- [ ] Repos sorted by PR count (descending)
- [ ] Maximum 50 repos displayed (show all if ≤50)
- [ ] If >50 repos, show top 50 with message: "Showing top 50 repositories by PR volume"
- [ ] Responsive grid layout:
  - [ ] Desktop: 3 columns
  - [ ] Tablet: 2 columns
  - [ ] Mobile: 1 column
- [ ] GitHub icon next to each link
- [ ] Hover state shows full repo URL in tooltip
- [ ] Section only appears if org has ≥1 tracked repo
- [ ] Loading state shows skeleton placeholders
- [ ] Zero state: "No repositories tracked yet" (should never occur for public orgs)

**Technical Notes**:
- Query `PullRequest.objects.filter(team=org.team).values('github_repo').annotate(count=Count('id'))`
- Cache repo list in `PublicOrgStats.tracked_repos` JSON field (add in migration)
- Render with HTMX partial for lazy loading

**Design Notes**:
- Use DaisyUI card components with subtle hover effect
- Match existing page aesthetic (white cards on light background)
- GitHub icon from Heroicons or similar

---

## Story #2: Combined Cycle Time + AI Adoption Chart

**Title**: Dual-Axis Chart Showing Cycle Time and AI Adoption Trends

**User Story**:
As a **technical leader researching AI impact**, I want to **see cycle time and AI adoption on the same chart** so that **I can visually correlate AI tool usage with delivery speed trends**.

**Priority**: P1 (High value for conversion)

**Dependencies**: None

**Acceptance Criteria**:
- [ ] Replace existing separate "AI Adoption Over Time" chart
- [ ] Keep existing "Cycle Time Over Time" chart (update to dual-axis)
- [ ] Chart shows last 90 days of data by default
- [ ] Left Y-axis: Cycle Time (hours) - blue color
- [ ] Right Y-axis: AI Adoption (%) - green color
- [ ] X-axis: Date (format: "Jan 15")
- [ ] Two lines plotted:
  - [ ] Blue line: 7-day rolling average cycle time
  - [ ] Green line: 7-day rolling average AI adoption %
- [ ] Legend shows both metrics with color coding
- [ ] Tooltip on hover shows:
  - [ ] Date
  - [ ] Cycle time: "X.X hours"
  - [ ] AI adoption: "X.X%"
  - [ ] Sample size: "N PRs merged this week"
- [ ] Chart is responsive (scales on mobile)
- [ ] Chart title: "Cycle Time & AI Adoption Trends"
- [ ] Chart subtitle: "7-day rolling averages, last 90 days"
- [ ] If insufficient data (<14 days), show message: "Insufficient data for trend analysis"
- [ ] Loading state shows skeleton chart
- [ ] Use Chart.js library (existing in project)
- [ ] Accessibility: Chart data available as table toggle

**Technical Notes**:
- Add `get_dual_axis_trend_data()` to `apps/public/aggregations.py`
- Group by week, calculate rolling averages
- Return format: `{dates: [], cycle_times: [], ai_adoption_pcts: [], sample_sizes: []}`
- Cache in view context for 1 hour

**Design Notes**:
- Use same card container as existing charts
- Blue (#3B82F6) for cycle time, green (#10B981) for AI adoption
- Match existing Chart.js theme (minimal, clean)

---

## Story #3: PR Size Distribution Chart

**Title**: Visualize Pull Request Size Distribution

**User Story**:
As a **visitor evaluating team practices**, I want to **see how PR sizes are distributed** so that **I can assess code review culture and development patterns**.

**Priority**: P2 (Nice to have, showcases depth)

**Dependencies**: None

**Acceptance Criteria**:
- [ ] Chart appears in main content area (above "Recent Pull Requests")
- [ ] Chart type: Horizontal bar chart
- [ ] Chart title: "Pull Request Size Distribution"
- [ ] Chart subtitle: "Based on lines changed (additions + deletions)"
- [ ] Size buckets:
  - [ ] XS: 1-10 lines
  - [ ] S: 11-50 lines
  - [ ] M: 51-200 lines
  - [ ] L: 201-500 lines
  - [ ] XL: 501-1000 lines
  - [ ] XXL: 1000+ lines
- [ ] Each bar shows:
  - [ ] Count of PRs in bucket
  - [ ] Percentage of total PRs
  - [ ] Bar colored by size (gradient: green for XS → red for XXL)
- [ ] Tooltip on hover: "X PRs (Y%) • Median: Z lines"
- [ ] Median lines changed per bucket shown in tooltip
- [ ] Only count merged PRs from last 90 days
- [ ] If <10 total PRs, show message: "Insufficient data for distribution analysis"
- [ ] Responsive design (stacks on mobile)
- [ ] Loading state shows skeleton chart
- [ ] Accessibility: Data available as table toggle

**Technical Notes**:
- Add `get_pr_size_distribution()` to `apps/public/aggregations.py`
- Query: `SELECT CASE WHEN (additions+deletions) BETWEEN...`
- Calculate median per bucket for tooltip
- Cache in view context for 1 hour

**Design Notes**:
- Color gradient: `#10B981` (XS) → `#EF4444` (XXL)
- Use DaisyUI card with Chart.js horizontal bar chart
- Match existing chart styling

---

## Story #4: Fix PR Author Attribution Bug

**Title**: Correct Pull Request Author Attribution

**User Story**:
As a **visitor viewing PR data**, I want to **see the correct PR author** so that **contributor attribution is accurate and trustworthy**.

**Priority**: P0 (Critical - data integrity issue)

**Dependencies**: None

**Acceptance Criteria**:
- [ ] Investigate root cause of author mismatch (e.g., PR #47983 showing "inkeep" instead of correct author)
- [ ] Hypothesis: Bot commits vs. PR author confusion
- [ ] Fix logic in GitHub sync to correctly identify PR author:
  - [ ] Use `pull_request.user.login` from GitHub API
  - [ ] NOT `commits[0].author.login` (can be bot/co-author)
- [ ] Add test case: PR with bot commits shows human author
- [ ] Add test case: PR with co-authored commits shows primary author
- [ ] Backfill existing PRs with correct author attribution
  - [ ] Write migration script: `fix_pr_author_attribution.py`
  - [ ] Dry-run mode to preview changes
  - [ ] Log all corrections to file for audit
  - [ ] Run on staging before production
- [ ] Verify fix on PostHog PR #47983 specifically
- [ ] Update `apps/integrations/services/github_sync/pr_sync.py` if needed
- [ ] Add monitoring: Alert if >5% PRs have null author
- [ ] Document correct attribution logic in code comments

**Technical Notes**:
- Check `apps/integrations/services/github_sync/pr_sync.py:sync_pull_request()`
- GitHub API: `GET /repos/{owner}/{repo}/pulls/{number}` → use `user.login`
- TeamMember lookup: `get_or_create(github_username=pull_request.user.login)`
- Edge cases: Deleted users, renamed users, organization bots

**Testing Requirements**:
- [ ] Unit test: Mock GitHub API with bot commit
- [ ] Unit test: Mock GitHub API with co-authored commit
- [ ] Integration test: Sync real PR with known author
- [ ] E2E test: Verify author displays correctly on public page

**Design Notes**:
- No UI changes needed (fix is backend data quality)

---

## Story #5: Enhanced Team Member Breakdown

**Title**: Top Contributors with Avatar Images

**User Story**:
As a **visitor exploring team composition**, I want to **see the top contributors with their GitHub avatars** so that **I can quickly identify key team members and feel connected to real people**.

**Priority**: P1 (High value for engagement)

**Dependencies**: None

**Acceptance Criteria**:
- [ ] Section title: "Top Contributors (Last 90 Days)"
- [ ] Show top 20 contributors only (sorted by PR count)
- [ ] Each contributor displays:
  - [ ] GitHub avatar image (40x40px, rounded)
  - [ ] Avatar loaded from `https://github.com/{username}.png?size=40`
  - [ ] GitHub username (clickable link to profile)
  - [ ] PR count: "X PRs"
  - [ ] AI adoption rate: "Y% AI-assisted"
- [ ] Layout:
  - [ ] Grid: 4 columns desktop, 2 columns tablet, 1 column mobile
  - [ ] Card-based design with hover effect
- [ ] Clicking username opens GitHub profile in new tab
- [ ] Clicking avatar also opens GitHub profile
- [ ] If contributor has no avatar, show placeholder initials (first letter of username)
- [ ] Tooltip on hover shows: "Username • X PRs • Y% AI-assisted"
- [ ] Sort order: PR count descending
- [ ] Only count merged PRs from last 90 days
- [ ] If <1 contributor, show: "No recent contributors"
- [ ] Loading state: Show 20 skeleton cards with placeholder avatars
- [ ] Error state: If avatar fails to load, show initials fallback
- [ ] Add `rel="noopener noreferrer"` to all external links

**Technical Notes**:
- Query: `TeamMember.objects.filter(pull_requests__merged_at__gte=90_days_ago, pull_requests__team=org.team)`
- Aggregate: `annotate(pr_count=Count('pull_requests'), ai_pct=Avg('pull_requests__is_ai_assisted'))`
- Avatar URL: Direct GitHub link (no storage needed)
- Cache contributor list in `PublicOrgStats.top_contributors` JSON field

**Design Notes**:
- Card with subtle shadow and hover lift effect
- Avatar with `ring-2 ring-gray-200` border
- Username in bold, metrics in muted text
- Use DaisyUI card component

---

## Story #6: Organization Logo Display

**Title**: Show Organization Logo in Page Header

**User Story**:
As a **visitor landing on an org page**, I want to **see the organization's logo prominently** so that **I immediately recognize the brand and feel confident I'm on the right page**.

**Priority**: P1 (High value for brand recognition)

**Dependencies**: None

**Acceptance Criteria**:
- [ ] Logo appears in hero section (top of page)
- [ ] Position: Left side of org name
- [ ] Logo size: 64x64px on desktop, 48x48px on mobile
- [ ] Logo source: `PublicOrgProfile.logo_url` field
- [ ] Logo has rounded corners (8px border radius)
- [ ] Logo has subtle shadow for depth
- [ ] If logo URL is blank/null, show placeholder:
  - [ ] Circle with org initials (first 2 letters of display name)
  - [ ] Background: Brand gradient (blue to purple)
  - [ ] Text: White, bold, centered
- [ ] Logo alt text: "{org_name} logo"
- [ ] Logo is NOT clickable (static visual element)
- [ ] Lazy loading: Use `loading="lazy"` attribute
- [ ] Error handling: If logo fails to load, show initials placeholder
- [ ] Logo responsive: Scales proportionally on mobile
- [ ] Logo aligns vertically center with org name

**Technical Notes**:
- `PublicOrgProfile.logo_url` already exists (may be empty for some orgs)
- Add fallback logo generator using org initials
- Use CSS for placeholder gradient background
- No external API calls (logo URL stored in DB)

**Design Notes**:
- Shadow: `shadow-md` (DaisyUI)
- Border radius: `rounded-lg`
- Placeholder gradient: `bg-gradient-to-br from-blue-500 to-purple-600`
- Spacing: 16px gap between logo and org name

---

## Story #7: Top Reviewers Limit

**Title**: Display Top 10 Reviewers Only

**User Story**:
As a **visitor scanning the page**, I want to **see the most active reviewers without overwhelming detail** so that **I can quickly identify code review leaders and keep the page scannable**.

**Priority**: P2 (Nice to have, reduces clutter)

**Dependencies**: None

**Acceptance Criteria**:
- [ ] Section title: "Top Reviewers (Last 90 Days)"
- [ ] Show exactly top 10 reviewers (sorted by review count)
- [ ] Each reviewer displays:
  - [ ] GitHub username (clickable link)
  - [ ] Review count: "X reviews"
  - [ ] Average approval time: "Y hours to approve"
- [ ] Clicking username opens GitHub profile in new tab
- [ ] If <10 reviewers, show all available
- [ ] If 0 reviewers, show: "No recent reviewers"
- [ ] Remove any "Show more" or pagination (hard limit at 10)
- [ ] Tooltip on hover shows full reviewer stats
- [ ] Layout: Table format (same as current)
- [ ] Sort order: Review count descending
- [ ] Only count reviews from last 90 days on merged PRs
- [ ] Loading state: 10 skeleton rows
- [ ] Add `rel="noopener noreferrer"` to GitHub links

**Technical Notes**:
- Query existing reviewer aggregation logic
- Add `.order_by('-review_count')[:10]` limit
- No pagination needed (hard cutoff)
- Cache in view context for 1 hour

**Design Notes**:
- Same table styling as current implementation
- No visual changes, just data limit

---

## Story #8: Enhanced PR Table with New Columns

**Title**: Add Technology, PR Size, and PR Type Columns to Recent PRs Table

**User Story**:
As a **visitor analyzing recent work**, I want to **see technology, PR size, and PR type at a glance** so that **I can quickly understand the nature of recent contributions without clicking into each PR**.

**Priority**: P1 (High value for depth)

**Dependencies**: None

**Acceptance Criteria**:
- [ ] Table displays recent 20 merged PRs (existing behavior)
- [ ] Add 3 new columns:
  1. **Technology** column:
     - [ ] Shows top 2 tech categories (e.g., "React, Python")
     - [ ] Source: `effective_tech_categories` property
     - [ ] If no tech detected: "—"
     - [ ] Format: Comma-separated, max 2 tags
     - [ ] Truncate long tech names (max 15 chars per tag)
  2. **PR Size** column:
     - [ ] Shows size badge: XS, S, M, L, XL, XXL
     - [ ] Based on `additions + deletions`
     - [ ] Color-coded: Green (XS) → Red (XXL)
     - [ ] Same buckets as PR Size Distribution chart
  3. **PR Type** column:
     - [ ] Shows PR type: Feature, Bugfix, Refactor, Docs, Test, Chore, CI
     - [ ] Source: `effective_pr_type` property
     - [ ] Icon + label (e.g., 🎯 Feature, 🐛 Bugfix)
     - [ ] If no type detected: "—"
- [ ] Existing columns remain:
  - [ ] PR title (with link to GitHub)
  - [ ] Author (with GitHub link)
  - [ ] Merged date (relative time, e.g., "2 days ago")
  - [ ] Cycle time (e.g., "4.2h")
- [ ] Column order (left to right):
  1. PR Title
  2. Author
  3. Technology (NEW)
  4. PR Type (NEW)
  5. PR Size (NEW)
  6. Cycle Time
  7. Merged Date
- [ ] Table is responsive:
  - [ ] Desktop: All columns visible
  - [ ] Tablet: Hide Technology column
  - [ ] Mobile: Only show Title, Author, PR Type
- [ ] NO filters or sorting controls (read-only view)
- [ ] Tooltip on hover shows full tech list (not just top 2)
- [ ] Links open in new tab with `rel="noopener noreferrer"`
- [ ] Loading state: 20 skeleton rows
- [ ] If 0 PRs: "No recent pull requests"

**Technical Notes**:
- `effective_tech_categories`: Returns list from LLM summary JSON
- `effective_pr_type`: Returns inferred type from LLM data or fallback logic
- Size calculation: `additions + deletions` (already on model)
- Query: Existing PR list query, add `.select_related('author')`
- No extra DB queries needed (all data on PullRequest model)

**Design Notes**:
- Tech tags: Small pills with `badge` class (DaisyUI)
- PR type: Icon + text (use Heroicons)
- PR size badge: Colored pill (match size distribution colors)
- Table styling: Match existing "Recent Pull Requests" table
- Ensure table doesn't overflow on mobile (horizontal scroll if needed)

---

## Story #9: Technology & PR Type Trends Charts

**Title**: Visualize Technology and PR Type Trends Over Time

**User Story**:
As a **technical leader evaluating tech stack evolution**, I want to **see how technology usage and PR types change over time** so that **I can understand focus areas, tech adoption, and work distribution patterns**.

**Priority**: P2 (Nice to have, showcases depth)

**Dependencies**: None

**Acceptance Criteria**:

### Chart 1: Technology Trends Over Time
- [ ] Chart title: "Technology Trends"
- [ ] Chart subtitle: "Top 5 technologies, last 90 days"
- [ ] Chart type: Stacked area chart
- [ ] X-axis: Date (weekly buckets)
- [ ] Y-axis: PR count
- [ ] Show top 5 technologies by PR count
- [ ] Each technology as colored area (stacked)
- [ ] Legend shows tech names with color coding
- [ ] Tooltip shows date + tech + PR count
- [ ] If <5 technologies total, show all
- [ ] If no tech data, show: "No technology data available"

### Chart 2: PR Type Trends Over Time
- [ ] Chart title: "PR Type Distribution"
- [ ] Chart subtitle: "Weekly breakdown, last 90 days"
- [ ] Chart type: Stacked bar chart
- [ ] X-axis: Week (format: "Jan 15")
- [ ] Y-axis: PR count
- [ ] Show all PR types: Feature, Bugfix, Refactor, Docs, Test, Chore, CI
- [ ] Each type as colored segment (stacked)
- [ ] Legend shows PR types with color coding
- [ ] Tooltip shows week + type + count + percentage
- [ ] If no type data, show: "No PR type data available"

### Shared Requirements
- [ ] Both charts appear at bottom of page (above "Tracked Repositories")
- [ ] Side-by-side on desktop, stacked on mobile/tablet
- [ ] Loading state: Skeleton charts
- [ ] Responsive design
- [ ] Use Chart.js library
- [ ] Accessibility: Data available as table toggle
- [ ] Only count merged PRs from last 90 days
- [ ] Cache data in view context for 1 hour

**Technical Notes**:
- Add `get_technology_trends()` to `apps/public/aggregations.py`
- Add `get_pr_type_trends()` to `apps/public/aggregations.py`
- Group by week: `TruncWeek('merged_at')`
- Query `effective_tech_categories` and `effective_pr_type` fields
- Return format: `{weeks: [], tech_counts: {tech1: [], tech2: []}, ...}`
- Handle null/missing LLM data gracefully

**Design Notes**:
- Technology chart colors: Use distinct colors from Chart.js palette
- PR type colors: Match PR type badges from table
  - Feature: Blue, Bugfix: Red, Refactor: Purple, Docs: Green, Test: Yellow, Chore: Gray, CI: Orange
- Same card container as other charts
- Match existing Chart.js theme

---

## Story #10: Daily Data Pipeline

**Title**: Automated Daily PR Sync and Weekly Insight Generation

**User Story**:
As a **Tformance platform operator**, I want **public org data to update automatically daily** so that **visitors see fresh data without manual intervention and we minimize LLM processing costs**.

**Priority**: P0 (Critical for production readiness)

**Dependencies**: Stories #1-9 (data must exist before pipeline runs)

**Acceptance Criteria**:

### Daily PR Sync (New PRs Only)
- [ ] Celery task: `sync_public_org_prs_daily`
- [ ] Schedule: Runs daily at 2:00 AM UTC
- [ ] Scope: All orgs where `PublicOrgProfile.is_public=True`
- [ ] Behavior:
  - [ ] For each public org's repos:
    - [ ] Query GitHub API for merged PRs since last sync
    - [ ] Use `since` parameter to fetch only new PRs (last 24 hours)
    - [ ] Create new `PullRequest` records
    - [ ] Skip PRs that already exist (by `github_pr_id + github_repo`)
  - [ ] Update `PublicOrgStats.last_computed_at` after each org
  - [ ] Log sync summary: "Synced X new PRs across Y orgs"
- [ ] Error handling:
  - [ ] If GitHub API rate limit hit, pause and retry after reset
  - [ ] If org sync fails, log error and continue to next org
  - [ ] Send Slack alert if >10% of orgs fail
- [ ] Monitoring:
  - [ ] Track PRs synced per day (Prometheus metric)
  - [ ] Alert if daily sync takes >2 hours
  - [ ] Alert if 0 PRs synced for 3+ consecutive days

### Daily LLM Batch Processing (Groq Batches Only)
- [ ] Celery task: `process_public_org_llm_batches_daily`
- [ ] Schedule: Runs daily at 4:00 AM UTC (2 hours after PR sync)
- [ ] Scope: PRs synced in last 24 hours that lack LLM summaries
- [ ] Behavior:
  - [ ] Query PRs where `llm_summary IS NULL AND merged_at > NOW() - INTERVAL '24 hours'`
  - [ ] Create Groq Batch API request (up to 1000 PRs per batch)
  - [ ] Submit batch to Groq API
  - [ ] Store batch ID in DB for status polling
  - [ ] Poll batch status every 10 minutes until complete
  - [ ] When complete, download results and update `llm_summary` field
  - [ ] Mark PRs as processed
- [ ] Cost optimization:
  - [ ] Use Groq Batch API (50% cost savings vs. real-time)
  - [ ] Batch size: 500-1000 PRs per request
  - [ ] Respect Groq rate limits (max 5 concurrent batches)
- [ ] Error handling:
  - [ ] If batch fails, retry up to 3 times
  - [ ] Log failed PRs to separate table for manual review
  - [ ] Send alert if >5% of PRs fail processing
- [ ] Monitoring:
  - [ ] Track LLM processing cost per day
  - [ ] Alert if daily cost >$50
  - [ ] Track batch processing time (target: <2 hours)

### Weekly Insight Generation
- [ ] Celery task: `generate_public_org_insights_weekly`
- [ ] Schedule: Runs weekly on Sundays at 6:00 AM UTC
- [ ] Scope: All public orgs
- [ ] Behavior:
  - [ ] For each org:
    - [ ] Query PRs from last 30 days
    - [ ] Generate engineering insight via LLM
    - [ ] Save to `PublicOrgProfile.latest_insight` (new field)
    - [ ] Update `PublicOrgProfile.latest_insight_generated_at`
  - [ ] Use existing `generate_public_insights.py` command logic
  - [ ] Generate insights based on 30-day rolling window
- [ ] Error handling:
  - [ ] If insight generation fails, keep previous insight
  - [ ] Log failures for review
  - [ ] Send weekly summary report: "X/Y insights generated successfully"
- [ ] Monitoring:
  - [ ] Track insight generation success rate
  - [ ] Alert if <80% success rate

### Stats Refresh (After Each Pipeline Step)
- [ ] After PR sync: Recompute `PublicOrgStats` for affected orgs
- [ ] After LLM processing: Recompute stats for orgs with newly processed PRs
- [ ] After insight generation: Update `last_computed_at` timestamp
- [ ] Stats computation:
  - [ ] Total PRs
  - [ ] AI adoption %
  - [ ] Median cycle time
  - [ ] Active contributors (90 days)
  - [ ] Top AI tools
  - [ ] Top reviewers
  - [ ] PR size distribution
  - [ ] Technology trends (for charts)
  - [ ] PR type trends (for charts)
  - [ ] Tracked repos list

### Infrastructure Requirements
- [ ] Use existing Celery infrastructure
- [ ] Use existing Redis for task queue
- [ ] Use existing Groq API integration
- [ ] Use existing GitHub API integration
- [ ] Add Celery Beat schedule configuration
- [ ] Add monitoring dashboard for pipeline health
- [ ] Add admin command to trigger manual sync: `python manage.py sync_public_orgs_manual`

**Technical Notes**:
- Reuse existing GitHub sync logic from `apps/integrations/services/github_sync/`
- Reuse existing LLM batch logic from `apps/metrics/management/commands/run_llm_batch.py`
- Add new tasks to `apps/public/tasks.py`
- Add Celery Beat schedule to `tformance/celery.py`
- Add monitoring to existing Prometheus/Grafana setup

**Testing Requirements**:
- [ ] Unit tests for each Celery task
- [ ] Integration test: Mock GitHub API, verify PR creation
- [ ] Integration test: Mock Groq API, verify batch processing
- [ ] Integration test: Verify stats recomputation after sync
- [ ] E2E test: Run full pipeline on staging, verify public page updates
- [ ] Load test: Verify pipeline handles 100 orgs, 500 new PRs/day

**Documentation Requirements**:
- [ ] Document pipeline architecture in `docs/plans/technical-architecture.md`
- [ ] Document monitoring setup in `dev/guides/MONITORING.md`
- [ ] Document manual sync procedure in runbook
- [ ] Document error recovery procedures

---

## Success Metrics

**User Engagement**:
- Time on page increases by 30%
- Scroll depth increases (more users reach bottom)
- Click-through rate to "Start Free Trial" increases by 20%

**Data Quality**:
- PR author accuracy: 100% (zero misattributed PRs)
- LLM processing coverage: >95% of PRs have summaries
- Data freshness: <24 hours lag from PR merge to public page

**Performance**:
- Page load time: <2 seconds (p95)
- Chart render time: <500ms
- Daily pipeline runtime: <3 hours total

**Conversion**:
- Trial signups from public pages increase by 25%
- Organic search traffic increases by 40%
- Page shares on social media increase by 50%

---

## Out of Scope

The following are explicitly NOT included in this phase:

- Real-time PR updates (daily sync only)
- User authentication/accounts for public pages
- Commenting or interaction features
- Custom date range selectors for charts
- Export/download features for data
- Comparison across multiple orgs
- Historical trend analysis beyond 90 days
- Mobile app for public pages
- Internationalization (English only)

---

## Open Questions

1. **Logo sourcing**: Should we automatically fetch org logos from GitHub API or require manual upload?
   - **Recommendation**: Auto-fetch from GitHub API, allow manual override in admin

2. **PR author bug**: Is this a sync issue or a display issue?
   - **Recommendation**: Investigate both sync logic and TeamMember creation

3. **Chart interactivity**: Should charts be clickable to filter/drill down?
   - **Recommendation**: No for MVP (adds complexity), revisit in Phase 2

4. **Repository count limit**: What if an org has 200+ repos?
   - **Recommendation**: Show top 50 by PR volume, note "partial coverage"

5. **LLM batch processing timing**: Should we process PRs immediately or wait for daily batch?
   - **Recommendation**: Daily batch only for 50% cost savings

6. **Insight generation frequency**: Weekly or daily?
   - **Recommendation**: Weekly (30-day window is stable, reduces LLM costs)

---

## Next Steps

1. **Technical Lead** reviews stories and creates technical architecture plan (Task #2)
2. **QA Lead** defines test plan and acceptance testing approach (Task #3)
3. **Marketing/Growth** defines SEO, analytics, and promotion strategy (Task #4)
4. **Team** reviews all plans together and estimates effort
5. **Product Manager** prioritizes stories into sprints based on dependencies and value

---

## Appendix: Story Prioritization Matrix

| Story | Priority | Effort | Value | Dependencies | Sprint |
|-------|----------|--------|-------|--------------|--------|
| #4 PR Author Bug | P0 | M | High | None | Sprint 1 |
| #10 Daily Pipeline | P0 | XL | High | All others | Sprint 3 |
| #1 Repo List | P0 | S | High | None | Sprint 1 |
| #5 Team Breakdown | P1 | M | High | None | Sprint 1 |
| #6 Org Logo | P1 | S | Medium | None | Sprint 1 |
| #8 Enhanced PR Table | P1 | L | High | #4 | Sprint 2 |
| #2 Dual-Axis Chart | P1 | M | High | None | Sprint 2 |
| #7 Top Reviewers Limit | P2 | XS | Low | None | Sprint 2 |
| #3 PR Size Chart | P2 | M | Medium | None | Sprint 2 |
| #9 Trend Charts | P2 | L | Medium | #8 | Sprint 3 |

**Effort Scale**: XS (1-2 days), S (3-5 days), M (1 week), L (2 weeks), XL (3+ weeks)

**Sprint Breakdown**:
- **Sprint 1** (2 weeks): Foundation - Stories #1, #4, #5, #6
- **Sprint 2** (2 weeks): Enhancements - Stories #2, #3, #7, #8
- **Sprint 3** (3 weeks): Pipeline & Advanced - Stories #9, #10

**Total Estimated Timeline**: 7 weeks (includes buffer for testing, refinement, and production deployment)
