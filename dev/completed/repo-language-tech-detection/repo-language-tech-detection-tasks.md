# Repository-Aware Technology Detection - Tasks

**Last Updated: 2025-12-25**

---

## Phase 1: Baseline Measurement ✅ COMPLETE

**Goal**: Measure current pattern accuracy vs LLM ground truth

### 1.1 Data Validation ✅
- [x] Verified PRs with LLM summary: **16,996 PRs**
- [x] Verified repos with language stats: **43 repos** (fetched from GitHub API)
- [x] Verified files with "javascript" category: **31,127 files**
- [x] Confirmed languages JSON populated for all seeded repos

### 1.2 Baseline Analysis Script ✅
- [x] Created `analyze_baseline.py` (standalone script, not management command)
- [x] Implemented baseline metrics calculation
- [x] Calculated per-category accuracy
- [x] Generated confusion matrix
- [x] Exported results to `baseline_results.json`

### 1.3 Baseline Results ✅

| Metric | Value |
|--------|-------|
| Total files analyzed | 185,222 |
| Overall accuracy | **55.5%** |
| "javascript" precision | **29.1%** |
| "javascript" files | 31,127 |

**"javascript" Confusion Matrix:**
- 43.1% should be `frontend` (13,416 files)
- 29.1% correctly `javascript` (9,045 files)
- 27.8% should be `backend` (8,666 files)

**Decision**: Precision (29.1%) < 80% → PROCEED to Phase 2

---

## Phase 2: Enhanced Detector Implementation ✅ COMPLETE

**Goal**: Implement repo-aware categorization function

### 2.1 Implementation ✅
- [x] Created `analyze_enhanced.py` with `categorize_file_with_repo_context()`
- [x] Implemented language percentage calculation
- [x] Implemented backend-dominant detection
- [x] Implemented frontend-dominant detection
- [x] Added fallback for missing repo languages

### 2.2 Enhanced Analysis Results ✅

| Threshold | Baseline | Enhanced | Improvement |
|-----------|----------|----------|-------------|
| 50% | 55.5% | 58.0% | **+2.5%** |
| 60% | 55.5% | 57.9% | +2.4% |
| 70% | 55.5% | 57.9% | +2.4% |
| 80% | 55.5% | 57.5% | +2.0% |
| 90% | 55.5% | 57.4% | +2.0% |

**Reclassification Analysis (t=50%):**
- Correctly reclassified: 13,635 (43.8%)
- Incorrectly reclassified: 17,489 (56.2%)

**Decision**: Improvement (+2.5%) < 10% target → **DO NOT PROCEED** to Phase 4

---

## Phase 3: Threshold Optimization ✅ COMPLETE

### 3.1 Threshold Sweep Results ✅

Best threshold: **50%** (max improvement of +2.5%)

However, even at best threshold:
- Reclassification accuracy only 43.8%
- We're correct 43% of the time, wrong 57%

### 3.2 Root Cause Analysis ✅

The enhancement fails because repo language stats alone cannot distinguish:

1. **Frontend JS/TS in TS-dominant repo** → correctly reclassified to "frontend" ✓
2. **Backend services in TS-dominant repo** → incorrectly reclassified to "frontend" ✗
3. **Ambiguous utility code** → over-reclassified, should stay "javascript" ✗

The LLM uses additional context (file paths, content, PR description) that repo stats can't capture.

---

## Phase 4: Integration ❌ SKIPPED

**Reason**: Improvement (+2.5%) below 10% threshold. Enhancement not worth the complexity.

---

## Experiment Conclusion

### Findings

1. **Baseline accuracy is low (55.5%)** due to fundamental mismatch between file-level categorization and PR-level LLM analysis
2. **"javascript" category precision (29.1%)** is poor because pattern detection doesn't consider file content
3. **Repo language stats provide minimal improvement (+2.5%)** because they can't distinguish between frontend vs backend JS/TS
4. **LLM uses richer context** (PR description, file paths, content patterns) that simple repo stats can't replicate

### Recommendations

1. **Keep current pattern detection** for instant, free categorization
2. **Rely on LLM for accurate tech detection** in dashboard displays
3. **Consider file content analysis** if higher accuracy needed (would require reading file diffs)
4. **Don't pursue repo language enhancement** - insufficient ROI

### Files Created

| File | Purpose |
|------|---------|
| `fetch_repo_languages.py` | Fetches GitHub API language stats |
| `analyze_baseline.py` | Baseline accuracy analysis |
| `analyze_enhanced.py` | Enhanced analysis with threshold sweep |
| `repo_languages.json` | Cached language data for 43 repos |
| `baseline_results.json` | Baseline metrics |
| `enhanced_results_t*.json` | Per-threshold results |
| `threshold_sweep_results.json` | Summary of all thresholds |

---

## Quick Reference Commands

```bash
# Run baseline analysis
python dev/active/repo-language-tech-detection/analyze_baseline.py

# Run enhanced analysis with threshold sweep
python dev/active/repo-language-tech-detection/analyze_enhanced.py --sweep

# Run enhanced analysis with specific threshold
python dev/active/repo-language-tech-detection/analyze_enhanced.py --threshold 70
```
