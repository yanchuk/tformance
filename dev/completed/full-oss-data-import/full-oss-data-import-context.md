# Full OSS Data Import - Context

**Last Updated: 2025-12-25 (Session 2)**

## Status: ✅ COMPLETE - All PRs Imported and LLM Analyzed

All 25 OSS projects fully seeded with LLM analysis complete.

---

## Session Summary (2025-12-25 Session 2)

### What Was Accomplished

1. **Seeded all 25 OSS projects** with full historical data
2. **Processed 13,732 PRs via LLM** in 5 batches (5000, 5000, 5000, 1299, 61)
3. **Regenerated weekly metrics** for all 33 teams × 12 weeks
4. **Fixed GitHub Actions CI** - Added Redis service, SECRET_KEY, pytest -n 4

### Database State (Final)

| Metric | Count |
|--------|-------|
| **Total PRs** | 18,712 |
| **With LLM Summary** | 16,996 (90.8%) |
| **Without LLM** | 1,716 (most have no body) |
| **No Body (can't analyze)** | 1,696 |

### Team Breakdown (Top 10)

| Team | PRs | Regex AI % | LLM AI % |
|------|-----|-----------|----------|
| Plane | 1,546 | 85.0% | 86.7% |
| Dub | 1,295 | 54.1% | 82.8% |
| Formbricks | 1,562 | 49.9% | 53.3% |
| Infisical | 1,566 | 22.1% | 25.8% |
| Comp AI | 1,536 | 14.3% | 14.7% |
| Novu | 2,048 | 12.7% | 16.5% |
| Coolify | 935 | 5.0% | 9.6% |
| Twenty CRM | 4,014 | 0.8% | 5.6% |
| PostHog | 657 | 2.7% | 5.0% |
| Hoppscotch | 435 | 13.6% | 17.4% |

### LLM Batch Processing Stats

| Batch | Submitted | Successful | Failed | Time |
|-------|-----------|------------|--------|------|
| 1 | 500 | 486 | 14 | ~45s |
| 2 | 500 | 489 | 11 | ~45s |
| 3 | 5,000 | 4,884 | 116 | ~2min |
| 4 | 5,000 | 4,878 | 122 | ~2min |
| 5 | 1,299 | 1,238 | 61 | ~1min |
| 6 | 61 | 41 | 20 | ~30s |
| **Total** | **12,360** | **12,016** | **344** | ~7min |

### Seeding Performance Stats

From seeding log analysis:
- **Average time per 100 PRs**: ~39 seconds
- **Total PRs seeded**: 16,132 PRs
- **Total time**: 104 minutes

---

## Key Findings

### LLM vs Regex Detection

LLM consistently detects more AI-assisted PRs:
- **Dub**: +28.7% (54.1% → 82.8%) - biggest improvement
- **Twenty CRM**: +4.8% (0.8% → 5.6%)
- **Novu**: +3.8% (12.7% → 16.5%)

LLM catches AI usage that isn't explicitly disclosed.

### PRs Without LLM Analysis

~1,700 PRs have no body text (can't analyze):
- Dependabot/Renovate PRs
- Quick merge commits
- Bot-generated PRs with minimal descriptions

---

## Files Modified This Session

| File | Changes |
|------|---------|
| `.github/workflows/tests.yml` | Added SECRET_KEY, Redis service, -n 4 |
| `apps/metrics/seeding/github_authenticated_fetcher.py` | Bug fix: removed undefined until_date |
| `apps/metrics/management/commands/seed_real_projects.py` | Bug fix: proper exception chaining |

---

## GitHub Actions CI Fixes

### Problem 1: SECRET_KEY Missing
```yaml
env:
  SECRET_KEY: "test-secret-key-for-ci-only-not-for-production"
```

### Problem 2: Redis Connection Refused
```yaml
services:
  redis:
    image: redis:7-alpine
    options: >-
      --health-cmd "redis-cli ping"
      --health-interval 5s
      --health-timeout 3s
      --health-retries 3
    ports:
      - 6379:6379
```

### Problem 3: pytest Workers
```yaml
run: uv run pytest -n 4  # 4 workers on 2 vCPU (I/O bound tests)
```

---

## Commands for Next Session

```bash
# Check database state
.venv/bin/python manage.py shell -c "
from apps.metrics.models import PullRequest
print(f'Total: {PullRequest.objects.count()}')
print(f'With LLM: {PullRequest.objects.exclude(llm_summary__isnull=True).exclude(llm_summary={}).count()}')
"

# Run more LLM batches if needed
GROQ_API_KEY=$GROQ_API_KEY .venv/bin/python manage.py run_llm_batch --limit 5000

# Check batch status
GROQ_API_KEY=$GROQ_API_KEY .venv/bin/python manage.py run_llm_batch --status <batch_id>
```

---

## No Migrations Needed

No Django model changes in this session.

---

## Task Status: ✅ COMPLETE

This task can be moved to `dev/completed/` as all 25 OSS projects are fully seeded and analyzed.
