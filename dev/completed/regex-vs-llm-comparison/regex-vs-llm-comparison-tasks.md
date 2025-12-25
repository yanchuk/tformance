# Regex vs LLM Detection Comparison - Tasks

**Last Updated: 2025-12-25**

## Research Objective

Determine whether LLM-based detection provides sufficient value over regex patterns.

---

## Phase 1: Data Collection ✅ COMPLETE

- [x] Run batch LLM analysis on 500+ PRs
- [x] Compute regex detection for same PRs
- [x] Initial comparison statistics

**Results**: 4,980 PRs analyzed (expanded from 787), 96.61% agreement

---

## Phase 2: AI Detection Accuracy ✅ COMPLETE

### 2.1 Analyze Discrepancies ✅
- [x] Review all 154 LLM-only detections (expanded from 27)
- [x] Categorize: true positive, false positive, ambiguous
- [x] Review 15 regex-only detections (expanded from 1)

### 2.2 Sample Verification ✅
- [x] Analyzed 4,980 PRs with confusion matrix
- [x] 6 sampling rounds of 50 PRs each (250+ manual reviews)
- [x] Documented disagreements and categorized

### 2.3 Edge Case Analysis ✅
- [x] Large PRs both agree NoAI - verified no obvious FNs
- [x] Bot-authored PRs - LLM correctly identifies
- [x] Product-context PRs - ai_generic causes FPs

### 2.4 Metrics Calculated ✅

**UPDATED METRICS (4,980 PRs, v1.9.0 patterns)**

| Metric | LLM | Regex (v1.9.0) | Winner |
|--------|-----|----------------|--------|
| Detection Rate | 26.41% | 23.43% | LLM (+2.98%) |
| Agreement | 96.62% | 96.62% | Tie |
| Est. Precision | ~91% | ~89% | **LLM** |
| Est. Recall | ~98% | ~89% | **LLM** |
| Regex FPs | N/A | 10 (was 15) | ✅ 33% reduction |

---

## Phase 3: Technology Detection Quality

### 3.1 Language Detection Accuracy
- [ ] Sample 100 PRs with LLM tech data
- [ ] Compare LLM languages vs actual file extensions
- [ ] Calculate accuracy percentage

### 3.2 Framework Detection Quality
- [ ] Sample 50 PRs with frameworks detected
- [ ] Verify against package.json, requirements.txt
- [ ] Note false positives/negatives

*Deferred - AI detection accuracy prioritized*

---

## Phase 4: PR Type Classification

### 4.1 Type Accuracy
- [ ] Sample 100 PRs with LLM summary.type
- [ ] Compare against PR title prefixes
- [ ] Calculate confusion matrix

*Deferred - AI detection accuracy prioritized*

---

## Phase 5: Health Assessment Value

- [ ] Compare LLM scope vs actual lines changed
- [ ] Sample PRs marked high/medium risk

*Deferred - AI detection accuracy prioritized*

---

## Phase 6: Cost-Benefit Analysis ✅ COMPLETE

### 6.1 Cost Calculation ✅
- [x] LLM cost per PR: ~$0.08/1000 PRs (Groq batch)
- [x] Regex cost: $0.00

### 6.2 Value Assessment ✅
- [x] LLM detects 2.8% more AI usage
- [x] Tech detection unique to LLM
- [x] Summaries and health metrics unique to LLM

### 6.3 Recommendation ✅ COMPLETE

**Decision: Use LLM as primary, regex as fallback**

---

## Implementation Phase - v1.9.0 ✅ COMPLETE

### Regex Pattern Improvements (P0) ✅ DONE
- [x] Improve `cubic` patterns (added commit markers) ✅
- [x] Add `greptile` pattern (bot + text) ✅
- [x] Review/modify `ai_generic` pattern (removed header patterns) ✅
- [x] Backfill all 5,654 PRs with v1.9.0 patterns ✅

**Results:**
- Regex FPs reduced from 15 → 10 (33% reduction)
- Agreement improved slightly: 96.61% → 96.62%

### Regex Pattern Improvements (P1) 🔄 FUTURE
- [ ] Add Cursor IDE patterns (+16 detections expected)
- [ ] Improve Copilot patterns (+27 detections expected)
- [ ] Add Claude patterns improvements (+46 detections expected)

### LLM Prompt Improvements 🔄 FUTURE
- [ ] Add "require explicit evidence" guidance
- [ ] Lower confidence when no tool identified
- [ ] Add product-context awareness

### Configuration Changes 🔄 FUTURE
- [ ] Set LLM confidence threshold to 0.90
- [ ] Document hybrid approach decision

---

## Success Criteria

| Metric | Target | Achieved |
|--------|--------|----------|
| Agreement Rate | >95% | 96.61% ✅ |
| LLM Precision | >90% | ~91% ✅ |
| LLM Recall | >85% | ~98% ✅ |
| Full analysis doc | Complete | ✅ RESEARCH-SYNTHESIS.md |

---

## Quick Reference

```bash
# View confusion matrix
.venv/bin/python manage.py shell -c "
from apps.metrics.models import PullRequest
from django.db.models import Count, Case, When, BooleanField
qs = PullRequest.objects.exclude(llm_summary__isnull=True)
print(f'Total: {qs.count()}')
print(f'Both AI: {qs.filter(is_ai_assisted=True).extra(where=[\"(llm_summary->'ai'->>'is_assisted')::boolean = true\"]).count()}')
"

# Run comparison report
cd dev/active/ai-detection-pr-descriptions/experiments
GROQ_API_KEY=\$GROQ_API_KEY npx promptfoo eval -c compare-detection.yaml
npx promptfoo view
```
