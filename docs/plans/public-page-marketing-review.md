# Public Org Detail Page -- Marketing Review

**Date:** 2026-02-15
**Reviewer:** Product Marketing
**Page:** `templates/public/org_detail.html`
**Code:** `apps/public/views.py`, `apps/public/services.py`

---

## Summary

The page shows data but tells no story. It presents numbers without context, skips every chance to convert visitors, and never hints at what the paid product does. A visitor absorbs everything in 30 seconds and leaves.

The fix: turn flat numbers into a narrative, add industry context, and show visitors what they're missing.

---

## 1. What's Missing

| Gap | Why it matters |
|-----|----------------|
| **No narrative** | "21% AI adoption" is forgettable. "21% -- 3x the industry average" sticks. |
| **No quotable opening** | AI search engines need one self-contained paragraph to cite. The page opens with a bare H1 + badge. |
| **No industry comparison** | We have the data. We don't show it. This is the most useful free insight we can give. |
| **No trend on cards** | The paid dashboard shows sparklines and "+12% vs. last month." The public page shows flat numbers. |
| **No premium tease** | The paid product has AI insights, team breakdowns, bottleneck alerts, Copilot ROI. The public page mentions none of it. |
| **No CTA** | Zero. No signup link. No "get this for your team." Nothing. |
| **No credibility signals** | No mention of how many orgs we track or how often data refreshes. |
| **Weak related orgs** | One link to the industry page. Should show 3-4 org cards to keep visitors exploring. |
| **Nothing shareable** | No stat is designed to screenshot or tweet. AI adoption should be the hero number. |

### What works

- Clean design, fast load
- Good structured data (JSON-LD Dataset + FAQPage)
- Solid SEO meta tags with real numbers
- Two useful charts (AI trend + velocity)
- AI tools table
- Methodology section builds trust

---

## 2. Three-Tier Value Story

The public page should make visitors feel informed but incomplete.

**Free -- "See what's happening"**
Org-level AI adoption, trend charts, cycle time, AI tools, industry rank.

**Teased -- "But you can't see why"**
Per-developer breakdown, AI quality impact, bottleneck detection, recommendations.

**Premium -- "Sign up for answers"**
AI-generated insights, team health indicators, Copilot ROI, Ask AI, Slack surveys, Jira tracking.

The goal: visitors think "This is useful. I bet the paid version tells me *why* and *what to do about it*."

---

## 3. Lead with AI Adoption

AI adoption is the most shareable, search-friendly metric on this page. Make it the hero.

**Now:** `AI-Assisted PRs: 21.0%` (same visual weight as every other card)

**Better:**
> **21% of PostHog's PRs are AI-assisted** -- 1.5x the industry average, putting them in the top quartile of analytics companies.

### Best metrics for storytelling (ranked)

1. **AI Adoption %** -- universally interesting, drives search traffic
2. **AI Adoption Trend** -- "Up 8 points in 6 months" is a story
3. **Cycle Time vs. Industry** -- context makes raw numbers meaningful
4. **AI Tools Breakdown** -- "67% Copilot, 22% Cursor" is specific and quotable
5. **Active Contributors** -- shows project scale

### De-emphasize

- Total PRs (scale metric, not an insight)
- Raw cycle time without comparison (meaningless alone)

---

## 4. CTAs

### Above the fold
Below the hero paragraph, before metric cards.
- **"Get these metrics for your repos"** -- Start Free Trial
- Supporting: "Connect GitHub in 2 minutes. No card required."

### After charts
Between charts and AI tools table. Subtle premium tease card.
- **"Which developers are driving this adoption?"**
- "See per-developer breakdowns, AI quality impact, and weekly recommendations with Tformance Pro."
- Button: "See what Pro includes"

### Bottom of page
After methodology, before related orgs. Full-width accent card.
- **"You're looking at open source data. Imagine this for your team."**
- Four bullet points: per-dev tracking, quality impact, bottleneck detection, weekly insights
- Button: "Start Free Trial"

### Mobile sticky
Fixed bottom bar after scrolling past hero.
- **"Get this for your team"** -- "Try Free"

---

## 5. What Premium Features to Tease

From the authenticated dashboard (`templates/metrics/team_dashboard.html` and partials):

**A. Team Breakdown** (`team_breakdown_table.html`)
Show blurred table headers: "Team Member | PRs | Cycle Time | AI % | Copilot %"
Copy: "See who's adopting AI tools -- and how it affects their speed."

**B. Engineering Insights** (`engineering_insights.html`)
Show a locked card with a sample headline: "AI-assisted PRs ship 23% faster on this team"
Copy: "AI-powered analysis of your team. Every week."

