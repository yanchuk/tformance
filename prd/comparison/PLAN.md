# Comparison Pages Implementation Plan

**Content drafts location:** `/prd/comparison/`

## Overview

Create a hybrid comparison page system:
- **Hub page** (`/compare/`) - Overview with feature matrix & pricing calculator
- **7 Individual pages** (`/compare/<slug>/`) - Deep-dive for each competitor

**Goals:** SEO capture ("X alternative") + Sales enablement (help prospects decide)
**Tone:** Honest & direct (acknowledge competitor strengths where relevant)

---

## Writing Style Guide

*Based on Scott Adams' advice (via ma.tt) and William Zinsser's "On Writing Well"*

### Core Principles

1. **Clarity over cleverness** - Business writing is about clarity and persuasion. Keep things simple.

2. **Every word must earn its place** - Cut ruthlessly. "Very happy" → "happy". "In order to" → "to". "Due to the fact that" → "because".

3. **Short sentences** - Break complex ideas into bite-sized pieces. One thought per sentence.

4. **Active voice** - "Tformance tracks AI usage" not "AI usage is tracked by Tformance". Active verbs = energy.

5. **Open strong** - First sentence must hook. Create curiosity. Rewrite it five times if needed.

### What to Cut (Zinsser's "Clutter")

| Cut This | Keep This |
|----------|-----------|
| "It is important to note that" | (just state the thing) |
| "In terms of pricing" | "Pricing:" |
| "At this point in time" | "Now" |
| "The fact that" | (remove entirely) |
| "In the event that" | "If" |
| "A large number of" | "Many" |
| "Has the ability to" | "Can" |

### Comparison Page Writing Rules

**Headlines:**
- Bad: "A Comprehensive Analysis of the Key Differences Between Tformance and LinearB"
- Good: "Tformance vs LinearB: Same Metrics, 70% Less"

**Feature descriptions:**
- Bad: "Tformance provides users with the capability to track and measure AI tool adoption across their engineering teams"
- Good: "Track AI tool adoption across your team"

**Pricing copy:**
- Bad: "Our pricing model is significantly more affordable compared to competitor offerings"
- Good: "Save $33,000/year vs LinearB"

**Calls to action:**
- Bad: "Click here to begin your free trial experience"
- Good: "Start free"

### Tone for Honest Comparisons

From Zinsser: *"Writing is an act of ego, and you might as well admit it."*

Be confident but not arrogant:
- ✅ "We're cheaper. Here's why."
- ❌ "We humbly believe our solution may offer some cost advantages"

Be honest but not self-deprecating:
- ✅ "Jira integration coming soon"
- ❌ "Unfortunately, we don't yet have Jira integration like our competitors do"

Acknowledge competitors fairly:
- ✅ "LinearB's Dev Interrupted community is valuable. We don't have that."
- ❌ "LinearB wastes your time with a podcast"

### The Readability Test

Before publishing any comparison page, read it aloud. If you stumble, rewrite. If you sound like a brochure, rewrite. If your friend would roll their eyes, rewrite.

---

## Comparison Page Copywriting Structure

*Best practices from SaaS comparison page leaders (Notion, Linear, Webflow)*

### The Proven Structure (Individual Competitor Page)

```
1. HOOK (Above the fold)
   - H1: "Tformance vs [Competitor]"
   - Subhead: One punchy line with key differentiator
   - Alpha badge (honest about stage)
   - Two CTAs: Primary action + Secondary

2. TL;DR BOX (For skimmers)
   - 3 bullet points max
   - Numbers speak louder than adjectives
   - "Save $33K/year" not "more affordable"

3. AT A GLANCE TABLE
   - Side-by-side comparison (5-7 rows max)
   - Visual checkmarks, X marks, "Soon" badges
   - Our weaknesses visible (builds trust)

4. THE HONEST TAKE
   - "Choose [Competitor] if..." (acknowledge their strengths)
   - "Choose Tformance if..." (our sweet spot)
   - No FUD, no trash talk

5. PRICING COMPARISON
   - Real numbers, real scenarios
   - Team sizes: 10, 25, 50, 100 devs
   - Annual savings highlighted
   - Calculator if interactive

6. DEEP DIVE (Expandable sections)
   - AI Detection: How each works
   - Integrations: What connects
   - Metrics: What's measured
   - Only for users who want details

7. FAQ (SEO + Objection handling)
   - 5-8 questions
   - Address real concerns
   - "Is Tformance ready for production?" → Honest answer

8. FINAL CTA
   - Reiterate value prop
   - Free during alpha messaging
   - Low commitment ask
```

