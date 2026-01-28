# Feature Marketing Pages - Implementation Plan

**Last Updated:** 2026-01-25

## Executive Summary

Create 3 dedicated marketing pages (`/features/dashboard/`, `/features/analytics/`, `/features/pr-explorer/`) to showcase Tformance features with CTO-focused copy, expand the navigation mega-menu, and improve SEO. Implementation follows TDD with Playwright verification.

## Current State

- Single `/features/` page with anchor sections
- Basic dropdown navigation (w-80, single column)
- No dedicated feature subpages
- Sitemap includes: home, pricing, team, terms, privacy, compare pages
- Terminal-style visual aesthetic established on landing page

## Proposed Future State

- **3 new feature pages** with rich, CTO-focused content
- **Wide mega-menu** (~500px, 3-column layout like Notion/Linear)
- **Reusable components** for heroes and screenshots
- **Hub page** transformation of existing `/features/`
- **Complete sitemap** including all new pages

---

## Implementation Phases

### Phase 1: Foundation (TDD Setup)
**Goal:** Create reusable components and URL structure

| Task | Description | Effort | Acceptance Criteria |
|------|-------------|--------|---------------------|
| 1.1 | Write TDD tests for new URL routes | S | Tests fail (RED) |
| 1.2 | Add URL routes and view stubs | S | Tests pass (GREEN) |
| 1.3 | Create `feature_page_hero.html` component | M | Reusable hero with configurable headline, subhead, badge |
| 1.4 | Create `feature_screenshot.html` component | M | Terminal-style frame matching landing page aesthetic |
| 1.5 | Update sitemap with new pages | S | All 3 new pages in sitemap |

### Phase 2: Dashboard Page
**Goal:** Create `/features/dashboard/` with CTO-focused content

| Task | Description | Effort | Acceptance Criteria |
|------|-------------|--------|---------------------|
| 2.1 | Write Playwright test for dashboard page | S | Test fails - page doesn't exist |
| 2.2 | Create dashboard template with hero | M | Hero renders with correct copy |
| 2.3 | Add Weekly Report section | S | Section with screenshot placeholder |
| 2.4 | Add AI Insights section | S | Section with screenshot placeholder |
| 2.5 | Add Needs Attention section | S | Section with screenshot placeholder |
| 2.6 | Add Unified View section | S | Section with screenshot placeholder |
| 2.7 | Add CTA section | S | Reuses `cta_terminal.html` |
| 2.8 | Verify with Playwright | S | Test passes |

### Phase 3: Analytics Page
**Goal:** Create `/features/analytics/` with 6 scrollable sections

| Task | Description | Effort | Acceptance Criteria |
|------|-------------|--------|---------------------|
| 3.1 | Write Playwright test for analytics page | S | Test fails |
| 3.2 | Create analytics template with hero | M | Hero renders correctly |
| 3.3 | Add Overview section (#overview) | S | Anchor link works |
| 3.4 | Add AI Adoption section (#ai-adoption) | S | Anchor link works |
| 3.5 | Add Delivery section (#delivery) | S | Anchor link works |
| 3.6 | Add Quality section (#quality) | S | Anchor link works |
| 3.7 | Add Team section (#team) | S | Anchor link works |
| 3.8 | Add Trends section (#trends) | S | Anchor link works |
| 3.9 | Add CTA section | S | Reuses component |
| 3.10 | Verify with Playwright | S | Test passes, all anchors work |

### Phase 4: PR Explorer Page
**Goal:** Create `/features/pr-explorer/`

| Task | Description | Effort | Acceptance Criteria |
|------|-------------|--------|---------------------|
| 4.1 | Write Playwright test for PR explorer | S | Test fails |
| 4.2 | Create PR explorer template with hero | M | Hero renders correctly |
| 4.3 | Add Advanced Filters section | S | Screenshot placeholder |
| 4.4 | Add AI Detection section | S | Screenshot placeholder |
| 4.5 | Add User Notes section | S | Screenshot placeholder |
| 4.6 | Add CSV Export section | S | Screenshot placeholder |
| 4.7 | Add CTA section | S | Reuses component |
| 4.8 | Verify with Playwright | S | Test passes |

### Phase 5: Navigation Update
**Goal:** Transform dropdown into wide mega-menu

| Task | Description | Effort | Acceptance Criteria |
|------|-------------|--------|---------------------|
| 5.1 | Write Playwright test for nav dropdown | S | Test fails - old structure |
| 5.2 | Update desktop dropdown (3-column) | L | 500px wide, all links correct |
| 5.3 | Update mobile nav (accordion) | M | Same structure, collapsible |
| 5.4 | Verify all nav links with Playwright | M | All links navigate correctly |

### Phase 6: Hub Page Update
**Goal:** Transform `/features/` into navigation hub

| Task | Description | Effort | Acceptance Criteria |
|------|-------------|--------|---------------------|
| 6.1 | Add feature cards section | M | 3 cards linking to subpages |
| 6.2 | Condense AI Impact section | S | Shorter, links to analytics |
| 6.3 | Condense Team Performance section | S | Shorter, links to analytics |
| 6.4 | Keep Integrations as-is | - | No change needed |
| 6.5 | Final Playwright verification | M | All pages, links, mobile work |

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Copy doesn't resonate with CTOs | High | Follow writing-well skill, test with real CTOs |
| Screenshots delay launch | Medium | Use placeholder images, swap later |
| Mobile nav breaks | Medium | Test thoroughly with Playwright |
| SEO impact from URL changes | Low | No existing pages being moved |

---

## Success Metrics

1. **All Playwright tests pass** - pages render, links work, mobile works
2. **All 3 pages in sitemap** - verified via sitemap.xml
3. **No broken links** - navigation fully functional
4. **Mobile-friendly** - responsive at all breakpoints

---

## Technical Decisions

1. **Function-based views** - per CLAUDE.md guidelines
2. **Template inheritance** - all pages extend `web/base.html`
3. **Reusable components** - hero and screenshot components
4. **Alpine.js for nav** - consistent with existing dropdown
5. **No new Django apps** - all in `apps/web`

---

## Dependencies

- `apps/web/urls.py` - URL patterns
- `apps/web/views.py` - View functions
- `apps/web/sitemaps.py` - Sitemap config
- `templates/web/components/top_nav.html` - Navigation
- `templates/web/features.html` - Existing features page
