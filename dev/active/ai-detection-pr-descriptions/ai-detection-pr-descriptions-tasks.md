# AI Detection via PR Description Analysis - Tasks

**Last Updated: 2025-12-24 23:15 UTC**

## Pattern Improvement Loop ✅ COMPLETE

### 2.6.6 Pattern v1.7.0 (2024-12-24) ✅
- [x] Run LLM experiment on 100 PRs (96% agreement)
- [x] Add CodeRabbit text patterns (22 new detections)
- [x] Add Mintlify agent patterns (3 new detections)
- [x] Bump PATTERNS_VERSION to 1.7.0
- [x] Add 4 new tests for new patterns (117 total)
- [x] Backfill database (459 PRs detected, 20.2%)

### 2.6.5 Pattern v1.6.0 (2024-12-24) ✅
- [x] Add Cubic AI patterns (59 new detections)
- [x] Add Cursor.com domain patterns
- [x] Add Copilot Coding Agent patterns (6 new)

---

## PRIORITY: Enhanced LLM Prompt v6.0.0 [Effort: L]

### Phase 1: User Prompt Enhancement
- [ ] Update `get_user_prompt()` to accept full PR data dict
- [ ] Add file paths (from `files_changed` JSONField or fetch)
- [ ] Add commit messages with Co-Authored-By detection
- [ ] Add comment bodies (requires API fetch or store)
- [ ] Add timing metrics: cycle_time_hours, review_time_hours
- [ ] Add state, labels, is_draft, assignees, linked_issues

### Phase 2: System Prompt v6.0.0
- [ ] Add "PR Health Assessment" task to system prompt
- [ ] Document what each metric means for CTO
- [ ] Add health indicators: review_friction, scope, risk_level
- [ ] Add insights generation guidance

### Phase 3: Response Schema Update
- [ ] Add `health` section to response schema
- [ ] Update `llm_summary` JSONField to store health data
- [ ] Update GroqBatchProcessor to parse new format

### Phase 4: Testing
- [ ] Update promptfoo.yaml with v6 tests
- [ ] Add unit tests for new prompt fields
- [ ] Run evaluation on 100 PRs

---

## Future Tasks

### Celery Batch Processing (Phase 2.7)
- [ ] Create `queue_prs_for_llm_analysis` task
- [ ] Create `apply_llm_analysis_results` task
- [ ] Add to Celery beat schedule (nightly 2 AM UTC)

### Dashboard Integration (Phase 3)
- [ ] Display `llm_summary` in PR list UI
- [ ] Show technology badges
- [ ] Show health indicators with color coding

---

## Phase 2.6: Technology Detection [Effort: M] ✅ COMPLETE

### 2.6.1 Prompt v4/v5 - Tech Detection ✅
- [x] Update `DEFAULT_SYSTEM_PROMPT` with Task 2: Technology Detection
- [x] Add primary_language detection (20 languages from SO 2025)
- [x] Add tech_categories detection (frontend, backend, test, config, docs)
- [x] Create v5 prompt with comprehensive PR summary
- [x] Create `apps/metrics/services/llm_prompts.py` as source of truth
- [x] Verify 24 Groq batch tests pass (including v5 format)

### 2.6.2 Repository Languages ✅ COMPLETE
- [x] Add fields to `TrackedRepository` model (migration 0015)
- [x] Implement `fetch_repo_languages()` using GitHub API
- [x] Implement `update_repo_languages()` to store results
- [x] Implement `get_top_languages()` helper
- [x] Create `refresh_repo_languages_task` Celery task
- [x] Create `refresh_all_repo_languages_task` Celery task
- [x] Add to Celery beat schedule (monthly, 1st of month 3 AM UTC)
- [x] Write 16 tests for language service
- [x] Backfill languages for active repos

### 2.6.3 LLM Summary Field ✅ COMPLETE
- [x] Add `llm_summary` JSONField to PullRequest (migration 0019)
- [x] Add `llm_summary_version` CharField to PullRequest
- [x] Apply migration

### 2.6.4 User Prompt Enhancement ✅ COMPLETE
- [x] Update `get_user_prompt()` in llm_prompts.py to include:
  - pr_title
  - additions/deletions
  - file_count
  - comment_count
  - repo_languages (from TrackedRepository)
- [x] Add 19 tests for llm_prompts.py

### 2.6.5 Update GroqBatchProcessor ✅ COMPLETE
- [x] Import prompts from `llm_prompts.py`
- [x] Use `PR_ANALYSIS_SYSTEM_PROMPT` by default
- [x] Parse both v4 (flat) and v5 (nested) response formats
- [x] Store `llm_summary` and `prompt_version` on BatchResult

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