### Hub Page Structure

```
1. HERO
   - "Find the right engineering analytics tool"
   - Subhead: We compared ourselves honestly

2. COMPETITOR GRID
   - Cards for each competitor
   - One-liner positioning each
   - "Compare →" links

3. FEATURE MATRIX
   - All competitors in columns
   - Features in rows
   - Visual indicators (✅, 🔜, ❌)

4. PRICING OVERVIEW
   - Quick cost comparison
   - "Starting at" for each

5. "WE'RE DIFFERENT" SECTION
   - Alpha stage honesty
   - Our focus: AI impact
   - What we're NOT (yet)

6. CTA
   - Try free, no commitment
```

### Content Files to Create

```
/prd/comparison/
├── PLAN.md                    # Full implementation plan
├── STRUCTURE.md               # This copywriting guide
├── hub-page.md               # Hub page content draft
├── vs-linearb.md             # Individual competitor drafts
├── vs-jellyfish.md
├── vs-swarmia.md
├── vs-span.md
├── vs-workweave.md
├── vs-mesmer.md
└── vs-nivara.md
```

---

## Alpha Stage Honesty

**CRITICAL: We're in alpha. Be upfront about it.**

### Alpha Messaging (Use on all comparison pages)

```html
<div class="alpha-notice">
  <span class="badge badge-warning">Alpha</span>
  <p>Tformance is in early alpha. We're building fast and shipping weekly.
     Some features competitors have, we don't — yet.</p>
</div>
```

**Why this helps:**
- Sets expectations correctly
- Builds trust through transparency
- Positions us as the underdog (people root for underdogs)
- "Free during alpha" becomes a compelling offer

### What We Say

| Instead of | Say |
|------------|-----|
| "We offer comprehensive metrics" | "We're focused on AI impact. Other metrics coming." |
| "Full-featured platform" | "Early alpha. Core features work. More shipping weekly." |
| "Enterprise-ready" | "Startup-ready. Enterprise features on the roadmap." |
| "Complete solution" | "GitHub + AI tracking live. Jira, Slack coming soon." |

---

## Tformance Feature Status (Be Honest!)

**CRITICAL: Comparison pages must clearly indicate what's live vs planned.**

### ✅ LIVE NOW (Alpha)
| Feature | Status | Notes |
|---------|--------|-------|
| GitHub integration | ✅ Live | PRs, commits, reviews, cycle time |
| AI tool detection | ✅ Live | Automatic detection from PR patterns (Copilot, Cursor, etc.) |
| Team Performance dashboard | ✅ Live | Throughput, cycle time, review load |
| AI Adoption dashboard | ✅ Live | AI-assisted vs traditional PRs |
| Insights | ✅ Live | AI-powered trend analysis |
| Copilot metrics | ✅ Live | Tracked via GitHub integration |

### 🔜 COMING SOON (Planned)
| Feature | Status | Notes |
|---------|--------|-------|
| Jira integration | 🔜 Soon | Ticket linking, sprint velocity |
| Slack bot/surveys | 🔜 Soon | Developer surveys, weekly digests |
| Google Calendar | 🔜 Soon | Meeting load, focus time |
| Gamified surveys ("AI Detective") | 🔜 Soon | Fun survey experience |
| DORA metrics (full) | 🔜 Soon | Basic cycle time available now |
| SOC 2 certification | 🔜 Planned | Currently in process |

### ❌ What Competitors Have That We Don't (Yet)
- Full DORA metrics suite (we have cycle time only)
- Jira deep integration
- Slack surveys and notifications
- SOC 2 certification
- Workflow automation (PR routing, approvals)
- R&D capitalization / DevFinOps

### Feature Matrix Honesty Rules
1. Use clear indicators: ✅ (live), 🔜 (coming soon), ❌ (not planned)
2. Don't hide "coming soon" - make it visible
3. In comparison tables, show competitor features honestly even if they have more
4. Highlight where we excel (price, AI focus) not feature count
5. **Always show "Alpha" badge on comparison pages**

---

## Competitors to Cover

