# Report Reviewer Fixes - Context

**Last Updated: 2025-12-28**

## Key Files

### Primary Files to Modify
| File | Purpose |
|------|---------|
| `docs/report_data_for_llms.md` | LLM-readable report text - main content |
| `docs/templates/content.html.j2` | HTML template - visual report |
| `docs/templates/base.html.j2` | Base template - includes scripts |

### Data Source Files (Read-Only Reference)
| File | Purpose |
|------|---------|
| `docs/data/ai_categories.csv` | Tool mention counts (6631 code, 18534 review, 52 unknown) |
| `docs/data/category_metrics.csv` | CI values and aggregate stats |
| `docs/data/normalized_metrics.csv` | Size-normalized metrics |
| `docs/data/team_level_metrics.csv` | Per-team breakdown |

### Script Files
| File | Purpose |
|------|---------|
| `docs/scripts/export_report_data.py` | Generates CSV from DB |
| `docs/scripts/build_report.py` | Builds HTML from templates |

---

## Critical Data Points

### Correct CI Values (from category_metrics.csv)
```
Code AI:
- Cycle time: +15% (CI: +4% to +25%)
- Review time: -14% (CI: -32% to +1%) ← CROSSES ZERO = NOT SIGNIFICANT

Review AI:
- Cycle time: -11% (CI: -18% to -7%)
- Review time: -55% (CI: -60% to -49%)
```

### Correct Counts (from ai_categories.csv)
```
Code AI mentions: 6,631
Review AI mentions: 18,534
Unknown: 52
Total: 25,217
```

### Median Values (from category_metrics.csv)
```
Baseline: 5.7 hours
Code AI: 11.4 hours (+100% slower)
Review AI: 6.0 hours (+5% slower)
```

---

## User Decisions

1. **CI Fix approach**: Add explicit 'n.s.' marker for non-significant Code AI review CI
2. **Median truth prominence**: Add prominent warning box about medians telling different story

---

## Key Findings from Reviews

### Reviewer 1 (Statistical)
- CI mismatch between CSV and text
- Code AI review CI crosses zero (not significant)
- Simpson's Paradox not prominent enough

### Reviewer 2 (Data Consistency)
- Count mismatches: 25,209 vs 25,217
- Sample sizes differ across files without explanation

### Reviewer 3 (Methodology)
- Causal language from observational data
- Mean vs median issue with 14x skew
- Selection bias not addressed

---

## Dependencies

- No Django model changes needed
- No migrations needed
- Static HTML report generation only
- Build process: `python docs/scripts/build_report.py`
