# Report Improvements V2 - Implementation Plan

**Last Updated: 2025-12-27**

---

## Executive Summary

This plan addresses 8 identified credibility risks in the AI Impact Research Report while capitalizing on Tformance's unique differentiation: **Code AI vs Review AI categorization**. The goal is to transform the report from a potentially controversial claim document into a credible, differentiated research piece that positions Tformance as the "behavioral reality" counterpoint to survey-based industry reports.

### Key Outcomes
1. Address all HIGH-risk credibility issues identified in critical review
2. Add Code AI vs Review AI analysis (unique differentiator)
3. Incorporate industry context (METR study, SO 2025, JetBrains 2025)
4. Improve statistical framing and add proper disclaimers
5. Create reusable data export pipeline for future reports

---

## Current State Analysis

### What Exists
- `docs/index.html` - Main research report (GitHub Pages)
- `docs/scripts/export_report_data.py` - Data export script
- `dev/active/report-critical-review.md` - 8 debate points identified
- `dev/active/report-improvements/` - Initial improvement context
- `apps/metrics/services/ai_categories.py` - Code AI vs Review AI categorization (NEW)

### Identified Issues (from Critical Review)

| Issue | Risk | Status |
|-------|------|--------|
| 1. Adoption gap (21% vs 84%) | HIGH | Partially addressed |
| 2. Missing Copilot/ChatGPT disclosure | HIGH | NOT addressed |
| 3. +42% cycle time causation | MEDIUM | Spun positively, needs disclaimer |
| 4. Agent metrics denominator | MEDIUM | NOT addressed |
| 5. Trust data missing | MEDIUM | NOT included |
| 6. "Sweet spot" claim | LOW | Stated as fact |
| 7. Selection bias | LOW | Mentioned briefly |
| 8. Detection accuracy | LOW | Overstated |

### Competitive Landscape (2025)

| Competitor | Approach | Our Advantage |
|------------|----------|---------------|
| Greptile | Ecosystem trends (PyPI/npm) | PR-level behavioral data |
| CodeRabbit | Quality metrics (issues/PR) | Team-specific insights |
| SO/JetBrains | Developer surveys | Actual behavior vs perception |
| METR | RCT (gold standard) | Scale (60k PRs vs 246 issues) |

---

## Proposed Future State

### Report Structure (Revised)

```
1. Executive Summary (unchanged)
2. Key Findings (revised with disclaimers)
3. NEW: Industry Context & Methodology Comparison
4. NEW: Code AI vs Review AI Analysis
5. Team Analysis (unchanged)
6. Tool Market Share (revised with detection caveats)
7. Monthly Trends (unchanged)
8. NEW: Quality Impact Analysis
9. Detection Method Analysis (expanded)
10. Methodology (expanded with limitations)
11. Actionable Insights (revised)
```

### New Sections to Add

#### A. Industry Context Section
- Comparison table: Our data vs SO 2025 vs JetBrains vs METR
- "What each metric measures" explanation
- "Behavioral vs Survey" positioning

#### B. Code AI vs Review AI Analysis
- Tool categorization breakdown
- Impact comparison by category
- Team adoption patterns by category

#### C. Quality Impact Analysis
- Revert rate by AI category
- Hotfix rate by AI category
- Review iterations by AI category

---

## Implementation Phases

### Phase 1: Data Pipeline Updates (Effort: M)
Update export script to include Code AI vs Review AI categorization and quality metrics.

### Phase 2: Methodology & Disclaimers (Effort: S)
Add statistical disclaimers and methodology transparency throughout.

### Phase 3: Industry Context Section (Effort: M)
Create new section comparing our approach to industry surveys.

### Phase 4: Code AI vs Review AI Analysis (Effort: L)
Add the unique differentiating section with proper visualizations.

### Phase 5: Quality Metrics (Effort: M)
Add revert/hotfix analysis by AI category.

### Phase 6: Visual & UX Improvements (Effort: S)
Charts, tables, and responsive improvements.

---

## Detailed Tasks

### Phase 1: Data Pipeline Updates

#### Task 1.1: Add AI Category to Export Script
**Effort:** S | **Priority:** P0 | **Dependencies:** None

Update `docs/scripts/export_report_data.py` to include:
- `ai_category` (code/review/both/none) per PR
- Tool categorization in tool breakdown
- Category-level aggregations

**Acceptance Criteria:**
- [ ] Export includes `ai_category` field
- [ ] New CSV: `ai_category_summary.csv`
- [ ] Tool breakdown includes category column

#### Task 1.2: Add Quality Metrics to Export
**Effort:** M | **Priority:** P1 | **Dependencies:** 1.1

Add quality metrics to data export:
- Revert rate by AI status and category
- Hotfix rate by AI status and category
- Review rounds by AI category