| Priority | Competitor | Slug | Our Angle |
|----------|------------|------|-----------|
| HIGH | LinearB | `linearb` | "Same DORA metrics, 70% less cost. No enterprise sales calls." |
| HIGH | Jellyfish | `jellyfish` | "Enterprise features at startup prices. Actually affordable." |
| HIGH | Swarmia | `swarmia` | "AI impact + gamification. More than developer experience." |
| MEDIUM | Span | `span` | "AI detection without enterprise complexity or pricing." |
| MEDIUM | Workweave | `workweave` | "Similar AI focus, simpler pricing model." |
| LOW | Mesmer | `mesmer` | "Metrics + surveys, not just status automation." |
| LOW | Nivara | `nivara` | "Proven product, not just YC hype." |

---

## Hub Page Structure (`/compare/`)

### Sections

1. **Hero** - "Compare Tformance" + value prop
2. **Quick Comparison Cards** - Visual grid of top competitors with key differentiators
3. **Feature Comparison Matrix** - Side-by-side feature table (all competitors)
4. **Pricing Calculator** - Interactive annual savings calculator
5. **"Best For" Guide** - When to choose us vs when to consider alternatives
6. **CTA** - "Start Free Trial"

### Feature Matrix Categories

| Category | Features |
|----------|----------|
| AI Tracking | AI code detection, AI tool usage, AI ROI metrics |
| Core Metrics | DORA metrics, PR insights, cycle time |
| Developer Experience | Surveys, gamification, sentiment tracking |
| Integrations | GitHub, Jira, Slack, AI tools |
| Pricing | Free tier, per-seat, flat rate |
| Security | SOC 2, GDPR, data handling |

---

## Individual Page Structure (`/compare/<slug>/`)

### Standard Template Sections

```
1. Hero
   - "Tformance vs [Competitor]"
   - One-liner positioning statement
   - Two CTAs: "Start Free" | "See How It Works"

2. TL;DR Summary (3 bullets)
   - Key reason #1 to switch
   - Key reason #2 to switch
   - Key reason #3 to switch

3. Feature Comparison Table
   - Side-by-side for THIS competitor only
   - Checkmarks, partial support indicators
   - Honest about competitor strengths

4. Pricing Comparison
   - Annual cost calculator for different team sizes
   - Show savings at 10, 25, 50, 100 dev team sizes
   - Use our tiered pricing vs their per-seat

5. Honest Comparison Section
   - "When to choose [Competitor]" (be honest!)
   - "When to choose Tformance"

6. Migration/Switch Guide (optional)
   - What data carries over
   - Setup time comparison

7. FAQ (competitor-specific)
   - Common questions about switching
   - Feature parity questions

8. CTA Section
   - "Try Tformance Free" with 30-day trial messaging
```

---

## Pricing Data to Use

### Our Pricing (Tiered Flat Rate)
| Tier | Team Size | Price/mo |
|------|-----------|----------|
| Trial | Any | $0 (30 days) |
| Starter | ≤10 devs | $99 |
| Team | 11-50 devs | $299 |
| Business | 51-150 devs | $699 |
| Enterprise | 150+ | Custom |

### Competitor Pricing (for comparison)
| Competitor | Model | Est. Cost |
|------------|-------|-----------|
| LinearB | $35-46/seat/mo | $42,000/yr @ 100 devs |
| Jellyfish | ~$50/seat/mo | $60,000/yr @ 100 devs |
| Swarmia | €42/dev/mo | $50,400/yr @ 100 devs |
| Workweave | $50/seat/mo | $60,000/yr @ 100 devs |
| Span | Custom (enterprise) | $60,000+/yr (est) |
| Mesmer | Custom | Unknown |
| Nivara | Demo only | Unknown |

### Annual Savings Calculator (100 devs)
| vs Competitor | Their Cost | Our Cost | Savings |
|---------------|------------|----------|---------|
| Jellyfish | $60,000 | $8,388 | **$51,612 (86%)** |
| LinearB | $42,000 | $8,388 | **$33,612 (80%)** |
| Swarmia | $50,400 | $8,388 | **$42,012 (83%)** |

*Our cost: $699/mo × 12 = $8,388/yr for Business tier*

---

## Implementation Files

### New Files to Create

