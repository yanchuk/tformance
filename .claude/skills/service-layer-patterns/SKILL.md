---
name: service-layer-patterns
description: Guide to existing service layer in Tformance. Triggers on business logic, service class, DashboardService, PRListService, aggregation, data processing. Know existing services before creating new ones.
---

# Service Layer Patterns

## Purpose

Document existing services to prevent duplication and ensure consistent patterns when adding business logic.

## When to Use

**Automatically activates when:**
- Adding business logic that could belong in a service
- Creating aggregations or data processing
- Working on dashboard or analytics features
- Needing to understand where logic lives

## Existing Services

### Dashboard Services (`apps/metrics/services/`)

| Service | Purpose | Key Methods |
|---------|---------|-------------|
| `DashboardService` | Main metrics aggregation | `get_summary_metrics()`, `get_ai_metrics()` |
| `PRListService` | PR listing with filters | `get_prs()`, `get_pr_detail()` |
| `AICategories` | AI tool categorization | `categorize_tools()`, `get_category_stats()` |

### Integration Services (`apps/integrations/services/`)

| Service | Purpose | Key Methods |
|---------|---------|-------------|
| `GitHubSyncService` | Sync GitHub data | `sync_prs()`, `sync_members()` |
| `JiraSyncService` | Sync Jira data | `sync_issues()` |
| `GroqBatchService` | LLM batch processing | `analyze_prs()` |

### AI Detection (`apps/metrics/services/`)

| Service | Purpose |
|---------|---------|
| `ai_patterns.py` | Regex pattern detection |
| `llm_prompts.py` | LLM prompt generation |

## Service Pattern

### Standard Structure

```python
class MyService:
    """Service for handling X domain logic."""

    def __init__(self, team: Team):
        self.team = team

    def get_data(self, **filters) -> QuerySet:
        """Fetch data with team isolation."""
        return Model.objects.filter(team=self.team, **filters)

    def aggregate_metrics(self) -> dict:
        """Compute aggregated metrics."""
        qs = self.get_data()
        return {
            'count': qs.count(),
            'avg': qs.aggregate(avg=Avg('field'))['avg'],
        }
```

### Usage in Views

```python
@login_and_team_required
def dashboard_view(request, team_slug):
    team = get_object_or_404(Team, slug=team_slug)
    service = DashboardService(team)
    metrics = service.get_summary_metrics()
    return render(request, 'dashboard.html', {'metrics': metrics})
```

## When to Create a New Service

### ✅ Create a Service When:

- Logic is reused across multiple views
- Complex aggregations or calculations
- External API interactions
- Business rules that shouldn't live in views

### ❌ Don't Create a Service When:

- Simple CRUD operations
- One-off view logic
- Logic already exists in another service

## Check Before Creating

```bash
# Search for existing services
grep -r "class.*Service" apps/*/services/

# Check for similar functionality
grep -r "def get_.*metrics" apps/
grep -r "def aggregate" apps/
```

## Service Locations

```
apps/
├── metrics/
│   └── services/
│       ├── dashboard_service.py    # Dashboard metrics
│       ├── pr_list_service.py      # PR listing
│       ├── ai_categories.py        # AI categorization
│       ├── ai_patterns.py          # Regex detection
│       └── llm_prompts.py          # LLM prompts
├── integrations/
│   └── services/
│       ├── github_sync.py          # GitHub sync
│       ├── jira_sync.py            # Jira sync
│       └── groq_batch.py           # LLM processing
```

## Testing Services

```python
class TestDashboardService(TestCase):
    def setUp(self):
        self.team = TeamFactory()
        self.service = DashboardService(self.team)

    def test_get_summary_metrics(self):
        PullRequestFactory.create_batch(5, team=self.team, state='merged')
        metrics = self.service.get_summary_metrics()
        self.assertEqual(metrics['pr_count'], 5)
```

## Quick Reference

| Need | Use This Service |
|------|------------------|
| Dashboard metrics | `DashboardService` |
| PR listing/filtering | `PRListService` |
| AI tool categories | `AICategories` |
| GitHub data sync | `GitHubSyncService` |
| LLM analysis | `GroqBatchService` |

---

**Enforcement Level**: SUGGEST
**Priority**: Medium
