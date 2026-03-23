# Outreach Sprint Tracker

**Sprint dates:** 2026-03-22 → 2026-04-19 (4 weeks)
**Goal:** 15-20 CTO conversations, 3+ "would pay" responses

---

## Sequencing (Codex review fix)

**Step 0 (this week):** Approach your own company about being a design partner. This is your strongest signal and should be the FIRST conversation, not an open question.

**Step 1 (parallel from Week 1):** Run BOTH cold outreach AND warm intro requests simultaneously. Don't wait until Week 2 to activate warm intros — cold DM response rates are 3-8%, so you need a larger pipeline than 20 targets.

**Pipeline math:** To get 15 conversations, plan for ~50 DMs (assuming 30% response rate from warm community + cold LinkedIn mix). Track response rate by channel to learn which works.

## Week 1-2: Outreach (Target: 50 DMs sent, 15 conversations booked)

| # | Name | Company | Team Size | Source | DM Sent | Response | Call Booked | Call Done | Notes |
|---|------|---------|-----------|--------|---------|----------|-------------|-----------|-------|
| 1 | | | | | | | | | |
| 2 | | | | | | | | | |
| 3 | | | | | | | | | |
| 4 | | | | | | | | | |
| 5 | | | | | | | | | |
| 6 | | | | | | | | | |
| 7 | | | | | | | | | |
| 8 | | | | | | | | | |
| 9 | | | | | | | | | |
| 10 | | | | | | | | | |
| 11 | | | | | | | | | |
| 12 | | | | | | | | | |
| 13 | | | | | | | | | |
| 14 | | | | | | | | | |
| 15 | | | | | | | | | |
| 16 | | | | | | | | | |
| 17 | | | | | | | | | |
| 18 | | | | | | | | | |
| 19 | | | | | | | | | |
| 20 | | | | | | | | | |

## Scorecard

| Metric | Target | Actual |
|--------|--------|--------|
| DMs sent | 20 | |
| Responses received | 8+ | |
| Conversations completed | 15-20 | |
| "Would pay" responses | 3+ | |
| Must-have feature identified | 1 clear pattern | |
| Design partners secured | 1-2 | |

## Conversation Summaries

Link to each completed conversation capture:

| # | Name | Date | ICP Fit | Would Pay? | Key Insight | File |
|---|------|------|---------|------------|-------------|------|
| | | | | | | |

## Fallback Plan

If fewer than 5 conversations by end of Week 2:
- Pivot to warm intros through investors, advisors, or engineering leadership communities
- Supplement with LinkedIn outreach to engineering leaders at Series A-D companies (50-200 engineers)
- Consider posting in engineering communities with a genuine question, not a pitch

## Week 3-4: Synthesize (Evidence Memo First, Then Rewrites)

**Step 1: Evidence memo** (do this BEFORE rewriting strategy docs)

Write a 1-page evidence memo at `docs/sales/evidence-memo.md` with:
- [ ] Tally pain categories across all conversations
- [ ] Identify top 3 feature requests
- [ ] Response rate by channel (community vs LinkedIn vs warm intro)
- [ ] Segment comparison (A: 15-50 eng vs B: 51-150 eng vs C: 150+)
- [ ] Determine real ICP vs. hypothesized ICP
- [ ] Decide on wedge (AI detection? Review bottlenecks? Multi-signal performance?)
- [ ] Key quotes that support or contradict each premise (P1-P4)

**Step 2: Strategy doc rewrites** (only if evidence memo shows clear patterns)

- [ ] Rewrite `prd/dna_codex.md` — update wedge based on what buyers care about
- [ ] Rewrite `prd/icp_target_audience_codex.md` — update firmographics based on genuine demand
- [ ] Rewrite `prd/gtm_go_to_market_codex.md` — update channels based on conversation learnings
- [ ] Align `prd/PRD-MVP.md` pricing with willingness-to-pay data
- [ ] Update `prd/COMPETITOR-RESEARCH.md` with any new competitors mentioned

If the evidence memo doesn't show clear patterns after 15 conversations, do NOT rewrite yet — run 10 more conversations with tighter targeting.

## What NOT To Do During This Sprint

- Do NOT build new features
- Do NOT rewrite strategy docs before conversations (evidence memo first)
- Do NOT expand integrations
- Do NOT optimize public pages for SEO
- The product is good enough for demos. The strategy is not good enough for customers.

**Exception (Codex review fix):** If a conversation reveals a demo blocker (crash, broken flow, missing data) that would kill the next conversation, fix it. But ONLY the blocker — no scope creep. Log any fix in the tracker with "DEMO FIX: [what and why]".