```
templates/web/compare/
├── base_compare.html          # Base template for all comparison pages
├── hub.html                   # /compare/ hub page
├── competitor.html            # Individual competitor template
├── components/
│   ├── feature_matrix.html    # Reusable feature comparison table
│   ├── pricing_calculator.html # Interactive savings calculator
│   ├── competitor_card.html   # Card for hub page grid
│   ├── comparison_table.html  # Side-by-side for individual pages
│   └── best_for_section.html  # When to choose us vs them

apps/web/
├── views.py                   # Add compare_hub, compare_competitor views
├── urls.py                    # Add /compare/ routes
├── compare_data.py            # Competitor data as Python dicts (SEO meta, features, etc.)
```

### Files to Modify

| File | Change |
|------|--------|
| `apps/web/urls.py` | Add `/compare/` and `/compare/<slug>/` routes |
| `apps/web/views.py` | Add view functions for comparison pages |
| `templates/web/components/footer.html` | Add "Compare" link section (see below) |
| `templates/llms.txt` | Add comparison pages content for LLM discovery |
| `apps/web/sitemaps.py` | Add ComparisonSitemap class |

### Footer Update (`templates/web/components/footer.html`)

Current footer has: Terms | Privacy | Contact

**Add comparison links section:**
```html
<footer class="mt-10 mb-4">
  <div class="text-center text-base-content/70 space-y-2">
    <!-- NEW: Compare section -->
    <p class="text-sm">
      <span class="text-base-content/50">Compare:</span>
      <a href="{% url 'web:compare_competitor' competitor='linearb' %}" class="hover:text-primary transition-colors">vs LinearB</a>
      <span class="mx-1">&middot;</span>
      <a href="{% url 'web:compare_competitor' competitor='jellyfish' %}" class="hover:text-primary transition-colors">vs Jellyfish</a>
      <span class="mx-1">&middot;</span>
      <a href="{% url 'web:compare_competitor' competitor='swarmia' %}" class="hover:text-primary transition-colors">vs Swarmia</a>
      <span class="mx-1">&middot;</span>
      <a href="{% url 'web:compare' %}" class="hover:text-primary transition-colors">All Comparisons</a>
    </p>
    <!-- Existing links -->
    <p class="text-sm">
      <a href="{% url 'web:terms' %}">Terms</a>
      <span class="mx-2">&middot;</span>
      <a href="{% url 'web:privacy' %}">Privacy</a>
      <span class="mx-2">&middot;</span>
      <a href="mailto:hello@tformance.com">Contact</a>
    </p>
    <p>{{project_meta.NAME}} — Copyright <span id="copyright-year">2024</span></p>
  </div>
</footer>
```

**Why these 3 competitors in footer:**
- LinearB, Jellyfish, Swarmia = highest search volume for "[name] alternative"
- "All Comparisons" catches people who want to see the full picture

---

## URL Structure

```python
# apps/web/urls.py additions
path("compare/", views.compare_hub, name="compare"),
path("compare/<slug:competitor>/", views.compare_competitor, name="compare_competitor"),
```

Valid slugs: `linearb`, `jellyfish`, `swarmia`, `span`, `workweave`, `mesmer`, `nivara`

---

## SEO Requirements (Technical SEO Brief)

### 1. URL Structure
```
/compare/                        # Hub page
/compare/linearb/                # Individual pages (trailing slash)
/compare/jellyfish/
/compare/swarmia/
...
```
**Rules:**
- Lowercase, hyphens for word separation
- Trailing slash consistency (pick one, stick to it)
- No parameters in URLs (use canonical if filtering needed)

### 2. Title Tags (50-60 characters optimal)
| Page | Title Tag |
|------|-----------|
| Hub | `Compare Tformance to Top Engineering Analytics Tools (2026)` |
| LinearB | `Tformance vs LinearB: Pricing, Features & Honest Comparison` |
| Jellyfish | `Tformance vs Jellyfish: 70% Less Cost, Same AI Insights` |
| Swarmia | `Tformance vs Swarmia: AI Impact Analytics Comparison 2026` |
| Span | `Tformance vs Span: AI Code Detection Comparison` |
| Workweave | `Tformance vs Workweave: Engineering Analytics Compared` |
| Mesmer | `Tformance vs Mesmer: Engineering Visibility Tools Compared` |
| Nivara | `Tformance vs Nivara: AI Engineering Analytics Comparison` |

