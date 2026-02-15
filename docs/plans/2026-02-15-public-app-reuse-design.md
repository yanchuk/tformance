# Public App Reuse for OSS Analytics Pages — Comprehensive Design Document

**Date:** 2026-02-15
**Status:** Design Review Complete
**Team:** Product Marketer (Lead), Product Manager, System Architect, Engineer, QA Lead, UI/UX Designer

---

## Executive Summary

This document proposes reusing the full `/app` experience (analytics tabs, PR lists, insights dashboard) for public OSS analytics pages at `/open-source/{slug}/`. Instead of building simplified read-only views, we'll adapt existing authenticated app views to work in public mode with the same team-scoped data model.

**Key Decision:** Show 80% of the product publicly in read-only mode to drive "try before you buy" conversions, differentiating from competitors (LinearB, Sleuth, Jellyfish, Faros AI) who gate everything behind login walls.

**URL Structure:**
```
/open-source/posthog/              → Overview (dashboard + insights)
/open-source/posthog/analytics/    → Analytics tab (AI adoption, delivery, quality, team, trends)
/open-source/posthog/pull-requests/→ PR list with filters/sorting
```

**Impact:**
- **Projected Conversion:** 8-12% visitor→signup (vs. 3% baseline, 2-5% industry average)
- **Competitive Moat:** "See the actual product before you sign up" — no competitor offers this
- **SEO Multiplier:** 60+ unique dashboard pages vs. 1 static directory page
- **Implementation:** ~49 hours (6 days focused dev) + 20% buffer = 7.5 days total

---

## 1. Product Marketing Analysis

### 1.1 Competitive Positioning: The "Transparent Analytics" Wedge

**The Market Gap:**

All major engineering analytics competitors hide their product behind login walls:

| Competitor | Product Visibility | Buyer's Journey Time |
|------------|-------------------|---------------------|
| **LinearB** | Screenshots + sales demos only | 7-14 days (book demo → see product) |
| **Sleuth** | Demo requires calendar booking | 3-7 days (schedule call → see product) |
| **Jellyfish** | Free trial requires work email + company info BEFORE dashboard access | 2-3 days (submit form → approval → see product) |
| **Faros AI** | No public product preview at all | 7-14 days (contact sales → qualification → custom demo) |

**Tformance's Position:**
> "See exactly what Tformance looks like for YOUR team by browsing PostHog, Vercel, or Supabase's live dashboards. No signup required."

**Core Positioning Statement:**
> "We're so confident in our product, we run it on 60+ public OSS repos and let you explore the full dashboard."

This attacks the core friction point in B2B SaaS: **buyers don't know what they're getting until after signup.**

### 1.2 Conversion Impact: "Try Before You Buy" Funnel Transformation

#### Current Funnel (Static Public Pages):
```
Visitor → reads summary cards → sees static charts → CTA → signup
├─ Conversion Rate: ~3% (baseline)
├─ Time on Page: ~1 minute
└─ Qualification: Low (minimal product exposure)
```

#### Proposed Funnel (Full App Reuse):
```
Visitor → browses analytics tab → explores PR list with filters → sees AI insights
        → "I want this for my team" → signup
├─ Conversion Rate: 8-12% (projected)
├─ Time on Page: 4-7 minutes
└─ Qualification: High (self-qualified through exploration)
```

**Conversion Drivers:**

1. **Feature Discovery Through Exploration**
   - Users naturally click through tabs, discovering capabilities organically
   - Interactive elements (filters, date ranges, drill-downs) create engagement
   - Longer session duration = more qualified leads (mental investment)

2. **Aspirational Product Experience**
   - Seeing "PostHog's AI adoption trend" triggers: "I want to track this for MY team"
   - Built-in social proof: "If Vercel uses Tformance, I should too"
   - Creates FOMO: competitors' dashboards are visible, yours aren't

3. **Self-Qualification Through Use**
   - Users who spend 5+ minutes exploring tabs are HIGH-intent (mentally mapping their team onto the product)
   - Users who bounce after 30 seconds weren't good fits anyway (saves sales time)
   - CTA timing improves: appears AFTER value demonstration

**Projected Metrics:**
- **Month 1:** 5-7% conversion (learning phase, A/B testing CTAs)
- **Month 3:** 8-12% conversion (optimized flow, refined messaging)
- **Benchmark Context:** 2-5x industry standard for SaaS free trial signups (which hide product initially)

### 1.3 Show vs. Hide Strategy: The 80/20 Balance

**Principle:** Show 80% of capabilities publicly, gate 20% behind "Connect your repos"

#### ✅ SHOW PUBLICLY (Full Access)

**Analytics Tab:**
- ✅ All charts (AI adoption, PR velocity, cycle time trends, quality indicators, team breakdown aggregates)
- ✅ Date range filters (limited to last 90 days for public view)
- ✅ Industry benchmark comparisons (inline overlays on charts)
- ✅ Chart tooltips and interactions (zoom, legend toggles)
- ⚠️ Export buttons (visible but disabled with tooltip: "Connect your repos to export")

**Pull Requests Tab:**
- ✅ Full PR list with filters (AI-assisted yes/no, date range, contributors, PR size)
- ✅ PR detail modals (size breakdown, cycle time, review rounds, AI tool detection reasoning)
- ✅ Sorting (by date, cycle time, size, reviews)
- ✅ Search by PR title
- ✅ Pagination (limit to 100 results per page, 5000 max for performance)

**Overview/Dashboard Tab:**
- ✅ Summary stats cards (total PRs, AI %, median cycle time, active contributors last 90d)
- ✅ Latest AI-generated insight (1 static insight, read-only)
- ✅ Industry comparison module ("vs. Industry Median")
- ⚠️ "Ask a question" input (disabled with CTA: "Sign up to ask custom questions")

#### 🚫 GATE BEHIND SIGNUP (Premium Indicators)

**Features to Withhold:**

1. **Custom Date Ranges Beyond 90 Days**
   - Public: Last 90 days visible
   - Reasoning: Show recent trends, gate historical analysis

2. **Team Member Breakdown (Per-Contributor Stats)**
   - Public: Aggregate metrics only
   - Reasoning: Privacy + signup incentive

3. **Export to CSV/PDF**
   - Public: Buttons visible but disabled with tooltip
   - Reasoning: "Take this data with you" requires signup

4. **AI Insights Q&A**
   - Public: Input box disabled with placeholder: "Ask about YOUR team's AI impact... (Sign up to unlock)"
   - Reasoning: Custom questions = personalized value = signup driver

5. **Notes & Feedback Features**
   - Public: Completely hidden (no UI)
   - Reasoning: Collaboration features only make sense for authenticated users

6. **Insight Dismissal**
   - Public: Insights are read-only
   - Reasoning: Personalization requires account

7. **Integration Previews (Slack/Jira)**
   - Public: Mentioned in sidebar with "Sign up to connect" CTA
   - Reasoning: Awareness of integrations without functional access

**Why This Balance Works:**
- Users see 100% of the UI but 80% is functional = feels generous, not crippled
- Gated features are clearly *additive* (enhancing core value, not blocking it)
- Creates natural upgrade path: free preview → free trial → paid plan
- Disabled features remain *visible* (tooltips explain why + how to unlock)

### 1.4 CTA Strategy: Context-Aware, Non-Pushy

**Design Philosophy:** CTAs should feel helpful, not desperate. Users should *want* to sign up because they see value, not because they're nagged.

#### **Directory Page (`/open-source/`)**

**Primary CTA:**
Top-right nav: "See your team's dashboard" button
Bottom banner: "Track engineering metrics for 60+ OSS teams. Connect your repos to see yours."

**Secondary CTA:**
"Browse by industry" (engagement before conversion)

**Copy Tone:** Informational, inviting

---

#### **Org Overview Page (`/open-source/posthog/`)**

**Primary CTA (Sticky Bottom Bar):**
```
┌──────────────────────────────────────────────────────────────┐
│ Get this dashboard for [Your Team Name]  [Input: your-org]  │
│                                           [Connect Repos →]  │
└──────────────────────────────────────────────────────────────┘
```
- Sticky to bottom of viewport (always visible while scrolling)
- Input field validates GitHub org name (optional pre-fill for signup)
- Button redirects to `/signup/?org=<input-value>`

**Secondary CTA (Dismissible Hero Banner):**
```
[ℹ️ Info] Browsing PostHog's public analytics. Want this for your private repos?
         [Connect Your Team] [Dismiss]
```
- Shows once per session (localStorage dismissal)
- Non-intrusive (can be dismissed)

---

#### **Analytics Tab (`/open-source/posthog/analytics/`)**

**Primary CTA:**
Bottom of page: "This is PostHog's dashboard. Yours will look like this. [Connect Your Repos →]"

**Contextual CTA:**
Tooltip on disabled "Export" button:
```
"📊 Sign up to export charts and share with your team"
```

---

#### **PR List Tab (`/open-source/posthog/pull-requests/`)**

**Top Banner (Subtle):**
```
"Exploring 4,521 PostHog PRs. Want to see yours? [Start Free Trial →]"
```

**Disabled Filter CTA:**
When user tries advanced filter (disabled for public):
```
Tooltip: "Advanced filters available on paid plans. [See Pricing →]"
```

---

#### **CTA Frequency Rules:**

- **1 primary CTA per page** (persistent, non-intrusive)
- **2-3 contextual CTAs** (triggered by interaction: clicking disabled features, hovering over locked elements)
- **No popups, no exit-intent modals** (breaks "generous free experience" vibe)
- **All CTAs tracked to PostHog:** `public_cta_clicked` event with `{source_page, cta_type, org_slug}`

### 1.5 Messaging Framework

**Launch Tagline Options (A/B Test):**

1. "This is your dashboard. Just with your data."
2. "Try the full product on PostHog's repos. Connect yours to start tracking."
3. "Engineering analytics, fully transparent. Explore 60+ live dashboards."
4. **Recommended:** "The only analytics platform confident enough to show you the product first."

**Launch Narrative (Blog Post/HN/Twitter):**

> "We're making engineering analytics radically transparent. Starting today, you can explore Tformance's full product on 60+ open-source teams—no signup, no demo call, no sales pitch. Just browse PostHog, Vercel, or Supabase's live dashboards. If you like what you see, connect your repos."

**Content Marketing Strategy:**

**Week 1 (Launch):**
- Blog: "Why We're Open-Sourcing Our Product (Not Our Code)"
- Twitter thread: "While competitors hide behind demos, we're running our product on OSS repos. Here's why."
- HN: "Show HN: Tformance — Engineering analytics for 60+ OSS teams (explore live dashboards, no signup)"

