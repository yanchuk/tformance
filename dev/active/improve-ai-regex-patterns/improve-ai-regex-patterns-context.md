# Improve AI Detection Regex Patterns - Context

**Last Updated: 2025-12-26**

## LLM-to-Regex Pattern Discovery (Research Notes)

This feature demonstrates how LLM analysis can systematically improve regex pattern detection. This approach could be valuable for public research on hybrid AI detection systems.

### Methodology

1. **LLM Analysis First**: Ran LLM (Groq/Llama 3.3 70B) on 53,876 PRs to detect AI usage
2. **Gap Analysis**: Compared LLM detections vs regex detections to find misses
3. **Pattern Mining**: Extracted actual text from PRs where LLM detected but regex missed
4. **Selective Addition**: Added regex patterns only for cases with clear text signatures

### Key Findings

| Discovery | LLM Detected | Actionable? | Regex Added? |
|-----------|--------------|-------------|--------------|
| **Replexica AI** (i18n tool) | 9 PRs | Yes - clear signatures | Yes |
| **CodeRabbit author** | 467 PRs | Partial - only 31 with text patterns | Yes |
| Greptile | 456 PRs | No - from review context only | No |
| Copilot (implicit) | 163 PRs | No - no text markers | No |
| Claude (implicit) | 145 PRs | No - no text markers | No |
| Cursor (implicit) | 110 PRs | No - no text markers | No |

### Insight: LLM vs Regex Detection Roles

**LLM is better for:**
- Detecting AI from code style/patterns (implicit detection)
- Understanding context (review comments, negations)
- Complex multi-signal inference

**Regex is better for:**
- Explicit text signatures (fast, deterministic)
- Bot username detection
- Co-author email patterns

### Hybrid Detection Value

The LLM helps discover new patterns, but not all discoveries translate to regex:
- 1,717 PRs: LLM detected, regex missed
- ~500 PRs: Could add regex patterns (clear text markers)
- ~1,200 PRs: Must stay LLM-only (implicit/contextual)

This validates the hybrid approach: LLM for discovery and complex cases, regex for explicit patterns.

## Key Files

| File | Purpose |
|------|---------|
| `apps/metrics/services/ai_patterns.py` | Pattern definitions (source of truth) |
| `apps/metrics/services/ai_detector.py` | Pattern matching logic |
| `apps/metrics/tests/test_ai_detector.py` | Unit tests for patterns |
| `apps/metrics/management/commands/backfill_ai_detection.py` | Backfill command |
| `prd/AI-DETECTION-TESTING.md` | AI detection documentation |

## Pattern Structure

### Adding New Signature Patterns

```python
# In AI_SIGNATURE_PATTERNS list
AI_SIGNATURE_PATTERNS: list[tuple[str, str]] = [
    # (regex_pattern, tool_type)
    (r"\breplexica\s+ai\b", "replexica"),
    (r"\@replexica\b", "replexica"),
]
```

### Adding New Bot Usernames

```python
# In AI_REVIEWER_BOTS dict
AI_REVIEWER_BOTS: dict[str, str] = {
    "replexica[bot]": "replexica",
    "lingodotdev[bot]": "replexica",
}
```

### Adding Display Names

```python
# In AI_TOOL_DISPLAY_NAMES dict
AI_TOOL_DISPLAY_NAMES: dict[str, str] = {
    "replexica": "Replexica AI",
}
```

## Sample PR Bodies (Patterns to Match)

### Replexica (Currently Missed)

```
Hey team,

[**Replexica AI**](https://replexica.com) here with fresh translations!

### In this update

- Added missing translations
- Performed brand voice, context and glossary checks
- Enhanced translations using Replexica Localization Engine

### Next Steps

- [ ] Review the changes
- [ ] Merge when ready
```

Patterns needed:
- `\bReplexica\s+AI\b`
- `\breplexica\.com\b`
- `\bReplexica\s+Localization\s+Engine\b`
- `\@replexica\b`
- `\@lingodotdev\b`

### CodeRabbit Author (Currently Missed)

```
Docstrings generation was requested by @dnywh.

* https://github.com/supabase/supabase/pull/41527#issuecomment-3680610884

The following files were modified:

* `apps/studio/data/config/project-upgrade-eligibility-query.ts`

<details>
<summary>ℹ️ Note</summary><blockquote>

CodeRabbit cannot perform edits on its own pull requests yet.

</blockquote></details>
```