### 3. Meta Descriptions (150-160 characters optimal)
| Page | Meta Description |
|------|------------------|
| Hub | `Compare Tformance to LinearB, Jellyfish, Swarmia & more. Side-by-side features, honest pricing comparison. Save 70%+ on AI engineering analytics.` |
| LinearB | `LinearB alternative: Tformance offers same AI metrics at 70% less cost. Compare features, pricing & see which fits your team. No enterprise sales calls.` |
| Jellyfish | `Looking for a Jellyfish alternative? Tformance: enterprise AI insights at startup prices. Compare features & save $50K+ annually on 100-dev teams.` |

### 4. Heading Hierarchy (H1-H6)
```html
<h1>Tformance vs LinearB: 2026 Comparison</h1>  <!-- One H1 per page -->
  <h2>TL;DR: Why Teams Switch</h2>
  <h2>Feature Comparison</h2>
    <h3>AI Impact Tracking</h3>
    <h3>Core Metrics</h3>
    <h3>Integrations</h3>
  <h2>Pricing Comparison</h2>
    <h3>Annual Cost Calculator</h3>
  <h2>When to Choose LinearB</h2>
  <h2>When to Choose Tformance</h2>
  <h2>Frequently Asked Questions</h2>
```

### 5. Schema Markup (Structured Data)

**Required schemas:**
```json
// FAQPage schema for FAQ sections
{
  "@context": "https://schema.org",
  "@type": "FAQPage",
  "mainEntity": [{
    "@type": "Question",
    "name": "How does Tformance compare to LinearB?",
    "acceptedAnswer": {
      "@type": "Answer",
      "text": "Tformance offers similar AI impact tracking at 70% lower cost..."
    }
  }]
}

// Product comparison schema
{
  "@context": "https://schema.org",
  "@type": "Product",
  "name": "Tformance",
  "description": "AI Impact Analytics for Engineering Teams",
  "offers": {
    "@type": "AggregateOffer",
    "lowPrice": "99",
    "highPrice": "699",
    "priceCurrency": "USD"
  }
}

// BreadcrumbList schema
{
  "@context": "https://schema.org",
  "@type": "BreadcrumbList",
  "itemListElement": [
    {"@type": "ListItem", "position": 1, "name": "Home", "item": "https://tformance.com/"},
    {"@type": "ListItem", "position": 2, "name": "Compare", "item": "https://tformance.com/compare/"},
    {"@type": "ListItem", "position": 3, "name": "vs LinearB", "item": "https://tformance.com/compare/linearb/"}
  ]
}
```

### 6. Keyword Strategy Per Page

| Page | Primary Keyword | LSI/Secondary Keywords | Search Volume Est. |
|------|-----------------|------------------------|-------------------|
| Hub | engineering analytics comparison | developer productivity tools, DORA metrics tools, AI coding tools comparison | Medium |
| LinearB | linearb alternative | linearb pricing, linearb review, linearb vs competitors | High |
| Jellyfish | jellyfish alternative | jellyfish engineering, jellyfish pricing, jellyfish competitors | High |
| Swarmia | swarmia alternative | swarmia pricing, swarmia review, developer productivity platform | Medium |
| Span | span ai alternative | span app review, AI code detection tools | Low-Medium |
| Workweave | workweave alternative | workweave pricing, AI developer tools | Low |

### 7. Internal Linking Structure
```
Homepage
  └── /compare/ (hub)
        ├── /compare/linearb/
        ├── /compare/jellyfish/
        ├── /compare/swarmia/
        └── ...

Cross-links:
- Each individual page links to hub
- Each individual page links to 2-3 related competitor pages
- Hub links to all individual pages
- All pages link to /pricing/ and signup CTA
- Blog posts about competitors link to comparison pages
```

### 8. Social Meta Tags (Open Graph + Twitter)
```html
<!-- Open Graph -->
<meta property="og:title" content="Tformance vs LinearB: 2026 Comparison">
<meta property="og:description" content="Compare AI engineering analytics tools. See features, pricing, and honest analysis.">
<meta property="og:image" content="https://tformance.com/images/og/compare-linearb.png">
<meta property="og:url" content="https://tformance.com/compare/linearb/">
<meta property="og:type" content="article">

<!-- Twitter Card -->
<meta name="twitter:card" content="summary_large_image">
<meta name="twitter:title" content="Tformance vs LinearB Comparison">
<meta name="twitter:description" content="70% less cost, same AI metrics. See the full comparison.">
<meta name="twitter:image" content="https://tformance.com/images/og/compare-linearb.png">
```