**Acceptance Criteria:**
- [ ] New CSV: `quality_by_ai_category.csv`
- [ ] Revert/hotfix rates calculated correctly
- [ ] Statistical significance indicators included

#### Task 1.3: Add Detection Method Comparison
**Effort:** S | **Priority:** P1 | **Dependencies:** None

Export data comparing LLM vs Pattern detection by AI category.

**Acceptance Criteria:**
- [ ] Breakdown of detection methods by category
- [ ] LLM-only vs Pattern-only counts by tool type

---

### Phase 2: Methodology & Disclaimers

#### Task 2.1: Add Causation Disclaimers
**Effort:** S | **Priority:** P0 | **Dependencies:** None

Add disclaimers to cycle time and review time claims:
- "Correlation, not causation" boxes
- Alternative explanations listed
- Simpson's Paradox reference

**Acceptance Criteria:**
- [ ] All comparative claims have disclaimers
- [ ] Warning box component created
- [ ] Applied to cycle time, review time, PR size sections

#### Task 2.2: Add Detection Limitations Section
**Effort:** S | **Priority:** P0 | **Dependencies:** None

Add explicit disclosure about:
- Silent tools (Copilot autocomplete) underdetected
- Tool rankings reflect detectability, not market share
- False negative rate unknown

**Acceptance Criteria:**
- [ ] "Detection Limitations" callout box added
- [ ] Copilot/ChatGPT gap explicitly mentioned
- [ ] "What we can vs cannot measure" table

#### Task 2.3: Expand Methodology Section
**Effort:** M | **Priority:** P1 | **Dependencies:** 2.1, 2.2

Rewrite methodology to include:
- Data collection process
- Detection method details
- Sample characteristics and limitations
- Statistical approach

**Acceptance Criteria:**
- [ ] Methodology section doubled in length
- [ ] All 8 critique points addressed somewhere
- [ ] Sample bias explicitly discussed

---

### Phase 3: Industry Context Section

#### Task 3.1: Create Industry Comparison Table
**Effort:** M | **Priority:** P0 | **Dependencies:** None

Add visual comparison of:
- Stack Overflow 2025 (84% adoption, 46% distrust)
- JetBrains 2025 (85% use AI, 88% save time)
- METR 2025 (19% slower in RCT)
- Our data (21% detected, +42% cycle time)

**Acceptance Criteria:**
- [ ] Side-by-side comparison table
- [ ] "What each measures" explanations
- [ ] Visual distinction between survey vs behavioral data

#### Task 3.2: Add METR Study Context
**Effort:** S | **Priority:** P1 | **Dependencies:** 3.1

Highlight the METR RCT findings:
- Only randomized controlled trial in the space
- 19% slower with AI (contradicts surveys)
- 43-point perception gap

**Acceptance Criteria:**
- [ ] METR study cited with link
- [ ] Key finding highlighted in callout
- [ ] Implications for interpreting survey data discussed

#### Task 3.3: Position "Behavioral Reality" Angle
**Effort:** S | **Priority:** P1 | **Dependencies:** 3.1, 3.2

Frame our data as complementary to surveys:
- Surveys = what developers think/believe
- Our data = what actually happens in PRs
- Both are valuable, different perspectives

**Acceptance Criteria:**
- [ ] "Behavioral vs Perception" framing throughout
- [ ] Clear positioning statement in intro
- [ ] No dismissal of survey data, just differentiation

---

### Phase 4: Code AI vs Review AI Analysis

#### Task 4.1: Create AI Category Overview
**Effort:** M | **Priority:** P0 | **Dependencies:** 1.1

Add section explaining the categorization:
- Code AI: Tools that write/generate code (Cursor, Copilot, Claude)
- Review AI: Tools that review/comment (CodeRabbit, Greptile)
- Mixed: Tools that do both (Ellipsis, Bito)

**Acceptance Criteria:**
- [ ] Clear definitions with examples
- [ ] Visual tool categorization chart
- [ ] Explanation of why this matters

#### Task 4.2: Add Category Adoption Analysis
**Effort:** M | **Priority:** P0 | **Dependencies:** 4.1, 1.1

Show adoption patterns by category:
- Overall: X% Code AI, Y% Review AI, Z% Both
- Trend over time by category
- Team-level category preferences

**Acceptance Criteria:**
- [ ] Pie/doughnut chart of category breakdown
- [ ] Time series by category
- [ ] Team heatmap by category

#### Task 4.3: Add Category Impact Comparison
**Effort:** L | **Priority:** P0 | **Dependencies:** 4.2, 1.2

Compare metrics by AI category:
- Cycle time: Code AI vs Review AI vs Both vs None
- Review time: Same breakdown
- PR size: Same breakdown

