# Report Reviewer Feedback Fixes

**Last Updated: 2025-12-28**

## Executive Summary

Address critical reviewer feedback from 3 independent reviews. Key issues:
1. **Data inconsistencies** between CSV files and report text
2. **CI values mismatch** - one crosses zero (not significant) but reported as significant
3. **Simpson's Paradox buried** - 60% teams slower but headline says -11% faster
4. **Causal language** from observational data

## User Decisions

Two clarification questions were asked and answered:
1. **CI Fix approach**: Add explicit 'n.s.' marker for non-significant Code AI review CI
2. **Median truth prominence**: Add prominent warning box about medians

---

## Critical Issues Identified

### Issue 1: Count Mismatches (P0)
| Location | Says | CSV Says | Diff |
|----------|------|----------|------|
| ai_categories.csv total | 25,209 (text) | 25,217 | -8 |
| Code AI count | 6,633 (text) | 6,631 | +2 |
| Unknown count | 50 (text) | 52 | -2 |

**Root Cause:** Hardcoded values in template/report don't match regenerated CSV.

### Issue 2: CI Mismatch - CRITICAL (P0)
| Metric | Report Says | CSV Says | Issue |
|--------|-------------|----------|-------|
| Code cycle CI | +3% to +27% | +4% to +25% | Different |
| Code review CI | **-31% to -1%** | **-32% to +1%** | **CROSSES ZERO!** |
| Review cycle CI | -18% to -6% | -18% to -7% | Minor |
| Review review CI | -61% to -50% | -60% to -49% | Minor |

**CRITICAL:** Code AI review time CI crosses zero (-32% to +1%) meaning NOT statistically significant!
Report says -31% to -1% which appears significant. This is a **misrepresentation**.

### Issue 3: Sample Size Confusion (P1)
| File | none | code | review | total |
|------|------|------|--------|-------|
| category_metrics.csv | 111,215 | 3,056 | 11,302 | 125,573 |
| normalized_metrics.csv | 96,903 | 3,502 | 12,290 | 112,695 |
| ai_categories.csv | — | 6,631 | 18,534 | 25,217 |

**Missing explanation:** Why do counts differ? (ai_categories = mentions, category_metrics = unique PRs, normalized = merged only)

### Issue 4: Simpson's Paradox Buried (P1)
- **Headline:** "Review AI -11% faster"
- **Reality:** 60% of individual teams show AI is SLOWER
- Current warning exists but is buried in "Within-Team" section

### Issue 5: Mean vs Median (P1)
- Means used for headlines with 14x skew (mean 82h vs median 5.7h)
- **Median shows Review AI is SLIGHTLY SLOWER** (6.0h vs 5.7h baseline)
- This contradicts the "Review AI is faster" narrative when using typical PR

### Issue 6: Causal Language (P2)
- "Deploy Review AI immediately" — from observational data
- Should use correlational language

---

## Implementation Plan

### Phase F1: Fix Data Inconsistencies (P0)
**Effort: S | Files: 3**

1. Regenerate `ai_categories.csv` to get authoritative counts
2. Update `report_data_for_llms.md` to match CSV exactly
3. Update `content.html.j2` hardcoded values (25,209 → use template var)

**Files:**
- `docs/scripts/export_report_data.py` - Verify export logic
- `docs/report_data_for_llms.md` - Fix counts
- `docs/templates/content.html.j2` - Replace hardcoded with template vars

### Phase F2: Fix CI Values - CRITICAL (P0)
**Effort: M | Files: 2**

1. Update report text to match CSV exactly
2. Add **explicit 'n.s.' marker** that Code AI review time is NOT statistically significant
3. Change color/presentation of non-significant results

**Key Change:** Code AI review time (-14%) must be marked as "n.s. (CI crosses zero)"

**Files:**
- `docs/report_data_for_llms.md` - Fix CI values, add significance note
- `docs/templates/content.html.j2` - Add visual indicator for non-significant

### Phase F3: Add Sample Size Explanations (P1)
**Effort: S | Files: 2**

Add clear explanation of why different files have different counts:

```
ai_categories.csv: 25,217 = TOOL MENTIONS (one PR can mention multiple tools)
category_metrics.csv: 14,358 = UNIQUE AI PRs (from merged PRs only)
normalized_metrics.csv: 15,792 = PRs with valid size data (>0 lines)
```

**Files:**
- `docs/report_data_for_llms.md` - Add "Understanding the Numbers" section
- `docs/templates/content.html.j2` - Add footnote to data tables

### Phase F4: Elevate Simpson's Paradox Warning (P1)
**Effort: M | Files: 2**

Move Simpson's Paradox from buried section to **prominent TL;DR warning**:

```
IMPORTANT: While aggregate data shows Review AI is 11% faster,
60% of individual teams show AI is SLOWER. Aggregate stats can mislead.
```

**Files:**
- `docs/report_data_for_llms.md` - Add to TL;DR section
- `docs/templates/content.html.j2` - Add alert box near headlines

### Phase F5: Address Mean vs Median Issue (P1)
**Effort: M | Files: 2**

**User chose: Prominent warning box**

Add prominent warning box with median comparison:
```
MEDIAN WARNING: The typical (median) PR shows different results:
- Baseline: 5.7 hours
- Code AI: 11.4 hours (+100% slower)
- Review AI: 6.0 hours (+5% slower)
Means are heavily influenced by long-tail outliers (14x skew factor).
```

**Files:**
- `docs/report_data_for_llms.md` - Expand Distribution Note
- `docs/templates/content.html.j2` - Add prominent warning box

### Phase F6: Soften Causal Language (P2)
**Effort: S | Files: 2**

Change:
- "Deploy Review AI immediately" → "Review AI correlates with faster cycles"
- "Use Code AI selectively" → "Code AI shows mixed correlations"

Add explicit disclaimer to recommendations section:
```
These are correlations from observational data, not causal findings.
Your results may vary based on team, codebase, and workflow.
```

**Files:**
- `docs/report_data_for_llms.md` - Revise recommendations
- `docs/templates/content.html.j2` - Update recommendation language

---

## Files to Modify

| File | Changes |
|------|---------|
| `docs/scripts/export_report_data.py` | Verify export produces consistent counts |
| `docs/report_data_for_llms.md` | Fix CIs, counts, add disclaimers |
| `docs/templates/content.html.j2` | Replace hardcoded values, add warnings |
| `docs/data/*.csv` | Regenerate if needed |

---

## Success Criteria

1. All numbers in report match CSV files exactly
2. Code AI review time clearly marked as non-significant (n.s.)
3. Simpson's Paradox warning visible in TL;DR
4. Median comparison in prominent warning box
5. Recommendations use "correlation" not "causation" language
6. LLM verification prompt gives grade B+ or higher