### 9. OG Images (Create for each page)
- **Size:** 1200x630px
- **Format:** PNG or JPG
- **Content:** Side-by-side logos, key stat ("Save 70%"), clear text
- **Files needed:**
  - `/static/images/og/compare-hub.png`
  - `/static/images/og/compare-linearb.png`
  - `/static/images/og/compare-jellyfish.png`
  - ... (one per competitor)

### 10. Canonical URLs
```html
<!-- On each page -->
<link rel="canonical" href="https://tformance.com/compare/linearb/">
```
- Prevent duplicate content issues
- Always use full absolute URLs
- Self-referencing canonicals on each page

### 11. Content Requirements for SEO

**Minimum content per page:**
- **Word count:** 1,500-2,500 words per comparison page
- **Hub page:** 1,000-1,500 words + feature matrix
- **Unique content:** Each page must have unique intro, analysis, and conclusion

**Content sections that help rankings:**
1. **Executive summary** (50-100 words) - answers search intent immediately
2. **Detailed feature comparison** - table + explanatory text
3. **Pricing analysis** - specific numbers, not vague
4. **Use case scenarios** - "Best for teams who..."
5. **FAQ section** (5-8 questions) - targets long-tail queries
6. **Last updated date** - shows freshness

### 12. Page Speed Requirements
- **Target:** Core Web Vitals pass (LCP < 2.5s, FID < 100ms, CLS < 0.1)
- **Image optimization:** WebP format, lazy loading
- **No heavy JavaScript:** Use HTMX/Alpine.js (already in stack)
- **Cache headers:** Set appropriate cache for static assets

### 13. Mobile Optimization
- **Responsive tables:** Horizontal scroll or card layout on mobile
- **Touch targets:** 44x44px minimum for CTAs
- **Readable fonts:** 16px+ body text on mobile
- **Test:** Google Mobile-Friendly Test on all pages

### 14. Robots.txt & Sitemap

**Robots.txt** - No changes needed (Django allows all by default)

**Sitemap** - Update `apps/web/sitemaps.py`:
```python
class StaticViewSitemap(sitemaps.Sitemap):
    @property
    def protocol(self):
        return get_protocol()

    def items(self):
        return [
            "web:home",
            "web:compare",           # Hub page
            "web:compare_competitor",  # Dynamic - handle separately
        ]

# OR create a dedicated ComparisonSitemap class:
class ComparisonSitemap(sitemaps.Sitemap):
    changefreq = "monthly"
    priority = 0.7

    @property
    def protocol(self):
        return get_protocol()

    def items(self):
        return ["hub", "linearb", "jellyfish", "swarmia", "span", "workweave", "mesmer", "nivara"]

    def location(self, item):
        if item == "hub":
            return reverse("web:compare")
        return reverse("web:compare_competitor", kwargs={"competitor": item})

    def priority(self, item):
        return 0.8 if item == "hub" else 0.7
```

### 14b. LLMs.txt Update

Add comparison pages section to `templates/llms.txt`:
```markdown
## Comparison Pages

We provide honest comparisons to help you choose the right engineering analytics tool:

- Compare All Tools: https://tformance.com/compare/
- Tformance vs LinearB: https://tformance.com/compare/linearb/
- Tformance vs Jellyfish: https://tformance.com/compare/jellyfish/
- Tformance vs Swarmia: https://tformance.com/compare/swarmia/
- Tformance vs Span: https://tformance.com/compare/span/
- Tformance vs Workweave: https://tformance.com/compare/workweave/
- Tformance vs Mesmer: https://tformance.com/compare/mesmer/
- Tformance vs Nivara: https://tformance.com/compare/nivara/

## How We Compare

Our comparison pages include:
- Honest feature-by-feature comparison (we show where competitors are ahead)
- Pricing comparison with annual cost calculator
- "When to choose them" and "When to choose us" guidance
- We're transparent about features that are "coming soon" vs "live now"

## Competitors We Compare Against

- LinearB: Workflow automation + DORA metrics ($35-46/seat/mo)
- Jellyfish: Enterprise engineering intelligence (~$50/seat/mo)
- Swarmia: DevEx surveys + productivity (€22-42/dev/mo)
- Span: AI code detection specialist (enterprise pricing)
- Workweave: AI-focused PR analytics ($50/seat/mo)
- Mesmer: Engineering visibility/status automation (custom pricing)
- Nivara: AI engineering manager (YC F25, early stage)

Our positioning: AI impact focus at 70% less cost than enterprise alternatives.
```

