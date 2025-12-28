# Groq Batch Improvements - Context

Last Updated: 2025-12-26 18:30

## Status: Phase 4 COMPLETE - Ready for Insights Analysis

### LLM Processing Summary

| Metric | Value |
|--------|-------|
| Total PRs | 60,545 |
| With LLM Summary | 52,224 (86.3%) |
| Empty Body PRs | 6,669 (excluded) |
| AI-Assisted PRs | 11,051 (21.2% of analyzed) |
| Date Range | 2025-01-01 to 2025-12-25 |

### AI Tools Detected

| Tool | Count | % of AI PRs |
|------|-------|-------------|
| CodeRabbit | 5,643 | 51.1% |
| Devin | 1,718 | 15.5% |
| Cubic | 1,571 | 14.2% |
| Claude | 665 | 6.0% |
| Cursor | 648 | 5.9% |
| Copilot | 396 | 3.6% |
| ChatGPT | 230 | 2.1% |

### Top Teams by AI Adoption

| Team | Analyzed | AI PRs | Rate |
|------|----------|--------|------|
| Plane | 1,524 | 1,322 | 86.7% |
| Dub | 894 | 750 | 83.9% |
| Antiwork | 3,935 | 2,429 | 61.7% |
| Formbricks | 1,553 | 828 | 53.3% |
| Trigger.dev | 811 | 368 | 45.4% |
| Cal.com | 5,515 | 2,292 | 41.6% |

---

## Previous Session Bug Fix (Still Valid)

**Issue**: `submit_batch_with_fallback()` was only checking parse errors in results, NOT the error file where Groq puts actual request failures.

**Fix Applied** (lines 631-635 in `groq_batch.py`):
```python
# Combines error file failures + parse errors
error_file_failed = self._get_failed_pr_ids(stats["first_batch_id"])
parse_error_failed = [r.pr_id for r in first_results if r.error]
failed_pr_ids = list(set(error_file_failed + parse_error_failed))
```

---

## NEXT TASK: Team Insights Analysis

**User Request**: Analyze each team separately for insights and correlations in trends during the year based on monthly grouping.

### Required Analysis Per Team:
1. Monthly AI adoption trend (increasing/decreasing?)
2. Correlation: AI usage vs PR cycle time
3. Correlation: AI usage vs PR size
4. Correlation: AI usage vs review time
5. AI tool mix evolution over months
6. LLM detection accuracy per project

### Priority Teams to Analyze:
1. **Plane** (86.7% AI) - Highest adoption
2. **Antiwork** (61.7% AI) - Large sample, high adoption
3. **Cal.com** (41.6% AI) - Large sample, medium adoption
4. **PostHog** (6.7% AI) - Large sample, low adoption
5. **Vercel** (2.1% AI) - Large sample, minimal adoption

---

## Commands for Next Session

### Monthly Insights Query
```bash
.venv/bin/python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tformance.settings')
import django
django.setup()
from apps.metrics.models import PullRequest
from django.db.models import Count, Avg, Q
from django.db.models.functions import TruncMonth

team_slug = 'plane-demo'  # Change per team
qs = PullRequest.objects.filter(
    team__slug=team_slug,
    pr_created_at__year=2025
).exclude(llm_summary__isnull=True).exclude(llm_summary={}).annotate(
    month=TruncMonth('pr_created_at')
).values('month').annotate(
    total=Count('id'),
    ai_count=Count('id', filter=Q(llm_summary__ai__is_assisted=True)),
    avg_cycle=Avg('cycle_time_hours'),
    avg_review=Avg('review_time_hours')
).order_by('month')

for row in qs:
    pct = row['ai_count']/row['total']*100 if row['total'] else 0
    cycle = row['avg_cycle'] or 0
    review = row['avg_review'] or 0
    print(f\"{row['month'].strftime('%Y-%m')}: {row['total']:4} PRs, {pct:5.1f}% AI, cycle: {cycle:6.1f}h, review: {review:6.1f}h\")
"
```

### Check Empty Body Exclusion
```bash
.venv/bin/python -c "
import os
os.environ.setdefault('DJANGO_SETTINGS_MODULE', 'tformance.settings')
import django
django.setup()
from apps.metrics.models import PullRequest
from django.db.models import Q

total = PullRequest.objects.count()
empty = PullRequest.objects.filter(Q(body__isnull=True) | Q(body='')).count()
with_llm = PullRequest.objects.exclude(llm_summary__isnull=True).exclude(llm_summary={}).count()
print(f'Total: {total:,}')
print(f'Empty body: {empty:,} ({empty/total*100:.1f}%)')
print(f'With LLM: {with_llm:,}')
"
```

---

## No Migrations Needed

Only service-layer code changes. No model modifications.

## Testing

```bash
# Run groq batch tests
.venv/bin/pytest apps/integrations/tests/test_groq_batch.py -v

# Verify dev server works
curl -s http://localhost:8000/ | head -1
```
