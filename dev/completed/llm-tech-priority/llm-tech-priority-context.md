# LLM Tech Priority Feature - Context

**Last Updated:** 2025-12-25

---

## Key Files

### Models & Data

| File | Purpose |
|------|---------|
| `apps/metrics/models/github.py:10-262` | `PullRequest` model with `llm_summary` JSONField |
| `apps/metrics/models/github.py:202-214` | `llm_summary` and `llm_summary_version` fields |
| `apps/metrics/prompts/schemas.py:54-78` | `TECH_SCHEMA` - defines `categories`, `languages`, `frameworks` |

### Services

| File | Purpose |
|------|---------|
| `apps/metrics/services/pr_list_service.py:93-100` | Current `tech_categories` annotation |
| `apps/metrics/services/pr_list_service.py:250-259` | `get_filter_options()` with tech choices |

### Templates

| File | Purpose |
|------|---------|
| `templates/metrics/pull_requests/partials/table.html:134-147` | Tech column display |
| `templates/metrics/analytics/pull_requests.html:201` | Tech filter dropdown |

### Template Tags

| File | Purpose |
|------|---------|
| `apps/metrics/templatetags/pr_list_tags.py` | `tech_abbrev`, `tech_badge_class`, `tech_display_name` |

### Migrations

| File | Purpose |
|------|---------|
| `apps/metrics/migrations/0019_add_llm_summary.py` | Added `llm_summary` JSONField |
| `apps/metrics/migrations/0020_add_query_optimization_indexes.py` | GIN indexes on `llm_summary->'tech'->'categories'` |

---

## LLM Summary Structure

From `apps/metrics/prompts/schemas.py`:

```python
# TECH_SCHEMA
{
    "type": "object",
    "required": ["languages", "frameworks", "categories"],
    "properties": {
        "languages": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Programming languages detected (lowercase)",
        },
        "frameworks": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Frameworks/libraries detected (lowercase)",
        },
        "categories": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["backend", "frontend", "devops", "mobile", "data"],
            },
            "description": "Technology categories",
        },
    },
}
```

**Example `llm_summary` value:**
```json
{
  "ai": {
    "is_assisted": true,
    "tools": ["cursor"],
    "confidence": 0.9
  },
  "tech": {
    "languages": ["python", "typescript"],
    "frameworks": ["django", "react"],
    "categories": ["backend", "frontend"]
  },
  "summary": {
    "title": "Add user dashboard",
    "description": "Implements dashboard view with charts.",
    "type": "feature"
  },
  "health": {
    "review_friction": "low",
    "scope": "medium",
    "risk_level": "low",
    "insights": []
  }
}
```

---

## Current Pattern Categories

From `apps/metrics/models/github.py` (PRFile model):

```python
CATEGORY_CHOICES = [
    ("frontend", "Frontend"),
    ("backend", "Backend"),
    ("javascript", "JavaScript"),
    ("test", "Test"),
    ("docs", "Documentation"),
    ("config", "Configuration"),
    ("other", "Other"),
]
```

---

## Category Mapping Table

| Pattern | LLM | Abbreviation | Badge Class |
|---------|-----|--------------|-------------|
| `frontend` | `frontend` | `FE` | `badge-info` |
| `backend` | `backend` | `BE` | `badge-secondary` |
| `javascript` | (ambiguous) | `JS` | `badge-warning` |
| `test` | (none) | `TS` | `badge-ghost` |
| `docs` | (none) | `DC` | `badge-ghost` |
| `config` | → `devops` | `CF` | `badge-ghost` |
| `other` | (none) | `OT` | `badge-ghost` |
| (none) | `devops` | `DO` | `badge-accent` |
| (none) | `mobile` | `MB` | `badge-success` |
| (none) | `data` | `DA` | `badge-primary` |

---

## Related Active Tasks

### `dev/active/trends-benchmarks-dashboard/`

**Relevance:** Dashboard improvements that may display tech categories
- Phase 3: Sparkline Summary Cards
- Phase 5: Actionable Insights Engine

**Integration Point:** When showing technology breakdown in trends/insights, use LLM categories.

---

## Database Query Examples

**Check PRs with LLM tech categories:**
```sql
SELECT id, title, llm_summary->'tech'->'categories' as tech
FROM metrics_pullrequest
WHERE llm_summary IS NOT NULL
  AND llm_summary->'tech'->'categories' IS NOT NULL
LIMIT 10;
```

**Compare pattern vs LLM categories:**
```sql
SELECT
  pr.id,
  pr.title,
  array_agg(DISTINCT pf.file_category) as pattern_cats,
  pr.llm_summary->'tech'->'categories' as llm_cats
FROM metrics_pullrequest pr
LEFT JOIN metrics_prfile pf ON pf.pull_request_id = pr.id
WHERE pr.llm_summary IS NOT NULL
GROUP BY pr.id
LIMIT 10;
```

---

## Test Data Availability

```sql
-- Count PRs with LLM summary
SELECT COUNT(*) FROM metrics_pullrequest WHERE llm_summary IS NOT NULL;

-- Count PRs with tech categories in LLM
SELECT COUNT(*) FROM metrics_pullrequest
WHERE llm_summary->'tech'->'categories' IS NOT NULL
  AND jsonb_array_length(llm_summary->'tech'->'categories') > 0;
```
