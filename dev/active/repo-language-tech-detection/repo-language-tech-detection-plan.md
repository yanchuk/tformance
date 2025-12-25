# Repository-Aware Technology Detection Experiment

**Last Updated: 2025-12-25**

---

## Executive Summary

Improve technology detection accuracy by incorporating GitHub repository language statistics into file categorization. Currently, `PRFile.categorize_file()` uses only file extensions and path patterns, ignoring repo context. A `.js` file in a 95% Python repo is likely tooling, not core frontend code.

**Hypothesis**: Incorporating repo language percentages will improve technology detection accuracy by 10-20% for ambiguous files (`.js`, `.ts`) compared to LLM-based detection.

**Success Criteria**:
- Measure baseline pattern accuracy vs LLM (ground truth)
- Demonstrate measurable improvement with repo-weighted detection
- Identify repos where enhancement provides most value

---

## 1. Current State Analysis

### 1.1 Pattern-Based Detection (`PRFile.categorize_file`)

**Location**: `apps/metrics/models/github.py:867-980`

**Current Categories**:
| Category | Description | Extensions/Patterns |
|----------|-------------|---------------------|
| `frontend` | Frontend code | `.jsx`, `.tsx`, `.vue`, `.css`, `/components/` |
| `backend` | Backend code | `.py`, `.go`, `.java`, `.rb`, `/api/`, `/services/` |
| `javascript` | Ambiguous JS/TS | `.js`, `.ts` (when path doesn't match FE/BE) |
| `test` | Test files | `/tests/`, `_test.`, `.spec.` |
| `docs` | Documentation | `.md`, `.rst`, `.txt` |
| `config` | Configuration | `.json`, `.yaml`, `.toml` |
| `other` | Uncategorized | Everything else |

**Problem**: `javascript` category is a catch-all for ambiguous files (2,847 files in dataset).

### 1.2 Repository Language Stats (`TrackedRepository.languages`)

**Location**: `apps/integrations/models.py:221-238`

**Available Data**:
```python
{
    "Python": 150000,      # bytes of Python code
    "JavaScript": 5000,    # bytes of JavaScript code
    "TypeScript": 0,       # etc.
}
```

**Already Fetched**: Via `github_repo_languages.py` service. Stored on `TrackedRepository`.

### 1.3 LLM-Based Detection

**Location**: `apps/metrics/prompts/templates/sections/tech_detection.jinja2`

**Output Schema** (`apps/metrics/prompts/schemas.py`):
```python
TECH_SCHEMA = {
    "languages": ["python", "typescript"],  # Programming languages
    "frameworks": ["django", "react"],       # Frameworks/libraries
    "categories": ["backend", "frontend"],   # High-level categories
}
```

**Advantage**: LLM considers full PR context (title, description, file paths, repo languages).

---

## 2. Proposed Enhancement

### 2.1 Core Algorithm: Repo-Weighted File Categorization

**New Function**: `categorize_file_with_repo_context(filename, repo_languages)`

```python
def categorize_file_with_repo_context(
    filename: str,
    repo_languages: dict[str, int] | None = None
) -> str:
    """Categorize file using extension + repo language distribution.

    Enhancement over base categorize_file():
    1. If base returns "javascript" (ambiguous), consult repo stats
    2. If repo is >70% Python/Go/Ruby, classify as backend (tooling)
    3. If repo is >70% JS/TS, check path for FE/BE heuristics
    """
    base_category = PRFile.categorize_file(filename)

    # Only enhance ambiguous cases
    if base_category != "javascript" or not repo_languages:
        return base_category

    # Calculate language percentages
    total_bytes = sum(repo_languages.values())
    if total_bytes == 0:
        return base_category

    percentages = {
        lang: (bytes_ / total_bytes) * 100
        for lang, bytes_ in repo_languages.items()
    }

    # Backend-dominant repos: JS/TS is likely tooling/build
    backend_langs = {"Python", "Go", "Ruby", "Java", "PHP", "Rust", "C#", "Kotlin"}
    backend_pct = sum(percentages.get(l, 0) for l in backend_langs)
    if backend_pct >= 70:
        return "backend"  # Reclassify as backend tooling

    # Frontend-dominant repos: JS/TS is likely frontend
    frontend_langs = {"JavaScript", "TypeScript", "CSS", "SCSS"}
    frontend_pct = sum(percentages.get(l, 0) for l in frontend_langs)
    if frontend_pct >= 70:
        # Additional path heuristics for FE-dominant repos
        filename_lower = filename.lower()
        if any(p in filename_lower for p in ["/api/", "/server/", "/backend/"]):
            return "backend"
        return "frontend"

    # Mixed repo: keep as ambiguous
    return "javascript"
```

### 2.2 Threshold Tuning

The 70% threshold is hypothesis-based. Experiment will test:
- 60%, 70%, 80%, 90% thresholds
- Different language groupings

### 2.3 Integration Points

| Location | Change | Purpose |
|----------|--------|---------|
| `PRFile.categorize_file()` | Add optional `repo_languages` param | Backward compatible |
| `github_graphql_sync.py` | Pass repo languages to categorize | Use during sync |
| `pr_list_service.py` | Re-annotate with enhanced categories | Dashboard display |

---

## 3. Experiment Design

### 3.1 Dataset

**Source**: Existing PRs with both:
1. `llm_summary.tech.categories` (LLM ground truth)
2. `TrackedRepository.languages` (repo stats)

**Query**:
```sql
SELECT COUNT(*) FROM metrics_pullrequest pr
JOIN integrations_trackedrepository r ON pr.repository_id = r.id
WHERE pr.llm_summary IS NOT NULL
  AND r.languages != '{}';
```

**Expected**: ~5,000 PRs from existing dataset

### 3.2 Ground Truth Definition

**LLM as Ground Truth**: Use `llm_summary.tech.categories` as reference.

**Rationale**:
- LLM sees full PR context (title, description, files, repo)
- Research showed 96.6% agreement with human judgment for AI detection
- Tech detection expected to be more objective (based on file content)

### 3.3 Comparison Metrics

| Metric | Definition |
|--------|------------|
| **Accuracy** | % of files where pattern matches LLM category |
| **Precision** | TP / (TP + FP) per category |
| **Recall** | TP / (TP + FN) per category |
| **F1 Score** | Harmonic mean of precision/recall |
| **Improvement** | Enhanced accuracy - Baseline accuracy |

### 3.4 Experiment Phases

**Phase 1: Baseline Measurement**
- Run `categorize_file()` on all files in dataset
- Compare to LLM categories
- Calculate accuracy/F1 per category

**Phase 2: Enhanced Detection**
- Run `categorize_file_with_repo_context()` with repo languages
- Compare to LLM categories
- Calculate improvement over baseline

**Phase 3: Threshold Optimization**
- Test 60%, 70%, 80%, 90% thresholds
- Find optimal threshold per repo type

**Phase 4: Edge Case Analysis**
- Identify repos where enhancement helps most
- Identify repos where enhancement hurts (if any)
- Document failure modes

---

## 4. Implementation Plan

### 4.1 Phase 1: Baseline Analysis (Effort: S)

**Goal**: Measure current pattern accuracy vs LLM

**Tasks**:
1. Write analysis script to compute baseline metrics
2. Export results to CSV for analysis
3. Calculate per-category accuracy
4. Identify "javascript" misclassification rate

**Output**: Baseline accuracy report

### 4.2 Phase 2: Enhanced Detector (Effort: M)

**Goal**: Implement repo-aware categorization

**Tasks**:
1. Add `categorize_file_with_repo_context()` function
2. Write unit tests for new function
3. Run on same dataset as baseline
4. Compare metrics

**Output**: Enhanced accuracy report

### 4.3 Phase 3: Threshold Tuning (Effort: S)

**Goal**: Optimize percentage thresholds

**Tasks**:
1. Run experiment with [60, 70, 80, 90]% thresholds
2. Calculate accuracy for each threshold
3. Find optimal threshold by category
4. Document trade-offs

**Output**: Threshold recommendation

### 4.4 Phase 4: Integration (Effort: M)

**Goal**: Integrate into production if improvement >10%

**Tasks**:
1. Add `repo` param to `categorize_file()` (backward compatible)
2. Update sync code to pass repo context
3. Add migration to backfill existing PRs (optional)
4. Update tests

**Output**: Production-ready enhancement

---

## 5. Technical Details

### 5.1 Database Queries

**Get PRs with repo languages**:
```python
from apps.metrics.models import PullRequest, PRFile
from apps.integrations.models import TrackedRepository

prs_with_languages = PullRequest.objects.filter(
    llm_summary__isnull=False,
    repository__languages__isnull=False
).select_related('repository').exclude(
    repository__languages={}
)
```

**Get files for analysis**:
```python
files = PRFile.objects.filter(
    pull_request__in=prs_with_languages
).select_related('pull_request__repository')
```

### 5.2 Accuracy Calculation

```python
def calculate_accuracy(files: QuerySet, enhanced: bool = False) -> dict:
    """Calculate per-category accuracy metrics."""
    results = {cat: {"tp": 0, "fp": 0, "fn": 0} for cat, _ in PRFile.CATEGORY_CHOICES}

    for file in files:
        repo_langs = file.pull_request.repository.languages if enhanced else None

        predicted = categorize_file_with_repo_context(
            file.filename, repo_langs
        ) if enhanced else PRFile.categorize_file(file.filename)

        llm_categories = file.pull_request.llm_summary.get("tech", {}).get("categories", [])
        actual = map_llm_to_file_category(llm_categories, file.filename)

        if predicted == actual:
            results[predicted]["tp"] += 1
        else:
            results[predicted]["fp"] += 1
            results[actual]["fn"] += 1

    return results
```

### 5.3 LLM Category Mapping

LLM returns: `["backend", "frontend", "devops", "mobile", "data"]`
File categories: `["frontend", "backend", "javascript", "test", "docs", "config", "other"]`

**Mapping**:
```python
def map_llm_to_file_category(llm_categories: list, filename: str) -> str:
    """Map LLM categories to PRFile category."""
    # Direct mappings
    if "backend" in llm_categories and "frontend" not in llm_categories:
        return "backend"
    if "frontend" in llm_categories and "backend" not in llm_categories:
        return "frontend"
    if "backend" in llm_categories and "frontend" in llm_categories:
        # Ambiguous - use extension
        if filename.endswith(('.py', '.go', '.java', '.rb')):
            return "backend"
        if filename.endswith(('.jsx', '.tsx', '.vue')):
            return "frontend"
        return "javascript"  # Still ambiguous

    # Fallback to extension-based
    return PRFile.categorize_file(filename)
```

---

## 6. Risk Assessment

### 6.1 Technical Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Low improvement (<5%) | Medium | High | Abandon enhancement, document learnings |
| Regression on some repos | Low | Medium | Keep threshold conservative, add repo-type rules |
| LLM ground truth inaccurate | Low | High | Sample 100 PRs for manual validation |
| Performance impact | Low | Low | Repo languages already cached on model |

### 6.2 Scope Risks

| Risk | Probability | Impact | Mitigation |
|------|-------------|--------|------------|
| Threshold varies by repo type | High | Medium | Implement per-language-group thresholds |
| New languages not covered | Medium | Low | Add fallback to base categorization |

---

## 7. Success Metrics

### 7.1 Primary Metrics

| Metric | Target | Acceptable |
|--------|--------|------------|
| Overall accuracy improvement | +15% | +10% |
| "javascript" misclassification reduction | -50% | -30% |
| No regression on unambiguous files | 0% | 0% |

### 7.2 Secondary Metrics

| Metric | Target |
|--------|--------|
| Per-repo improvement correlation with language dominance | r > 0.5 |
| Threshold stability across repo types | Std dev < 10% |

---

## 8. Timeline Estimate

| Phase | Effort | Dependencies |
|-------|--------|--------------|
| Phase 1: Baseline Analysis | S (2-4 hours) | None |
| Phase 2: Enhanced Detector | M (4-8 hours) | Phase 1 |
| Phase 3: Threshold Tuning | S (2-4 hours) | Phase 2 |
| Phase 4: Integration | M (4-8 hours) | Phase 3 results positive |

**Total**: 12-24 hours if proceeding to integration

---

## 9. Decision Points

### 9.1 After Phase 1 (Baseline)

**Go Criteria**:
- "javascript" category has >500 files
- Misclassification rate vs LLM >20%

**No-Go**: Misclassification rate <10% (pattern already good enough)

### 9.2 After Phase 2 (Enhanced)

**Go Criteria**:
- Overall improvement >10%
- No regression on clear frontend/backend files

**No-Go**: Improvement <5% (not worth integration complexity)

### 9.3 After Phase 3 (Tuning)

**Proceed if**:
- Optimal threshold is stable (60-80% range)
- Works across repo types

---

## 10. Appendix: Sample Repos for Testing

### 10.1 Backend-Dominant Repos (>70% Python/Go)

| Repo | Primary Language | JS/TS % | Expected Enhancement |
|------|------------------|---------|---------------------|
| tiangolo/fastapi | Python 95% | 2% | High |
| denoland/deno | Rust 70% | 20% | Medium |
| Infisical/infisical | TypeScript 45% | 45% | Low |

### 10.2 Frontend-Dominant Repos (>70% JS/TS)

| Repo | Primary Language | BE Lang % | Expected Enhancement |
|------|------------------|-----------|---------------------|
| calcom/cal.com | TypeScript 85% | 5% | High |
| dubinc/dub | TypeScript 90% | 3% | High |
| formbricks/formbricks | TypeScript 88% | 2% | High |

### 10.3 Mixed Repos

| Repo | Languages | Enhancement Expectation |
|------|-----------|------------------------|
| PostHog/posthog | Python 40%, TS 40% | Low (ambiguous) |
| antiwork/gumroad | Ruby 50%, JS 30% | Medium |
