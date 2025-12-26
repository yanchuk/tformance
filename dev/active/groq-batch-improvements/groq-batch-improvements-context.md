# Groq Batch Improvements - Context

Last Updated: 2025-12-26

## Problem Statement

Investigation of Groq batch processing revealed **93.5% of failures are JSON validation errors** caused by using a smaller, less capable model (`openai/gpt-oss-20b`) in batch processing vs. the larger model (`llama-3.3-70b-versatile`) in direct API.

## Root Cause

```python
# groq_batch.py (line 301) - PROBLEM
model: str = "openai/gpt-oss-20b"  # 20B params, fails JSON generation

# run_llm_analysis.py - WORKS
model = "llama-3.3-70b-versatile"  # 70B params, reliable JSON
```

## Error Analysis

### From Groq Batch Dashboard

| Batch ID | Total | Failed | Failure % |
|----------|-------|--------|-----------|
| batch_01kd9xbskdfg0tmcr2c4evg3dt | 1,000 | 578 | **57.8%** |
| batch_01kdabnj80eyhbkgwpxdzv9bz9 | 5,000 | 122 | 2.4% |
| batch_01kdabf6cqed4vagpng9sx4ef9 | 5,000 | 116 | 2.3% |
| batch_01kdabvkt7fbk84agw6t4z3fam | 1,299 | 61 | 4.7% |

### Error Type Breakdown (836 errors analyzed)

| Error Type | Count | % |
|------------|-------|---|
| JSON validation failed | 782 | **93.5%** |
| Max tokens exceeded | 54 | 6.5% |

### Sample Error Structure

```json
{
  "id": "batch_req_out_01kd9xbwxjfsvrz95mc0dh0mph",
  "custom_id": "pr-9953",
  "response": {
    "status_code": 400,
    "body": {
      "error": {
        "message": "Failed to validate JSON. Please adjust your prompt.",
        "type": "invalid_request_error",
        "code": "json_validate_failed",
        "failed_generation": ""
      }
    }
  }
}
```

## Validation Test

Retried failed PR #26313 with correct model:

```python
# Using llama-3.3-70b-versatile (same as run_llm_analysis.py)
response = client.chat.completions.create(
    model="llama-3.3-70b-versatile",
    messages=[...],
    response_format={"type": "json_object"},
)
# Result: SUCCESS - Valid JSON returned
```

## Key Files

| File | Purpose | Issue |
|------|---------|-------|
| `apps/integrations/services/groq_batch.py` | Batch API wrapper | **Uses wrong model (line 301)** |
| `apps/metrics/management/commands/run_llm_batch.py` | Batch command | Inherits wrong model |
| `apps/metrics/management/commands/run_llm_analysis.py` | Direct API command | Uses correct model |
| `apps/metrics/services/llm_prompts.py` | Prompt templates | v7.0.0, same for both |

## Model Comparison

| Model | Parameters | Context | Batch Support | JSON Reliability |
|-------|------------|---------|---------------|------------------|
| `openai/gpt-oss-20b` | 20B | 131K | Yes | **Poor (93.5% errors)** |
| `llama-3.3-70b-versatile` | 70B | 131K | Yes | **Excellent** |

## Commands

```bash
# Check batch status
python manage.py run_llm_batch --status <batch_id>

# Process PRs (will use fixed model after change)
GROQ_API_KEY=$GROQ_API_KEY python manage.py run_llm_batch --limit 100 --poll

# Direct API (already uses correct model)
GROQ_API_KEY=$GROQ_API_KEY python manage.py run_llm_analysis --limit 50
```

## Useful Queries

```sql
-- Check coverage by team
SELECT
    t.name,
    COUNT(CASE WHEN p.llm_summary IS NOT NULL THEN 1 END) as processed,
    COUNT(CASE WHEN p.llm_summary IS NULL THEN 1 END) as unprocessed,
    ROUND(100.0 * COUNT(CASE WHEN p.llm_summary IS NOT NULL THEN 1 END) / COUNT(*), 1) as pct
FROM metrics_pullrequest p
JOIN teams_team t ON t.id = p.team_id
WHERE p.body IS NOT NULL AND p.body != ''
GROUP BY t.id, t.name
ORDER BY pct ASC;

-- Check PRs from failed batch
SELECT id, title, LENGTH(body) as body_len, llm_summary IS NOT NULL as has_summary
FROM metrics_pullrequest
WHERE id IN (26313, 22939, 25924, 27321);
```

## Fix Location

```python
# apps/integrations/services/groq_batch.py
# Line 301 - Change:
model: str = "openai/gpt-oss-20b"
# To:
model: str = "llama-3.3-70b-versatile"
```
