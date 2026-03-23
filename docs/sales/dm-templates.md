# Outreach DM Templates

**Created:** 2026-03-22
**Purpose:** Insight-led outreach to CTOs — not a pitch, a conversation starter.
**Rule:** Personalize every message. Generic DMs get ignored.

---

## Template 0: Discovery-First (RECOMMENDED for first 5 conversations)

Use when: ANY first conversation. Leads with questions, not the product. Avoids confirmation bias.

> Hey [name], I'm an engineering leader building a tool in the engineering analytics space. Before I go further, I'm trying to understand how CTOs at companies your size actually think about measuring team performance and AI tool impact.
>
> I have three questions I'm asking engineering leaders — takes 15 minutes max. No demo, no pitch. Just trying to learn whether the problem I'm working on is the right problem.
>
> Would you be up for a quick conversation?

**Why this template exists:** Codex review flagged that the other templates sell a specific wedge (review bottlenecks, AI correlation) and then ask for a demo — which manufactures confirmation instead of learning. Use this template for your first 5 conversations to get unbiased signal. Switch to the insight-led templates (1-5) once you know which pain resonates.

---

## Template 1: Review Bottleneck Signal

Use when: You've seen their team has high PR volume or public repos with slow review patterns.

> Hey [name], I noticed [company] has been shipping a lot — your team's PR volume in [repo/area] is impressive. I've been building a tool that surfaces review bottlenecks and delivery patterns from GitHub data, and I'm curious whether review turnaround is something your team thinks about.
>
> Not selling anything — trying to understand if this solves a real problem for teams your size. Would you be open to a 15-minute look?

---

## Template 2: AI Tool Evaluation Signal

Use when: They've mentioned AI tools, Copilot rollout, or AI ROI in community discussions.

> Hey [name], I saw your comment about [specific thing they said about AI tools / Copilot / Cursor]. I've been working on a way to correlate AI tool usage with actual delivery metrics — cycle time, review health, throughput — because most teams I talk to say they feel faster but can't prove it.
>
> Would you be open to a 15-minute conversation? I'm not pitching — I'm trying to figure out whether the problem I'm solving is the right problem.

---

## Template 3: Internal Dashboard Builder

Use when: They've mentioned building internal engineering dashboards or spreadsheets.

> Hey [name], I heard you've been building internal dashboards for engineering metrics at [company]. I did the same thing at my company (100 engineers) before I started building Tformance — a tool that pulls delivery metrics and AI impact signals from GitHub.
>
> I'm curious what you ended up building and whether it actually gives your leadership the answers they need. Would you be up for a quick 15-minute chat? I'll share what we built too.

---

## Template 4: Measurement Pain Signal (from CTO community)

Use when: They've expressed frustration about measuring team performance or AI impact in community channels.

> Hey [name], your point about [specific pain they mentioned — e.g., "not knowing if Copilot is actually helping"] resonated with me. I've been building a tool that tries to answer exactly that question by correlating GitHub PR data with AI usage signals.
>
> I'd love to hear how you're currently thinking about measuring this. Not a sales call — genuinely trying to understand whether the approach I'm taking makes sense for teams like yours. 15 minutes?

---

## Template 5: Cold Outreach (no prior signal)

Use when: LinkedIn outreach to engineering leaders at Series A-D companies with 50-200 engineers, no prior interaction.

> Hey [name], I'm building Tformance — engineering analytics that helps CTOs understand team delivery patterns and AI tool impact without enterprise pricing or setup.
>
> I'm reaching out to engineering leaders at companies your size because I think the existing tools (Jellyfish, Swarmia, etc.) are either too expensive or too broad for what most teams actually need.
>
> Would you be open to a 15-minute conversation about how you currently measure engineering performance? I'll show you what I've built — real data from OSS repos — and I'm genuinely looking for feedback on whether this solves a problem you have.

---

## Personalization Checklist

Before sending any DM:

- [ ] Mention something specific about their company, team, or a comment they made
- [ ] Reference their team size or stage if you know it
- [ ] Make clear this is a conversation, not a demo request
- [ ] Keep it under 100 words (excluding the greeting)
- [ ] Do NOT mention pricing
- [ ] Do NOT attach slides or PDFs
- [ ] Do NOT use phrases like "I'd love to pick your brain" or "quick sync"

## Follow-Up (if no response after 5 days)

> Hey [name], just bumping this — no pressure at all. If you're not the right person to talk to about engineering metrics, happy to be pointed in the right direction. Either way, no hard feelings.

---

## Template 6: Warm Intro Request (for investors/advisors)

Use when: Cold outreach response rate is low (<5%) and you need warm intros through your network.

> Hey [advisor/investor name], I'm looking for engineering leaders at Series A-D companies (50-200 engineers) who are thinking about measuring AI tool impact or team delivery patterns.
>
> I'm not pitching — I'm running a discovery sprint to understand whether the problem I'm solving with Tformance is the right problem. I just need 15-minute conversations.
>
> Do you know 2-3 CTOs or VP Engs who might be open to a quick chat? Happy to share what I learn with you afterward — the market data is interesting.

---

## SOC2 Objection Playbook

If SOC2 comes up in conversations, here's how to handle it:

**Their concern:** "We can't connect tools without SOC2 compliance."

**Your response framework:**

1. **Acknowledge:** "That's a fair concern. SOC2 is on our roadmap for [Q3/Q4 2026]."

2. **Reframe:** "For this conversation, I'm more interested in whether the problem we're solving resonates — does your team struggle with [the specific pain they mentioned]? If the product itself isn't valuable, SOC2 compliance doesn't matter."

3. **Offer alternatives:**
   - "We can do a demo with public/OSS data — no connection needed."
   - "Would a design partner arrangement work? Early access in exchange for feedback, with SOC2 completed before production use."
   - "We already use read-only GitHub permissions. Happy to share our security architecture."

4. **Qualify the blocker:**
   - "Is SOC2 a hard requirement before any evaluation, or before production deployment?"
   - "Does your team currently use any tools without SOC2?" (many do)

**What to capture:** Note whether SOC2 is a hard blocker (won't even evaluate) or a soft blocker (would evaluate but can't deploy). The difference matters for prioritization.

---

## What To Show In The Demo

If they say yes, here's what to walk through:

1. **Public pages** — show real OSS repo analytics (use a well-known repo)
2. **Dashboard** — show the team delivery overview with cycle time, throughput, review health
3. **AI correlation view** — show how AI-assisted PRs compare to non-AI PRs
4. **Ask the hard questions** (see conversation-capture-template.md)

Keep the demo under 10 minutes. Spend the remaining time asking questions and listening.