Patterns needed:
- `\bDocstrings\s+generation\s+was\s+requested\b`
- `\bCodeRabbit\s+cannot\s+perform\s+edits\b`

### Greptile Review (Pattern Exists But...)

The Greptile pattern `\bgreptile\b` exists but many detections are from **review context** (comments/reviews), not PR body. The LLM has access to review data via the user prompt, but regex only scans the PR body.

**Decision**: This is working as designed. Regex detects in PR body, LLM detects from full context. No change needed.

### Cubic (Pattern Exists)

Current patterns:
- `\bsummary\s+by\s+cubic\b`
- `\bauto-generated\s+(?:description\s+)?by\s+cubic\b`
- `\bgenerated\s+by\s+cubic\b`

These should be working. Need to verify match failures.

## Decision Log

| Date | Decision | Rationale |
|------|----------|-----------|
| 2025-12-26 | Focus on explicit text patterns only | Implicit detection (code style inference) belongs to LLM, not regex |
| 2025-12-26 | Add Replexica as new tool | Clear text signatures in PR bodies |
| 2025-12-26 | Add CodeRabbit author patterns | Distinct from review patterns, significant gap (467 PRs) |
| 2025-12-26 | Skip Copilot/Claude/Cursor implicit detection | No text markers, would cause false positives |

## LLM vs Regex Detection Boundaries

### Tools That Cannot Be Improved with Regex

Analysis of 1,668 LLM-only PRs revealed most are **implicit detections** with no text markers:

| Tool | LLM-only Count | Has Text Patterns? | Why? |
|------|----------------|-------------------|------|
| CodeRabbit | 459 | ❌ | Detected from review comments, not body |
| Greptile | 455 | ❌ | Team inference (PostHog 86%, Twenty 12%) |
| Copilot | 162 | ❌ | Code style inference |
| Claude | 145 | ❌ | Code style inference |
| Cursor | 110 | ❌ | Code style inference |
| Cubic | 89 | ❌ | No text markers |
| Devin | 38 | ❌ | No text markers |

**Key Insight**: The LLM detects Greptile with 98% high confidence in PostHog/Twenty PRs despite no "greptile" text. It's inferring from team patterns or code style.

### Detection Role Division

| Detection Type | Best For | Examples |
|---------------|----------|----------|
| **Regex** | Explicit text signatures | "Generated by Claude Code", "@replexica" |
| **LLM** | Implicit/contextual signals | Code style, team patterns, review context |

The 1,668 LLM-only gap represents the **true value** of LLM detection - cases that regex fundamentally cannot handle.

## Dependencies

- None - This is a self-contained pattern update

## Related Work

- `dev/completed/ai-detection-pr-descriptions/` - Original LLM detection implementation
- `dev/completed/enhanced-ai-detection/` - Signal aggregation (commits, reviews, files)

## Testing Strategy

1. **Unit Tests**: Add test cases for each new pattern
2. **Dry Run**: Run backfill with `--dry-run` to see impact
3. **Sampling**: Manually verify 10-20 new detections
4. **Comparison**: Re-run LLM vs regex comparison after backfill

## Commands Reference

```bash
# Run pattern tests
pytest apps/metrics/tests/test_ai_detector.py -v -k "replexica or coderabbit"

# Test pattern matching manually
python manage.py shell -c "
import re
from apps.metrics.services.ai_patterns import AI_SIGNATURE_PATTERNS
text = 'Replexica AI here with fresh translations'
for pattern, tool in AI_SIGNATURE_PATTERNS:
    if re.search(pattern, text, re.IGNORECASE):
        print(f'Matched: {tool} with pattern: {pattern}')
"

# Check current pattern version
python manage.py shell -c "
from apps.metrics.services.ai_patterns import PATTERNS_VERSION
print(f'Current version: {PATTERNS_VERSION}')
"

# Run backfill
python manage.py backfill_ai_detection --team "Cal.com"

# Compare detection after changes
python manage.py shell -c "
from apps.metrics.models import PullRequest
from django.db.models import Q

# Count LLM-only detections
llm_only = PullRequest.objects.filter(
    llm_summary__ai__is_assisted=True,
    llm_summary__ai__confidence__gte=0.5,
    is_ai_assisted=False
).count()
print(f'LLM-only (gap): {llm_only}')

# Count regex-only detections
regex_only = PullRequest.objects.filter(
    is_ai_assisted=True,
    llm_summary__ai__is_assisted=False
).count()
print(f'Regex-only (potential FP): {regex_only}')
"
```
