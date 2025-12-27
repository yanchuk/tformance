---
name: effective-property-reminder
description: Reminds to use effective_* properties on PullRequest model instead of raw fields. Triggers on is_ai_assisted, ai_tools_detected, tech_categories, llm_summary access. LLM data priority rule enforcement for AI detection.
---

# Effective Property Reminder

## Purpose

Ensure LLM-detected data is prioritized over regex/pattern detection by using `effective_*` model properties.

## When to Use

**Automatically activates when:**
- Accessing AI-related fields on PullRequest model
- Working with `is_ai_assisted`, `ai_tools_detected`, `tech_categories`
- Building dashboards, reports, or aggregations involving AI metrics

## The LLM Data Priority Rule

**IMPORTANT: Always prioritize LLM-detected data over pattern/regex detection.**

## Effective Properties

| Property | LLM Source | Fallback |
|----------|------------|----------|
| `pr.effective_is_ai_assisted` | `llm_summary.ai.is_assisted` (≥0.5 conf) | `is_ai_assisted` |
| `pr.effective_ai_tools` | `llm_summary.ai.tools` | `ai_tools_detected` |
| `pr.effective_tech_categories` | `llm_summary.tech.categories` | PRFile aggregation |

## Code Examples

### ❌ WRONG - Using Raw Fields

```python
pr = PullRequest.objects.get(id=pr_id)
is_ai = pr.is_ai_assisted  # Raw regex detection only
tools = pr.ai_tools_detected  # Raw regex detection only
```

### ✅ CORRECT - Using Effective Properties

```python
pr = PullRequest.objects.get(id=pr_id)
is_ai = pr.effective_is_ai_assisted  # Prioritizes LLM data
tools = pr.effective_ai_tools  # Prioritizes LLM data
categories = pr.effective_tech_categories  # Prioritizes LLM data
```

## When Raw Fields Are Acceptable

1. **Backfill scripts** - Updating raw fields from new patterns
2. **LLM analysis input** - Providing context to LLM
3. **Admin debugging** - Comparing raw vs LLM values
4. **Pattern testing** - Validating regex accuracy

```python
# Acceptable: Admin view comparing detection methods
def debug_detection(pr):
    return {
        'raw_is_ai': pr.is_ai_assisted,
        'llm_is_ai': pr.llm_summary.get('ai', {}).get('is_assisted'),
        'effective_is_ai': pr.effective_is_ai_assisted,
    }
```

## Service Layer Pattern

Services should encapsulate effective property usage:

```python
class PRAnalysisService:
    def get_ai_summary(self, pr: PullRequest) -> dict:
        return {
            'is_ai_assisted': pr.effective_is_ai_assisted,
            'tools': pr.effective_ai_tools,
            'categories': pr.effective_tech_categories,
        }
```

## Quick Reference

| Field | Use For | Don't Use For |
|-------|---------|---------------|
| `is_ai_assisted` | Backfills, debugging | Display, metrics |
| `ai_tools_detected` | Backfills, debugging | Display, metrics |
| `effective_is_ai_assisted` | Display, metrics | - |
| `effective_ai_tools` | Display, metrics | - |
| `effective_tech_categories` | Display, metrics | - |

---

**Enforcement Level**: WARN
**Priority**: High
