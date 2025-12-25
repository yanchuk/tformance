# Enhanced AI Detection - Context

**Last Updated: 2025-12-25**

## Status: Ready for Implementation

All prerequisite data exists. No new integrations required.

---

## Key Files

### Models
| File | Purpose |
|------|---------|
| `apps/metrics/models/github.py` | PullRequest, Commit, PRReview, PRFile models |
| `apps/metrics/models/__init__.py` | Model exports |

### AI Detection
| File | Purpose |
|------|---------|
| `apps/metrics/services/ai_detector.py` | `detect_ai_in_text()` function |
| `apps/metrics/services/ai_patterns.py` | Regex patterns + PATTERNS_VERSION |
| `apps/metrics/services/llm_prompts.py` | LLM prompt builder |
| `apps/metrics/prompts/` | Jinja2 templates for LLM |

### Sync Pipeline
| File | Purpose |
|------|---------|
| `apps/integrations/services/github_graphql_sync.py` | Main sync logic |
| `apps/integrations/tasks.py` | Celery sync tasks |

### Management Commands
| File | Purpose |
|------|---------|
| `apps/metrics/management/commands/backfill_ai_detection.py` | Regex backfill |
| `apps/metrics/management/commands/run_llm_batch.py` | LLM batch processing |

---

## Database State (Current)

```sql
-- Total data available
SELECT
    (SELECT COUNT(*) FROM metrics_pullrequest) as prs,
    (SELECT COUNT(*) FROM metrics_commit) as commits,
    (SELECT COUNT(*) FROM metrics_prreview) as reviews,
    (SELECT COUNT(*) FROM metrics_prfile) as files;
```

| Table | Count |
|-------|-------|
| PRs | 18,712 |
| Commits | 156,021 |
| Reviews | 41,610 |
| Files | 321,672 |

### AI Detection Status

```sql
-- Current AI detection coverage
SELECT
    'commits' as source,
    COUNT(*) FILTER (WHERE is_ai_assisted = true) as ai_detected
FROM metrics_commit
UNION ALL
SELECT 'reviews', COUNT(*) FILTER (WHERE is_ai_review = true)
FROM metrics_prreview;
```

| Source | AI Detected |
|--------|-------------|
| Commits | 525 |
| Reviews | 2,556 |

---

## Decisions Made

### 1. Composite Scoring Weights

| Signal | Weight | Rationale |
|--------|--------|-----------|
| LLM Detection | 0.40 | Most accurate, context-aware |
| Commit Signals | 0.25 | Hard evidence (signatures) |
| Regex Patterns | 0.20 | Fast, reliable for explicit mentions |
| Review Signals | 0.10 | Supplementary, AI review ≠ AI-authored |
| File Patterns | 0.05 | Weak signal, config files only |

### 2. Field Naming

- `has_ai_commits` (not `has_ai_assisted_commits`) - concise
- `has_ai_review` (not `has_ai_reviewer`) - about the review, not reviewer
- `ai_confidence_score` (not `ai_score`) - clear it's confidence

### 3. Signal Storage

```python
ai_signals = {
    "llm": {"is_assisted": True, "tools": ["claude"], "confidence": 0.95},
    "regex": {"is_assisted": True, "tools": ["cursor"]},
    "commits": {"has_ai": True, "co_authors": ["Claude"]},
    "reviews": {"has_ai": True, "reviewers": ["coderabbitai"]},
    "files": {"has_ai": True, "patterns": [".cursor/"]}
}
```

---

## Dependencies

### Required (All Exist)
- [x] Commit sync with `is_ai_assisted` detection
- [x] Review sync with `is_ai_review` detection
- [x] File sync with `filename` storage
- [x] LLM batch processing infrastructure
- [x] Regex pattern detection

### Not Required
- No new API integrations
- No new LLM providers
- No schema changes to external services

---

## Testing Strategy

### Unit Tests
- `test_aggregate_commit_signals()` - commit → PR aggregation
- `test_aggregate_review_signals()` - review → PR aggregation
- `test_detect_ai_file_patterns()` - file pattern matching
- `test_composite_score_calculation()` - weighted scoring

### Integration Tests
- Backfill commands work on real data
- Sync pipeline sets new fields correctly
- Dashboard displays signal breakdown

### Manual Validation
- Sample 50 PRs with multi-signal detection
- Verify each signal source is accurate
- Check for unexpected FPs

---

## Migration Plan

### Phase 1 Migration
```python
# 0022_add_ai_signal_fields.py
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='pullrequest',
            name='has_ai_commits',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='pullrequest',
            name='has_ai_review',
            field=models.BooleanField(default=False),
        ),
        migrations.AddField(
            model_name='pullrequest',
            name='has_ai_files',
            field=models.BooleanField(default=False),
        ),
    ]
```

### Phase 5 Migration
```python
# 0023_add_ai_confidence_score.py
class Migration(migrations.Migration):
    operations = [
        migrations.AddField(
            model_name='pullrequest',
            name='ai_confidence_score',
            field=models.DecimalField(
                max_digits=4, decimal_places=3, null=True
            ),
        ),
        migrations.AddField(
            model_name='pullrequest',
            name='ai_signals',
            field=models.JSONField(default=dict),
        ),
    ]
```

---

## Commands for Development

```bash
# Create migration
python manage.py makemigrations metrics --name add_ai_signal_fields

# Apply migration
python manage.py migrate

# Run backfill (after implementing)
python manage.py backfill_ai_signals --dry-run
python manage.py backfill_ai_signals

# Test specific module
pytest apps/metrics/tests/test_ai_signals.py -v

# Check database state
python manage.py shell -c "
from apps.metrics.models import PullRequest
print(f'With has_ai_commits: {PullRequest.objects.filter(has_ai_commits=True).count()}')
"
```

---

## File Patterns Reference

### AI Tool Config Files
| Pattern | Tool | Confidence |
|---------|------|------------|
| `.cursor/` | Cursor IDE | High |
| `.claude/` | Claude Code | High |
| `aider.chat/` | Aider | High |
| `.copilot/` | GitHub Copilot | Medium |
| `.coderabbit.yaml` | CodeRabbit | High |
| `.greptile.yaml` | Greptile | High |

### Generated File Patterns (Lower Confidence)
| Pattern | Indication |
|---------|------------|
| `*_generated.*` | Code generation |
| `auto_*` | Automation |
| `*.g.dart` | Dart code gen |
| `*.generated.ts` | TS code gen |

---

## No External Dependencies

This feature uses only existing infrastructure:
- PostgreSQL (existing)
- Django ORM (existing)
- Celery (existing, for async backfill)
- Groq API (existing, for enhanced LLM context)

No new services, APIs, or libraries required.
