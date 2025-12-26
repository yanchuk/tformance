# Report Improvements - Context

**Last Updated: 2025-12-27**

## Overview

Implement improvements to the AI Impact Research Report (GitHub Pages) based on critical review comparing our findings to Stack Overflow 2025 and JetBrains 2025 industry surveys.

## Problem Statement

The current report has 8 debate points that could undermine credibility:
1. **Adoption gap** (21% vs 84%) - not explained well
2. **Missing Copilot/ChatGPT** - dominant tools in surveys but absent in our data
3. **+42% cycle time** - contradicts industry productivity claims
4. **Agent metrics** - denominator unclear
5. **Trust data missing** - major industry trend not included
6. **"Sweet spot" claim** - stated as fact without qualification
7. **Selection bias** - mentioned but not quantified
8. **Detection accuracy** - false negatives unknown

## Key Industry Data

| Source | Metric | Value |
|--------|--------|-------|
| Stack Overflow 2025 | Use or plan to use AI | 84% |
| Stack Overflow 2025 | Professional devs using AI daily | 51% |
| Stack Overflow 2025 | Distrust AI outputs | 46% |
| Stack Overflow 2025 | Trust AI outputs | 33% |
| Stack Overflow 2025 | Say AI improved productivity | 52% |
| JetBrains 2025 | Regularly use AI for coding | 85% |
| JetBrains 2025 | Use AI coding assistant/agent | 62% |
| JetBrains 2025 | Save 1+ hour/week | 88% |
| **Our Report** | Detected AI in OSS PRs | 21.4% |

## Key Files

| File | Purpose |
|------|---------|
| `docs/index.html` | Main research report |
| `dev/active/report-critical-review.md` | Full critical review with 8 debate points |

## Decisions Made

1. **Priority Order**: HIGH risk items first (Copilot/ChatGPT disclosure, adoption gap)
2. **Approach**: Add disclosure sections, not rewrite findings
3. **Tone**: Transparent about limitations while maintaining value of behavioral data

## Dependencies

- None (standalone HTML file)
- No Django changes needed
- No migrations

## Related Documents

- `dev/active/report-critical-review.md` - Full analysis
- Stack Overflow 2025: https://survey.stackoverflow.co/2025/ai
- JetBrains 2025: https://devecosystem-2025.jetbrains.com/artificial-intelligence
