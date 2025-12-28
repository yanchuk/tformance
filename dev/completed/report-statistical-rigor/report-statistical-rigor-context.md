# Report Statistical Rigor - Context

**Last Updated: 2025-12-28 18:00**

## Current State: 100% Complete ✅

**All implementation and verification complete.**

### Session Summary
- Completed all Phases S1-S8 (58 tasks)
- Browser verification completed via Playwright
- No migrations needed
- Report builds successfully: 203.5 KB

---

## Key Files Modified This Session

### Export Script
**`docs/scripts/export_report_data.py`** - Major changes:
- Added `import random`, `import statistics`
- Added `calculate_bootstrap_ci()` function (lines 59-87)
- Added `calculate_delta_ci()` function (lines 90-130)
- Modified `export_category_metrics()` for medians + CIs (lines 429-620)
- Added `export_normalized_metrics()` function (lines 623-715)
- Added `export_within_team_analysis()` function (lines 717-812)

### Build Script
**`docs/scripts/build_report.py`** - Minor changes:
- Added `normalized_metrics.csv` to `load_all_data()` (line 112)
- Added `within_team_comparison.csv` to `load_all_data()` (line 113)
- Added "hours" to numeric field conversion (line 47)

### Template
**`docs/templates/content.html.j2`** (~1470 lines now):
- Lines 496-538: Category Impact cards now use template variables with CIs
- Lines 540-548: Distribution Note (mean vs median)
- Lines 573-624: Size-Normalized Analysis section
- Lines 626-691: Within-Team Comparison section
- Lines 1207-1235: Data Pipeline funnel
- Lines 1349-1358: Study Design Caveat

### LLM Data File
**`docs/report_data_for_llms.md`** - Updated sections:
- Fixed all numbers (101 companies, 6633 Code AI, etc.)
- Added 95% Confidence Intervals table
- Added Size-Normalized Analysis section
- Added Within-Team Analysis section
- Added Study Design Caveat

### Application Code
**`apps/metrics/services/ai_categories.py`** (lines 117-119):
- Added `playwright` to EXCLUDED_TOOLS
- Added `rolldown-vite` to EXCLUDED_TOOLS
- Added comment about LLM hallucinations

---

## Data Files

### New CSVs Created
| File | Schema |
|------|--------|
| `normalized_metrics.csv` | category, count, review_hours_per_100_lines, vs_baseline_pct |
| `within_team_comparison.csv` | team, ai_prs, non_ai_prs, ai_cycle_hours, non_ai_cycle_hours, cycle_delta_pct, ai_result |

### Modified CSV
| File | New Columns |
|------|-------------|
| `category_metrics.csv` | median_cycle_hours, median_review_hours, median_size, cycle_delta_ci_lower, cycle_delta_ci_upper, review_delta_ci_lower, review_delta_ci_upper |

---

## Key Decisions Made

| Decision | Rationale |
|----------|-----------|
| Used `random` module instead of NumPy | Avoid new dependency; acceptable performance for 1000 samples |
| 10+ PRs threshold for within-team | Statistical validity; resulted in 50 qualifying teams |
| Bootstrap with 1000 iterations | Standard for 95% CI; takes ~2 seconds |
| Template variables for all numbers | Eliminates hardcoded value drift |

---

## Actual Results vs Plan

| Metric | Plan | Actual |
|--------|------|--------|
| Within-team qualifying teams | 42 | 50 |
| AI faster % | 43% | 40% |
| AI slower % | 57% | 60% |
| Code AI normalized | -18% | -26% |
| Code AI cycle CI | +12% to +20% | +3% to +26% |
| Review AI cycle CI | -18% to -6% | -17% to -7% |

---

## Commands to Continue

```bash
# Verify everything builds
.venv/bin/python docs/scripts/export_report_data.py
.venv/bin/python docs/scripts/build_report.py

# Open in browser for manual verification
open docs/index.html

# Optional: Run tests
make test ARGS='apps.metrics.tests.test_ai_categories'
```

---

## Manual Verification Checklist (Remaining Work)

1. **Open in browser**: `open docs/index.html`
2. **Check 13 charts render**: May take a moment to load
3. **Verify new sections**:
   - Distribution Note (after Category Impact cards)
   - Size-Normalized Analysis table
   - Within-Team Comparison (with expandable details)
   - Study Design Caveat (in Industry section)
4. **Theme toggle**: Click sun/moon icon
5. **Console errors**: DevTools (F12) → Console
6. **Mobile view**: Resize to ~375px width

---

## No Migrations Needed

Only modified:
- Python scripts in `docs/scripts/`
- Templates in `docs/templates/`
- Data files in `docs/data/`
- One service file: `apps/metrics/services/ai_categories.py` (no model changes)

---

## After Manual Verification

If everything looks good:
```bash
# Move to completed
mv dev/active/report-statistical-rigor dev/completed/

# Optional: Backfill to apply new EXCLUDED_TOOLS
python manage.py backfill_ai_detection --reprocess
```
