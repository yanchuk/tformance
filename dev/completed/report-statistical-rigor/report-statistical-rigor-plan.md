# AI Impact Report Statistical Rigor Improvements

**Last Updated: 2025-12-28**

## Executive Summary

Address critical review feedback from colleagues to improve the AI Impact Report's statistical methodology, data consistency, and transparency. This makes the report defensible under rigorous academic/statistical scrutiny.

**Pre-requisite Completed:** Template refactor is done. The report now uses Jinja2 templates:
- `docs/templates/base.html.j2` - HTML skeleton
- `docs/templates/content.html.j2` - All HTML sections (~1340 lines)
- `docs/templates/scripts.js.j2` - All JavaScript (~890 lines)
- `docs/templates/styles.css.j2` - All CSS (~1350 lines)
- `docs/scripts/build_report.py` - Template renderer
- `docs/scripts/export_report_data.py` - Data exporter

---

## Current State Analysis

### Data Discrepancies Found

| Issue | Report Says | Actual Value | Source |
|-------|-------------|--------------|--------|
| Companies | 100 | 101 | DB query: 101 OSS teams |
| Code AI mentions | 6,625 | 6,633 | ai_categories.csv |
| Baseline PRs | 111,200 | 111,215 | category_metrics.csv |
| LLM-regex agreement | 96.1% | 93.4% | DB query: 99,952/107,071 |

### Statistical Issues Identified

1. **Extreme Distribution Skew** - Mean ≠ representative value
   - Baseline: Mean 82.2h vs Median 5.7h (14x skew)
   - Code AI: Mean 92.2h vs Median 10.4h (9x skew)
   - Review AI: Mean 71.4h vs Median 5.4h (13x skew)

2. **Confounding Variables** - PR size affects cycle time
   - AI PRs are 30% smaller on average
   - Need size-normalized metrics

3. **Simpson's Paradox Risk** - Aggregate hides team-level reality
   - Within-team analysis: 57% teams show AI slower, 43% faster

4. **Missing Data Pipeline Docs** - 167k → 125k unexplained
   - 5,346 PRs from teams <500 PRs excluded
   - 36,290 unmerged PRs excluded from cycle time

5. **False Positives** - LLM hallucinations
   - `playwright` (1 PR) - LLM hallucination
   - `rolldown-vite` (1 PR) - LLM hallucination

---

## Implementation Phases

### Phase S1: Data Consistency Fixes (P0)
**Effort: S | Priority: P0**

Fix all count mismatches between report text and CSV data.

**Tasks:**
1. Update `content.html.j2` to use template variables from CSVs
2. Update `docs/report_data_for_llms.md` with correct numbers
3. Change LLM-regex agreement from 96.1% to 93.4%
4. Run `make build-report` and verify

**Files to modify:**
- `docs/templates/content.html.j2`
- `docs/report_data_for_llms.md`

---

### Phase S2: Add Median Statistics (P0)
**Effort: M | Priority: P0**

Add median calculations to address extreme distribution skew.

**Implementation:**

1. Modify `docs/scripts/export_report_data.py`:
   - Add `PERCENTILE_CONT(0.5)` to SQL queries
   - Calculate medians for cycle_time, review_time, size
   - Export new columns to category_metrics.csv

2. Update CSV schema:
```csv
category,count,avg_cycle_hours,median_cycle_hours,avg_review_hours,median_review_hours,avg_size,median_size,cycle_delta_pct,review_delta_pct
```

3. Update `content.html.j2` to show both mean and median
4. Add "Distribution Note" explaining why medians matter

**Expected Results:**
| Category | Mean Cycle | Median Cycle | Skew |
|----------|------------|--------------|------|
| Baseline | 82.2h | 5.7h | 14x |
| Code AI | 92.2h | 10.4h | 9x |
| Review AI | 71.4h | 5.4h | 13x |

---

### Phase S3: Document Data Pipeline (P0)
**Effort: S | Priority: P0**

Explain where the 41k "missing" PRs went.

**Data Funnel:**
```
167,308 total PRs (all OSS companies)
  ├── 5,346 excluded: teams with <500 PRs
  │
  └── 161,962 from teams with 500+ PRs
        ├── 36,290 excluded: unmerged (no cycle_time)
        │
        └── 125,672 merged PRs
              └── This is category_metrics.csv
```

**Implementation:**
1. Add "Data Pipeline" section to `content.html.j2`
2. Add visual funnel diagram (ASCII or simple HTML)
3. Explain why unmerged PRs excluded from timing analysis

---

### Phase S4: Add Size-Normalized Metrics (P1)
**Effort: M | Priority: P1**

Address confounding variable (PR size) criticism.

**Implementation:**

1. Add to `export_report_data.py`:
```python
def export_normalized_metrics():
    """Export size-normalized review time."""
    # SQL: AVG(review_time_hours * 100.0 / NULLIF(additions + deletions, 0))
```

2. Create `docs/data/normalized_metrics.csv`:
```csv
category,count,review_hours_per_100_lines,vs_baseline_pct
none,111215,321.4,
code,3056,264.3,-18
review,11302,123.1,-62
```

3. Add "Size-Normalized Analysis" section to `content.html.j2`

**Expected Results:**
| Category | Review Hours/100 Lines | vs Baseline |
|----------|------------------------|-------------|
| Baseline | 321.4 | — |
| Code AI | 264.3 | **-18%** |
| Review AI | 123.1 | **-62%** |

---

### Phase S5: Add Within-Team Analysis (P1)
**Effort: M | Priority: P1**

Address Simpson's Paradox concern with team-level analysis.

**Implementation:**

1. Add to `export_report_data.py`:
```python
def export_within_team_analysis():
    """Compare AI vs non-AI within same teams."""
    # Filter: teams with 10+ PRs in BOTH groups
    # Compare avg cycle time for AI vs non-AI within each team
```