**Week 2-4 (Amplification):**
- Email to OSS maintainers: "Your repo is on Tformance. Here's what the data shows."
- Dev.to guest post: "How to benchmark your engineering team against OSS leaders"
- LinkedIn (CEO): "We're betting transparency beats demos. Here's the data after 30 days."

**Month 2-3 (Case Studies):**
- "How [Company X] Used Our Public Dashboards to Justify Buying Tformance"
- "PostHog's AI Adoption Jumped 14% in Q1 2026 (Here's How We Know)"
- "Engineering Benchmarks Report: OSS Teams Outpace Enterprises in AI Adoption"

### 1.6 Competitive Moat Analysis

| Aspect | LinearB / Sleuth / Jellyfish | Tformance (Public App Reuse) |
|--------|------------------------------|-------------------------------|
| **Product Transparency** | Screenshots + sales demos | Live dashboards with real data |
| **Time to Value** | 3-7 days (sales cycle) | Instant (browse now) |
| **Buyer Confidence** | "Is this worth $X/month?" (unknown) | "I've already used it, I know it works" |
| **Viral Coefficient** | 0 (no public links to share) | High (60+ shareable org dashboards) |
| **SEO Value** | Landing pages only (5-10 pages) | 60+ unique dashboards = 60+ entry points |
| **Sales Objection Handling** | "Can I see the product?" → schedule demo (friction) | "Can I see the product?" → here it is (instant) |
| **Brand Positioning** | "Trust us, we're good" | "See for yourself, we're confident" |

**Data Moat:**
- **167K+ PRs analyzed** across 60+ orgs (takes competitors months to replicate)
- **Daily-updated data** (freshness advantage)
- **"Transparent analytics" = Tformance** (brand positioning hard to copy without appearing derivative)
- **OSS community endorsement:** Maintainers become advocates ("My metrics are on Tformance")

**First-Mover Advantage:**
Being first to show the full product publicly creates a narrative: "Tformance pioneered transparent engineering analytics." Competitors copying later will look reactive, not innovative.

### 1.7 Success Metrics

#### Primary KPIs:

- **Visitor → Signup Conversion Rate:** 8-12% target (from public page CTAs)
- **Time on Public Pages:** 4-7 minutes average session duration
- **Organic Traffic:** 5K-10K monthly visitors by Month 3 (SEO + word-of-mouth)

#### Secondary KPIs:

- **CTA Click Rate:** 15-20% of visitors click at least one CTA
- **Tab Exploration Rate:** 60%+ of visitors browse 2+ tabs (indicates engagement)
- **Referral Attribution:** 20%+ of signups sourced from public OSS page CTAs (vs. landing page)
- **Bounce Rate:** <40% (lower = more engaging content)

#### Engagement Tracking (PostHog Events):

- `public_org_viewed`: `{org_slug, industry, referrer}`
- `public_tab_viewed`: `{org_slug, tab_name, time_on_tab}`
- `public_cta_clicked`: `{org_slug, cta_type, source_page}`
- `public_filter_used`: `{org_slug, filter_type, filter_value}`
- `public_chart_interaction`: `{org_slug, chart_type, interaction_type}` (hover, zoom, export attempt)

#### Vanity Metrics (Marketing Value):

- **AI Search Citations:** 50+ by Month 3 ("According to Tformance, PostHog's AI adoption is 21%...")
- **Social Shares:** CTOs/OSS maintainers sharing their org's dashboard on Twitter/LinkedIn
- **Backlinks:** Tech blogs citing Tformance data in articles

---

## 2. Product Management: Scope & User Stories

### 2.1 User Personas

#### **Primary: Evaluating CTO/Engineering Leader**

**Demographics:** CTO, VP Engineering, or Engineering Manager at 20-200 person company
**Goal:** Assess if Tformance fits their team's needs before committing budget ($199-$999/month)
**Behavior:**
- Compares 3-5 tools in parallel (LinearB, Sleuth, Jellyfish, Tformance)
- Reads reviews, explores product demos
- Has limited time (wants self-serve evaluation, not sales calls)

**Pain Points:**
- Tired of booking demos to see basic features
- Skeptical of marketing screenshots ("Does it actually work like this?")
- Needs to justify ROI to CFO (needs data, not promises)

**Success Metric:** Can self-qualify within 5 minutes of browsing public pages (knows if Tformance is a fit)

---

#### **Secondary: Curious Developer**

**Demographics:** Individual contributor, OSS contributor, engineering manager
**Goal:** See how their OSS org's metrics compare to others
**Behavior:**
- Browses their own org's page out of curiosity
- Shares interesting insights on social media
- May not have budget authority but can influence team decisions

