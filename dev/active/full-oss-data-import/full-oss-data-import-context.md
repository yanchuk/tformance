# Full OSS Data Import - Context

**Last Updated: 2025-12-25**

## Status: Q4 Complete, Q1-Q3 Scripts Ready

Q4 2025 data fully imported and analyzed. Pattern v1.9.0 applied to all PRs.

---

## Session Summary (2025-12-25)

### What Was Accomplished

1. **Q4 2025 Import Complete**: ~5,000+ PRs from all 25 projects
2. **LLM Batch Analysis Complete**: 4,980 PRs analyzed with Groq
3. **Q1-Q3 Scripts Created**: Two batch scripts ready to run
4. **Pattern v1.9.0 Applied**: All PRs backfilled with improved patterns

### Database State (Post v1.9.0)

| Metric | Count |
|--------|-------|
| Total PRs | 5,654 |
| With LLM Summary | 4,980 |
| AI-Assisted (Regex v1.9.0) | 1,167 |
| AI-Assisted (LLM) | 1,315 |

### Projects Imported (25 total)

**High AI Signal:**
- antiwork (Gumroad, Flexile, Helper)
- polar, posthog, fastapi
- anthropic, langchain

**Product Teams:**
- twenty, novu, hoppscotch, plane, documenso
- coolify, infisical, dub, lago, formbricks, compai

**DevTools/Infrastructure:**
- calcom, trigger, vercel, supabase
- linear, resend, deno, neon

---

## Key Technical Details

### Seeding Command Options

```bash
python manage.py seed_real_projects \
    --project <name> \
    --start-date 2025-01-01 \
    --end-date 2025-09-30 \
    --no-pr-limit \
    --no-member-limit \
    --no-check-runs \
    --refresh
```

| Option | Purpose |
|--------|---------|
| `--no-pr-limit` | Fetch all PRs (no 300 limit) |
| `--no-member-limit` | Include all contributors |
| `--no-check-runs` | Skip CI data (faster) |
| `--refresh` | Force re-fetch from GitHub |
| `--start-date` | Filter by merge date start |
| `--end-date` | Filter by merge date end |

### Rate Limit Handling

- Uses token rotation (GITHUB_SEEDING_TOKENS env var)
- GraphQL API for efficiency (fewer calls)
- 5-second delay between projects
- Checkpoint support for resume

---

## Next Steps

### Immediate (When Ready)
1. Run `scripts/seed_all_oss.sh` to import Q1-Q3 for 11 projects
2. Run `scripts/seed_all_oss_part2.sh` for remaining 14 projects
3. Submit new LLM batch for Q1-Q3 PRs

### After Q1-Q3 Import
4. Re-run LLM vs Regex analysis on full year
5. Build QoQ/MoM comparison views
6. Identify AI adoption trends over time

---

## Commands for Next Session

```bash
# Start Q1-Q3 import (takes 4-8 hours)
export GITHUB_SEEDING_TOKENS="token1,token2,token3"
./scripts/seed_all_oss.sh

# After completion, run part 2
./scripts/seed_all_oss_part2.sh

# Submit LLM batch for new PRs
GROQ_API_KEY=$GROQ_API_KEY .venv/bin/python manage.py run_llm_batch --limit 20000

# Re-run backfill with v1.9.0 for new PRs
.venv/bin/python manage.py shell
# (use backfill script from regex-vs-llm-comparison-context.md)
```

---

## Files Created

| File | Purpose |
|------|---------|
| `scripts/seed_all_oss.sh` | Batch script for 11 projects, Q1-Q3 2025 |
| `scripts/seed_all_oss_part2.sh` | Batch script for 14 projects, Q1-Q3 2025 |

---

## Dependencies

- `GITHUB_SEEDING_TOKENS` env var with comma-separated PATs
- `GROQ_API_KEY` env var for LLM batch processing
- PostgreSQL database running
- Sufficient disk space for cache files