**Acceptance Criteria:**
- [ ] Comparison bar charts
- [ ] Statistical significance indicators
- [ ] Clear insights derived

#### Task 4.4: Add Category Insights Section
**Effort:** M | **Priority:** P1 | **Dependencies:** 4.3

Derive actionable insights:
- "Teams using both categories show X% faster reviews"
- "Review AI adds process overhead but catches issues"
- "Code AI correlates with larger PRs"

**Acceptance Criteria:**
- [ ] 3-5 key insights specific to categories
- [ ] Each insight has data backing
- [ ] Actionable recommendations for CTOs

---

### Phase 5: Quality Metrics

#### Task 5.1: Add Revert Rate Analysis
**Effort:** M | **Priority:** P1 | **Dependencies:** 1.2

Analyze revert rates by AI category:
- Overall revert rate
- Revert rate: AI vs non-AI
- Revert rate: Code AI vs Review AI vs Both

**Acceptance Criteria:**
- [ ] Revert rate chart by category
- [ ] Statistical comparison with confidence intervals
- [ ] Insight on quality implications

#### Task 5.2: Add Hotfix Rate Analysis
**Effort:** S | **Priority:** P2 | **Dependencies:** 5.1

Same analysis for hotfix rates.

**Acceptance Criteria:**
- [ ] Hotfix rate chart by category
- [ ] Comparison to revert rate patterns

#### Task 5.3: Add Review Friction Analysis
**Effort:** M | **Priority:** P2 | **Dependencies:** 1.2

Analyze review metrics by AI category:
- Review rounds
- Comments per PR
- Time to first approval

**Acceptance Criteria:**
- [ ] Review friction metrics by category
- [ ] Insight on whether AI increases review burden

---

### Phase 6: Visual & UX Improvements

#### Task 6.1: Create Warning/Caveat Component
**Effort:** S | **Priority:** P0 | **Dependencies:** None

Create reusable UI component for disclaimers:
- Yellow/amber background
- Clear icon indicator
- Consistent styling

**Acceptance Criteria:**
- [ ] CSS class defined
- [ ] Used consistently throughout report

#### Task 6.2: Add Category Color Scheme
**Effort:** S | **Priority:** P1 | **Dependencies:** 4.1

Define consistent colors for AI categories:
- Code AI: Orange (primary)
- Review AI: Teal (secondary)
- Both: Purple
- None: Gray

**Acceptance Criteria:**
- [ ] Color constants defined
- [ ] Applied to all category charts

#### Task 6.3: Mobile Responsiveness Check
**Effort:** S | **Priority:** P2 | **Dependencies:** All above

Ensure new sections work on mobile:
- Tables scroll horizontally
- Charts resize appropriately
- Callout boxes stack properly

**Acceptance Criteria:**
- [ ] All new content mobile-tested
- [ ] No horizontal overflow issues

---

## Risk Assessment

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Data export script breaks | Medium | High | Add tests before modifying |
| Statistical claims challenged | Medium | High | Add all disclaimers upfront |
| Code AI vs Review AI data insufficient | Low | Medium | Validate sample sizes first |
| Report becomes too long | Medium | Low | Add collapsible sections |
| Industry context section dated | Low | Medium | Add "as of Dec 2025" dates |

---

## Success Metrics

| Metric | Target | Measurement |
|--------|--------|-------------|
| All 8 critique points addressed | 100% | Manual review |
| New sections added | 3+ | Section count |
| Disclaimers added | 5+ | Warning box count |
| Code AI vs Review AI analysis | Complete | Section exists with data |
| Statistical rigor improved | Qualitative | External review |

---

## Dependencies

### Internal
- `apps/metrics/services/ai_categories.py` - Must be complete (✅ DONE)
- `docs/scripts/export_report_data.py` - Base for updates
- Database with 2025 PR data

### External
- Stack Overflow 2025 survey data (public)
- JetBrains 2025 survey data (public)
- METR study findings (public)

---

## Timeline Estimate

| Phase | Effort | Dependencies | Estimate |
|-------|--------|--------------|----------|
| Phase 1: Data Pipeline | M | None | 2-3 hours |
| Phase 2: Disclaimers | S | None | 1-2 hours |
| Phase 3: Industry Context | M | None | 2-3 hours |
| Phase 4: Code AI vs Review AI | L | Phase 1 | 4-6 hours |
| Phase 5: Quality Metrics | M | Phase 1 | 2-3 hours |
| Phase 6: Visual/UX | S | All above | 1-2 hours |

**Total Estimate: 12-19 hours**

---

## Next Steps

1. Validate Phase 1 data requirements with current database
2. Begin with Phase 2 (disclaimers) as quick wins
3. Run export script to verify data availability for Phase 4
4. Create draft of Industry Context section for review
