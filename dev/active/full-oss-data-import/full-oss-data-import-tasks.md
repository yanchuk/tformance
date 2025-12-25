# Full OSS Data Import Tasks

**Last Updated: 2025-12-25**

## Status Summary

| Quarter | Status | PRs Imported |
|---------|--------|--------------|
| Q4 2025 | ✅ Complete | ~5,000+ |
| Q1-Q3 2025 | 🔄 Scripts Ready | Pending run |

---

## Phase 1: Add Batch Import Capability ✅ COMPLETE

- [x] Add `--start-date` and `--end-date` args to `seed_real_projects` command
- [x] Add `--no-pr-limit` flag (set max_prs to None)
- [x] Add `--no-member-limit` flag (set max_members to None)
- [x] Add `--max-files-per-pr` option (default 100)
- [x] Update GraphQL fetcher to respect date range filters
- [x] Update REST API fetcher for date range filters
- [x] Test batch import with single project ✅

---

## Phase 2: Import Full 2025 Data

### Q4 2025 (Oct-Dec) ✅ COMPLETE
- [x] Import all 25 OSS repos for Q4 2025
- [x] Run LLM batch analysis on Q4 PRs
- [x] Verify data quality (4,980 PRs with LLM summaries)

**Results:**
- 5,654 total PRs in database
- 4,980 with LLM summaries
- 1,186 AI-assisted PRs detected

### Q1-Q3 2025 (Jan-Sep) 🔄 SCRIPTS READY

Created two batch scripts to import remaining 2025 data:

**Script 1: `scripts/seed_all_oss.sh`** (11 projects)
```bash
./scripts/seed_all_oss.sh
# Projects: twenty, novu, hoppscotch, plane, documenso,
#           coolify, infisical, dub, lago, formbricks, compai
```

**Script 2: `scripts/seed_all_oss_part2.sh`** (14 projects)
```bash
./scripts/seed_all_oss_part2.sh
# Projects: antiwork, polar, posthog, fastapi, anthropic,
#           langchain, calcom, trigger, vercel, supabase,
#           linear, resend, deno, neon
```

**To run (requires GitHub tokens):**
```bash
export GITHUB_SEEDING_TOKENS="token1,token2,token3"
./scripts/seed_all_oss.sh
# Then after completion:
./scripts/seed_all_oss_part2.sh
```

**Estimated time:** 4-8 hours per script (depends on rate limits)

---

## Phase 3: Period Comparison Analytics

- [ ] Design QoQ comparison view
- [ ] Design MoM comparison view
- [ ] Implement aggregation queries for period comparison
- [ ] Add period selector to analytics pages

*Deferred until full 2025 data is imported*

---

## Quick Commands

```bash
# Check current database state
.venv/bin/python manage.py shell -c "
from apps.metrics.models import PullRequest
from django.db.models.functions import TruncMonth
from django.db.models import Count
print('PRs by month:')
for row in PullRequest.objects.annotate(month=TruncMonth('merged_at')).values('month').annotate(c=Count('id')).order_by('month'):
    print(f'  {row[\"month\"]}: {row[\"c\"]}')
"

# Run LLM batch after seeding
GROQ_API_KEY=$GROQ_API_KEY .venv/bin/python manage.py run_llm_batch --limit 10000
```

---

## Files Modified This Session

| File | Changes |
|------|---------|
| `scripts/seed_all_oss.sh` | Created - 11 projects, Q1-Q3 |
| `scripts/seed_all_oss_part2.sh` | Created - 14 projects, Q1-Q3 |
| `apps/metrics/seeding/real_project_seeder.py` | Date range support |
| `apps/metrics/management/commands/seed_real_projects.py` | CLI args |
