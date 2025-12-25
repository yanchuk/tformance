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

## Phase 2: Enhanced Detector Implementation

**Goal**: Implement repo-aware categorization function

### 2.1 TDD: Write Tests First
- [ ] Create `apps/metrics/tests/test_repo_aware_categorization.py`
- [ ] Test: backend-dominant repo (95% Python) → JS files become "backend"
- [ ] Test: frontend-dominant repo (90% TS) → JS files become "frontend"
- [ ] Test: mixed repo (50/50) → JS files stay "javascript"
- [ ] Test: no repo languages → fallback to base categorization
- [ ] Test: empty languages dict → fallback to base categorization

### 2.2 Implementation
- [ ] Add `categorize_file_with_repo_context()` to `apps/metrics/models/github.py`
- [ ] Implement language percentage calculation
- [ ] Implement backend-dominant detection (threshold 70%)
- [ ] Implement frontend-dominant detection (threshold 70%)
- [ ] Run tests → all pass

### 2.3 Enhanced Analysis
- [ ] Add `--enhanced` flag to analysis script
- [ ] Calculate enhanced accuracy per category
- [ ] Calculate improvement over baseline
- [ ] Export results to CSV: `dev/active/repo-language-tech-detection/enhanced-results.csv`

### 2.4 Results Comparison
- [ ] Create comparison table: baseline vs enhanced
- [ ] Calculate per-repo improvement
- [ ] Identify repos with highest improvement
- [ ] Identify repos with no improvement or regression

**Acceptance Criteria**:
- Overall improvement > 10% on "javascript" files → proceed to Phase 3
- If improvement < 5% → document learnings, consider alternative approaches

---

## Phase 3: Threshold Optimization

**Goal**: Find optimal percentage threshold for repo language dominance

### 3.1 Threshold Sweep
- [ ] Run analysis with threshold = 60%
- [ ] Run analysis with threshold = 70%
- [ ] Run analysis with threshold = 80%
- [ ] Run analysis with threshold = 90%
- [ ] Calculate accuracy for each threshold

### 3.2 Per-Category Analysis
- [ ] Identify optimal threshold for backend-dominant repos
- [ ] Identify optimal threshold for frontend-dominant repos
- [ ] Check if different thresholds needed per category

### 3.3 Threshold Recommendation
- [ ] Document recommended threshold(s)
- [ ] Document trade-offs (coverage vs precision)
- [ ] Create threshold decision matrix

**Acceptance Criteria**:
- Clear optimal threshold identified (or small range)
- No significant regression at chosen threshold

---

## Phase 4: Integration (Conditional)

**Goal**: Integrate enhancement into production sync

### 4.1 Code Changes
- [ ] Update `PRFile.categorize_file()` signature to accept optional `repo_languages`
- [ ] Add backward compatibility (default None preserves existing behavior)
- [ ] Update `github_graphql_sync.py` to pass repo languages
- [ ] Update `github_sync.py` to pass repo languages

### 4.2 Testing
- [ ] Add integration tests for sync with repo languages
- [ ] Run full test suite → no regressions
- [ ] Test with real repo sync

### 4.3 Backfill (Optional)
- [ ] Create management command to recategorize existing files
- [ ] Run on subset (1 repo) first
- [ ] Verify dashboard displays correctly
- [ ] Run on full dataset

### 4.4 Documentation
- [ ] Update CLAUDE.md with new categorization behavior
- [ ] Document in `dev/completed/` when done

**Acceptance Criteria**:
- All tests pass
- Dashboard displays enhanced categories correctly
- No performance regression

---

## Quick Reference Commands

```bash
# Verify data availability
.venv/bin/python manage.py shell -c "
from apps.metrics.models import PullRequest, PRFile
from apps.integrations.models import TrackedRepository
print('PRs with LLM:', PullRequest.objects.filter(llm_summary__isnull=False).count())
print('Repos with langs:', TrackedRepository.objects.exclude(languages={}).count())
print('JS files:', PRFile.objects.filter(file_category='javascript').count())
"

# Run baseline analysis
.venv/bin/python manage.py analyze_tech_detection --baseline

# Run enhanced analysis
.venv/bin/python manage.py analyze_tech_detection --enhanced --threshold 70

# Compare results
.venv/bin/python manage.py analyze_tech_detection --compare

# Run tests
pytest apps/metrics/tests/test_repo_aware_categorization.py -v
```

---

## Decision Checkpoints

### After Phase 1
| Condition | Action |
|-----------|--------|
| "javascript" accuracy < 80% | Proceed to Phase 2 |
| "javascript" accuracy > 90% | Close task - pattern already good |
| Insufficient data | Expand dataset or close |

### After Phase 2
| Condition | Action |
|-----------|--------|
| Improvement > 10% | Proceed to Phase 3 |
| Improvement 5-10% | Evaluate cost/benefit |
| Improvement < 5% | Document learnings, close |

### After Phase 3
| Condition | Action |
|-----------|--------|
| Clear optimal threshold | Proceed to Phase 4 |
| Threshold varies wildly | Consider per-repo-type rules |
| No stable threshold | Close without integration |

---

## Results Tracking

### Phase 1 Results
| Metric | Value | Notes |
|--------|-------|-------|
| Total files analyzed | - | |
| "javascript" files | - | |
| Baseline accuracy (overall) | - | |
| Baseline accuracy (javascript only) | - | |
| Misclassification breakdown | - | |

### Phase 2 Results
| Metric | Baseline | Enhanced | Improvement |
|--------|----------|----------|-------------|
| Overall accuracy | - | - | - |
| JavaScript → Backend (correct) | - | - | - |
| JavaScript → Frontend (correct) | - | - | - |
| Regression count | - | - | - |

### Phase 3 Results
| Threshold | Accuracy | FP Rate | Best For |
|-----------|----------|---------|----------|
| 60% | - | - | - |
| 70% | - | - | - |
| 80% | - | - | - |
| 90% | - | - | - |