### 15. Content Freshness Strategy
- **Last updated date:** Display on page ("Last updated: January 2026")
- **Quarterly review:** Check competitor pricing/features every 3 months
- **Blog support:** Write supporting content targeting related keywords
- **Changelog:** Keep `compare_data.py` updated when competitors change

### 16. External Links (Trust Signals)
- **Link to competitor sites** - shows fairness, builds trust
- **Use `rel="nofollow noopener"` on competitor links** - don't pass PageRank
- **Link to authoritative sources** - G2, Capterra reviews if citing

### 17. Tracking & Analytics
```javascript
// Track comparison page engagement
gtag('event', 'view_comparison', {
  'competitor': 'linearb',
  'page_section': 'pricing_calculator'
});

// Track CTA clicks
gtag('event', 'comparison_cta_click', {
  'competitor': 'linearb',
  'cta_location': 'hero'
});
```

---

## SEO Checklist (Pre-Launch)

- [ ] All title tags < 60 characters
- [ ] All meta descriptions < 160 characters
- [ ] One H1 per page
- [ ] Schema markup validated (Google Rich Results Test)
- [ ] OG images created and tested
- [ ] Canonical URLs set
- [ ] Internal links working
- [ ] Mobile-friendly test passed
- [ ] Page speed > 90 (Lighthouse)
- [ ] Sitemap updated
- [ ] Robots.txt allows crawling
- [ ] Analytics tracking implemented
- [ ] Google Search Console submitted after launch

---

## Data Architecture

### Competitor Data Structure (`compare_data.py`)

```python
# Feature status constants
LIVE = "live"           # ✅ Available now
SOON = "coming_soon"    # 🔜 In development
PLANNED = "planned"     # 📋 On roadmap
NO = False              # ❌ Not available

# Our features (honest status)
OUR_FEATURES = {
    "github": LIVE,
    "ai_code_detection": LIVE,  # Via PR patterns, not ML
    "ai_usage_correlation": LIVE,
    "team_performance": LIVE,
    "insights": LIVE,
    "copilot_metrics": LIVE,
    "jira": SOON,
    "slack_surveys": SOON,
    "gamified_surveys": SOON,  # AI Detective game
    "dora_metrics": "partial",  # Cycle time yes, deployment freq no
    "soc2": PLANNED,
}

COMPETITORS = {
    "linearb": {
        "name": "LinearB",
        "tagline": "The AI productivity platform for engineering leaders",
        "website": "linearb.io",
        "pricing_model": "per-seat",
        "pricing_range": "$35-46/seat/mo",
        "annual_cost_100_devs": 42000,
        "free_tier": "8 contributors",
        "our_angle": "AI-focused metrics at 70% less cost",
        "their_strengths": [
            "Strong Dev Interrupted community",
            "Advanced workflow automation (PR routing)",
            "Free tier for 8 contributors",
            "SOC 2 certified"
        ],
        "our_advantages": [
            "70% cheaper ($299/mo vs $1,750+/mo for 50 devs)",
            "Simpler flat-rate pricing (no per-seat anxiety)",
            "AI adoption focus (not workflow automation)",
            "Faster setup, less complexity"
        ],
        "honest_gaps": [
            "They have Jira integration (we're adding soon)",
            "They have more workflow automation features",
            "They have SOC 2 (we're working on it)"
        ],
        "best_for_them": "Teams prioritizing workflow automation + community",
        "best_for_us": "Budget-conscious teams focused on AI impact measurement",
        "features": {
            "ai_code_detection": "partial",
            "ai_usage_correlation": True,
            "gamified_surveys": False,
            "dora_metrics": True,
            "pr_insights": True,
            "github": True,
            "jira": True,
            "slack": True,
            "soc2": True,
        },
        "seo": {
            "title": "Tformance vs LinearB: 2026 Comparison",
            "description": "Honest comparison of Tformance vs LinearB. See pricing (save 70%+), features, and when to choose each tool.",
            "keywords": ["linearb alternative", "linearb pricing", "linearb vs tformance"],
        }
    },
    # ... other competitors with same honest structure
}
```

