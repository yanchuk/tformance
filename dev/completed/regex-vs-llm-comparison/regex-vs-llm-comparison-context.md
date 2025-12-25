# Regex vs LLM Detection Comparison - Context

**Last Updated: 2025-12-25**

## Status: ✅ v1.9.0 COMPLETE - Pattern Improvements Deployed

Pattern v1.9.0 implemented, backfilled, and analyzed. 33% reduction in regex FPs.

---

## Session Summary (2025-12-25)

### What Was Accomplished

1. **Implemented v1.9.0 patterns** in `ai_patterns.py`
2. **Backfilled 5,654 PRs** with new patterns via Django shell
3. **Ran 10 rounds of analysis** across all 25 OSS repos
4. **Updated documentation** with v1.9.0 results

### v1.9.0 Changes Made

| Action | Pattern | Result |
|--------|---------|--------|
| Added | greptile bot usernames | +1 detection |
| Added | greptile text patterns | Context detection |
| Improved | cubic patterns (commit markers) | Better coverage |
| **REMOVED** | AI Disclosure headers | **-5 FPs** |

### Key Results (4,980 PRs)

| Metric | v1.8.0 | v1.9.0 | Change |
|--------|--------|--------|--------|
| **Regex FPs** | 15 | 10 | **-33%** |
| Agreement Rate | 96.61% | 96.62% | +0.01% |
| Regex AI Rate | 23.61% | 23.43% | -0.18% |
| LLM AI Rate | 26.41% | 26.41% | - |
| Both_AI | 1,161 | 1,157 | -4 |
| LLM_Only | 154 | 158 | +4 |

---

## Key Decisions Made This Session

### 1. Removed AI Disclosure Header Patterns
**Why**: Patterns like `"### AI Disclosure"` triggered FPs when followed by "No AI was used".
Regex cannot understand negation context - LLM handles this correctly.

### 2. Remaining 10 FPs Are Context-Dependent
All remaining FPs are product/documentation mentions that cannot be fixed with regex:
- anthropic-cookbook: Claude Code SDK docs
- PostHog: AI product features
- FastAPI: Greptile sponsor announcement
- SDK dependency bumps

**Conclusion**: These require semantic understanding (LLM).

### 3. Detection is Repo-Dependent (User's Observation Confirmed)
- **High agreement**: dubinc (99.3%), makeplane (83.5%)
- **LLM advantage**: coollabsio (+10.4%), formbricks (+7.7%)
- Repos with explicit AI signatures show perfect regex/LLM agreement
- Repos with implicit AI usage show LLM advantage

---

## Files Modified This Session

| File | Changes |
|------|---------|
| `apps/metrics/services/ai_patterns.py` | v1.9.0 - Added greptile, improved cubic, removed FP-prone patterns |
| `dev/active/regex-vs-llm-comparison/RESEARCH-SYNTHESIS.md` | Updated with v1.9.0 results |
| `dev/active/regex-vs-llm-comparison/regex-vs-llm-comparison-tasks.md` | Marked P0 complete |
| `dev/active/HANDOFF-NOTES.md` | Updated with session summary |

---

## Backfill Script Used

```python
# Ran in Django shell to backfill all PRs
from apps.metrics.models import PullRequest
from apps.metrics.services.ai_detector import detect_ai_in_text
from apps.metrics.services.ai_patterns import PATTERNS_VERSION

prs = PullRequest.objects.all()
batch_size = 500
updated = 0

for i in range(0, prs.count(), batch_size):
    batch = list(prs[i:i+batch_size])
    for pr in batch:
        text = f'{pr.title or ""} {pr.body or ""}'
        result = detect_ai_in_text(text)
        pr.is_ai_assisted = result['is_ai_assisted']
        pr.ai_tools_detected = result['ai_tools']
        pr.ai_detection_version = PATTERNS_VERSION
    PullRequest.objects.bulk_update(batch, ['is_ai_assisted', 'ai_tools_detected', 'ai_detection_version'])
    updated += len(batch)
    print(f'Updated {updated}')
```

---

## Remaining 10 Regex FPs (Cannot Fix)

| Repo | PR | Pattern | Why FP |
|------|-----|---------|--------|
| documenso | #2305 | ai_generic | "AI features more discoverable" - product |
| PostHog | #43805 | ai_generic | "AI-first session summarization" - product |
| PostHog/posthog-js | #2728 | claude | @anthropic-ai/sdk bump - dependency |
| PostHog/posthog-js | #2734 | claude | AI providers group bump - dependency |
| anthropics/courses | #104 | claude | "Update to latest Claude models" - docs |
| anthropics/cookbook | #229 | claude_code | Claude Code SDK - product |
| anthropics/cookbook | #232 | claude_code+claude | Legacy models - docs |
| anthropics/cookbook | #260 | claude_code | GitHub Actions workflow - product |
| neondatabase | #176 | claude_code | Playwright bump with mention |
| tiangolo/fastapi | #14429 | greptile | Sponsor announcement |

---

## Commands to Verify State

```bash
# Check database state
.venv/bin/python manage.py shell -c "
from apps.metrics.models import PullRequest
print(f'Total PRs: {PullRequest.objects.count()}')
print(f'AI-Assisted: {PullRequest.objects.filter(is_ai_assisted=True).count()}')
print(f'Detection version: {PullRequest.objects.values(\"ai_detection_version\").distinct()}')"

# Run tests
make test

# View confusion matrix
.venv/bin/python manage.py shell -c "
from apps.metrics.models import PullRequest
qs = PullRequest.objects.exclude(llm_summary__isnull=True)
regex_only = qs.filter(is_ai_assisted=True).extra(where=[\"(llm_summary->'ai'->>'is_assisted')::boolean = false\"]).count()
print(f'Regex-only FPs: {regex_only}')"  # Should be 10
```

---

## Next Steps (Future Work)

### P1: Additional Pattern Improvements
- [ ] Add Cursor IDE patterns (+16 expected detections)
- [ ] Improve Copilot patterns (+27 expected detections)

### P2: LLM Improvements
- [ ] Set confidence threshold to 0.90 in production
- [ ] Add "require explicit evidence" to prompt

### P3: Data Expansion
- [ ] Run Q1-Q3 2025 seeding scripts
- [ ] Re-analyze with full year data

---

## No Migrations Needed

This session modified regex patterns only. No Django models changed.
