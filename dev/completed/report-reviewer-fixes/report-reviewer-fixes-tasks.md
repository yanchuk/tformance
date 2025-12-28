# Report Reviewer Fixes - Tasks

**Last Updated: 2025-12-28**

## Phase F1: Fix Data Inconsistencies (P0)
- [x] Verify ai_categories.csv has correct counts (6631, 18534, 52)
- [x] Update report_data_for_llms.md count references to match CSV
- [x] Update content.html.j2 hardcoded values (25,209 → 25,217, 6,633 → 6,631)

## Phase F2: Fix CI Values (P0) - CRITICAL
- [x] Update Code AI cycle CI: +3%/+27% → +4%/+25%
- [x] Update Code AI review CI: -31%/-1% → -32%/+1%
- [x] Add 'n.s.' marker for Code AI review (CI crosses zero)
- [x] Update Review AI cycle CI: -18%/-6% → -18%/-7%
- [x] Update Review AI review CI: -61%/-50% → -60%/-49%
- [x] Add visual indicator in HTML for non-significant results

## Phase F3: Add Sample Size Explanations (P1)
- [x] Add "Understanding the Numbers" section to report_data_for_llms.md
- [x] Explain ai_categories = tool mentions (can have multiple per PR)
- [x] Explain category_metrics = unique PRs
- [x] Add note about 125,573 merged PRs from teams with 500+ PRs

## Phase F4: Elevate Simpson's Paradox Warning (P1)
- [x] Add Simpson's Paradox warning to TL;DR in report_data_for_llms.md
- [x] Add "IMPORTANT CAVEATS" alert box in content.html.j2 TL;DR section
- [x] Include "60% of teams show AI is SLOWER" statistic

## Phase F5: Add Median Warning Box (P1)
- [x] Add prominent "MEDIAN WARNING" section to report_data_for_llms.md
- [x] Include median values: Baseline 5.7h, Code AI 11.4h (+100%), Review AI 6.0h (+5%)
- [x] Explain skew factors (14x, 8x, 12x)
- [x] Add to HTML TL;DR caveats box

## Phase F6: Soften Causal Language (P2)
- [x] Change "Deploy Review AI immediately" → "Review AI correlates with faster cycles"
- [x] Change "Use Code AI selectively" → "Code AI shows mixed correlations"
- [x] Add observational study disclaimer to CTO recommendations
- [x] Update "Key Insight" section to use correlational language

## Phase F7: Additional Improvements
- [x] Add "What This Research SHOWS" and "What This Research Does NOT Show" sections
- [x] Add two-column layout in HTML TL;DR for show/don't sections
- [x] Add "About the Author" section with Oleksii Ianchuk bio
- [x] Remove Claude Code mention from bio
- [x] Remove Discord link (not available yet)
- [x] Fix LinkedIn URL to correct one (linkedin.com/in/yanch/)

## Phase F8: Round 2 Peer Review Feedback (2025-12-28)
- [x] Add bot speed caveat for Review AI (bots auto-comment instantly)
- [x] Strengthen Copilot invisibility warning (68% industry adoption)
- [x] Add clustering caveat for CIs (PR-level, not team-level)
- [x] Fix formula inconsistency (clarify bootstrap vs proportion)
- [x] Create prominent Median Reality Check section in TL;DR
- [x] Update HTML template with all new caveats and median section

## Final Verification
- [x] Regenerate report with build_report.py
- [x] Verify LinkedIn URL in generated HTML
- [x] Commit and push Round 1 changes
- [x] Commit and push Round 2 changes
