# Session Handoff Notes

**Last Updated: 2025-12-26 18:30 UTC**

## Session Goal

Parse PRs from 25 OSS projects for 2025 (Jan 1 - Dec 25), process with LLM, and display AI trends in UI.

## Current State - LLM Processing Complete

| Metric | Value |
|--------|-------|
| Total PRs in DB | 60,545 |
| With LLM Summary | 52,224 (86.3%) |
| Empty Body PRs | 6,669 (excluded from analysis) |
| AI-Assisted PRs | 11,051 (21.2% of analyzed) |
| Date Range | 2025-01-01 to 2025-12-25 |

---

## AI Detection Summary Generated

### Top AI Tools Detected
1. **CodeRabbit** - 5,643 PRs (51.1%) - AI code review bot
2. **Devin** - 1,718 PRs (15.5%) - Autonomous AI developer
3. **Cubic** - 1,571 PRs (14.2%)
4. **Claude** - 665 PRs (6.0%)
5. **Cursor** - 648 PRs (5.9%)
6. **Copilot** - 396 PRs (3.6%)

### Teams by AI Adoption Rate
| Team | Total | Analyzed | AI PRs | Rate |
|------|-------|----------|--------|------|
| Plane | 1,717 | 1,524 | 1,322 | 86.7% |
| Dub | 1,354 | 894 | 750 | 83.9% |
| Antiwork | 4,144 | 3,935 | 2,429 | 61.7% |
| Formbricks | 1,669 | 1,553 | 828 | 53.3% |
| Trigger.dev | 1,054 | 811 | 368 | 45.4% |
| Cal.com | 5,670 | 5,515 | 2,292 | 41.6% |

---

## COMPLETED: Analytics Insights Generation

**Full Report**: `dev/active/AI-INSIGHTS-REPORT-2025.md`

### Key Findings

| Metric | AI Impact | Interpretation |
|--------|-----------|----------------|
| **Review Time** | -31% faster | AI code is easier/faster to review |
| **Cycle Time** | +42% longer | Teams tackle more complex tasks with AI |
| **PR Size** | -17% smaller | AI enables atomic, focused changes |

### AI Tool Market Share
1. CodeRabbit (53.5%) - Review Bot
2. Devin (17.9%) - Autonomous Agent
3. Cubic (12.8%) - Autonomous Agent
4. Claude (4.9%) - LLM Assistant
5. Cursor (4.7%) - AI IDE

### Team Analysis Completed
- [x] Plane (86.7% AI) - Bot-heavy, smaller PRs
- [x] Antiwork (61.7% AI) - Best outcomes, mixed tool strategy
- [x] Cal.com (41.6% AI) - Agent-heavy, larger PRs
- [x] PostHog (6.7% AI) - Emerging adopter, fast reviews
- [x] Vercel (2.1% AI) - Minimal adoption

### CTO Insights
1. **Mixed tool strategy wins** - Teams using bot + IDE + LLM show best outcomes
2. **Review velocity is consistent win** - 6/8 teams show faster reviews
3. **Autonomous agents create larger PRs** - Devin/Cubic need more oversight
4. **40-60% AI adoption is sweet spot** - Best balance of velocity and quality

---

## Uncommitted Changes

```
M apps/metrics/seeding/real_project_seeder.py
M apps/metrics/seeding/survey_ai_simulator.py
M dev/active/HANDOFF-NOTES.md
M dev/active/groq-batch-improvements/groq-batch-improvements-context.md
M package-lock.json
M package.json
M tformance/settings.py
?? dev/active/ai-detection-pr-descriptions/
?? dev/active/db-performance-celery/
```

---

## Commands for Next Session

### 1. Monthly Insights Query
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

### 2. Check Empty Body Exclusion
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
print(f'Expected max analyzable: {total - empty:,}')
"
```

### 3. Continue LLM Batch if Needed
```bash
/bin/bash -c 'export GROQ_API_KEY=$(grep "^GROQ_API_KEY=" .env | cut -d= -f2) && .venv/bin/python manage.py run_llm_batch --team "TEAM_NAME" --limit 2000 --with-fallback'
```

---

## Active Tasks Status

| Task | Location | Status |
|------|----------|--------|
| groq-batch-improvements | dev/active/ | Phase 4 COMPLETE |
| Team Insights Analysis | AI-INSIGHTS-REPORT-2025.md | **COMPLETE** |
| db-performance-celery | dev/active/ | Documentation done |
| trends-benchmarks-dashboard | dev/active/ | Phases 1-5 complete |
| posthog-analytics | dev/active/ | In progress |

---

## No Migrations Needed

Only service-layer code changes. Dev server should work immediately.

---

## Test Commands

```bash
# Verify dev server
curl -s http://localhost:8000/ | head -1

# Run groq batch tests
.venv/bin/pytest apps/integrations/tests/test_groq_batch.py -v

# Full test suite
make test
```

---

## Environment Notes

- GROQ_API_KEY in .env for LLM batch processing
- Dev server running on localhost:8000
- Docker/PostgreSQL required for database access
- Empty body PRs (6,669) are automatically excluded by LLM batch processor