2. Create `docs/data/within_team_comparison.csv`:
```csv
team,ai_cycle_hours,non_ai_cycle_hours,ai_is_faster
TeamA,45.2,38.1,false
TeamB,12.5,18.9,true
...
```

3. Add "Within-Team Comparison" section to `content.html.j2`

**Expected Findings:**
| Metric | Value |
|--------|-------|
| Teams with both AI & non-AI PRs | 42 |
| Teams where AI is faster | 18 (43%) |
| Teams where AI is slower | 24 (57%) |

---

### Phase S6: Add Confidence Intervals (P1)
**Effort: L | Priority: P1**

Add statistical rigor to key claims.

**Implementation:**

1. Add bootstrap CI function to `export_report_data.py`:
```python
import numpy as np

def calculate_bootstrap_ci(data, n_bootstrap=1000, confidence=0.95):
    """Return (mean, lower, upper) CI bounds."""
    samples = np.random.choice(data, (n_bootstrap, len(data)), replace=True)
    means = samples.mean(axis=1)
    lower = np.percentile(means, (1 - confidence) / 2 * 100)
    upper = np.percentile(means, (1 + confidence) / 2 * 100)
    return data.mean(), lower, upper
```

2. Calculate CIs for:
   - Cycle time delta (Code AI vs baseline)
   - Cycle time delta (Review AI vs baseline)
   - Review time deltas

3. Add CI columns to `category_metrics.csv`:
```csv
category,...,cycle_delta_pct,cycle_delta_ci_lower,cycle_delta_ci_upper
```

4. Display as ± ranges in tables or error bars in charts

---

### Phase S7: Transparency Improvements (P2)
**Effort: S | Priority: P2**

Add caveats and fix documentation issues.

**Sub-tasks:**

1. **METR Comparison Caveat**
   - Add explicit disclaimer about different study designs
   - METR: RCT (randomized controlled trial) → causal
   - This report: Observational → correlation, not causation
   - Location: Industry Comparison section

2. **False Positives Documentation**
   - Add `playwright`, `rolldown-vite` to EXCLUDED_TOOLS
   - Document 0.01% LLM hallucination rate (2/167,308)
   - File: `apps/metrics/services/ai_categories.py`

3. **Fix Ellipsis Categorization**
   - Report says "review" but code says "code" (via MIXED_TOOLS)
   - Update report text to match code

4. **Correct Agreement Rate**
   - Change 96.1% to 93.4% everywhere
   - Files: `content.html.j2`, `report_data_for_llms.md`

---

## Files to Modify

### Export Script & Data
| File | Changes |
|------|---------|
| `docs/scripts/export_report_data.py` | Add median, CI, normalized, within-team functions |
| `docs/data/category_metrics.csv` | Add median columns, regenerate |
| `docs/data/normalized_metrics.csv` | **New file** |
| `docs/data/within_team_comparison.csv` | **New file** |

### Templates
| File | Changes |
|------|---------|
| `docs/templates/content.html.j2` | Update stats, add new sections |
| `docs/templates/scripts.js.j2` | Add charts for new data if needed |

### Application Code
| File | Changes |
|------|---------|
| `apps/metrics/services/ai_categories.py` | Add false positives to EXCLUDED_TOOLS |

### Documentation
| File | Changes |
|------|---------|
| `docs/report_data_for_llms.md` | Update all stats, add new sections |

---

## Success Criteria

1. ✅ Template refactor complete (prerequisite)
2. [ ] All count discrepancies fixed (101 companies, 6633 code mentions, etc.)
3. [ ] Median statistics shown alongside means in tables
4. [ ] Data pipeline documented (167k → 125k funnel explained)
5. [ ] Size-normalized metrics show Review AI advantage persists (-62%)
6. [ ] Within-team analysis shows 57%/43% split
7. [ ] 95% confidence intervals on key deltas
8. [ ] METR caveat explicit about RCT vs observational
9. [ ] LLM-regex agreement corrected to 93.4%
10. [ ] False positives (playwright, rolldown-vite) added to EXCLUDED_TOOLS

---

## Risk Assessment

| Risk | Impact | Mitigation |
|------|--------|------------|
| Median calculations slow on 167k PRs | Low | Use SQL PERCENTILE_CONT (fast) |
| Bootstrap CI computation slow | Medium | Sample 10k PRs, cache results |
| New sections break page layout | Low | Test in browser before commit |
| Within-team analysis changes conclusions | High | Present transparently as nuance |

---

## Dependencies

- Python 3.12 with Django
- PostgreSQL database with 167k PRs
- NumPy for bootstrap CI calculations
- Jinja2 for template rendering (already in use)

---

## Estimated Effort

| Phase | Priority | Effort | Est. Time |
|-------|----------|--------|-----------|
| S1. Data Consistency | P0 | S | 30 min |
| S2. Median Statistics | P0 | M | 1 hour |
| S3. Data Pipeline Docs | P0 | S | 30 min |
| S4. Normalized Metrics | P1 | M | 1 hour |
| S5. Within-Team Analysis | P1 | M | 1.5 hours |
| S6. Confidence Intervals | P1 | L | 2 hours |
| S7. Transparency | P2 | S | 1 hour |
| **Total** | — | — | **~7.5 hours** |

---

## Next Steps

1. Start with Phase S1 (data consistency) - quick wins
2. Complete P0 phases (S1-S3) first
3. Then P1 phases (S4-S6) for statistical rigor
4. Finally P2 (S7) for transparency improvements
5. Regenerate all CSVs with `python docs/scripts/export_report_data.py`
6. Rebuild report with `make build-report`
7. Visual review in browser
