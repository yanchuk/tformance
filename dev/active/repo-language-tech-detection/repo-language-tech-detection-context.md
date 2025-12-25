# Repository-Aware Technology Detection - Context

**Last Updated: 2025-12-25**

---

## Key Files

### Pattern Detection (Current)

| File | Purpose | Key Functions |
|------|---------|---------------|
| `apps/metrics/models/github.py:867-980` | File categorization | `PRFile.categorize_file()` |
| `apps/metrics/models/github.py:452-460` | Category choices | `PRFile.CATEGORY_CHOICES` |
| `apps/metrics/models/github.py:516-862` | Extension mappings | `FRONTEND_EXTENSIONS`, `BACKEND_EXTENSIONS` |

### Repository Language Stats

| File | Purpose | Key Functions |
|------|---------|---------------|
| `apps/integrations/models.py:221-238` | Language storage | `TrackedRepository.languages`, `.primary_language` |
| `apps/integrations/services/github_repo_languages.py` | API fetching | `fetch_repo_languages()`, `update_repo_languages()` |

### LLM Tech Detection

| File | Purpose | Key Functions |
|------|---------|---------------|
| `apps/metrics/prompts/templates/sections/tech_detection.jinja2` | Prompt section | Tech detection instructions |
| `apps/metrics/prompts/templates/user.jinja2:116-118` | Repo languages in context | `repo_languages` variable |
| `apps/metrics/prompts/schemas.py:53-78` | Response schema | `TECH_SCHEMA` |
| `apps/integrations/services/groq_batch.py` | LLM processing | `GroqBatchProcessor` |

### Sync Integration

| File | Purpose | Key Functions |
|------|---------|---------------|
| `apps/integrations/services/github_graphql_sync.py:447` | File category during sync | `_process_pr()` |
| `apps/integrations/services/github_sync.py:486` | REST sync categorization | `sync_pr_files()` |

### Dashboard Display

| File | Purpose |
|------|---------|
| `apps/metrics/services/pr_list_service.py:94` | `tech_categories` annotation |
| `templates/metrics/pull_requests/partials/table.html:134` | Category display |

---

## Key Data Structures

### PRFile.CATEGORY_CHOICES

```python
CATEGORY_CHOICES = [
    ("frontend", "Frontend"),
    ("backend", "Backend"),
    ("javascript", "JS/TypeScript"),  # Ambiguous - target for improvement
    ("test", "Test"),
    ("docs", "Documentation"),
    ("config", "Configuration"),
    ("other", "Other"),
]
```

### TrackedRepository.languages (Example)

```python
{
    "Python": 1500000,    # 75%
    "JavaScript": 300000, # 15%
    "HTML": 100000,       # 5%
    "CSS": 60000,         # 3%
    "Shell": 40000,       # 2%
}
```

### LLM TECH_SCHEMA Output

```python
{
    "languages": ["python", "javascript"],
    "frameworks": ["django", "react"],
    "categories": ["backend", "frontend"],  # Ground truth for comparison
}
```

---

## Existing Analysis Reference

### Regex vs LLM Comparison (AI Detection)

**Location**: `dev/active/regex-vs-llm-comparison/RESEARCH-SYNTHESIS.md`

**Methodology Used**:
1. Confusion matrix analysis
2. Manual sampling (6 rounds, 250+ reviews)
3. Per-repo breakdown
4. Cost-benefit analysis

**Applicable Learnings**:
- LLM confidence >0.90 is reliable ground truth
- Repo-specific analysis reveals patterns
- Sample manual review validates automated comparison

---

## Database Queries Reference

### Count PRs with LLM summary and repo languages

```sql
SELECT COUNT(*)
FROM metrics_pullrequest pr
JOIN integrations_trackedrepository r ON pr.repository_id = r.id
WHERE pr.llm_summary IS NOT NULL
  AND r.languages != '{}';
```

### Count files by category

```sql
SELECT file_category, COUNT(*)
FROM metrics_prfile
GROUP BY file_category
ORDER BY 2 DESC;
```

### PRs per repo with language dominance

```sql
SELECT
    r.full_name,
    r.primary_language,
    COUNT(pr.id) as pr_count,
    r.languages
FROM integrations_trackedrepository r
JOIN metrics_pullrequest pr ON pr.repository_id = r.id
WHERE r.languages != '{}'
GROUP BY r.id
ORDER BY pr_count DESC;
```

---

## Related Past Work

### File Categorization Expansion (Completed)

**Location**: `dev/completed/file-categorization-expansion/`

**Summary**: Extended `categorize_file()` to support 40+ languages from Stack Overflow 2025 survey.

**Relevance**: Establishes the extension-based approach we're enhancing.

### PR Technology Filter (Completed)

**Location**: `dev/completed/pr-technology-filter/`

**Summary**: Added tech filter to PR list page, uses `tech_categories` annotation.

**Relevance**: UI already supports enhanced categories.

### LLM Prompt System (Completed)

**Location**: `dev/completed/prompt-template-system/`

**Summary**: Jinja2-based prompt templates with golden tests.

**Relevance**: Established LLM tech detection we use as ground truth.

---

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-25 | Use LLM as ground truth | 96.6% agreement with human judgment on AI detection; tech detection is more objective |
| 2025-12-25 | Focus on "javascript" category | Only ambiguous category; clear extensions already accurate |
| 2025-12-25 | 70% threshold initial hypothesis | Balance between signal strength and coverage |
| 2025-12-25 | Backward-compatible enhancement | Optional param keeps existing behavior for callers without repo context |

---

## Test Data Summary (Estimated)

From existing seeded data:

| Metric | Value | Source |
|--------|-------|--------|
| PRs with LLM summary | ~5,000 | `metrics_pullrequest.llm_summary` |
| Repos with language stats | 25+ | `integrations_trackedrepository.languages` |
| Files categorized as "javascript" | ~2,800 | `metrics_prfile.file_category` |
| Backend-dominant repos (>70%) | ~8 | Manual classification |
| Frontend-dominant repos (>70%) | ~12 | Manual classification |

---

## Command Reference

### Run analysis script (to be created)

```bash
.venv/bin/python manage.py analyze_tech_detection --baseline
.venv/bin/python manage.py analyze_tech_detection --enhanced
.venv/bin/python manage.py analyze_tech_detection --compare
```

### Query file category distribution

```bash
.venv/bin/python manage.py shell -c "
from apps.metrics.models import PRFile
from django.db.models import Count
print(PRFile.objects.values('file_category').annotate(c=Count('id')).order_by('-c'))
"
```

### Query repo language distribution

```bash
.venv/bin/python manage.py shell -c "
from apps.integrations.models import TrackedRepository
for r in TrackedRepository.objects.exclude(languages={}):
    total = sum(r.languages.values())
    top = sorted(r.languages.items(), key=lambda x: -x[1])[:3]
    print(f'{r.full_name}: {[(l, f\"{b/total*100:.0f}%\") for l,b in top]}')"
```