---

## Honest Positioning Examples

*Following Writing Style Guide: Short. Direct. No fluff.*

### LinearB

**Choose LinearB if:**
- You need PR routing and workflow automation
- You value their Dev Interrupted community
- You want a free tier (8 contributors)
- Jira is a must-have today

**Choose Tformance if:**
- Budget matters. Save $33K/year on a 50-dev team.
- AI impact is your focus, not workflow automation
- You hate per-seat pricing anxiety
- Jira can wait (coming soon)

### Jellyfish

**Choose Jellyfish if:**
- You have 200+ engineers
- DevFinOps and R&D capitalization are priorities
- $60K/year for 100 devs is fine
- SOC 2 is required today

**Choose Tformance if:**
- You're 10-150 engineers
- That budget could fund another engineer
- You want AI insights without enterprise sales calls
- Setup in 5 minutes, not 5 weeks

### Swarmia

**Choose Swarmia if:**
- Full DORA metrics are essential
- You want modular pricing (pick your modules)
- European support hours work for you

**Choose Tformance if:**
- AI impact is priority #1
- One price. No module math.
- You're growing fast and don't want per-seat penalties

### "Honest Gaps" Callout Box

```html
<div class="honest-gaps">
  <h4>Where they're ahead (for now)</h4>
  <ul>
    <li>Jira integration — ours is coming soon</li>
    <li>SOC 2 — we're working on it</li>
    <li>Slack surveys — shipping next quarter</li>
  </ul>
  <p class="text-sm">We ship fast. Check back.</p>
</div>
```

---

## Verification Plan

1. **Visual QA:** Check all pages render correctly
2. **Link verification:** All competitor links work, no broken internal links
3. **Mobile responsive:** Test on mobile breakpoints
4. **SEO check:** Verify meta tags, titles, descriptions render correctly
5. **Calculator test:** Verify pricing calculator math is accurate
6. **Cross-browser:** Test Chrome, Firefox, Safari

### Manual Testing Steps
```bash
# Start dev server
make dev

# Test routes
curl -I http://localhost:8000/compare/
curl -I http://localhost:8000/compare/linearb/
curl -I http://localhost:8000/compare/jellyfish/
# ... etc for all 7 competitors
```

---

## Implementation Order

1. **Data layer** - Create `compare_data.py` with all competitor data
2. **URL routing** - Add routes to `urls.py`
3. **Base template** - Create `base_compare.html` with SEO meta tags, schema markup
4. **Hub page** - Build `/compare/` with feature matrix
5. **Individual template** - Build competitor template with all SEO elements
6. **Top 3 pages** - LinearB, Jellyfish, Swarmia (populate data)
7. **Remaining pages** - Span, Workweave, Mesmer, Nivara (populate data)
8. **OG Images** - Create 8 social sharing images (hub + 7 competitors)
9. **Sitemap update** - Add `ComparisonSitemap` to `apps/web/sitemaps.py`
10. **LLMs.txt update** - Add comparison pages section to `templates/llms.txt`
11. **Footer/Nav links** - Add navigation links to comparison hub
12. **SEO validation** - Schema markup test, title/meta check, mobile test
13. **Analytics setup** - Add comparison page event tracking

---

## Open Questions (Already Resolved)

- ✅ Page approach: Hybrid (hub + individual)
- ✅ Competitors: All 7
- ✅ Goal: Both SEO + sales enablement
- ✅ Tone: Honest & direct
- ✅ Pricing: Use tiered flat rate model from PRICING-STRATEGY.md
- ✅ Feature honesty: Clearly distinguish live vs coming soon features

## Important Notes

### Pricing Disclaimer
The pricing in PRICING-STRATEGY.md is marked as "Draft" and "TBD - requires validation with beta customers". The comparison pages should:
- Use the recommended tiered pricing as a reference point
- Include "pricing subject to change" disclaimer if needed
- Focus on the *value proposition* (70% cheaper) rather than exact numbers

### Feature Status Updates
When features ship, update `compare_data.py` to change status from `SOON` to `LIVE`. This ensures comparison pages stay accurate without template changes.
