# Session Handoff Notes

**Last Updated: 2025-12-26 21:00 UTC**

## Current Session: AI Regex Pattern Improvements ✅ COMPLETE

### What Was Done
1. **Analyzed LLM vs Regex gap** - Found 1,717 PRs where LLM detected AI but regex missed
2. **Added new patterns** using TDD Red-Green approach:
   - **Replexica AI** (i18n tool): 5 signature patterns + 2 bot usernames
   - **CodeRabbit author**: 3 patterns for docstrings/PRs created by CR bot
   - **Mintlify Writer**: 1 pattern (skipped mintlify.com to avoid FP)
3. **Fixed .claude/settings.local.json** - Removed malformed quote and exposed API key
4. **Documented LLM-to-regex methodology** for research purposes
5. **Ran full backfill** on 60,964 PRs

### Results

| Metric | Before | After | Change |
|--------|--------|-------|--------|
| LLM-only gap | 1,717 | 1,668 | **-49 (2.9%)** |
| Regex detections | ~11,828 | 12,388 | +560 |

**Tool Detections:**
- Replexica: 430 PRs (mostly Cal.com @LingoDotDev translations)
- CodeRabbit: 6,884 PRs (includes new author patterns)
- Mintlify: 13 PRs (conservative Writer-only pattern)

### Key Files Modified
- `apps/metrics/services/ai_patterns.py` - Added 9 new patterns, version 1.9.0 → 2.0.0
- `apps/metrics/tests/test_ai_detector.py` - Added 12 new tests (129 total, all passing)
- `dev/active/improve-ai-regex-patterns/` - Full task documentation with results

### Pattern Changes Summary
```python
# New bot usernames (AI_REVIEWER_BOTS)
"replexica[bot]": "replexica"
"lingodotdev[bot]": "replexica"

# New signature patterns (AI_SIGNATURE_PATTERNS)
(r"\bdocstrings?\s+generation\s+was\s+requested\b", "coderabbit")
(r"\bcoderabbit\s+cannot\s+perform\s+edits\b", "coderabbit")
(r"\bgenerated\s+by\s+coderabbit\b", "coderabbit")
(r"\bmintlify\s+writer\b", "mintlify")
(r"\breplexica\s+ai\b", "replexica")
(r"\breplexica\.com\b", "replexica")
(r"\breplexica\s+localization\s+engine\b", "replexica")
(r"\@replexica\b", "replexica")
(r"\@lingodotdev\b", "replexica")

# New display name
"replexica": "Replexica AI"
```

### Analysis: Further Regex Improvements Not Practical

Investigated top missed tools - **all are implicit LLM detections** without text markers:
- Greptile (455): Team inference (PostHog 86%, Twenty 12%), no explicit mentions
- Copilot/Claude/Cursor: Code style inference, no text markers
- CodeRabbit: Detection from review comments, not PR body

**Conclusion**: The 1,668 LLM-only gap represents genuine LLM value - contextual detection that regex cannot do.

### Next Steps
- [x] Commit changes to git
- [ ] Move `dev/active/improve-ai-regex-patterns/` to `dev/completed/`

### Research Notes: LLM-to-Regex Discovery
Documented in `dev/active/improve-ai-regex-patterns/improve-ai-regex-patterns-context.md`:
- LLM helps discover patterns, but ~70% are implicit (no text markers)
- Only ~30% of LLM detections can be converted to regex
- Validates hybrid approach: LLM for discovery, regex for explicit patterns

---

## Previous Session: OSS Expansion (25 → 100 Projects)

### What Was Done
1. Researched and added 75 new OSS product companies to seeding config
2. Organized 100 projects into 20 industry categories for benchmarking
3. Added `industry` field and helper functions to `real_projects.py`
4. Provided parallel seeding commands with 2 PATs
5. **Phase 1 seeding (26-50) is running** in user's terminals

### Key File Modified
`apps/metrics/seeding/real_projects.py`:
- Added `industry` field to `RealProjectConfig` dataclass
- Added `INDUSTRIES` dict with 20 categories
- Added 75 new project configs (now 100 total)
- Added helper functions: `get_projects_by_industry()`, `list_industries()`, `get_industry_display_name()`

---

## LLM Processing Status

| Metric | Value |
|--------|-------|
| Total PRs in DB | 63,403+ |
| With LLM Summary | 53,876 (85%+) |
| AI-Assisted PRs | ~11,500 |
| LLM-only gap | 1,717 (target: reduce with new patterns) |

---

## Active Tasks Status

| Task | Location | Status |
|------|----------|--------|
| **improve-ai-regex-patterns** | dev/active/ | Patterns added, backfill pending |
| oss-expansion | dev/active/ | Phase 1 seeding running |
| groq-batch-improvements | dev/active/ | Complete |
| trends-benchmarks-dashboard | dev/active/ | Phases 1-5 complete |

---

## Uncommitted Changes

```bash
# Check current status
git status --short

# Expected modified files:
M apps/metrics/services/ai_patterns.py
M apps/metrics/tests/test_ai_detector.py
M dev/active/HANDOFF-NOTES.md
M dev/active/improve-ai-regex-patterns/
```

---

## Commands for Next Session

### 1. Verify Tests Pass
```bash
.venv/bin/pytest apps/metrics/tests/test_ai_detector.py -v
# Expected: 129 tests pass
```

### 2. Run Backfill
```bash
# Check if force flag needed
python manage.py backfill_ai_detection --help

# Run backfill
python manage.py backfill_ai_detection
```

### 3. Verify Gap Reduction
```bash
python manage.py shell -c "
from apps.metrics.models import PullRequest
from django.db.models import Q
llm_only = PullRequest.objects.filter(
    llm_summary__ai__is_assisted=True,
    llm_summary__ai__confidence__gte=0.5,
    is_ai_assisted=False
).count()
print(f'LLM-only gap: {llm_only}')
# Was: 1,717 - Should be lower after backfill
"
```

### 4. Commit Changes
```bash
git add apps/metrics/services/ai_patterns.py apps/metrics/tests/test_ai_detector.py
git commit -m "Add Replexica, CodeRabbit author, Mintlify Writer patterns (v2.0.0)

Pattern improvements based on LLM gap analysis:
- Replexica AI: 5 signature patterns + 2 bot usernames
- CodeRabbit: 3 author patterns (docstrings, cannot edit)
- Mintlify: 1 pattern (Writer only, skip FP-prone .com)

Tests: 129 pass (+12 new)
Version: 1.9.0 → 2.0.0

🤖 Generated with [Claude Code](https://claude.com/claude-code)

Co-Authored-By: Claude Opus 4.5 <noreply@anthropic.com>"
```

---

## No Migrations Needed

Only service-layer code changes. Dev server should work immediately.

---

## Test Commands

```bash
# AI detector tests
.venv/bin/pytest apps/metrics/tests/test_ai_detector.py -v

# Full test suite
make test

# Dev server check
curl -s http://localhost:8000/ | head -1
```
