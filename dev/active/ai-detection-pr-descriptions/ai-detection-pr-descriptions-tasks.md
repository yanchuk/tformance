# AI Detection via PR Description Analysis - Tasks

**Last Updated: 2025-12-25 12:00 UTC**

## Immediate Next Steps (On Restart)

1. **Enhance user prompt with full PR data** (highest priority):
   ```python
   # Update llm_prompts.py get_user_prompt() to include:
   - pr_title
   - additions/deletions (PR size)
   - repo_languages from TrackedRepository
   - total_comments
   - file_count
   ```

2. **Update GroqBatchProcessor to use llm_prompts.py**:
   ```python
   from apps.metrics.services.llm_prompts import (
       PR_ANALYSIS_SYSTEM_PROMPT,
       PROMPT_VERSION,
       get_user_prompt,
   )
   ```

3. **Commit uncommitted changes**:
   ```bash
   git add apps/metrics/services/llm_prompts.py
   git add apps/metrics/models/github.py
   git add apps/metrics/migrations/0019_add_llm_summary.py
   git add apps/integrations/services/github_repo_languages.py
   git add apps/integrations/tests/test_github_repo_languages.py
   git add apps/metrics/management/commands/export_prs_to_promptfoo.py
   git add apps/metrics/management/commands/run_llm_experiment.py
   git add prd/AI-DETECTION-TESTING.md
   git add CLAUDE.md
   ```

---

## Phase 2.6: Technology Detection [Effort: M] ✅ MOSTLY COMPLETE

### 2.6.1 Prompt v4/v5 - Tech Detection ✅
- [x] Update `DEFAULT_SYSTEM_PROMPT` with Task 2: Technology Detection
- [x] Add primary_language detection (20 languages from SO 2025)
- [x] Add tech_categories detection (frontend, backend, test, config, docs)
- [x] Create v5 prompt with comprehensive PR summary
- [x] Create `apps/metrics/services/llm_prompts.py` as source of truth
- [x] Verify 22 Groq batch tests pass

### 2.6.2 Repository Languages ✅ COMPLETE
- [x] Add fields to `TrackedRepository` model (migration 0015)
- [x] Implement `fetch_repo_languages()` using GitHub API
- [x] Implement `update_repo_languages()` to store results
- [x] Implement `get_top_languages()` helper
- [x] Create `refresh_repo_languages_task` Celery task
- [x] Create `refresh_all_repo_languages_task` Celery task
- [x] Add to Celery beat schedule (monthly, 1st of month 3 AM UTC)
- [x] Write 16 tests for language service

### 2.6.3 LLM Summary Field ✅ COMPLETE
- [x] Add `llm_summary` JSONField to PullRequest (migration 0019)
- [x] Add `llm_summary_version` CharField to PullRequest
- [x] Apply migration

### 2.6.4 User Prompt Enhancement ⟵ NEXT
- [ ] Update `get_user_prompt()` in llm_prompts.py to include:
  - pr_title
  - additions/deletions
  - file_count (from PRFile relation)
  - total_comments
  - repo_languages (from TrackedRepository via github_repo)
- [ ] Add test for enhanced user prompt

### 2.6.5 Update GroqBatchProcessor
- [ ] Import prompts from `llm_prompts.py`
- [ ] Store results in `llm_summary` field
- [ ] Store `PROMPT_VERSION` in `llm_summary_version`

---

## Phase 2.7: Nightly LLM Batch [Effort: M] ⟵ PENDING

### 2.7.1 Create Celery Tasks
- [ ] `queue_prs_for_llm_analysis` - Find PRs needing analysis
  - Filter: `llm_summary__isnull=True` or `llm_summary_version != PROMPT_VERSION`
  - Limit batch size (100? 500?)
- [ ] `apply_llm_analysis_results` - Process batch results
  - Parse LLM response
  - Store in `llm_summary` field
  - Set `llm_summary_version`

### 2.7.2 Add to Celery Beat
- [ ] Schedule nightly (e.g., 2 AM UTC)
- [ ] Add rate limiting to avoid Groq limits

### 2.7.3 Testing
- [ ] Test batch creation with real PRs
- [ ] Test result application
- [ ] Verify dashboard shows summary data

---

## Phase 3: Dashboard Enhancement [Effort: L] ⟵ FUTURE

### 3.1 Show LLM Summary in UI
- [ ] Display `summary.title` in PR list
- [ ] Display `summary.description` in PR detail/tooltip
- [ ] Display `summary.type` as badge (feature/bugfix/etc.)

### 3.2 Technology Insights
- [ ] Show `tech.languages` in PR list
- [ ] Show `tech.frameworks` in tooltip
- [ ] Add filter by `tech.categories`

### 3.3 AI Usage Analytics
- [ ] Use `ai.is_assisted` from LLM (higher accuracy)
- [ ] Show `ai.tools` with friendly names
- [ ] Show `ai.confidence` indicator

---

## Progress Tracking

| Phase | Description | Status |
|-------|-------------|--------|
| 1 ✅ | Regex patterns (v1.5.0) | Complete |
| 2 ✅ | Groq LLM integration | Complete |
| 2.5 ✅ | Pattern sync (GPT, Warp, Gemini) | Complete |
| 2.6 ⚠️ | Tech detection + repo languages | 90% - need user prompt |
| 2.7 | Nightly batch Celery task | Pending |
| 3 | Dashboard + production | Future |

---

## Uncommitted Changes

### New Files
- `apps/metrics/services/llm_prompts.py` - Prompt source of truth
- `apps/metrics/migrations/0019_add_llm_summary.py`
- `apps/integrations/services/github_repo_languages.py`
- `apps/integrations/tests/test_github_repo_languages.py`
- `apps/integrations/migrations/0015_add_repo_languages.py`
- `apps/metrics/management/commands/export_prs_to_promptfoo.py`
- `apps/metrics/management/commands/run_llm_experiment.py`
- `prd/AI-DETECTION-TESTING.md`
- `dev/active/.../experiments/prompts/v5-system.txt`

### Modified Files
- `apps/metrics/models/github.py` - llm_summary fields
- `apps/integrations/models.py` - languages fields
- `apps/integrations/tasks.py` - refresh language tasks
- `tformance/settings.py` - Celery beat schedule
- `CLAUDE.md` - Added testing docs reference

---

## Commands to Verify

```bash
# Check uncommitted changes
git status

# Run all tests
make test

# Run specific test suites
.venv/bin/pytest apps/integrations/tests/test_github_repo_languages.py -v
.venv/bin/pytest apps/integrations/tests/test_groq_batch.py -v

# Check migrations are applied
.venv/bin/python manage.py showmigrations metrics integrations

# Verify prompts file
cat apps/metrics/services/llm_prompts.py | head -50
```

---

## Key Decisions Log

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Prompt source of truth | `llm_prompts.py` | Single location, versioned |
| LLM summary storage | JSONField on PR | Flexible schema |
| Repo languages refresh | Monthly Celery task | Languages change rarely |
| Testing framework | Promptfoo + pytest | Fast iteration + regression |
| LLM provider | Groq (Llama 3.3 70B) | $0.08/1000 PRs, fast |
