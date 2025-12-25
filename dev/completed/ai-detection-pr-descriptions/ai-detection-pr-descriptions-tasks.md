# AI Detection via PR Description Analysis - Tasks

**Last Updated: 2025-12-24 22:45 UTC**

## Current Status: LLM Pipeline Complete, DB Population In Progress

---

## ✅ COMPLETED: LLM Prompt v6.0.0

### Phase 1: User Prompt Enhancement ✅
- [x] Update `get_user_prompt()` to accept 14 params
- [x] Add state, labels, is_draft, is_hotfix, is_revert
- [x] Add cycle_time_hours, review_time_hours
- [x] Add commits_after_first_review, review_rounds
- [x] Add file_paths (limited to 20), commit_messages (limited to 5)
- [x] 51 tests for llm_prompts.py - all passing

### Phase 2: System Prompt v6.0.0 ✅
- [x] Add "Health Assessment" task to system prompt
- [x] Document timing metrics (cycle_time, review_time thresholds)
- [x] Document iteration indicators (commits_after_review, review_rounds)
- [x] Document scope indicators (line counts, file counts)
- [x] Document risk flags (hotfix, revert)

### Phase 3: Response Schema Update ✅
- [x] Add `health` section: review_friction, scope, risk_level, insights
- [x] Update GroqBatchProcessor to parse v6 format
- [x] 27 tests for groq_batch.py - all passing

### Phase 4: Promptfoo Testing ✅
- [x] Create promptfoo-v6.yaml (12 test cases)
- [x] Create v6-system.txt prompt file
- [x] 12/12 tests passing (100%)
- [x] Learned: Use ranges in assertions for LLM variance

---

## 🔄 IN PROGRESS: Database Population

### run_llm_analysis.py ⟵ CURRENT
- [x] Create management command
- [x] Fix field name issues (github_pr_id, total_comments)
- [ ] Complete 50 PR batch (23/50 done when context hit)
- [ ] Verify data in database

```bash
# Resume this:
GROQ_API_KEY=gsk_... .venv/bin/python manage.py run_llm_analysis --limit 50
```

### Verify Data:
```sql
SELECT id, title, llm_summary_version,
       llm_summary->'health' as health
FROM metrics_pullrequest
WHERE llm_summary IS NOT NULL;
```

---

## ⏳ PENDING: Celery Nightly Task

### 2.7.1 Create Celery Tasks
- [ ] `run_llm_analysis_batch` task
- [ ] Filter: `llm_summary__isnull=True` OR version mismatch
- [ ] Add rate limiting (2 sec between calls for free tier)
- [ ] Add to Celery beat schedule

---

## ⏳ PENDING: Display Health in UI

### PR List Page
- [ ] Add scope badge (small/medium/large/xlarge)
- [ ] Add risk indicator (color-coded)
- [ ] Add insights tooltip on hover
- [ ] Use `pr.llm_summary['health']` in templates

---

## ✅ COMPLETED: Pattern v1.7.0

- [x] LLM experiment on 100 PRs (96% agreement)
- [x] CodeRabbit text patterns (22 new)
- [x] Mintlify agent patterns (3 new)
- [x] 459 PRs detected (20.2%)
- [x] 117 tests for ai_detector.py

---

## Progress Summary

| Phase | Description | Status |
|-------|-------------|--------|
| Patterns v1.7.0 | Regex detection | ✅ Complete |
| LLM Prompt v6.0.0 | Health assessment | ✅ Complete |
| Promptfoo v6 | 12 test cases | ✅ Complete |
| DB Population | run_llm_analysis | 🔄 In Progress |
| Celery Nightly | Batch processing | ⏳ Pending |
| UI Display | Health badges | ⏳ Pending |

---

## Commands for Next Session

```bash
# 1. Complete LLM analysis
GROQ_API_KEY=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 \
  .venv/bin/python manage.py run_llm_analysis --limit 50

# 2. Verify data in DB
.venv/bin/python manage.py shell -c "
from apps.metrics.models import PullRequest
prs = PullRequest.objects.filter(llm_summary__isnull=False)[:5]
for pr in prs:
    print(f'{pr.title[:40]}: {pr.llm_summary.get(\"health\", {})}')"

# 3. Run tests
.venv/bin/pytest apps/metrics/tests/test_llm_prompts.py -v  # 51 tests
.venv/bin/pytest apps/integrations/tests/test_groq_batch.py -v  # 27 tests

# 4. Run promptfoo
cd dev/active/ai-detection-pr-descriptions/experiments
GROQ_API_KEY=... npx promptfoo eval -c promptfoo-v6.yaml
```

---

## Key Clarification

**Two different systems - don't conflate:**

| Tool | Purpose | Output |
|------|---------|--------|
| `npx promptfoo eval` | Test/evaluate prompts | localhost:15500 UI |
| `run_llm_analysis.py` | Populate database | PostgreSQL llm_summary |

Promptfoo is for development/testing. Management command is for production data.