**Pain Points:**
- Wants transparency into team performance (not just manager's high-level summaries)
- Interested in industry trends (AI adoption, cycle time benchmarks)

**Success Metric:** Discovers interesting insights, shares org page with teammates, advocates for Tformance

---

#### **Tertiary Personas:**

- **Tech Journalist:** Researching AI adoption trends in OSS for an article
- **AI Researcher:** Looking for citation-worthy engineering productivity data
- **OSS Maintainer:** Checking if their repo is tracked, requesting addition
- **Student/Academic:** Studying software engineering metrics for research

### 2.2 User Stories by Page/Tab

#### **US-1: Overview/Dashboard Tab** (`/open-source/posthog/`)

**As a** evaluating CTO
**I want** to see a summary dashboard with key metrics and an AI-generated insight
**So that** I can quickly assess what Tformance offers without reading docs

**Acceptance Criteria:**

- [ ] **Hero section:** Org logo, display name, industry badge, GitHub link, "Last updated: {date}"
- [ ] **Summary stats cards (4 cards):**
  - Total PRs (2025+)
  - AI-Assisted PR % (with trend arrow vs. previous month)
  - Median Cycle Time (hours)
  - Active Contributors (last 90 days)
- [ ] **Latest AI insight:** 1 static insight (2-3 sentences), read-only, e.g.:
  > "PostHog's AI adoption increased 14% in Q1 2026, with GitHub Copilot accounting for 68% of AI-assisted PRs. Median cycle time dropped from 22h to 18h over the same period."
- [ ] **Industry comparison module:** "vs. Product Analytics & Observability median" (side-by-side stats)
- [ ] **Tab navigation:** Horizontal pill tabs (Overview [active], Analytics, Pull Requests)
- [ ] **Disabled features hidden:** No Notes UI, no Feedback buttons, no "Ask a question" Q&A input (or show disabled)
- [ ] **CTA:** Sticky bottom bar "Get this dashboard for [your-team]" + input field + button
- [ ] **Mobile responsive:** Stats stack vertically, tabs scroll horizontally

---

#### **US-2: Analytics Tab** (`/open-source/posthog/analytics/`)

**As a** evaluating CTO
**I want** to explore detailed analytics charts (AI adoption, delivery, quality, team)
**So that** I can see the depth of insights Tformance provides before signing up

**Acceptance Criteria:**

- [ ] **Sub-sections or sub-tabs:**
  - AI Adoption (line chart: monthly AI % over time)
  - Delivery Metrics (bar chart: PRs merged per week, split by AI vs. traditional)
  - Quality Indicators (multi-metric card: revert rate, hotfix rate, CI pass rate, avg review rounds)
  - Team Breakdown (aggregate table: total contributors, avg PRs/contributor, NOT per-person breakdown)
  - Trends (cycle time trend line chart, PR size distribution bar chart)

- [ ] **Charts (Chart.js, Easy Eyes theme):**
  - ✅ AI Adoption Over Time (line chart, monthly %, industry median overlay)
  - ✅ PR Velocity (bar chart, merged PRs per week)
  - ✅ Cycle Time Trend (line chart, monthly median)
  - ✅ Quality Indicators (stat cards with trend arrows)
  - ✅ Top AI Tools Detected (bar chart or table: tool name, count, %)

- [ ] **Date range filter:** Dropdown (last 30/60/90 days), default 90 days, max for public view (no custom range picker)
- [ ] **Export button:** Visible but disabled with tooltip "Sign up to export charts and data"
- [ ] **All charts interactive:** Tooltips on hover, legends clickable, zoom where applicable
- [ ] **Charts loaded lazily:** `hx-get` with `hx-trigger="load"` for fast initial HTML load
- [ ] **Industry benchmark overlays:** Dotted line on charts showing "Industry median: 18h"
- [ ] **Mobile responsive:** Charts resize, stack vertically on mobile

---

#### **US-3: Pull Requests Tab** (`/open-source/posthog/pull-requests/`)

**As a** curious developer
**I want** to see a filterable list of PRs with AI tool detection
**So that** I can understand how the PR analysis works and what insights are available

**Acceptance Criteria:**

- [ ] **Table columns:** PR title (linked to GitHub), author, state (merged), size (XS/S/M/L/XL), cycle time (hours), AI tool (badge or icon), created date
- [ ] **Filters (HTMX partial reloads):**
  - AI-assisted: All / AI-assisted / Traditional
  - Date range: last 7/30/90 days
  - Contributors: dropdown (top 20 contributors by PR count)
  - PR size: All / XS / S / M / L / XL
- [ ] **Sorting:** By date (default: newest first), by cycle time (ascending/descending), by size
- [ ] **Search:** By PR title (client-side Alpine.js filter OR server-side query param)
- [ ] **Pagination:** 50 PRs per page, limit to 100 pages (5000 results max) for public view
- [ ] **PR detail modal:** Click row → modal shows:
  - PR metadata (author, reviewers, merge date)
  - Size breakdown (files changed, lines added/deleted)
  - Review rounds (count, avg time per round)
  - Cycle time breakdown (time to first review, time to merge)
  - AI tool reasoning (if detected): "Detected GitHub Copilot based on commit patterns and PR metadata"
- [ ] **Export button:** Visible but disabled with tooltip "Sign up to export PR data to CSV"
- [ ] **Banner (top of page):** "Exploring 4,521 PostHog PRs. Want to see yours? [Start Free Trial →]"
- [ ] **Mobile responsive:** Table scrolls horizontally, filters collapse to dropdowns

---

#### **US-4: Tab Navigation (Shared Component)**

**As a** visitor
**I want** to navigate between Overview, Analytics, and PR List tabs
**So that** I can explore different aspects of the org's metrics

**Acceptance Criteria:**

- [ ] **Horizontal tab bar:** DaisyUI `tabs-boxed` component (pill-style tabs)
- [ ] **Active tab highlighted:** Border + background color (DaisyUI `tab-active`)
- [ ] **Tab URLs:**
  - `/open-source/posthog/` (overview, default)
  - `/open-source/posthog/analytics/` (analytics)
  - `/open-source/posthog/pull-requests/` (PR list)
- [ ] **Tabs persist org context:** Slug in URL path, not query param
- [ ] **Mobile:** Tabs scroll horizontally (`overflow-x-auto`) OR collapse to dropdown menu
- [ ] **Breadcrumbs above tabs:** Open Source → {Industry} → {Org Name}

---

### 2.3 Interactive Features: Enable/Disable Matrix

| Feature | Public Mode | Authenticated Mode | Implementation |
|---------|-------------|-------------------|----------------|
| **View charts** | ✅ Enabled | ✅ Enabled | Same view logic, no changes |
| **Filter date range** | ✅ Limited (90d max) | ✅ Full range | Conditional logic in view |
| **Filter PR list** | ✅ Enabled | ✅ Enabled | Same view logic |
| **Sort PR list** | ✅ Enabled | ✅ Enabled | Same view logic |
| **Search PRs** | ✅ Enabled | ✅ Enabled | Same view logic |
| **Export CSV/PDF** | ⚠️ Disabled (visible w/ tooltip) | ✅ Enabled | Template conditional + CTA |
| **View AI insights** | ✅ Latest only (1 insight) | ✅ All insights (paginated) | Query limit in service layer |
| **Ask LLM questions** | ❌ Disabled (input locked w/ CTA) | ✅ Enabled | Template conditional |
| **Dismiss insights** | ❌ Hidden | ✅ Enabled | Template conditional (remove button) |
| **Create notes** | ❌ Hidden | ✅ Enabled | Feature completely hidden in public template |
| **Create feedback** | ❌ Hidden | ✅ Enabled | Feature completely hidden in public template |
| **Team breakdown (per-contributor)** | ❌ Aggregate only | ✅ Full per-contributor table | Query excludes contributor detail |

### 2.4 MVP Scope vs. Future Iterations

#### **MVP (Phase 1 — Launch):**

- ✅ Overview tab (dashboard with summary stats + 1 latest insight)
- ✅ Analytics tab (all charts, limited to 90-day date range)
- ✅ PR list tab (filters, sorting, pagination, PR detail modal)
- ✅ Tab navigation (3 tabs: Overview, Analytics, PRs)
- ✅ Read-only mode (all write features disabled/hidden)
- ✅ Basic CTAs (sticky bottom bar, disabled feature tooltips)
- ✅ Mobile responsive layout
- ✅ SEO optimization (meta tags, sitemap, robots.txt, JSON-LD)

#### **Phase 2 (Post-Launch Enhancements):**

- 🔲 **Insights tab:** Separate tab with full insight history (not just latest), paginated
- 🔲 **Team breakdown tab:** Per-contributor stats, gated behind "Sign up to unlock" blur overlay
- 🔲 **Comparison mode:** Side-by-side org comparison (e.g., PostHog vs. Supabase)
- 🔲 **Embeddable widgets:** Badges for OSS repos ("Tracked on Tformance" with live metrics)
- 🔲 **Advanced filters:** PR type (feature/bugfix/refactor), file path regex, label filters
- 🔲 **Historical snapshots:** View org metrics as of a specific date (time machine feature)
- 🔲 **Public API:** Rate-limited endpoints for programmatic access to OSS data

#### **Out of Scope (V3+):**

- User accounts for OSS maintainers to customize their public page
- Bounty tracking integration (GitHub Sponsors, OpenCollective)
- Dynamic OG image generation per org (custom social cards with live stats)
- Real-time data updates (daily batch sync is sufficient for MVP)

---

## 3. System Architecture: View Reuse Strategy

### 3.1 Architectural Constraints

**Current `/app` Views:**
- Use `@login_and_team_required` decorator which sets `request.team` from authenticated user session
- Templates extend `web/base.html` with sidebar navigation (multi-level nav menu)
- All queries use `BaseTeamModel.for_team()` manager (team-scoped by default)
- HTMX partials assume authenticated context (e.g., `request.user` in templates)

**Public Pages Requirements:**
- NO authentication required (anonymous access)
- MUST still have team context (from `PublicOrgProfile.public_slug → team_id`)
- Templates extend `public/base.html` with simple header/footer (no sidebar, just horizontal tabs)
- Read-only mode (disable write operations, hide collaboration features)

**Key Challenge:**
> How to reuse view functions that expect `request.team` (set by auth decorator) in a public context where there's no login?

### 3.2 View Reuse Strategy: Dual-Mode Decorator

**Decision: Create a new decorator that works in both public and authenticated contexts**

#### **Architecture: `@public_or_authenticated_team_required`**

```python
# apps/public/decorators.py

from functools import wraps
from django.conf import settings
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect
from django.core.exceptions import PermissionDenied

from apps.public.models import PublicOrgProfile
from apps.teams.models import Team


def public_or_authenticated_team_required(view_func):
    """
    Decorator that works in both public and authenticated contexts.

    Public mode:
        - URL pattern includes 'public_slug' (e.g., /open-source/posthog/)
        - Sets request.team from PublicOrgProfile lookup via slug
        - Sets request.is_public_view = True

    Authenticated mode:
        - URL pattern includes 'team_slug' (e.g., /a/my-team/)
        - Requires user login and team membership
        - Sets request.team from Team lookup via slug
        - Sets request.is_public_view = False

    View functions can use request.team identically in both modes.
    Templates use {% if is_public_view %} for conditional rendering.

    Usage:
        @public_or_authenticated_team_required
        def analytics_overview(request):
            team = request.team  # Works in both modes
            # ... view logic ...
    """
    @wraps(view_func)
    def wrapper(request, *args, **kwargs):
        # Determine mode based on URL pattern parameter
        public_slug = kwargs.get('public_slug')
        team_slug = kwargs.get('team_slug')

        if public_slug:
            # PUBLIC MODE: lookup team via PublicOrgProfile
            try:
                profile = PublicOrgProfile.objects.select_related('team').get(
                    public_slug=public_slug,
                    is_public=True  # CRITICAL: only show public orgs
                )
                request.team = profile.team
                request.is_public_view = True
                request.public_profile = profile  # For additional metadata (logo, industry, etc.)

            except PublicOrgProfile.DoesNotExist:
                raise Http404("Organization not found or not public")

        elif team_slug:
            # AUTHENTICATED MODE: require login and team membership
            if not request.user.is_authenticated:
                return redirect(f"{settings.LOGIN_URL}?next={request.path}")

            team = get_object_or_404(Team, slug=team_slug)

            # Check user has access to this team
            if not request.user.teams.filter(id=team.id).exists():
                raise PermissionDenied("You don't have access to this team")

            request.team = team
            request.is_public_view = False

        else:
            # Neither public_slug nor team_slug in URL — invalid usage
            raise ValueError(
                "View must be called with either 'public_slug' (public mode) "
                "or 'team_slug' (authenticated mode) in URL pattern"
            )

        # Call the actual view function (same in both modes)
        return view_func(request, *args, **kwargs)

    return wrapper
```

#### **URL Routing: Dual-Mode Routes**

```python
# apps/public/urls.py (PUBLIC ROUTES)

from django.urls import path
from apps.metrics.views.analytics_views import analytics_overview, analytics_detail
from apps.metrics.views.pr_list_views import pr_list, pr_detail_modal
from apps.metrics.views.chart_views import (
    ai_adoption_chart, pr_velocity_chart, cycle_time_chart
)

app_name = 'public'

urlpatterns = [
    # Public org pages (dual-mode views, public_slug parameter)
    path(
        '<slug:public_slug>/',
        analytics_overview,  # SAME view as authenticated /app
        name='org_overview'
    ),
    path(
        '<slug:public_slug>/analytics/',
        analytics_detail,  # SAME view as authenticated /app
        name='org_analytics'
    ),
    path(
        '<slug:public_slug>/pull-requests/',
        pr_list,  # SAME view as authenticated /app
        name='org_pull_requests'
    ),

    # HTMX chart partials (also dual-mode)
    path(
        '<slug:public_slug>/charts/ai-adoption/',
        ai_adoption_chart,
        name='chart_ai_adoption'
    ),
    path(
        '<slug:public_slug>/charts/pr-velocity/',
        pr_velocity_chart,
        name='chart_pr_velocity'
    ),
    path(
        '<slug:public_slug>/charts/cycle-time/',
        cycle_time_chart,
        name='chart_cycle_time'
    ),

    # PR detail modal (HTMX partial)
    path(
        '<slug:public_slug>/pr/<int:pr_id>/detail/',
        pr_detail_modal,
        name='pr_detail'
    ),
]
```

```python
# apps/teams/urls.py (AUTHENTICATED ROUTES — UNCHANGED)

from apps.metrics.views.analytics_views import analytics_overview, analytics_detail
from apps.metrics.views.pr_list_views import pr_list, pr_detail_modal

# Team-scoped URL patterns (mounted under /a/<team_slug>/)
team_urlpatterns = (
    [
        path('', analytics_overview, name='overview'),  # SAME view function!
        path('analytics/', analytics_detail, name='analytics'),
        path('pull-requests/', pr_list, name='pull_requests'),
        # ... more authenticated routes ...
    ],
    'team',  # namespace
)
```

**Key Insight:** The SAME view function handles both public and authenticated requests. The decorator sets `request.team` appropriately, and the view logic is identical.

---

#### **View Function Example: NO CHANGES NEEDED**

```python
# apps/metrics/views/analytics_views.py (EXISTING CODE, MINIMAL CHANGES)

from apps.public.decorators import public_or_authenticated_team_required  # NEW import
from apps.public.aggregations import compute_team_summary, compute_monthly_trends  # Shared logic

@public_or_authenticated_team_required  # CHANGED from @login_and_team_required
def analytics_overview(request):
    """
    Analytics overview page.
    Works in both public (via public_slug) and authenticated (via team_slug) contexts.
    """
    team = request.team  # Set by decorator in BOTH modes

    # Query logic remains IDENTICAL
    summary = compute_team_summary(team.id)
    monthly_trends = compute_monthly_trends(team.id)

    # Conditional logic for public vs. authenticated (NEW)
    if request.is_public_view:
        # Public mode: limit date range to 90 days
        from django.utils import timezone
        from datetime import timedelta
        date_limit = timezone.now() - timedelta(days=90)
        monthly_trends = [t for t in monthly_trends if t['month'] >= date_limit.date()]
    else:
        # Authenticated mode: full history
        pass

    context = {
        'team': team,
        'summary': summary,
        'monthly_trends': monthly_trends,
        'is_public_view': request.is_public_view,  # For template conditionals
    }

    # Template handles conditional extends (see next section)
    return render(request, 'metrics/analytics/overview.html', context)
```

---

### 3.3 Template Strategy: Conditional Base Template

**Challenge:** Public pages need to extend `public/app_base.html` (tab layout), while authenticated pages extend `web/app_base.html` (sidebar layout). How to use the same template for both?

**Solution: Conditional `{% extends %}`**

```django
{# templates/metrics/analytics/overview.html (MODIFIED) #}

{# Conditional base template based on mode #}
{% if is_public_view %}
    {% extends "public/app_base.html" %}  {# NEW: public tab layout #}
{% else %}
    {% extends "web/app_base.html" %}  {# EXISTING: authenticated sidebar #}
{% endif %}

{% block page_title %}
    {% if is_public_view %}
        {{ team.display_name }} Engineering Metrics — Tformance
    {% else %}
        Analytics Overview — {{ team.name }}
    {% endif %}
{% endblock %}

{% block content %}
    {# Summary stats cards (SAME in both modes) #}
    <div class="stats stats-vertical lg:stats-horizontal shadow">
        <div class="stat">
            <div class="stat-title">Total PRs</div>
            <div class="stat-value">{{ summary.total_prs|intcomma }}</div>
        </div>
        <div class="stat">
            <div class="stat-title">AI-Assisted</div>
            <div class="stat-value">{{ summary.ai_assisted_pct }}%</div>
        </div>
        {# ... more stats ... #}
    </div>

    {# Charts (SAME in both modes) #}
    <div class="grid grid-cols-1 lg:grid-cols-2 gap-6 mt-6">
        <div class="card bg-base-100 shadow">
            <div class="card-body">
                <h3 class="card-title">AI Adoption Over Time</h3>
                <canvas id="ai-adoption-chart"
                        hx-get="{% url 'public:chart_ai_adoption' public_slug=public_profile.public_slug %}"
                        hx-trigger="load"></canvas>
            </div>
        </div>
        {# ... more charts ... #}
    </div>

    {# Export button (CONDITIONAL) #}
    {% if is_public_view %}
        {# Public: disabled with tooltip #}
        <div class="tooltip tooltip-bottom"
             data-tip="Sign up to export charts and share with your team">
            <button class="btn btn-primary btn-disabled gap-2" disabled>
                <svg class="w-5 h-5"><!-- Export icon --></svg>
                Export Charts
                <svg class="w-4 h-4 opacity-50"><!-- Lock icon --></svg>
            </button>
        </div>
    {% else %}
        {# Authenticated: enabled #}
        <a href="{% url 'metrics:export_analytics' team_slug=team.slug %}"
           class="btn btn-primary gap-2">
            <svg class="w-5 h-5"><!-- Export icon --></svg>
            Export Charts
        </a>
    {% endif %}
{% endblock %}
```

---

#### **New Base Template: `templates/public/app_base.html`**

```django
{# templates/public/app_base.html (NEW FILE) #}

{% extends "public/base.html" %}

{% block content %}
    {# Hero section: org identity (sticky on scroll) #}
    <div class="hero bg-base-200 py-8 sticky top-0 z-10 shadow-md">
        <div class="hero-content flex-col lg:flex-row gap-4">
            <img src="{{ public_profile.logo_url }}" alt="{{ team.display_name }}"
                 class="w-20 h-20 rounded-full shadow-lg">
            <div class="text-center lg:text-left">
                <h1 class="text-4xl font-bold">{{ team.display_name }}</h1>
                <div class="flex gap-2 justify-center lg:justify-start mt-2">
                    <span class="badge badge-primary">{{ public_profile.industry_display }}</span>
                    <a href="{{ public_profile.github_org_url }}" target="_blank"
                       class="badge badge-outline gap-1">
                        <svg class="w-4 h-4"><!-- GitHub icon --></svg>
                        GitHub
                    </a>
                </div>
                <p class="text-sm text-base-content/70 mt-1">
                    Last updated: {{ public_profile.last_synced_at|date:"F j, Y" }}
                </p>
            </div>
        </div>
    </div>

    {# Breadcrumbs (above tabs) #}
    <div class="max-w-7xl mx-auto px-4 mt-4">
        <div class="text-sm breadcrumbs">
            <ul>
                <li><a href="{% url 'public:directory' %}">Open Source</a></li>
                <li><a href="{% url 'public:industry_detail' industry=public_profile.industry %}">
                    {{ public_profile.industry_display }}
                </a></li>
                <li>{{ team.display_name }}</li>
            </ul>
        </div>
    </div>

    {# Tab navigation (horizontal pills) #}
    <div class="tabs tabs-boxed max-w-7xl mx-auto mt-4 bg-base-200">
        <a class="tab tab-lg {% if active_tab == 'overview' %}tab-active{% endif %}"
           href="{% url 'public:org_overview' public_slug=public_profile.public_slug %}">
            <svg class="w-5 h-5 mr-2"><!-- Dashboard icon --></svg>
            Overview
        </a>
        <a class="tab tab-lg {% if active_tab == 'analytics' %}tab-active{% endif %}"
           href="{% url 'public:org_analytics' public_slug=public_profile.public_slug %}">
            <svg class="w-5 h-5 mr-2"><!-- Chart icon --></svg>
            Analytics
        </a>
        <a class="tab tab-lg {% if active_tab == 'pull_requests' %}tab-active{% endif %}"
           href="{% url 'public:org_pull_requests' public_slug=public_profile.public_slug %}">
            <svg class="w-5 h-5 mr-2"><!-- PR icon --></svg>
            Pull Requests
        </a>
    </div>

    {# Tab content area (from child template) #}
    <div class="max-w-7xl mx-auto px-4 py-6">
        {% block page_content %}
            {# Child templates fill this #}
        {% endblock %}
    </div>

    {# Sticky CTA bar (always visible at bottom) #}
    <div class="fixed bottom-0 left-0 right-0 bg-primary text-primary-content p-4 shadow-lg z-50">
        <div class="max-w-7xl mx-auto flex flex-col lg:flex-row items-center justify-between gap-4">
            <span class="text-lg font-semibold">Get this dashboard for your team</span>
            <div class="flex gap-2 w-full lg:w-auto">
                <input type="text"
                       placeholder="your-github-org"
                       class="input input-bordered w-full lg:w-48"
                       id="signup-org-input">
                <button class="btn btn-secondary" onclick="validateAndSignup()">
                    Connect Repos →
                </button>
            </div>
        </div>
    </div>

    {# JavaScript for CTA validation (Alpine.js alternative) #}
    <script>
    function validateAndSignup() {
        const org = document.getElementById('signup-org-input').value.trim();
        if (org) {
            window.location.href = `/signup/?org=${encodeURIComponent(org)}`;
        } else {
            window.location.href = '/signup/';
        }
    }
    </script>
{% endblock %}
```

---

### 3.4 Read-Only Enforcement: Feature Gating Patterns

**Strategy: Hide write features entirely, disable interactive actions with CTAs**

#### **Pattern 1: Hide Features Completely (Notes, Feedback)**

```django
{# Only show Notes in authenticated mode #}
{% if not is_public_view %}
    <div class="card bg-base-100 shadow mt-6">
        <div class="card-body">
            <h3 class="card-title">PR Notes</h3>
            <button hx-post="{% url 'notes:create_pr_note' pr_id=pr.id %}"
                    class="btn btn-sm btn-primary">
                Add Note
            </button>
            {# ... notes list ... #}
        </div>
    </div>
{% endif %}
```

**Result:** Public users don't see Notes UI at all (clean, not cluttered with locked features).

---

#### **Pattern 2: Show Disabled with Tooltip (Export, Advanced Filters)**

```django
{% if is_public_view %}
    {# Public: disabled with tooltip CTA #}
    <div class="tooltip tooltip-bottom" data-tip="Sign up to export PR data to CSV">
        <button class="btn btn-primary btn-disabled gap-2" disabled>
            <svg class="w-5 h-5"><!-- Export icon --></svg>
            Export to CSV
            <svg class="w-4 h-4 opacity-50"><!-- Lock icon --></svg>
        </button>
    </div>
{% else %}
    {# Authenticated: enabled #}
    <a href="{% url 'metrics:export_prs_csv' team_slug=team.slug %}"
       class="btn btn-primary gap-2">
        <svg class="w-5 h-5"><!-- Export icon --></svg>
        Export to CSV
    </a>
{% endif %}
```

**Result:** Public users see the feature exists (awareness), understand it's gated (CTA), can't click (disabled).

---

#### **Pattern 3: Locked Input with CTA (LLM Q&A)**

```django
<div class="card bg-base-100 shadow mt-6">
    <div class="card-body">
        <h3 class="card-title">Ask About Your Team's Metrics</h3>

        {% if is_public_view %}
            {# Public: locked input with CTA #}
            <div class="form-control opacity-50 cursor-not-allowed">
                <input type="text"
                       placeholder="Ask about YOUR team's AI impact... (Sign up to unlock)"
                       class="input input-bordered"
                       disabled>
            </div>
            <div class="card-actions justify-end mt-2">
                <a href="/signup/" class="btn btn-primary btn-sm">
                    Unlock Q&A →
                </a>
            </div>
        {% else %}
            {# Authenticated: functional input #}
            <form hx-post="{% url 'insights:ask' team_slug=team.slug %}"
                  hx-target="#answer-container">
                <input type="text" name="question" class="input input-bordered w-full"
                       placeholder="Ask a question about your team...">
                <button type="submit" class="btn btn-primary mt-2">Ask</button>
            </form>
            <div id="answer-container"></div>
        {% endif %}
    </div>
</div>
```

---

#### **Pattern 4: Blurred Teaser with Overlay (Team Breakdown)**

```django
<div class="card bg-base-100 shadow">
    <div class="card-body">
        <h3 class="card-title">Team Breakdown</h3>

        {# Aggregate summary (visible in both modes) #}
        <div class="stats stats-vertical lg:stats-horizontal mb-4">
            <div class="stat">
                <div class="stat-title">Total Contributors</div>
                <div class="stat-value">{{ summary.active_contributors }}</div>
            </div>
            <div class="stat">
                <div class="stat-title">Avg PRs per Contributor</div>
                <div class="stat-value">{{ summary.avg_prs_per_contributor|floatformat:1 }}</div>
            </div>
        </div>

        {% if is_public_view %}
            {# Public: blurred table with unlock overlay #}
            <div class="relative">
                <table class="table blur-sm pointer-events-none">
                    <thead>
                        <tr>
                            <th>Contributor</th>
                            <th>PRs Merged</th>
                            <th>Cycle Time</th>
                            <th>AI %</th>
                        </tr>
                    </thead>
                    <tbody>
                        {# Show fake/placeholder rows #}
                        <tr><td>User 1</td><td>45</td><td>12h</td><td>32%</td></tr>
                        <tr><td>User 2</td><td>38</td><td>18h</td><td>21%</td></tr>
                        <tr><td>User 3</td><td>29</td><td>14h</td><td>45%</td></tr>
                    </tbody>
                </table>

                {# Overlay with unlock CTA #}
                <div class="absolute inset-0 flex items-center justify-center bg-base-100/80">
                    <div class="card bg-base-100 shadow-lg max-w-md">
                        <div class="card-body text-center">
                            <h4 class="card-title">See Per-Contributor Breakdown</h4>
                            <p>Connect your repos to unlock detailed team analytics.</p>
                            <a href="/signup/" class="btn btn-primary mt-2">
                                Connect Your Team →
                            </a>
                        </div>
                    </div>
                </div>
            </div>
        {% else %}
            {# Authenticated: full table #}
            <table class="table">
                <thead>
                    <tr>
                        <th>Contributor</th>
                        <th>PRs Merged</th>
                        <th>Median Cycle Time</th>
                        <th>AI %</th>
                        <th>Reviews Given</th>
                    </tr>
                </thead>
                <tbody>
                    {% for contributor in team_breakdown %}
                    <tr>
                        <td>{{ contributor.name }}</td>
                        <td>{{ contributor.pr_count }}</td>
                        <td>{{ contributor.median_cycle_time_hours }}h</td>
                        <td>{{ contributor.ai_pct }}%</td>
                        <td>{{ contributor.reviews_given }}</td>
                    </tr>
                    {% endfor %}
                </tbody>
            </table>
        {% endif %}
    </div>
</div>
```

---

### 3.5 Performance: Caching Strategy

**Goal:** Public pages load in <2s, handle 10K concurrent visitors without DB strain.

#### **Layer 1: Cloudflare Edge Cache (HTML)**

```python
# View response headers

def analytics_overview(request):
    # ... view logic ...
    response = render(request, template, context)

    if request.is_public_view:
        # Public: aggressive HTML caching at edge
        response['Cache-Control'] = 'public, max-age=43200'  # 12 hours
        response['Vary'] = 'Accept-Encoding'  # Gzip variance only
    else:
        # Authenticated: no caching (user-specific data)
        response['Cache-Control'] = 'private, no-cache, no-store'

    return response
```

**Cloudflare Cache Rule (via dashboard):**
- **Match:** `hostname = tformance.com AND URI path starts with /open-source/`
- **Action:** Eligible for cache
- **Edge TTL:** 12 hours
- **Browser TTL:** 1 hour
- **Purge:** Triggered by `compute_public_stats_task` after daily sync

---

#### **Layer 2: Django Redis Cache (Query Results)**

```python
# apps/public/services.py

from django.core.cache import cache

def get_org_summary(public_slug):
    """
    Get pre-computed summary stats for a public org.
    Cached for 1 hour in Redis.
    """
    cache_key = f'public:{public_slug}:summary'
    cached = cache.get(cache_key)

    if cached:
        return cached

    # Fetch from DB
    profile = PublicOrgProfile.objects.get(public_slug=public_slug, is_public=True)
    summary = compute_team_summary(profile.team_id)  # From aggregations.py

    # Cache for 1 hour
    cache.set(cache_key, summary, timeout=3600)
    return summary
```

**Cache Invalidation:**
```python
# apps/integrations/tasks.py

from django.core.cache import cache

@shared_task
def compute_public_stats_task():
    """
    Compute and cache stats for all public orgs.
    Runs after daily sync completes.
    """
    for profile in PublicOrgProfile.objects.filter(is_public=True):
        # Compute fresh stats
        stats = compute_all_metrics(profile.team_id)

        # Update PublicOrgStats model
        PublicOrgStats.objects.update_or_create(
            org_profile=profile,
            defaults=stats
        )

        # Clear Django Redis cache for this org
        cache_pattern = f'public:{profile.public_slug}:*'
        cache.delete_pattern(cache_pattern)

    # Purge Cloudflare cache (HTML pages)
    purge_cloudflare_cache()
```

---

#### **Layer 3: Pre-Computed Stats (DB)**

```python
# apps/public/models.py

class PublicOrgStats(BaseModel):
    """
    Pre-computed stats for fast directory queries.
    Refreshed daily by compute_public_stats_task.
    """
    org_profile = models.OneToOneField(PublicOrgProfile, on_delete=models.CASCADE)

    # Pre-aggregated metrics
    total_prs = models.IntegerField()
    ai_assisted_pct = models.DecimalField(max_digits=5, decimal_places=2)
    median_cycle_time_hours = models.DecimalField(max_digits=10, decimal_places=2)
    median_review_time_hours = models.DecimalField(max_digits=10, decimal_places=2, null=True)
    active_contributors_90d = models.IntegerField()
    top_ai_tools = models.JSONField(default=list)  # [{tool, count, pct}, ...]

    last_computed_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name_plural = "Public Org Stats"
```

**Directory Page Query (Instant):**
```python
# apps/public/views.py

def directory(request):
    """
    Directory page listing all public orgs.
    Uses pre-computed PublicOrgStats (no aggregation).
    """
    orgs = (
        PublicOrgStats.objects
        .filter(org_profile__is_public=True, total_prs__gte=500)
        .select_related('org_profile')
        .order_by('-total_prs')
    )
    # Result: ~70 rows, instant query (<50ms)

    context = {'orgs': orgs, ...}
    return _public_response(request, 'public/directory.html', context)
```

---

#### **Query Limiting for Public Views**

```python
# Limit PR list pagination for public views

if request.is_public_view:
    max_results = 5000  # 100 pages × 50 PRs/page
    prs = prs[:max_results]  # Cap queryset
else:
    # Authenticated: no limit
    pass
```

**Database Indexes (for performance):**
```python
# Migration: apps/metrics/migrations/0044_add_public_view_indexes.py

class Migration(migrations.Migration):
    operations = [
        # Compound index for PR queries
        migrations.AddIndex(
            model_name='pullrequest',
            index=models.Index(
                fields=['team', 'pr_created_at'],
                name='pr_team_date_idx'
            ),
        ),
        # Compound index for AI-filtered queries
        migrations.AddIndex(
            model_name='pullrequest',
            index=models.Index(
                fields=['team', 'is_ai_assisted', 'pr_created_at'],
                name='pr_team_ai_date_idx'
            ),
        ),
        # Partial index for merged PRs only
        migrations.AddIndex(
            model_name='pullrequest',
            index=models.Index(
                fields=['team'],
                name='pr_team_merged_idx',
                condition=models.Q(state='merged'),
            ),
        ),
    ]
```

---

### 3.6 URL Routing Summary

**Public URLs:**
```
/open-source/posthog/                     → analytics_overview(public_slug='posthog')
/open-source/posthog/analytics/           → analytics_detail(public_slug='posthog')
/open-source/posthog/pull-requests/       → pr_list(public_slug='posthog')
/open-source/posthog/charts/ai-adoption/  → chart_partial(public_slug='posthog', chart_type='ai-adoption')
/open-source/posthog/pr/123/detail/       → pr_detail_modal(public_slug='posthog', pr_id=123)
```

**Authenticated URLs (UNCHANGED):**
```
/a/my-team/                              → analytics_overview(team_slug='my-team')
/a/my-team/analytics/                    → analytics_detail(team_slug='my-team')
/a/my-team/pull-requests/                → pr_list(team_slug='my-team')
/a/my-team/charts/ai-adoption/           → chart_partial(team_slug='my-team', chart_type='ai-adoption')
/a/my-team/pr/123/detail/                → pr_detail_modal(team_slug='my-team', pr_id=123)
```

**Same view functions handle both contexts!**

---

## 4. Engineering Assessment: Implementation Effort

### 4.1 View Inventory (18 views to adapt)

**From `apps/metrics/views/analytics_views.py` (6 views):**
- `analytics_overview()` — Dashboard with summary stats
- `analytics_detail()` — Full analytics page (all charts)
- `ai_adoption_analytics()` — AI adoption sub-tab
- `delivery_metrics()` — Delivery sub-tab
- `quality_indicators()` — Quality sub-tab
- `team_breakdown()` — Team breakdown (gated for public)

**From `apps/metrics/views/pr_list_views.py` (3 views):**
- `pr_list()` — Main PR list with filters
- `pr_detail_modal()` — HTMX partial for PR detail
- `export_prs_csv()` — CSV export (disabled for public)

**From `apps/metrics/views/chart_views.py` (8 HTMX partials):**
- `ai_adoption_chart()` — Line chart
- `pr_velocity_chart()` — Bar chart
- `cycle_time_chart()` — Line chart
- `quality_chart()` — Multi-metric chart
- `ai_tools_chart()` — Bar chart
- `contributor_chart()` — Table or chart
- `trend_sparkline()` — Mini sparkline
- `benchmark_comparison()` — Industry vs. team

**From `apps/web/views.py` (1 view):**
- `team_home()` — Dashboard (becomes Overview tab)

**Total: 18 views**

### 4.2 Decorator Analysis

**Current Usage:**
- `@login_and_team_required`: ~18 views (all analytics, PR list, dashboard)
- `@team_admin_required`: ~5 views (settings, billing) — NOT needed for public pages

**Change Required:**
- Replace `@login_and_team_required` with `@public_or_authenticated_team_required` in 18 views
- Add conditional logic for date limits, feature hiding (minimal)

**Effort:** Simple find-replace + 5-10 lines of conditional logic per view = **2 hours total**

### 4.3 Template Dependencies

**Templates to Modify (18 files):**
- All `templates/metrics/analytics/*.html` (6 templates)
- All `templates/metrics/pull_requests/*.html` (3 templates)
- `templates/web/app_home.html` (1 template)
- 8 chart partial templates

**Change Required:**
- Add conditional `{% if is_public_view %}{% extends "public/app_base.html" %}{% else %}{% extends "web/app_base.html" %}{% endif %}`
- Add `{% if is_public_view %}` blocks around disabled features (export, notes, feedback)

**Effort:** ~30 minutes per template × 18 = **9 hours**

**New Template to Create:**
- `templates/public/app_base.html` — Public tab layout (hero + tabs + sticky CTA)

**Effort:** **2 hours**

### 4.4 Service Layer Readiness

**Assessment:** ✅ Service layer is already ready. Views are thin, delegating to service functions.

**Example (good pattern):**
```python
# apps/metrics/views/analytics_views.py
def analytics_overview(request):
    team = request.team
    summary = compute_team_summary(team.id)  # Service function
    trends = compute_monthly_trends(team.id)  # Service function
    return render(request, template, {'summary': summary, 'trends': trends})
```

**No refactoring needed.** Just extract aggregations to `apps/public/aggregations.py` for DRY.

### 4.5 Risks & Blockers

#### **Risk 1: N+1 Query Performance Without User-Specific Caching**

**Problem:** Authenticated views cache per-user. Public views share cache across all visitors (higher load).

**Mitigation:**
- Use `select_related()` and `prefetch_related()` aggressively
- Pre-compute expensive aggregations in `PublicOrgStats`
- Add DB indexes (see Architecture section)

**Impact:** Medium (query optimization required, but patterns are well-known)

---

#### **Risk 2: Template Coupling to Sidebar Layout**

**Problem:** Some templates assume sidebar exists (e.g., `{% block sidebar %}`)

**Mitigation:** New `public/app_base.html` doesn't include sidebar blocks, templates gracefully degrade (optional blocks)

**Impact:** Low (templates already use optional blocks)

---

#### **Risk 3: HTMX Partials Assume Authenticated Context**

**Problem:** Chart partials might reference `request.user` in templates or analytics tracking

**Mitigation:** Add conditionals: `{% if request.user.is_authenticated %}...{% endif %}`

**Impact:** Low (few partials reference user, mostly team-scoped data)

---

#### **Risk 4: Feature Flag Dependencies**

**Problem:** Some features gated behind Waffle flags (e.g., new charts, LLM insights)

**Mitigation:** Public views bypass flags (always show stable features), OR use `flag_is_active(request, 'flag_name')` which works for anonymous users

**Impact:** Low (Waffle supports anonymous flag checks)

---

#### **Risk 5: Security — Private Data Leakage**

**Problem:** Bug in decorator could expose private team data via public URLs

**Mitigation:**
- Comprehensive test suite (see QA section)
- Add `is_public=True` filter to ALL public queries (belt-and-suspenders)
- Security audit before launch

**Impact:** High (critical to prevent), mitigated by tests + code review

---

### 4.6 Effort Estimate

| Component | Size | Hours | Notes |
|-----------|------|-------|-------|
| **New decorator** (`@public_or_authenticated_team_required`) | M | 4h | Core logic, error handling, unit tests |
| **New base template** (`public/app_base.html`) | S | 2h | Hero, tabs, sticky CTA, breadcrumbs |
| **Modify 18 view templates** (conditional extends + feature hiding) | L | 9h | 30 min each × 18 |
| **Update 18 view functions** (decorator swap + conditionals) | S | 2h | Simple find-replace + date limit logic |
| **Query optimization** (indexes, select_related) | M | 4h | DB migrations, query analysis with EXPLAIN |
| **Conditional logic** (date limits, feature hiding in views) | M | 5h | Template + view conditionals |
| **HTMX partials** (8 chart views, add `is_public_view` checks) | S | 3h | Minimal changes per partial |
| **URL routing** (public app patterns) | S | 2h | New `apps/public/urls.py` routes |
| **Caching layer** (Redis + headers + Cloudflare purge) | M | 4h | Cache utility, view headers, purge function |
| **Testing** (unit + integration + security + E2E) | L | 12h | See QA section (comprehensive coverage) |
| **Documentation** (code comments, update CLAUDE.md) | S | 2h | Inline docs, dev guide update |

**Total Effort: 49 hours**

**Risk Buffer (+20%): 59 hours**

**Calendar Time: 7.5 days (focused dev) or 2-week sprint (with code review, iteration)**

**Recommendation:** **2-week sprint** (allows for testing, QA, polish)

---

## 5. QA & Testing Strategy

### 5.1 Security Testing (CRITICAL)

**Goal:** Ensure public views NEVER expose private team data.

#### **Test Suite: `apps/public/tests/test_security.py`**

```python
import pytest
from django.test import Client
from apps.teams.factories import TeamFactory
from apps.public.factories import PublicOrgProfileFactory

@pytest.mark.django_db
class TestPublicViewSecurity:

    def test_private_team_not_in_directory(self):
        """Private team (no PublicOrgProfile) must not appear in directory."""
        private_team = TeamFactory(slug='private-team')
        # No PublicOrgProfile created

        client = Client()
        response = client.get('/open-source/')

        assert response.status_code == 200
        assert 'private-team' not in response.content.decode()

    def test_private_team_org_detail_404(self):
        """Accessing private team's slug via public URL returns 404."""
        private_team = TeamFactory(slug='private-team')
        # No PublicOrgProfile created

        client = Client()
        response = client.get('/open-source/private-team/')

        assert response.status_code == 404

    def test_public_false_returns_404(self):
        """Team with is_public=False returns 404."""
        team = TeamFactory(slug='secret-demo')
        PublicOrgProfileFactory(
            team=team,
            public_slug='secret',
            is_public=False  # Explicitly private
        )

        client = Client()
        response = client.get('/open-source/secret/')

        assert response.status_code == 404

    def test_directory_only_shows_public_teams(self):
        """Service methods filter by is_public=True."""
        public = TeamFactory(slug='public-demo')
        PublicOrgProfileFactory(team=public, public_slug='public', is_public=True)

        private = TeamFactory(slug='private-demo')
        PublicOrgProfileFactory(team=private, public_slug='private', is_public=False)

        from apps.public.services import PublicAnalyticsService
        orgs = PublicAnalyticsService.get_directory_data()

        assert len(orgs) == 1
        assert orgs[0]['slug'] == 'public'

    def test_write_endpoints_blocked(self):
        """POST/PUT/DELETE to write endpoints returns 403/404/405."""
        team = TeamFactory(slug='posthog-demo')
        profile = PublicOrgProfileFactory(team=team, public_slug='posthog', is_public=True)
        pr = PullRequestFactory(team=team)

        client = Client()

        # Attempt to create note (should be blocked)
        response = client.post(f'/open-source/posthog/notes/pr/{pr.id}/', {'text': 'hack'})
        assert response.status_code in [403, 404, 405]

    def test_llms_txt_no_private_orgs(self):
        """llms.txt only includes public orgs."""
        public = TeamFactory(slug='public-demo')
        PublicOrgProfileFactory(team=public, public_slug='public', is_public=True)

        private = TeamFactory(slug='private-demo')
        PublicOrgProfileFactory(team=private, public_slug='private', is_public=False)

        client = Client()
        response = client.get('/llms.txt')
        content = response.content.decode()

        assert 'public' in content
        assert 'private' not in content
```

**Additional Security Tests:**
- Rate limiting enforced (31st request/min → 429)
- RSS feed only includes public orgs
- HTMX partials respect public context (no user-specific data)

### 5.2 Functional Testing

#### **Test Cases (20 scenarios):**

1. **Directory Page:**
   - [ ] Loads for anonymous user (200)
   - [ ] Shows all public orgs (500+ PR threshold)
   - [ ] Filter by industry works (HTMX partial reload)
   - [ ] Sort works (AI %, total PRs, cycle time, name)
   - [ ] Client-side search filters org cards

2. **Org Overview:**
   - [ ] Loads with valid public_slug (200)
   - [ ] 404 for non-existent slug
   - [ ] 404 for private team slug
   - [ ] Summary stats display correctly
   - [ ] Latest insight displays
   - [ ] Tab navigation links work
   - [ ] CTA visible

3. **Analytics Tab:**
   - [ ] All charts render (canvas elements exist)
   - [ ] Date range limited to 90 days (public view)
   - [ ] Chart data matches org metrics
   - [ ] Export button disabled with tooltip
   - [ ] Industry benchmarks display

4. **PR List Tab:**
   - [ ] Table displays up to 50 PRs/page
   - [ ] Filters work (AI, date, contributor, size)
   - [ ] Sorting works (date, cycle time, size)
   - [ ] Pagination works (100 page limit)
   - [ ] PR modal opens on click
   - [ ] Export button disabled with tooltip

5. **Mobile:**
   - [ ] Tabs scroll horizontally on mobile
   - [ ] Charts resize correctly
   - [ ] PR table scrolls or stacks
   - [ ] CTA bar adapts to mobile

### 5.3 Performance Testing

**Load Test (Locust):**

```python
# locustfile.py
from locust import HttpUser, task, between

class PublicPageVisitor(HttpUser):
    wait_time = between(1, 5)

    @task(3)
    def directory(self):
        self.client.get("/open-source/")

    @task(2)
    def org_overview(self):
        self.client.get("/open-source/posthog/")

    @task(2)
    def analytics(self):
        self.client.get("/open-source/posthog/analytics/")

    @task(1)
    def pr_list(self):
        self.client.get("/open-source/posthog/pull-requests/")
```

**Targets:**
- Page load (cached): <2s
- Page load (uncached): <4s
- 100 concurrent users: avg <3s
- Cache hit rate: >80%

### 5.4 Edge Cases

1. **Org with no PRs:** Shows zeros, no errors
2. **Org with no insights:** Hides insight section
3. **Org with 50K+ PRs:** Pagination capped, <2s query
4. **Logged-in user visits public page:** Renders public view (not redirected)
5. **Bot scraping:** Rate limiter blocks after 30 req/min

### 5.5 Regression Testing

- [ ] Authenticated /app views still work
- [ ] Current public pages still work
- [ ] SEO elements intact (meta tags, sitemap)
- [ ] Permissions still enforced

### 5.6 E2E Smoke Tests (Playwright)

```typescript
// tests/e2e/public-pages.spec.ts
test('Directory loads and shows orgs', async ({ page }) => {
    await page.goto('/open-source/');
    await expect(page.locator('h1')).toContainText('Open Source');
    await expect(page.locator('[data-testid="org-card"]')).toHaveCount({ min: 1 });
});

test('Org overview has tabs and charts', async ({ page }) => {
    await page.goto('/open-source/posthog/');
    await expect(page.locator('h1')).toContainText('PostHog');
    await expect(page.locator('[data-testid="tab-analytics"]')).toBeVisible();
    await expect(page.locator('.stat')).toHaveCount({ min: 3 });
});
```

---

## 6. UI/UX Design: Public App Experience

### 6.1 Tab Navigation Layout

**Component:** DaisyUI `tabs-boxed` (horizontal pills)

```html
<div class="tabs tabs-boxed max-w-7xl mx-auto mt-4 bg-base-200">
  <a class="tab tab-lg {% if active_tab == 'overview' %}tab-active{% endif %}"
     href="/open-source/posthog/">
    <svg class="w-5 h-5 mr-2"><!-- Icon --></svg>
    Overview
  </a>
  <a class="tab tab-lg {% if active_tab == 'analytics' %}tab-active{% endif %}"
     href="/open-source/posthog/analytics/">
    <svg class="w-5 h-5 mr-2"><!-- Icon --></svg>
    Analytics
  </a>
  <a class="tab tab-lg {% if active_tab == 'pull_requests' %}tab-active{% endif %}"
     href="/open-source/posthog/pull-requests/">
    <svg class="w-5 h-5 mr-2"><!-- Icon --></svg>
    Pull Requests
  </a>
</div>
```

**Mobile:** Horizontal scroll (`overflow-x-auto`) with hidden scrollbar

### 6.2 Hero Section (Sticky)

```html
<div class="hero bg-base-200 py-8 sticky top-0 z-10 shadow-md">
  <div class="hero-content flex-col lg:flex-row gap-4">
    <img src="{{ logo_url }}" class="w-20 h-20 rounded-full shadow-lg">
    <div>
      <h1 class="text-4xl font-bold">{{ team.display_name }}</h1>
      <div class="flex gap-2 mt-2">
        <span class="badge badge-primary">{{ industry }}</span>
        <a href="{{ github_url }}" class="badge badge-outline">
          GitHub →
        </a>
      </div>
      <p class="text-sm text-base-content/70 mt-1">
        Last updated: {{ last_synced_at|date:"F j, Y" }}
      </p>
    </div>
  </div>
</div>
```

### 6.3 Read-Only Indicators

**Disabled Export Button:**
```html
<div class="tooltip" data-tip="Sign up to export">
  <button class="btn btn-disabled" disabled>
    Export
    <svg class="w-4 h-4 opacity-50"><!-- Lock --></svg>
  </button>
</div>
```

**Locked Q&A Input:**
```html
<input type="text"
       placeholder="Ask about YOUR team... (Sign up)"
       class="input input-bordered opacity-50"
       disabled>
<a href="/signup/" class="btn btn-primary btn-sm mt-2">
  Unlock Q&A →
</a>
```

**Blurred Team Breakdown:**
```html
<div class="relative">
  <table class="table blur-sm"></table>
  <div class="absolute inset-0 flex items-center justify-center bg-base-100/80">
    <div class="card shadow-lg">
      <div class="card-body text-center">
        <h4>See Per-Contributor Stats</h4>
        <a href="/signup/" class="btn btn-primary">Unlock →</a>
      </div>
    </div>
  </div>
</div>
```

### 6.4 CTA Placement

**Sticky Bottom Bar:**
```html
<div class="fixed bottom-0 w-full bg-primary text-primary-content p-4 z-50">
  <div class="max-w-7xl mx-auto flex gap-4 items-center">
    <span class="text-lg font-semibold">Get this dashboard for your team</span>
    <input type="text" placeholder="your-github-org" class="input w-48">
    <button class="btn btn-secondary">Connect Repos →</button>
  </div>
</div>
```

**Dismissible Banner:**
```html
<div x-data="{ show: !localStorage.getItem('banner_dismissed') }" x-show="show"
     class="alert alert-info shadow-lg max-w-7xl mx-auto mt-4">
  <span>Browsing PostHog's analytics. Want this for your private repos?</span>
  <a href="/signup/" class="btn btn-sm btn-primary">Connect Team</a>
  <button class="btn btn-sm btn-ghost"
          @click="show=false; localStorage.setItem('banner_dismissed','1')">
    Dismiss
  </button>
</div>
```

### 6.5 Mobile Experience

**Tabs:** Horizontal scroll with `overflow-x-auto`
**Charts:** Stack vertically, resize
**CTA Bar:** Full-width, input stacks above button on small screens
**Hero:** Image stacks above text on mobile

### 6.6 Visual Differentiation

**Public pages:**
- Secondary color for CTAs (vs. primary for auth)
- "Public View" badge (top-right corner)
- Sticky hero section
- Sticky CTA bar

**Authenticated pages:**
- Sidebar navigation
- Edit buttons visible
- No signup prompts

---

## 7. Implementation Roadmap

### **Week 1: Foundation**

- [ ] Day 1-2: Create `@public_or_authenticated_team_required` decorator + tests
- [ ] Day 3: Create `templates/public/app_base.html`
- [ ] Day 4: URL routing for public app pages
- [ ] Day 5: DB indexes for performance

**Deliverable:** Decorator works, base template renders, URLs route correctly

---

### **Week 2: View & Template Adaptation**

- [ ] Day 1-2: Update 18 view functions (decorator swap + conditionals)
- [ ] Day 3-4: Update 18 view templates (conditional extends + feature hiding)
- [ ] Day 5: Update 8 HTMX chart partials

**Deliverable:** All views work in both public and authenticated modes

---

### **Week 3: Caching & Performance**

- [ ] Day 1: Redis caching layer (`PublicAnalyticsService`)
- [ ] Day 2: View response headers (`Cache-Control`)
- [ ] Day 3: Pre-computed stats (`PublicOrgStats` populated)
- [ ] Day 4: Query optimization (`select_related`, indexes)
- [ ] Day 5: Load testing (Locust, 100 concurrent users)

**Deliverable:** Pages load <2s, cache hit >80%

---

### **Week 4: Testing & QA**

- [ ] Day 1: Security tests (`test_security.py`, 6 critical tests)
- [ ] Day 2: Functional tests (`test_functional.py`, 20 cases)
- [ ] Day 3: E2E smoke tests (Playwright, 7 scenarios)
- [ ] Day 4: Performance tests (load testing, query benchmarks)
- [ ] Day 5: Regression tests (verify auth /app still works)

**Deliverable:** All tests pass, no regressions

---

### **Week 5: Launch Prep**

- [ ] Day 1: UI/UX polish (CTA review, mobile tweaks, accessibility audit)
- [ ] Day 2: SEO optimization (meta tags, sitemap, robots.txt, Google Search Console)
- [ ] Day 3: Monitoring setup (PostHog events, Cloudflare Analytics, Sentry)
- [ ] Day 4: Staging deployment (`dev2.ianchuk.com`), QA pass
- [ ] Day 5: Production launch (`tformance.com`), monitoring, announce

**Deliverable:** Live public app pages, monitoring active

---

## 8. Success Criteria

### **Launch Week:**
- [ ] 60+ public org pages live and indexed
- [ ] All E2E tests passing
- [ ] No P0/P1 bugs
- [ ] Cache hit rate >70%

### **Month 1:**
- [ ] 1,000+ organic visitors
- [ ] 5-7% conversion rate
- [ ] 10+ AI search citations
- [ ] 50+ CTA clicks

### **Month 3:**
- [ ] 5K-10K organic visitors
- [ ] 8-12% conversion rate
- [ ] 50+ AI search citations
- [ ] 200+ signups from public pages
- [ ] 90%+ cache hit rate

---

## 9. Risks & Mitigation

| Risk | Impact | Probability | Mitigation |
|------|--------|-------------|------------|
| **Private data leak** | Critical | Low | Security test suite, code review, audit |
| **Poor performance (>5s)** | High | Medium | Caching, pre-computed stats, load testing |
| **Low conversion (<5%)** | Medium | Medium | A/B test CTAs, iterate messaging |
| **Competitors copy** | Low | High | First-mover advantage, data moat (167K PRs) |
| **Cloudflare cache issues** | Medium | Low | Fallback to Django cache, monitoring |
| **SEO cannibalization** | Low | Low | Canonical URLs, internal linking |

---

## 10. SEO & Keyword Strategy

### 10.1 The Opportunity: Programmatic SEO

We have ~100 org pages, each with **unique, real data** that changes daily. This is a textbook programmatic SEO play — one template, hundreds of keyword-rich pages, each serving genuine user intent.

Google's 2025-2026 algorithms penalize boilerplate programmatic pages but reward ones with genuinely unique data per page. Our pages pass this test — every org has different metrics, different AI adoption rates, different cycle times.

**Target:** 500-1000 indexable pages (100 orgs × 5 tabs each + industry pages + directory).

### 10.2 Keyword Clusters

#### Cluster 1: Brand + Metrics (High Intent, Low Competition)
Long-tail queries from CTOs researching specific teams.

| Keyword Pattern | Example | Est. Monthly Vol. | Target Page |
|----------------|---------|-------------------|-------------|
| `[org] engineering metrics` | "PostHog engineering metrics" | 50-200 | Org Overview |
| `[org] cycle time` | "Next.js cycle time" | 20-100 | Analytics/Delivery |
| `[org] developer productivity` | "Supabase developer productivity" | 20-100 | Org Overview |
| `[org] AI adoption` | "Vercel AI adoption rate" | 10-50 | Analytics/AI |
| `[org] pull request stats` | "React pull request statistics" | 10-50 | PR List |
| `[org] DORA metrics` | "PostHog DORA metrics" | 10-50 | Org Overview |

#### Cluster 2: Industry Benchmarks (Medium Intent, Medium Competition)
CTOs comparing their team to industry standards.

| Keyword Pattern | Example | Est. Monthly Vol. | Target Page |
|----------------|---------|-------------------|-------------|
| `[industry] engineering benchmarks` | "AI/ML engineering benchmarks 2026" | 200-500 | Industry page |
| `[industry] average cycle time` | "fintech average cycle time" | 50-200 | Industry page |
| `[industry] AI coding adoption` | "devtools AI adoption rate" | 100-300 | Industry page |
| `engineering metrics by industry` | — | 100-300 | Directory |
| `open source team velocity` | — | 50-200 | Directory |

#### Cluster 3: AI Coding Impact (High Volume, High Competition)
Broader awareness queries from the developer community. Key opportunity — 84% of developers now use AI tools, creating massive search demand.

| Keyword Pattern | Example | Est. Monthly Vol. | Target Page |
|----------------|---------|-------------------|-------------|
| `AI coding tools impact` | — | 500-2K | Directory intro |
| `Copilot vs Cursor productivity` | — | 1K-5K | AI Adoption tabs |
| `AI assisted pull requests` | — | 100-500 | Analytics/AI |
| `does AI improve developer productivity` | — | 500-2K | Directory |
| `AI code generation statistics 2026` | — | 200-1K | Directory |
| `AI adoption rate engineering teams` | — | 200-500 | Industry pages |

#### Cluster 4: DORA & Framework Queries (Medium Volume)

| Keyword Pattern | Example | Est. Monthly Vol. | Target Page |
|----------------|---------|-------------------|-------------|
| `DORA metrics open source` | — | 100-300 | Directory |
| `cycle time vs lead time` | — | 200-500 | Analytics/Delivery |
| `engineering KPIs 2026` | — | 500-1K | Directory |
| `SPACE metrics examples` | — | 100-500 | Analytics/Team |
| `PR cycle time benchmark` | — | 100-300 | Analytics/Delivery |

### 10.3 On-Page SEO Templates

#### Title Tags (max 60 chars, dynamic)

```
Org Overview:    "{org} Engineering Metrics: {ai_pct}% AI Adoption | Tformance"
Org AI Adoption: "{org} AI Coding Adoption: Copilot, Cursor & More"
Org Delivery:    "{org} Cycle Time & PR Velocity - {cycle_time}h Median"
Org Quality:     "{org} Code Quality Metrics - Review Time & CI Stats"
Org PR List:     "{org} Pull Requests: {total_prs} PRs with AI Classification"
Industry:        "{industry} Engineering Benchmarks 2026 - {org_count} Teams"
Directory:       "Open Source Engineering Analytics - {org_count} Projects"
```

#### Meta Descriptions (max 155 chars, dynamic)

```
Org Overview:    "Engineering metrics for {org}: {total_prs} PRs, {ai_pct}% AI-assisted,
                  {cycle_time}h cycle time. Compare with {industry} benchmarks. Updated daily."
Industry:        "{industry} engineering benchmarks: {org_count} projects compared.
                  Average AI adoption {avg_ai_pct}%, cycle time {avg_cycle}h."
Directory:       "Browse engineering metrics from {org_count} open source projects.
                  Compare AI adoption, cycle time, and team velocity. Updated daily."
```

#### H1/H2 Keyword Structure

```html
<!-- Org Overview -->
<h1>{org} Engineering Metrics</h1>
<h2>AI Adoption & Developer Productivity</h2>
<h2>Cycle Time & Delivery Velocity</h2>
<h2>Team Performance Breakdown</h2>

<!-- Org AI Adoption -->
<h1>{org} AI Coding Tool Adoption</h1>
<h2>AI-Assisted vs Traditional Pull Requests</h2>
<h2>AI Tools Detected: Copilot, Cursor & More</h2>

<!-- Industry page -->
<h1>{industry} Engineering Benchmarks 2026</h1>
<h2>AI Adoption Across {industry} Teams</h2>
<h2>Average Cycle Time & PR Velocity</h2>
```

### 10.4 Technical SEO Requirements

#### A. Inline Chart Data (Critical)

HTMX lazy-loaded charts via `hx-get` + `hx-trigger="load"` are **invisible to Googlebot**. Public pages must render chart data server-side:

```python
@public_org_required
def public_analytics_overview(request, slug):
    context = _get_analytics_context(request, "overview")
    # Pre-fetch data that /app lazy-loads via HTMX
    from apps.metrics.services import dashboard_service
    context["key_metrics"] = dashboard_service.get_key_metrics(
        request.team, context["start_date"], context["end_date"]
    )
    context["inline_charts"] = True  # Template renders data directly
    ...
```

```html
{% if inline_charts %}
  {% include "metrics/partials/key_metrics_cards.html" with metrics=key_metrics %}
{% else %}
  <div hx-get="{% url 'metrics:cards_metrics' %}" hx-trigger="load">
    <div class="skeleton h-24"></div>
  </div>
{% endif %}
```

#### B. JSON-LD Structured Data

```html
<!-- Org pages: Dataset schema (enables Google Dataset Search) -->
<script type="application/ld+json">
{
  "@context": "https://schema.org",
  "@type": "Dataset",
  "name": "{{ profile.display_name }} Engineering Metrics",
  "description": "{{ page_description }}",
  "url": "https://tformance.com/open-source/{{ profile.slug }}/",
  "creator": {
    "@type": "Organization",
    "name": "{{ profile.display_name }}",
    "url": "{{ profile.github_org_url }}"
  },
  "dateModified": "{{ summary.last_computed_at|date:'Y-m-d' }}",
  "temporalCoverage": "2025/2026",
  "variableMeasured": ["AI Adoption Rate", "Cycle Time", "Pull Request Volume"]
}
</script>
```

#### C. Dynamic Sitemap

```python
# apps/public/sitemaps.py
class PublicOrgSitemap(Sitemap):
    changefreq = "daily"
    priority = 0.8

    def items(self):
        return PublicOrgProfile.objects.filter(
            is_public=True, stats__total_prs__gte=10
        ).select_related("stats")

    def location(self, obj):
        return f"/open-source/{obj.public_slug}/"

    def lastmod(self, obj):
        try:
            return obj.stats.last_computed_at
        except Exception:
            return None


class PublicOrgTabsSitemap(Sitemap):
    """One entry per org per tab (500+ URLs)."""
    changefreq = "daily"
    priority = 0.7

    def items(self):
        profiles = PublicOrgProfile.objects.filter(
            is_public=True, stats__total_prs__gte=10
        )
        tabs = ["analytics", "analytics/ai-adoption", "analytics/delivery",
                "analytics/quality", "pull-requests"]
        return [(p, tab) for p in profiles for tab in tabs]

    def location(self, item):
        profile, tab = item
        return f"/open-source/{profile.public_slug}/{tab}/"


class IndustrySitemap(Sitemap):
    changefreq = "weekly"
    priority = 0.6

    def items(self):
        return [key for key, _ in INDUSTRY_CHOICES]

    def location(self, item):
        return f"/open-source/industry/{item}/"
```

#### D. Canonical URLs + Robots

```html
<link rel="canonical" href="https://tformance.com{{ request.path }}">
```

Update `robots.txt`:
```
Sitemap: https://tformance.com/sitemap.xml
Allow: /open-source/
```

#### E. Open Graph + Twitter Cards

```html
<meta property="og:title" content="{{ page_title }}">
<meta property="og:description" content="{{ page_description }}">
<meta property="og:url" content="https://tformance.com{{ request.path }}">
<meta property="og:image" content="https://tformance.com/og/{{ profile.slug }}.png">
<meta property="og:type" content="website">
<meta name="twitter:card" content="summary_large_image">
```

Optional V2: Generate dynamic OG images per org with stats baked in (Pillow or a serverless OG image service).

### 10.5 Content Blocks for Keyword Density

Contextual prose blocks that serve both users and Googlebot:

```html
<!-- Org Overview: about section -->
<div class="prose prose-sm text-base-content/70 mt-8">
  <h3>About {{ profile.display_name }} Engineering Metrics</h3>
  <p>
    These metrics are computed from {{ summary.total_prs }} merged pull requests
    in {{ profile.display_name }}'s public GitHub repositories. AI adoption is
    detected through PR metadata analysis and LLM classification. Cycle time
    measures duration from PR creation to merge. Data refreshes daily.
  </p>
  <p>
    {{ profile.display_name }} operates in the {{ profile.industry_display }}
    industry. The industry average AI adoption is {{ industry_stats.avg_ai_pct }}%,
    putting {{ profile.display_name }} at {{ summary.ai_assisted_pct }}% —
    {% if summary.ai_assisted_pct > industry_stats.avg_ai_pct %}above{% else %}below{% endif %}
    the benchmark.
  </p>
</div>
```

```html
<!-- Directory: intro paragraph -->
<div class="prose max-w-3xl mx-auto mb-8">
  <p>
    Engineering metrics from {{ global_stats.org_count }} open source organizations,
    covering {{ global_stats.total_prs }} pull requests across
    {{ global_stats.industry_count }} industries. Track AI coding tool adoption,
    developer productivity, and delivery velocity — updated daily from public
    GitHub data.
  </p>
</div>
```

### 10.6 Internal Linking Map

```
Directory ──→ Each org overview (100 links)
    │
    └──→ Industry pages (10+ links)
              │
              └──→ Each org in that industry

Org Overview ──→ Analytics tabs (4 links)
    │          └──→ PR List (1 link)
    │
    └──→ Related orgs in same industry (4 links)
    └──→ Industry comparison page (1 link)

Each page: 5-10 internal links minimum for crawl depth.
```

### 10.7 Static Generation: Decision

**Decision: No static generation. Django SSR + Cloudflare CDN is sufficient.**

| Factor | Django SSR + CDN | Static Generation |
|--------|-----------------|-------------------|
| CDN hit speed | ~50ms | ~50ms |
| Data freshness | Real-time on miss | Stale until rebuild |
| Build complexity | None | CI/CD pipeline |
| New org pages | Automatic | Requires rebuild |
| Inline charts | Server-side in view | Pre-rendered |

With 12h CDN TTL and daily data refresh, cache hit rate is ~95%. Adding SSG would mean a separate build pipeline for negligible speed gains.

**The actual SEO fix:** Render chart data inline for public views (not via HTMX). This gives Googlebot complete HTML without any build step.

### 10.8 SEO KPIs

| Metric | Tool | Target (3 months) |
|--------|------|-------------------|
| Indexed pages | Google Search Console | 500+ |
| Organic impressions | GSC | 50K/month |
| Organic clicks | GSC | 5K/month |
| Avg position (brand + metrics) | GSC | <20 |
| Core Web Vitals | PageSpeed Insights | All "Good" |
| Referring domains | Ahrefs/GSC | 20+ |
| Crawl errors | GSC | 0 on public pages |

---

## 11. Next Steps

1. **Review & Approve:** Team lead reviews doc, gathers feedback
2. **Spike: Decorator Prototype:** Build `@public_or_authenticated_team_required` (1 day)
3. **Spike: Template Conditional:** Test `{% if %}{% extends %}` pattern (1 day)
4. **Go/No-Go:** Based on spike results, commit to 5-week roadmap
5. **Sprint Planning:** Break down into Jira tickets, assign engineers

---

## Appendix: References

- **Original Plan:** [2026-02-15-public-oss-analytics.md](/Users/yanchuk/Documents/GitHub/tformance/docs/plans/2026-02-15-public-oss-analytics.md)
- **Codebase Context:** [CLAUDE.md](/Users/yanchuk/Documents/GitHub/tformance/CLAUDE.md)
- **Current Public Views:** [apps/public/views.py](/Users/yanchuk/Documents/GitHub/tformance/apps/public/views.py)

---

**Status:** ✅ Complete
**Next Action:** Team review & spike tasks
**Owner:** Product Marketer (Team Lead)
**Last Updated:** 2026-02-15
