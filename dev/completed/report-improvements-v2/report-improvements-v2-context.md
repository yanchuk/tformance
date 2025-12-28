# Report Improvements V2 - Context

**Last Updated: 2025-12-27**

---

## Overview

Comprehensive improvements to the AI Impact Research Report (docs/index.html) addressing 8 credibility risks while adding unique Code AI vs Review AI differentiation.

## Problem Statement

The current report has credibility risks when compared to industry surveys:
1. **21% vs 84% adoption gap** - appears to contradict Stack Overflow/JetBrains
2. **Missing Copilot/ChatGPT** - dominant tools absent from our rankings
3. **+42% cycle time** - contradicts productivity claims without causation disclaimer
4. **Tool rankings show detectability, not popularity** - could mislead readers

## Strategic Context

### Competitive Landscape (Dec 2025)

| Report | Data Type | Sample | Key Finding |
|--------|-----------|--------|-------------|
| Stack Overflow 2025 | Survey | 65k+ devs | 84% use AI, 46% distrust |
| JetBrains 2025 | Survey | 24,534 devs | 85% use AI, 88% save time |
| METR 2025 | RCT | 16 devs, 246 issues | AI makes devs 19% SLOWER |
| Greptile 2025 | Ecosystem | PyPI/npm | +76% dev output |
| CodeRabbit 2025 | PR analysis | 470 PRs | AI has 1.7x more issues |
| **Tformance** | PR behavioral | 60k+ PRs | 21% detected, +42% cycle time |

### Our Unique Differentiation

1. **Code AI vs Review AI categorization** - No competitor has this
2. **PR-level behavioral data** - Not self-reported surveys
3. **Team-specific metrics** - Can measure YOUR team, not aggregate
4. **Connected platform** - Report is proof-of-concept for product

## Key Files

| File | Purpose |
|------|---------|
| `docs/index.html` | Main research report (GitHub Pages) |
| `docs/scripts/export_report_data.py` | Data export for report |
| `docs/data/*.csv` | Generated data files |
| `dev/active/report-critical-review.md` | 8 debate points analysis |
| `apps/metrics/services/ai_categories.py` | Code AI vs Review AI logic |
| `apps/metrics/services/ai_patterns.py` | Detection patterns |
| `apps/metrics/services/dashboard_service.py` | Metric calculations |

## Key Technical Details

### AI Category System

```python
# From apps/metrics/services/ai_categories.py

CODE_AI_TOOLS = [
    "cursor", "copilot", "claude", "claude_code", "chatgpt",
    "gemini", "windsurf", "codeium", "devin", "aider", ...
]

REVIEW_AI_TOOLS = [
    "coderabbit", "greptile", "cubic", "sourcery", "codacy", ...
]

def get_ai_category(tools: list[str]) -> str | None:
    """Returns: "code" | "review" | "both" | None"""
```

### Detection Priority

```python
# LLM detection has priority over regex patterns
# From PullRequest model

@property
def effective_ai_tools(self) -> list[str]:
    """LLM-detected tools take priority over regex patterns."""
    if self.llm_summary:
        llm_tools = self.llm_summary.get("ai", {}).get("tools", [])
        if llm_tools:
            return llm_tools
    return self.ai_tools_detected or []
```

### Database Schema (Relevant Fields)

```sql
-- metrics_pullrequest
is_ai_assisted: BOOLEAN
ai_tools_detected: JSONB  -- ["cursor", "coderabbit"]
llm_summary: JSONB        -- {ai: {is_assisted, confidence, tools}}
cycle_time_hours: NUMERIC
review_time_hours: NUMERIC
is_revert: BOOLEAN
is_hotfix: BOOLEAN
```

## Decisions Made

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Keep OSS data only | Yes | Enterprise data not available yet |
| Add all disclaimers | Yes | Credibility > bold claims |
| Include METR study | Yes | Only RCT, validates our findings |
| Code AI vs Review AI in report | Yes | Unique differentiator |
| Reframe tool rankings | Yes | "Detectability" framing |

## Industry Data Sources

### Stack Overflow 2025
- URL: https://survey.stackoverflow.co/2025/ai
- Key stats: 84% use/plan to use AI, 46% distrust, 51% daily use
- Trust declined from 43% (2024) to 33% (2025)

### JetBrains 2025
- URL: https://blog.jetbrains.com/research/2025/10/state-of-developer-ecosystem-2025/
- Key stats: 85% use AI, 62% use assistant/agent, 88% save 1+ hr/week
- Sample: 24,534 developers

### METR RCT Study
- URL: https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/
- Key stats: AI makes devs 19% SLOWER (RCT), 43-point perception gap
- Sample: 16 devs, 246 issues
- CRITICAL: Only randomized controlled trial in the space

### Qodo 2025
- URL: https://www.qodo.ai/reports/state-of-ai-code-quality/
- Key stats: 82% daily/weekly AI use, 76% in "red zone"
- Sample: 609 developers

## Risk Register

| Risk | Probability | Impact | Mitigation | Owner |
|------|-------------|--------|------------|-------|
| Export script breaks | Medium | High | Add tests first | Dev |
| Statistical claims challenged | Medium | High | Add disclaimers | Dev |
| Report too long | Medium | Low | Collapsible sections | Dev |
| Data insufficient for categories | Low | Medium | Validate before building | Dev |

## Dependencies

### Completed
- [x] AI category system implemented (`ai_categories.py`)
- [x] Critical review document created
- [x] Current report exists

### Required
- [ ] Database access for data export
- [ ] Updated export script
- [ ] Industry data integration

## Open Questions

1. **Should we publish Code AI vs Review AI methodology?**
   - Pro: Establishes thought leadership
   - Con: Reveals proprietary approach

2. **How prominent should METR study be?**
   - Pro: Validates our counterintuitive findings
   - Con: Might seem like we're attacking AI tools

3. **Should we add interactive elements?**
   - Pro: More engaging
   - Con: More development time

## Related Documents

- `dev/active/report-critical-review.md` - Full 8-point analysis
- `dev/active/AI-INSIGHTS-REPORT-2025.md` - Current report content
- `prd/DASHBOARDS.md` - Dashboard specifications
- `prd/AI-DETECTION-TESTING.md` - Detection methodology
