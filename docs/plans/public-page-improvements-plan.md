# Public OSS Analytics: Comprehensive Implementation Plan

**Date:** 2026-02-15
**Branch:** `feature/public-oss-analytics`
**Status:** Ready for Implementation
**Prepared by:** Team (PM, Senior Dev, QA, Marketing)

---

## Table of Contents

1. [Executive Summary](#1-executive-summary)
2. [Goals & Success Metrics](#2-goals--success-metrics)
3. [Current State](#3-current-state)
4. [Sprint Plan & Story Map](#4-sprint-plan--story-map)
5. [Story Details (All 10)](#5-story-details)
6. [Daily Data Pipeline Architecture](#6-daily-data-pipeline-architecture)
7. [API Quota & Job Scheduling](#7-api-quota--job-scheduling)
8. [Redis Cache Strategy](#8-redis-cache-strategy)
9. [Test Plan](#9-test-plan)
10. [SEO, GEO & Marketing](#10-seo-geo--marketing)
11. [PostHog Analytics Events](#11-posthog-analytics-events)
12. [Open Questions & Decisions](#12-open-questions--decisions)
13. [Related Documents](#13-related-documents)

---

## 1. Executive Summary

Enhance public OSS analytics pages (e.g., `/open-source/posthog/`) with 10 improvements spanning new visualizations, data quality fixes, UI enhancements, and an automated daily data pipeline. The goal is to showcase Tformance's analytical depth, attract SEO/GEO traffic, and convert visitors to trial signups.

**Key deliverables:**
- 4 new charts (dual-axis trend, PR size distribution, tech trends, PR type trends)
- Enhanced PR table with technology, type, and size columns
- Repos analyzed list with GitHub links
- PR author attribution bug fix (github_id=0 collision)
- Organization logos and contributor avatars
- Automated daily sync pipeline (GitHub -> LLM -> Stats -> Cache purge)
- PostHog analytics on all interactive elements
- SEO/GEO optimizations (JSON-LD, llms.txt, citable paragraphs, CTAs)

---

## 2. Goals & Success Metrics

### Business Goals
- Showcase Tformance capabilities to attract trial signups
- Build SEO authority for "engineering metrics" and "AI coding tools" queries
- Enable AI search engines to cite our data (GEO)
- Increase organic traffic and reduce bounce rate

### Success Metrics

| Metric | Target | How to Measure |
|--------|--------|----------------|
| Time on page | +30% | PostHog |
| Scroll depth | +25% (more users reach bottom sections) | PostHog |
| Trial signups from public pages | +25% | PostHog conversion funnel |
| Organic search traffic | +40% | Google Search Console |
| PR author accuracy | 100% (zero misattributed) | Automated test |
| LLM processing coverage | >95% of PRs have summaries | DB query |
| Data freshness | <24h from PR merge to public page | Pipeline monitoring |
| Page load time (p95) | <2 seconds | Cloudflare analytics |
| Daily pipeline runtime | <30 minutes | Celery monitoring |

---

## 3. Current State

### Data Volume
- **100 public orgs**, 121 repos
- **23,463 total PRs**, 14,929 merged
- **~110 new merged PRs/day** across all public orgs
- **14,882 PRs unprocessed by LLM** (backlog)
- **GitHub PAT quota:** 5,000 GraphQL points/hour, 5,000 REST requests/hour

### Existing Infrastructure
- `apps/public/` app with models, views, services, aggregations, tasks, templates
- `PublicOrgProfile` + `PublicOrgStats` models (pre-computed stats)
- Redis cache with `public:` prefix (currently 1h TTL)
- Cloudflare CDN with 12h browser cache + purge-everything after stats refresh
- 246 passing tests, 1 failing (`test_directory_excludes_private_org`)
- Celery Beat for scheduled tasks

### Known Issues
- **PR author bug:** `github_id=0` collision in `RealProjectSeeder._create_team_members()` causes all cached contributors to map to the same TeamMember
- **Failing test:** `test_directory_excludes_private_org` - org name not rendering in directory HTML
- **Redis cache too short:** 1h TTL but data only refreshes daily

---

## 4. Sprint Plan & Story Map

### Sprint 1 (2 weeks): Foundation & Data Quality

| Story | Title | Priority | Effort |
|-------|-------|----------|--------|
| #4 | Fix PR Author Attribution Bug | P0 | M |
| #1 | Repository List | P0 | S |
| #6 | Organization Logo | P1 | S |
| #5 | Team Member Avatars (top 20) | P1 | M |

**Sprint 1 goal:** Fix data integrity, add transparency features, improve visual identity.

### Sprint 2 (2 weeks): Charts & Enhanced Table

| Story | Title | Priority | Effort |
|-------|-------|----------|--------|
| #2 | Combined Cycle Time + AI Adoption Chart | P1 | M |
| #8 | Enhanced PR Table (type, size, tech) | P1 | L |
| #7 | Top Reviewers Limit (10) | P2 | XS |
| #3 | PR Size Distribution Chart | P2 | M |

**Sprint 2 goal:** Rich visualizations and deeper data presentation.

### Sprint 3 (3 weeks): Pipeline & Advanced Charts

| Story | Title | Priority | Effort |
|-------|-------|----------|--------|
| #9 | Technology & PR Type Trends Charts | P2 | L |
| #10 | Daily Data Pipeline (sync + LLM + stats) | P0 | XL |

**Sprint 3 goal:** Automated data freshness and trend analysis.

**Effort scale:** XS (1-2 days), S (3-5 days), M (1 week), L (2 weeks), XL (3+ weeks)
**Total estimated timeline:** 7 weeks

---

## 5. Story Details

### Story #1: Tracked Repositories List

**User Story:** As a visitor evaluating an OSS organization, I want to see which repositories Tformance is analyzing so I can verify data completeness.

**Priority:** P0 | **Sprint:** 1 | **Effort:** S

**Acceptance Criteria:**
- Section at bottom of page above "Related Organizations"
- Title: "Tracked Repositories" with count badge
- Each repo: `owner/repo-name` as clickable GitHub link (new tab, `rel="noopener noreferrer"`)
- PR count per repo (e.g., "1,234 PRs analyzed")
- Sorted by PR count descending
- Responsive grid: 3 cols desktop, 2 cols tablet, 1 col mobile

**New Aggregation Function:** `apps/public/aggregations.py`

```python
def compute_repos_analyzed(team_id: int, start_date=None, end_date=None) -> list[dict]:
    """Returns [{repo, pr_count, github_url}, ...] sorted by pr_count desc."""
```

**Service change:** Add `repos_analyzed = compute_repos_analyzed(team_id)` to `get_org_detail()` result dict.

**Template:** New section in `org_detail.html` with responsive grid of repo cards.

---

### Story #2: Combined Cycle Time + AI Adoption Chart

**User Story:** As a technical leader, I want to see cycle time and AI adoption on the same chart to visually correlate AI tool usage with delivery speed trends.

**Priority:** P1 | **Sprint:** 2 | **Effort:** M

**Acceptance Criteria:**
- Chart.js dual-axis line chart
- Left Y-axis: Cycle Time (hours) - secondary color
- Right Y-axis: AI Adoption (%) - accent color
- X-axis: Monthly labels
- Uses existing `monthly_trends` and `cycle_time_trend` context data
- Responsive, with legend and tooltips

**Backend changes:** None needed - data already in template context from `compute_monthly_trends()` and `compute_monthly_cycle_time()`.

**Template:** Replace existing separate charts with single dual-axis chart using Chart.js multi-axis config.

---

### Story #3: PR Size Distribution Chart

**User Story:** As a visitor, I want to see how PR sizes are distributed to assess code review culture and development patterns.

**Priority:** P2 | **Sprint:** 2 | **Effort:** M

**Acceptance Criteria:**
- Doughnut chart with 5 buckets: XS (1-50), S (51-200), M (201-500), L (501-1000), XL (1000+)
- Each bucket shows count and percentage
- Color gradient: green (XS) -> red (XL)
- Tooltip: "XS: 145 PRs (29.0%)"
- Based on `additions + deletions` for merged PRs

**New Aggregation Function:** `apps/public/aggregations.py`

```python
def compute_pr_size_distribution(team_id, start_date=None, end_date=None) -> list[dict]:
    """Returns [{bucket, count, pct}, ...] for 5 size buckets."""
```

Uses Django ORM `Case/When` annotation with `F("additions") + F("deletions")`.

**Service change:** Add to `get_org_detail()` result dict.

---

### Story #4: Fix PR Author Attribution Bug (CRITICAL)

**User Story:** As a visitor, I want to see the correct PR author so contributor attribution is accurate and trustworthy.

**Priority:** P0 | **Sprint:** 1 | **Effort:** M

**Root Cause:** `RealProjectSeeder._create_team_members()` caches members by `github_id`. Cached PRs from GraphQL have `author_id=0`, causing all contributors to collide on key `"0"` in the `_members_by_github_id` dict. The first contributor gets cached, and all subsequent lookups for `github_id=0` return that same member.

**Fix (3 changes in `apps/metrics/seeding/real_project_seeder.py`):**

1. **`_create_team_members()`**: Skip caching in `_members_by_github_id` when `github_id == 0`
2. **`_find_member()`**: Skip `_members_by_github_id` lookup when `github_id == 0`, go straight to username lookup
3. **`_members_by_github_id` dict**: Never store key `"0"`

**After fix:** Re-run `python manage.py seed_from_cache` to correct existing data.

**Verification:** Check PostHog PR #47983 shows correct author (not "inkeep").

**Test file:** `apps/metrics/tests/seeding/test_member_collision.py` (new) with 5 regression tests.

---

### Story #5: Top Contributors with Avatars

**User Story:** As a visitor, I want to see top contributors with GitHub avatars to identify key team members and feel connected to real people.

**Priority:** P1 | **Sprint:** 1 | **Effort:** M

**Acceptance Criteria:**
- Top 20 contributors by PR count (existing limit)
- GitHub avatar: `https://github.com/{username}.png?size=40` (32x32px rounded)
- Fallback: DaisyUI `avatar placeholder` with initials
- `loading="lazy"` on images
- `onerror` handler to show initials on image load failure

**Backend change:** Add `avatar_url` field to `compute_member_breakdown()` results.

**Template:** Add `<img>` tags to contributor cells in team breakdown table.

---

### Story #6: Organization Logo in Header

**User Story:** As a visitor, I want to see the organization's logo prominently to immediately recognize the brand.

**Priority:** P1 | **Sprint:** 1 | **Effort:** S

**Acceptance Criteria:**
- Logo in hero section, left of org name
- Size: 64x64px desktop, 48x48px mobile
- Source: `PublicOrgProfile.logo_url`
- Fallback: GitHub org avatar via `https://github.com/{org_slug}.png?size=80`
- If both fail: circle with org initials + gradient background
- `loading="lazy"`, rounded corners, subtle shadow

**Backend changes:** None - `logo_url` already exists on `PublicOrgProfile`.

---

### Story #7: Limit Top Reviewers to 10

**User Story:** As a visitor, I want to see the most active reviewers without overwhelming detail.

**Priority:** P2 | **Sprint:** 2 | **Effort:** XS

**Change:** `apps/public/aggregations.py` - change `[:15]` to `[:10]` in `compute_review_distribution()`.

---

### Story #8: Enhanced PR Table

**User Story:** As a visitor, I want to see technology, PR size, and PR type at a glance in the recent PRs table.

**Priority:** P1 | **Sprint:** 2 | **Effort:** L

**Acceptance Criteria:**
- 3 new columns: Technology, PR Type, PR Size
- Technology: top 2 categories from `effective_tech_categories` (comma-separated pills)
- PR Type: badge with color coding (feature=blue, bugfix=red, refactor=orange, docs=purple, test=green, chore=gray, ci=cyan)
- PR Size: colored badge XS/S/M/L/XL (same buckets as Story #3)
- No filters or sorting (read-only view)
- Responsive: hide Tech column on tablet, show only Title+Author+Type on mobile

**Backend change:** Enhance `compute_recent_prs()` to include `pr_type`, `tech_categories`, `size_label`, `additions`, `deletions` using `effective_*` properties.

**Column order:** PR Title | Author | Technology | PR Type | PR Size | Cycle Time | Merged Date

---

### Story #9: Technology & PR Type Trends

**User Story:** As a technical leader, I want to see how technology usage and PR types change over time to understand focus areas and work distribution.

**Priority:** P2 | **Sprint:** 3 | **Effort:** L

**Acceptance Criteria:**
- **Chart 1:** Technology Trends - stacked area chart, top 5 technologies, monthly
- **Chart 2:** PR Type Distribution - stacked bar chart, all types, monthly
- Both at bottom of page above "Tracked Repositories"
- Side-by-side on desktop, stacked on mobile
- Handle missing LLM data gracefully (skip PRs without `llm_summary`)

**New Aggregation Functions:** `apps/public/aggregations.py`

```python
def compute_tech_category_trends(team_id, start_date=None, end_date=None) -> list[dict]:
    """Returns [{month, categories: {backend: N, frontend: N, ...}}, ...]"""

def compute_pr_type_trends(team_id, start_date=None, end_date=None) -> list[dict]:
    """Returns [{month, types: {feature: N, bugfix: N, ...}}, ...]"""
```

Uses ORM + Python grouping with `effective_tech_categories` and `effective_pr_type` properties. Groups by `TruncMonth("pr_created_at")`.

**Performance note:** These functions load PR objects to access `effective_*` properties. For large teams, consider caching results in `PublicOrgStats` or pre-computing during stats refresh.

---

### Story #10: Daily Data Pipeline

**User Story:** As a platform operator, I want public org data to update automatically daily so visitors see fresh data without manual intervention.

**Priority:** P0 | **Sprint:** 3 | **Effort:** XL

See [Section 6: Daily Data Pipeline Architecture](#6-daily-data-pipeline-architecture) for full details.

---

## 6. Daily Data Pipeline Architecture

### Pipeline Flow

```
4:00 AM UTC  sync_public_repos_task()     ~17 min
               |
               v
             process_public_prs_llm_task()  ~6 min
               |
               v
             compute_public_stats_task()    ~3 min (existing)
               |
               v
             _clear_public_cache()          ~1 sec
             purge_all_cache()              ~1 sec (Cloudflare)
```

**Total: ~26 minutes end-to-end**

### Task 1: `sync_public_repos_task()`

**File:** `apps/public/tasks.py`

```python
@shared_task(soft_time_limit=3600, time_limit=4000)
def sync_public_repos_task() -> dict[str, int]:
```

**Logic:**
1. Load all `PublicOrgProfile.objects.filter(is_public=True)`
2. For each org, get repos from `profile.repos` JSONField
3. Determine `since_date` from `PublicOrgStats.last_computed_at`
4. Use `GitHubGraphQLFetcher` with:
   - Cache validation via `repo.pushedAt` (1 cheap GraphQL point)
   - If repo unchanged since cache: use cached data (0 additional API calls)
   - If repo changed: incremental sync (fetch PRs updated since last sync)
   - Check runs fetched via REST API fallback (1 call per PR)
5. Deduplicate by `(team_id, github_pr_id, github_repo)` unique constraint
6. Create new PRs, update existing if data changed
7. Sequential org processing (not parallel) per GitHub best practices

**Error handling:** Per-org try/except. If rate limit hit, stop and return partial results. Other errors: log and continue to next org.

### Task 2: `process_public_prs_llm_task()`

**File:** `apps/public/tasks.py`

```python
@shared_task(soft_time_limit=7200, time_limit=8000)
def process_public_prs_llm_task() -> dict[str, int]:
```

**Logic:**
1. Query PRs where `llm_summary IS NULL` for all public org teams (limit 500/day)
2. Build JSONL batch for Groq Batch API
3. Submit batch (returns batch_id immediately)
4. Poll for completion with exponential backoff (30s initial, max 5 min)
5. Download results, parse JSON, save to `pr.llm_summary`
6. Update AI confidence scores via `update_pr_ai_confidence(pr)`

**Cost optimization:** Groq Batch API = 50% cost savings vs real-time.

### Task 3: `compute_public_stats_task()` (existing)

Already implemented in `apps/public/tasks.py:64-138`. No changes needed.

### Chain Orchestration

```python
@shared_task
def run_daily_public_pipeline():
    from celery import chain
    chain(
        sync_public_repos_task.si(),
        process_public_prs_llm_task.si(),
        compute_public_stats_task.si(),
    ).apply_async(link_error=handle_pipeline_error.s())
```

### Weekly Insight Generation

```python
# Separate task, runs Monday 6:00 AM UTC
@shared_task
def generate_public_insights_task():
    """Generate insights for all public orgs using 30-day window."""
```

### Celery Beat Schedule

```python
# tformance/settings.py
"sync-public-analytics-daily": {
    "task": "apps.public.tasks.run_daily_public_pipeline",
    "schedule": crontab(minute=0, hour=4),  # 4:00 AM UTC
    "expire_seconds": 60 * 60 * 6,
},
"generate-public-insights-weekly": {
    "task": "apps.public.tasks.generate_public_insights_task",
    "schedule": crontab(minute=0, hour=6, day_of_week=1),  # Monday 6 AM
    "expire_seconds": 60 * 60 * 2,
},
```

---

## 7. API Quota & Job Scheduling

### GitHub GraphQL Quota

| Scenario | Per Repo | Total (85 repos) | % of 5K limit |
|----------|----------|-------------------|---------------|
| Cache hit (unchanged) | 1 point | 70 repos x 1 = 70 | 1.4% |
| Incremental sync | ~75 points | 15 repos x 75 = 1,125 | 22.5% |
| **Daily total** | | **~1,200 points** | **24%** |

### GitHub REST Quota (Check Runs)

| Item | Count | % of 5K limit |
|------|-------|---------------|
| New PRs/day | ~150-250 | |
| REST calls | ~200 | **4%** |

**Conclusion:** We use <25% of GitHub rate limits. All 70+ orgs can sync in a single run. No need to batch or spread across hours.

### Wall-Clock Time

| Task | Duration |
|------|----------|
| Sync (70 cached + 15 changed) | ~17 min |
| LLM batch (500 PRs via Groq) | ~6 min |
| Stats recomputation (70 orgs) | ~3 min |
| **Total pipeline** | **~26 min** |

### Memory

- Sequential processing: ~4 MB peak per org (garbage collected between orgs)
- Safe for Heroku 512 MB dynos

### Scaling Threshold

If we grow to 200+ orgs (~100 min sync time, ~80% GraphQL quota), consider batching orgs into 2 hourly runs.

---

## 8. Redis Cache Strategy

### Current vs Recommended

| Setting | Current | Recommended | Rationale |
|---------|---------|-------------|-----------|
| Redis TTL | 1h (3600s) | **6h (21600s)** | Data updates daily; 1h causes 23 unnecessary cache misses/day |
| CDN Cache-Control | 12h (43200s) | 12h (unchanged) | Already appropriate |

### Cache Key Structure (unchanged)

```
public:directory          # All orgs
public:directory:{year}   # Year-filtered
public:org:{slug}         # Per-org detail
public:industry:{key}     # Industry comparison
public:global             # Aggregate stats
```

### Invalidation Strategy

1. **After `compute_public_stats_task()`:** Full invalidation via Redis SCAN + Cloudflare purge-everything (existing behavior)
2. **Manual org add:** Selective invalidation of affected keys
3. **Mid-day updates:** Management command for manual sync + cache clear

---

## 9. Test Plan

### Test Strategy

- **Pattern:** Follow `apps/public/tests/test_aggregations.py` exactly
- **Setup:** `setUpTestData()` for class-level fixtures with factories
- **Factories:** `TeamFactory`, `TeamMemberFactory`, `PullRequestFactory`, `PRReviewFactory`
- **Assertions:** Simple `assert` statements
- **Database:** PostgreSQL required (PERCENTILE_CONT, JSONB)

### Story #4 Tests (Most Critical)

**File:** `apps/metrics/tests/seeding/test_member_collision.py` (NEW)

| Test | What It Verifies |
|------|-----------------|
| `test_multiple_contributors_with_github_id_zero_create_distinct_members` | 3 contributors with id=0 create 3 separate TeamMembers |
| `test_find_member_with_github_id_zero_resolves_by_username` | Lookup by username when id=0 returns correct member |
| `test_members_by_github_id_dict_does_not_cache_zero` | Key "0" never appears in cache dict |
| `test_mixed_zero_and_nonzero_ids_handled_correctly` | Valid IDs cached normally, id=0 only in username cache |
| `test_prs_assign_correct_author_when_all_ids_zero` | End-to-end: 3 PRs by 2 authors with id=0 get correct attribution |

### New Aggregation Tests

**File:** `apps/public/tests/test_aggregations.py` (APPEND)

| Test Class | Story | Tests |
|------------|-------|-------|
| `ComputeReposAnalyzedTests` | #1 | returns all repos, sorted by count, includes URLs, empty team, excludes non-merged |
| `ComputePrSizeDistributionTests` | #3 | 5 buckets, counts, percentages, edge cases (0 lines, boundary 51), empty team |
| `ComputeRecentPrsEnhancedTests` | #8 | includes pr_type, tech_categories, size_label, additions/deletions, LLM fallback, unknown type |
| `ComputeTechCategoryTrendsTests` | #9 | monthly data, category counts per month, sorted, handles missing LLM, multi-category PRs, empty team |
| `ComputePrTypeTrendsTests` | #9 | monthly data, type counts per month, handles unknown type, sorted, empty team |

### Pipeline Task Tests

**File:** `apps/public/tests/test_tasks.py` (APPEND)

| Test Class | Tests |
|------------|-------|
| `SyncPublicReposTaskTests` | fetches for all public orgs, incremental sync, API error handling, idempotency |
| `ProcessPublicPrsLlmTaskTests` | processes only null llm_summary, uses batch mode, handles Groq failures, partial batch failure |
| `GeneratePublicInsightsTaskTests` | generates for all public orgs, uses 30-day window, stores as DailyInsight |
| `RunDailyPublicPipelineTests` | chains tasks in correct order, stops chain on sync failure |
| `GitHubApiErrorHandlingTests` | rate limit 403, network timeout |
| `GroqBatchErrorHandlingTests` | batch submit failure, partial batch failure |
| `EmptyDataEdgeCasesTests` | org with 0 PRs, malformed llm_summary, zero additions/deletions |

### Security Tests (existing - fix failing test)

- Fix `test_directory_excludes_private_org` in `apps/public/tests/test_security.py`

### E2E Tests

**File:** `tests/e2e/public-pages.spec.ts` (APPEND)

- Repos section renders with GitHub links
- Combined chart canvas visible
- PR size chart visible
- Enhanced table has Type/Size/Tech columns with badges
- Org image displays
- Team member avatars render
- Top reviewers limited to 10
- Tech trends and PR type trends charts render
- PostHog events fire on page load

### Test Count Estimate

- Existing: 246 tests (1 failing)
- New: ~60-70 tests
- Total after: ~310+ tests

---

## 10. SEO, GEO & Marketing

### SEO Fixes (from Audit)

| Priority | Fix | Location |
|----------|-----|----------|
| High | Add `<a>` tags to directory table rows (crawlers can't follow JS `onclick`) | `_directory_list.html` |
| Medium | Add RSS autodiscovery `<link>` tag | `public/base.html` |
| Medium | Add `Vary: HX-Request` header for HTMX responses | `views.py:directory` |
| Medium | Chart.js: add `defer` attribute | `org_detail.html` |
| Medium | Add related org links (3-5 cards) to detail page | `org_detail.html` |
| Medium | Add `hasPart` to industry JSON-LD schema | `industry.html` |
| Medium | Add screen reader fallback for canvas charts | `org_detail.html` |
| Low | Dynamic `temporalCoverage` in Dataset schema | `org_detail.html` |
| Low | Add `license` to Dataset schema | `org_detail.html` |

### GEO (Generative Engine Optimization)

- **Citable summary paragraph** in hero: self-contained, specific numbers, updated daily
- **RAG-chunk friendly sections:** 40-60 word paragraphs that work as standalone facts
- **Update `llms.txt` and `llms-full.txt`** with new metrics (repos tracked, PR size distribution, tech trends)
- **JSON-LD structured data** for all new sections

### Marketing & CTAs

**CTA placement (3 locations):**

1. **Above the fold** (hero): "Get these metrics for your repos" - Start Free Trial. Supporting: "Connect GitHub in 2 minutes. No card required."
2. **After charts** (mid-page): Subtle premium tease. "Which developers are driving this adoption?" -> "See per-developer breakdowns with Tformance Pro."
3. **Bottom of page** (before related orgs): Full-width card. "You're looking at open source data. Imagine this for your team." + 4 bullet points + CTA button.

**Premium features to tease:**
- Per-developer AI adoption breakdown
- AI quality impact analysis
- Bottleneck detection
- Weekly AI-generated insights

**Copy principles:**
- Lead with AI adoption as hero metric (most shareable, searchable)
- Add industry comparison context to all stat cards (e.g., "1.5x industry average")
- CTAs should feel natural, not spammy
- Related orgs section: show 3-4 org cards instead of single industry link

### JSON-LD Schema Updates

Add to org detail `Dataset` schema:
- `contributor` array with `Person` type for top contributors
- Dynamic `temporalCoverage` based on actual data range
- `license` property (CC BY 4.0)
- Additional `variableMeasured` for new metrics (PR size distribution, tech categories)

Add to FAQ schema:
- "How many repositories does {org} have tracked?" -> "{N} repositories"
- "What AI coding tools does {org} use?" -> "Most common: {tool1}, {tool2}, {tool3}"
- "What is {org}'s PR size distribution?" -> "{X}% small, {Y}% medium, {Z}% large"

---

## 11. PostHog Analytics Events

### Page-Level Events (auto-fire on load)

| Event | Properties |
|-------|-----------|
| `public_page_viewed` | `page_type` (directory/org_detail/industry), `org_slug`, `industry` |

### Interaction Events

| Event | Properties | Trigger |
|-------|-----------|---------|
| `public_chart_viewed` | `chart_type`, `org_slug` | Chart scrolls into viewport |
| `public_repo_link_clicked` | `repo`, `org_slug` | Click on repo GitHub link |
| `public_member_profile_clicked` | `username`, `org_slug` | Click on contributor avatar/name |
| `public_pr_link_clicked` | `pr_id`, `org_slug` | Click on PR title link |
| `public_signup_cta_clicked` | `source_section` (hero/mid/bottom), `org_slug` | Click on CTA button |
| `public_table_sorted` | `column`, `direction`, `org_slug` | Click sort header in team breakdown |
| `public_industry_filter_changed` | `industry`, `sort` | Change directory filter |

### Conversion Funnel

```
public_page_viewed -> public_signup_cta_clicked -> signup_page_viewed -> signup_completed
```

---

## 12. Open Questions & Decisions

| # | Question | Recommendation | Status |
|---|----------|---------------|--------|
| 1 | Logo sourcing | Auto-fetch from GitHub API (`https://github.com/{org}.png`), allow manual override in admin | Decided |
| 2 | PR author bug root cause | `github_id=0` collision in seeder. Fix in `_create_team_members()` and `_find_member()` | Decided |
| 3 | Chart interactivity | No drill-down for MVP. Revisit in Phase 2 | Decided |
| 4 | Repo count limit | Show all repos (most orgs have <10). Add "top 50" message if >50 | Decided |
| 5 | LLM batch timing | Daily batch only (50% cost savings). No real-time processing | Decided |
| 6 | Insight generation frequency | Weekly (30-day window is stable, reduces costs) | Decided |
| 7 | Redis cache TTL | Increase to 6h (from 1h). Data only changes daily | Decided |
| 8 | Tech/type trend aggregation | ORM + Python grouping via `effective_*` properties (not raw SQL) | Decided |
| 9 | Pipeline scheduling | Single run at 4 AM UTC. Sequential org processing | Decided |
| 10 | LLM backlog (14.9K PRs) | Process 500/day via batch. Full backlog clear in ~30 days | Open |

---

## 13. Related Documents

| Document | Purpose |
|----------|---------|
| [`docs/plans/user-stories-public-page-improvements.md`](user-stories-public-page-improvements.md) | Detailed user stories with acceptance criteria |
| [`docs/plans/technical-architecture.md`](technical-architecture.md) | Sync pipeline, API quota, cache strategy, function signatures |
| [`docs/plans/test-plan.md`](test-plan.md) | Complete test code for all new aggregations and pipeline tasks |
| [`docs/plans/public-page-marketing-review.md`](public-page-marketing-review.md) | Marketing copy, CTA strategy, premium feature teases |
| [`docs/plans/public-page-seo-audit.md`](public-page-seo-audit.md) | Technical SEO findings and fixes |
| [`docs/plans/public-page-ux-design.md`](public-page-ux-design.md) | Component specs, responsive design, color/typography reference |
| [`docs/plans/2026-02-15-public-oss-analytics.md`](2026-02-15-public-oss-analytics.md) | Original implementation plan (6 epics) |

---

**This plan is ready for implementation.** Start with Sprint 1 (Stories #4, #1, #6, #5) to fix data quality and build the foundation.
