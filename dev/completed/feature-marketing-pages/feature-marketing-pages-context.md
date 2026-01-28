# Feature Marketing Pages - Context

**Last Updated:** 2026-01-25

## Key Files

### To Create
| File | Purpose |
|------|---------|
| `templates/web/features/dashboard.html` | Dashboard & Insights page |
| `templates/web/features/analytics.html` | Analytics Deep Dive page |
| `templates/web/features/pr_explorer.html` | PR Data Explorer page |
| `templates/web/components/feature_page_hero.html` | Reusable hero component |
| `templates/web/components/feature_screenshot.html` | Terminal-style screenshot frame |
| `apps/web/tests/test_feature_pages.py` | TDD tests for new pages |
| `e2e/tests/test_feature_marketing.py` | Playwright E2E tests |

### To Modify
| File | Changes |
|------|---------|
| `apps/web/urls.py` | Add 3 new URL patterns |
| `apps/web/views.py` | Add 3 new view functions |
| `apps/web/sitemaps.py` | Add FeaturesSitemap class |
| `templates/web/components/top_nav.html` | Wide mega-menu dropdown |
| `templates/web/features.html` | Transform to hub page |

---

## URL Structure

```
/features/                    → features.html (hub)
/features/dashboard/          → features/dashboard.html
/features/analytics/          → features/analytics.html
/features/analytics/#overview
/features/analytics/#ai-adoption
/features/analytics/#delivery
/features/analytics/#quality
/features/analytics/#team
/features/analytics/#trends
/features/pr-explorer/        → features/pr_explorer.html
```

---

## Copy Style Guide (Writing Well + CTO Marketing)

### Headlines
- Direct, problem-first
- Numbers when possible
- No jargon ("leverage", "optimize", "comprehensive")

### Body Copy
- Active voice
- Short sentences
- "You" and "your" (talk to the reader)

### CTAs
- Primary: "Start Free" or "Start Free Trial"
- Secondary: "See How It Works"

---

## Page Copy Reference

### Dashboard Page (`/features/dashboard/`)
**Hero:**
- Headline: "One dashboard. Weekly clarity."
- Subhead: "Stop context-switching between tools. See what needs attention, what's improving, and what to do next."

**Sections:**
| Section | Headline | Copy |
|---------|----------|------|
| Weekly Report | "Monday morning. Inbox. Done." | Every week: key metrics, trends, anomalies. No spreadsheets, no manual work. Just clarity. |
| AI Insights | "Patterns you'd miss in a spreadsheet" | LLM-powered analysis surfaces what's changing—and why it matters. |
| Needs Attention | "Red, yellow, green. That simple." | Reverted PRs. Long cycles. Review bottlenecks. Know where to focus. |
| Unified View | "GitHub today. Jira and Slack soon." | One place for your engineering data. Connect once, see everything. |

### Analytics Page (`/features/analytics/`)
**Hero:**
- Headline: "See what matters. Ignore what doesn't."
- Subhead: "Cycle time, AI adoption, quality, team load. Drill down or zoom out."

**Sections:**
| Anchor | Headline | Copy |
|--------|----------|------|
| #overview | "Team health at a glance" | Key metrics cards show PRs merged, cycle time, review time. Health indicators flag what needs attention. |
| #ai-adoption | "Is AI actually helping?" | Compare AI vs traditional PRs side-by-side. See adoption % by team member and which tools they use. |
| #delivery | "Where work gets stuck" | Cycle time trends reveal bottlenecks. PR size distribution shows if PRs are staying small. |
| #quality | "Find problems before users do" | Track revert rate, CI pass rate, and review rounds. Spot quality trends before they become incidents. |
| #team | "Balance the load" | See reviewer workload distribution. Identify who's overloaded before burnout hits. |
| #trends | "Patterns over months, not days" | 12-month rolling view. Compare metrics year-over-year. Spot seasonal patterns. |

### PR Explorer Page (`/features/pr-explorer/`)
**Hero:**
- Headline: "Your PR data. Your way."
- Subhead: "Filter by repo, author, AI status, date range. Export to CSV. Add your own notes."

**Sections:**
| Section | Headline | Copy |
|---------|----------|------|
| Advanced Filters | "Find exactly what you need" | Filter by repository, author, AI status, size, date range, technology stack. |
| AI Detection | "AI-assisted? We'll tell you." | Automatic detection on every PR. No surveys required. |
| User Notes | "Context your team will actually read" | Add private notes to any PR. Document decisions, flag concerns. |
| CSV Export | "Take your data anywhere" | Export filtered results for reports, analysis, or stakeholder presentations. |

---

## Navigation Structure

### Desktop Mega-Menu (3 columns, ~500px)
```
┌─────────────────────────────────────────────────────────────────┐
│  DASHBOARD          │  ANALYTICS          │  DATA               │
│                     │                     │                     │
│  📊 Dashboard &     │  📈 Overview        │  📋 PR Explorer     │
│     Insights        │     Team health     │     Filter, export  │
│                     │                     │                     │
│                     │  🤖 AI Adoption     │  🔗 Integrations    │
│                     │     AI vs traditional│     GitHub + more  │
│                     │                     │                     │
│                     │  🚀 Delivery        │                     │
│                     │     Cycle time      │                     │
│                     │                     │                     │
│                     │  ✅ Quality         │                     │
│                     │     Revert rate     │                     │
│                     │                     │                     │
│                     │  👥 Team            │                     │
│                     │     Reviewer load   │                     │
│                     │                     │                     │
│                     │  📉 Trends          │                     │
│                     │     Long-term view  │                     │
├─────────────────────┴─────────────────────┴─────────────────────┤
│  Compare Tools →                                                 │
└─────────────────────────────────────────────────────────────────┘
```

---

## Feature Visibility Rules

**Show prominently:**
- Dashboard features
- All Analytics sections
- PR Explorer features
- GitHub integration (it's live)

**Hide for now:**
- Surveys/benchmarks (not ready)
- Slack/Jira integrations (coming soon - only show on features hub)

---

## Design Patterns

### Screenshot Component (Terminal Style)
- Dark terminal header with window controls
- Rounded corners
- Subtle shadow
- Placeholder image support

### Hero Component
- Configurable badge text
- H1 headline
- Subhead paragraph
- Optional trust indicators

### Section Layout
- Alternating screenshot left/right
- Anchor links with `scroll-mt-20`
- Consistent spacing (py-16)

---

## Screenshots Needed

1. Dashboard main view (insights + needs attention)
2. Analytics Overview tab
3. Analytics AI Adoption tab
4. Analytics Delivery tab
5. Analytics Quality tab
6. Analytics Team tab
7. Trends view
8. PR Explorer with filters

**Placeholder:** Use gradient placeholder until real screenshots provided.