**C. Team Health** (`team_health_indicators_card.html`)
Show 5 indicator rows with colored dots visible, values hidden.
Copy: "Five health signals. One glance."

**D. AI Quality Impact** (`ai_quality_chart.html`)
Copy: "Are AI PRs helping or hurting code quality? Pro measures the difference."

**Skip these:** Copilot seat management (too niche), Slack surveys (implementation detail), Jira linkage (narrows audience).

---

## 6. Copy Recommendations by Section

### Hero + Citable Summary

**Now:**
```
<h1>PostHog</h1>
<badge>Product Analytics</badge>
<p>{{ profile.description }}</p>
```

**Rewrite:**
```
<h1>PostHog Engineering Metrics</h1>
<badge>Product Analytics</badge> <badge>#3 in industry</badge>

<p class="lead">
  21% of PostHog's pull requests are AI-assisted -- 1.5x the
  product analytics industry average. Based on 4,521 merged PRs
  analyzed by Tformance. Median cycle time: 18 hours, 25% faster
  than peers.
</p>

<p class="text-sm">Updated daily.</p>

<a href="/signup/" class="btn btn-primary">
  Get these metrics for your repos
</a>
```

Self-contained, citable, specific. AI search engines will quote this verbatim.

### Metric Cards

| Now | Better | Why |
|-----|--------|-----|
| "Total PRs (2025+)" | "PRs Analyzed" | Simpler |
| "AI-Assisted PRs" | "AI Adoption Rate" | Frames it as a trend |
| "Median Cycle Time" | Keep, add "vs. Xh industry avg" | Context |
| "Active Contributors" | Keep as-is | Already clear |

Add a `stat-desc` to each card: "1.5x industry average" or "25% faster than peers."

### Industry Context (new section)

Between metric cards and charts:

```
How does PostHog compare?
Across 12 product analytics companies, average AI adoption is 14%.
PostHog's 21% puts them in the top quartile.

[View Product Analytics Benchmarks ->]
```

### Charts

Keep both existing charts. Add a horizontal dashed line on the AI Adoption chart showing the industry median. That line turns data into a story: "they crossed above average in July 2025."

### AI Tools Table

Rename "Top AI Tools Detected" to "AI Tools in Use." Add a note: "Detected from PR metadata. [How we detect AI tools ->]"

### "What Pro Reveals" (new section)

After AI tools, before methodology:

```
What Tformance Pro shows you

Per-Developer Breakdown
See who's adopting AI tools and how it changes their speed and quality.

AI Quality Impact
Are AI PRs causing more reverts? Measure the real effect.

Bottleneck Detection
Spot overloaded reviewers before they slow your team down.

Weekly AI Insights
Get specific recommendations based on your team's actual data.

[Start Free Trial -- No Card Required]
```

### Related Orgs

Replace the single link with 3-4 org cards from the same industry:

```
Compare with similar projects

[OrgName]        [OrgName]        [OrgName]
18% AI | 22h     31% AI | 14h     12% AI | 28h

View all Product Analytics organizations ->
```

Each click keeps visitors on-site. More pages, more chances to convert.

---

## 7. Priority

| Pri | Change | Effort | Impact |
|-----|--------|--------|--------|
| P0 | Citable summary paragraph | Small | High (SEO + GEO) |
| P0 | Primary CTA above fold | Small | High (conversion) |
| P0 | Industry comparison on cards | Medium | High (storytelling) |
| P1 | Premium tease after charts | Small | Medium (conversion) |
| P1 | Related orgs as cards | Medium | Medium (engagement) |
| P1 | "What Pro reveals" section | Small | Medium (conversion) |
| P2 | Industry median line on chart | Medium | Medium (storytelling) |
| P2 | Bottom CTA | Small | Low-Medium |
| P2 | Trend indicators on cards | Medium | Medium |

---

## 8. Data Needs

Everything here works with existing models and services:

1. **Industry stats** -- `PublicAnalyticsService.get_industry_comparison()` exists. Pass results into org detail context.
2. **Industry rank** -- Sort orgs in same industry by AI adoption. Simple query on existing data.
3. **Related orgs** -- 3-4 orgs from same industry, excluding current. Already available via `PublicOrgProfile`.
4. **Month-over-month trend** -- Compare current to previous month. `monthly_trends` is already in context.

No new models. No migrations.

---

## 9. Messaging by Audience

### CTOs
- "See how top open-source teams use AI coding tools."
- "Your competitors measure this. Do you?"

### Developers / OSS maintainers
- "Free engineering metrics for your project."
- "See how you compare."
- "Request your repo."

### AI search / citations
- Specific, quotable numbers in the first paragraph.
- Self-contained sections that work as standalone facts.
- Source attribution at page bottom.
