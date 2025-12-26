# Groq Batch Improvements - Tasks

Last Updated: 2025-12-26

## Phase 0: Fix Model (CRITICAL)

### Change batch model to llama-3.3-70b-versatile

- [ ] Edit `apps/integrations/services/groq_batch.py` line 301
  ```python
  # Change from:
  model: str = "openai/gpt-oss-20b"
  # To:
  model: str = "llama-3.3-70b-versatile"
  ```

- [ ] Test with small batch (10 PRs)
  ```bash
  GROQ_API_KEY=$GROQ_API_KEY python manage.py run_llm_batch --limit 10 --poll
  ```

- [ ] Verify results in Groq dashboard - failure rate should be <2%

## Phase 1: Reprocess Failed PRs

### Run backfill for unprocessed PRs

After model fix is verified, process remaining PRs:

- [ ] Process Cal.com (~4,147 unprocessed)
  ```bash
  GROQ_API_KEY=$GROQ_API_KEY python manage.py run_llm_batch --team "Cal.com" --limit 500 --poll
  ```

- [ ] Process Antiwork (~3,083 unprocessed)
  ```bash
  GROQ_API_KEY=$GROQ_API_KEY python manage.py run_llm_batch --team "Antiwork" --limit 500 --poll
  ```

- [ ] Process PostHog Analytics (~3,045 unprocessed)
  ```bash
  GROQ_API_KEY=$GROQ_API_KEY python manage.py run_llm_batch --team "PostHog Analytics" --limit 500 --poll
  ```

- [ ] Process LangChain (~2,817 unprocessed)
- [ ] Process Neon (~1,983 unprocessed)
- [ ] Process Deno (~1,757 unprocessed)
- [ ] Process remaining teams with >100 unprocessed PRs

## Phase 2: Optional Improvements

### Increase max_tokens (if still seeing truncation)

- [ ] Check if any new batches have "max tokens exceeded" errors
- [ ] If >5% have truncation errors, increase max_tokens:
  ```python
  # Line 369 in groq_batch.py
  "max_tokens": 2000,  # Increased from 1500
  ```

### Add retry logic for failures

- [ ] Consider implementing `retry_failed_llm_batch.py` command
- [ ] Or add automatic retry in `_download_results()` method

## Phase 3: Verification

- [ ] Query database to confirm all teams at >95% coverage
  ```sql
  SELECT t.name,
         ROUND(100.0 * COUNT(CASE WHEN p.llm_summary IS NOT NULL THEN 1 END) / COUNT(*), 1) as pct
  FROM metrics_pullrequest p
  JOIN teams_team t ON t.id = p.team_id
  WHERE p.body IS NOT NULL AND p.body != ''
  GROUP BY t.id, t.name
  ORDER BY pct ASC;
  ```

- [ ] Spot check llm_summary quality
  ```sql
  SELECT id, title, llm_summary->'ai', llm_summary->'health'
  FROM metrics_pullrequest
  WHERE llm_summary IS NOT NULL
  ORDER BY RANDOM()
  LIMIT 10;
  ```

- [ ] Verify Groq dashboard shows <2% failure rate for new batches

## Summary of Findings

### Root Cause Identified

| Issue | Cause | Fix |
|-------|-------|-----|
| 93.5% JSON validation errors | Wrong model (`openai/gpt-oss-20b`) | Change to `llama-3.3-70b-versatile` |
| 6.5% max tokens errors | 1500 token limit | Increase to 2000 (optional) |

### Validation Completed

- ✅ Retrieved error files from Groq batches
- ✅ Analyzed 836 failures across 4 batches
- ✅ Identified model mismatch between batch and direct API
- ✅ Tested retry with correct model - SUCCESS

### Expected Outcome

After model change:
- Failure rate: **~5-58% → <2%**
- JSON errors: **93.5% → <1%**
- Coverage: **44.8% → >95%** (after backfill)
