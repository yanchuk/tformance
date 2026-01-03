# Pricing Positioning Deep Dive

## Product Specification

**Author:** Product & Engineering
**Status:** Draft
**Decision:** TBD - requires validation with beta customers
**Priority:** HIGH - needed before MVP launch
**Timeline:** Finalize by end of beta period
**Created:** January 2026

---

## The Core Question

> "A 100-engineer team needs to pay $30,000/year. It's not a lot for such a company, but still significant and a barrier for smaller teams."

---

## 1. The Math: What Teams Actually Pay Today

### Competitor Annual Cost at Scale

| Team Size | Jellyfish ($50) | LinearB ($40) | Swarmia (€42) | **Us ($20)** |
|-----------|-----------------|---------------|---------------|--------------|
| **10 devs** | $6,000 | $4,800 | $5,040 | **$2,400** |
| **25 devs** | $15,000 | $12,000 | $12,600 | **$6,000** |
| **50 devs** | $30,000 | $24,000 | $25,200 | **$12,000** |
| **100 devs** | $60,000 | $48,000 | $50,400 | **$24,000** |
| **250 devs** | $150,000 | $120,000 | $126,000 | **$60,000** |

**Reality check:** At $30-50/seat, a 100-person team pays **$36,000-$60,000/year** for Jellyfish/LinearB/Swarmia.

---

## 2. How Competitors Justify Per-Seat Pricing

### The Value Story They Tell

| Competitor | Justification | Target Buyer |
|------------|---------------|--------------|
| **Jellyfish** | "Engineering intelligence at enterprise scale" - R&D capitalization, budget forecasting, DevFinOps | CFO + CTO |
| **LinearB** | "100M+ developer workflows automated" - Time savings per developer | Engineering Manager |
| **Swarmia** | "DORA metrics + DevEx surveys" - Industry benchmarks, team health | VP Engineering |
| **Span** | "95% AI detection accuracy" - AI ROI measurement | CTO evaluating AI spend |

### Why Per-Seat "Works" for Enterprise

1. **Budget predictability** - "I know exactly what I'll pay"
2. **Value scales with team** - More engineers = more value (in theory)
3. **Enterprise procurement** - IT buyers understand per-seat models
4. **Revenue predictability** - Stable MRR for the vendor

---

## 3. The Problems with Per-Seat Pricing

### User Complaints (Real Feedback)

| Source | Complaint |
|--------|-----------|
| Capterra - LinearB | "It's a little expensive" |
| Swarmia user | "Great product, ridiculous pricing" |
| G2 - Jellyfish | "Permissioning too rigid", "these metrics could be abused" |
| General | "Hidden tax on growth" - as team grows, cost grows even if value doesn't scale linearly |

### Structural Issues

| Problem | Impact |
|---------|--------|
| **Not all seats are equal** | Junior dev vs Staff engineer get same value? |
| **Seat sharing temptation** | Teams share logins to reduce cost |
| **Barrier to pilots** | Hard to try with 5 people when you'll need 50 |
| **Growth penalty** | Hire 10 people, pay $4,000 more (at $40/seat) |

---

## 4. Alternative Pricing Models Analysis

### Model 1: Per Active User (Slack Model)

**How it works:** Only charge for users who actually use the platform

**Slack's Fair Billing:**
- User marked dormant after 14 days of inactivity
- Prorated credit applied to account
- Result: **8.6% free-to-paid conversion** (vs 2-5% industry average)

**For Tformance:**
- Reduces adoption friction
- Only active contributors pay
- Engineering analytics is different - you want data on ALL engineers, not just active dashboard users

**Verdict:** Doesn't quite fit. Our value is tracking all developers, not just dashboard users.

---

### Model 2: Per Repository

**How it works:** Charge based on number of connected repos

| Tier | Repos | Price |
|------|-------|-------|
| Starter | 5 repos | Free |
| Team | 25 repos | $99/mo |
| Business | Unlimited | $299/mo |

**Pros:**
- Decouples from team size
- Small team with many repos pays more (often power users)
- Clear value unit (each repo = data)

**Cons:**
- Monorepo teams pay less than multi-repo teams for same value
- Doesn't correlate well with engineering complexity
- No industry precedent in this space

**Verdict:** Interesting but risky. Could attract monorepo teams gaming the model.

---

### Model 3: Per PR/Commit (Usage-Based)

**How it works:** Charge based on data volume processed

| Tier | PRs/month | Price |
|------|-----------|-------|
| Starter | 500 PRs | Free |
| Growth | 2,000 PRs | $199/mo |
| Scale | 10,000 PRs | $499/mo |
| Enterprise | Unlimited | Custom |

**Pros:**
- True usage correlation
- High-velocity teams pay more (get more value)
- Low-velocity teams don't overpay
- Aligns with AI analysis costs (more PRs = more LLM calls)

**Cons:**
- Revenue unpredictability for us
- Budget unpredictability for customers
- Teams may avoid merging to stay under limits

**Verdict:** Could work as a **hybrid component** (base + overage).

---

### Model 4: Tiered Flat Rate

**How it works:** Fixed price per tier based on rough team size

| Tier | Team Size | Price/mo | Per-Dev Equivalent |
|------|-----------|----------|-------------------|
| Starter | 1-10 | Free | Free |
| Team | 11-25 | $199 | $8-18/dev |
| Business | 26-75 | $499 | $7-19/dev |
| Enterprise | 76-200 | $999 | $5-13/dev |
| Scale | 200+ | Custom | Negotiated |

**Pros:**
- Simple mental model
- "Unlocks" at each tier (no per-seat anxiety)
- Growing from 25→26 doesn't feel like punishment
- Volume discount built-in

**Cons:**
- Cliff effects at tier boundaries
- Less revenue from large teams vs per-seat
- 25-dev team pays same as 11-dev team

**Verdict:** **Strong contender** for SMB focus. Simpler story than per-seat.

---

### Model 5: Hybrid (Base + Usage)

**How it works:** Platform fee + usage-based component

```
Monthly Cost = Base Platform Fee + (PRs analyzed × $0.05)
```

| Component | Example |
|-----------|---------|
| Base fee | $99/mo (includes 1,000 PRs) |
| Overage | $0.05/PR beyond included |
| AI Insights | $0.10/PR for LLM analysis |

**Example: 50-person team, 800 PRs/month**
- Base: $99
- PRs: Included
- AI Insights: 800 × $0.10 = $80
- **Total: $179/mo ($2,148/yr)**

**Pros:**
- Aligns cost with our costs (LLM usage)
- Light users pay less
- Power users pay more (but get more value)
- 38% higher net revenue retention vs pure subscription

**Cons:**
- More complex to explain
- Variable bills (some enterprises hate this)

**Verdict:** **Most aligned with value delivery** but needs careful positioning.

---

## 5. Budget Context: What's "Expensive"?

### Developer Cost Comparison

| Line Item | Annual Cost (100-dev team) |
|-----------|---------------------------|
| **Developer salaries** | $15,000,000 - $25,000,000 |
| **GitHub Enterprise** | $25,200 ($21/seat × 12) |
| **Jira Premium** | $86,400 ($72/seat × 12) |
| **Slack Business+** | $150,000 ($12.50/seat × 12) |
| **Tformance @ $20/seat** | **$24,000** |
| **Jellyfish @ $50/seat** | $60,000 |

### The Math CTOs Do

```
$24,000/year ÷ $20,000,000 payroll = 0.12% of eng cost

If we save 1% of eng time through better metrics = $200,000 value
ROI = 8.3x
```

**Reality:** At $20-30K/year, the tool is **rounding error** on eng budget. The question isn't "is it expensive" but "does it deliver value?"

---

## 6. The Barrier Problem for Smaller Teams

### Team Size Economics

| Team Size | Annual Cost @ $20 | Pain Level | Decision Maker |
|-----------|-------------------|------------|----------------|
| **5 devs** | $1,200 | Low | CTO credit card |
| **15 devs** | $3,600 | Low | Eng Manager approval |
| **30 devs** | $7,200 | Medium | Budget line item |
| **50 devs** | $12,000 | Medium | VP approval |
| **100 devs** | $24,000 | Medium-High | Procurement involved |
| **250 devs** | $60,000 | High | Enterprise sales |

### Trial vs Free Tier Strategy

Competitors use free tiers, but trials can be more effective:

| Competitor | Free Tier | Strategy |
|------------|-----------|----------|
| **Swarmia** | 9 developers | Land in small teams, expand |
| **LinearB** | 8 contributors | Same |
| **Workweave** | 5 developers | Same |
| **GitHub** | Unlimited (limited features) | Freemium upsell |

**Why we chose trial over free tier:**

| Factor | Free Tier | Extended Trial |
|--------|-----------|----------------|
| Lead quality | Lower (tire-kickers) | Higher (serious evaluators) |
| Support burden | Higher (no skin in game) | Lower (time-limited) |
| Conversion intent | Passive | Active (deadline creates urgency) |
| Feature access | Usually limited | Full (better evaluation) |
| Revenue certainty | Delayed indefinitely | Clear 30-day decision point |

**Our approach:** 30-day no-card trial with full features, then minimum $99/mo. Low friction signup, but time limit creates urgency to convert. Filters for serious evaluators while reducing support load.

---

## 7. Pricing Recommendations

### Option A: Simplified Tiered (Recommended for MVP)

| Tier | Size | Price | Per-Dev | Features |
|------|------|-------|---------|----------|
| **Trial** | Any size | $0 | Free | Full features, 30 days, no card required |
| **Starter** | ≤10 devs | $99/mo | $10-99 | Full metrics, AI insights, 1-year history |
| **Team** | 11-50 devs | $299/mo | $6-27 | Full metrics, AI insights, 1-year history |
| **Business** | 51-150 devs | $699/mo | $5-14 | + Jira deep analysis, custom reports |
| **Enterprise** | 150+ | Custom | Negotiated | + SSO, SLA, dedicated support |

**Why this works:**
- Extended trial (30 days) to prove value before commitment
- No free tier = qualified leads only, reduces support burden
- Starter tier ($99) captures small teams willing to pay
- No "per-seat anxiety" - one price per tier
- Volume discount built into structure
- Clear upgrade triggers (team size)

---

### Option B: Per-Seat with Fair Billing (Slack-Style)

| Tier | Price/Active Dev | Notes |
|------|-----------------|-------|
| **Trial** | $0 | 30-day full access, no card required |
| **Pro** | $15/active/mo | Only pay for devs with activity in billing period |
| **Enterprise** | $25/active/mo | + advanced features |

**"Active" defined as:** Had a merged PR in the billing period

**Why this could work:**
- Fair - only pay for value delivered
- Trial converts to paid with clear value demonstration
- Marketing story: "We only charge for developers who ship"
- Revenue less predictable

---

### Option C: Hybrid Base + AI (Usage-Aligned)

| Component | Price |
|-----------|-------|
| **Platform Base** | $199/mo (includes 50 devs, 1,000 PRs) |
| **Additional devs** | $5/dev/mo |
| **PR overage** | $0.02/PR beyond 1,000 |
| **AI Insights** | $0.10/PR analyzed |

**Example costs:**

| Scenario | Cost |
|----------|------|
| 30 devs, 500 PRs, no AI | $199 |
| 50 devs, 1,000 PRs, all AI | $199 + $100 AI = $299 |
| 100 devs, 2,000 PRs, all AI | $199 + $250 + $20 + $200 = $669 |

**Why this could work:**
- Our costs scale with usage (LLM calls)
- Light users pay less
- AI insights are clear premium
- Complex to explain initially

---

## 8. Recommendation

### For MVP Launch: Option A (Tiered Flat Rate)

**Rationale:**
1. **Simplicity wins** - Easy to understand, easy to budget
2. **Extended trial (30 days)** - Prove value before asking for payment
3. **No free tier** - Qualified leads only, better conversion quality
4. **No per-seat anxiety** - Team of 25 pays same as team of 11
5. **Low entry point** - $99/mo Starter tier captures small teams
6. **Clear upgrade path** - When you hit 51, you need Business tier
7. **Undercuts competitors** - $299/mo for 50 devs vs $2,000+/mo at LinearB

### Future Evolution: Add Usage Component

Once you have paying customers:
1. Track actual LLM costs per team
2. Identify power users vs light users
3. Consider: "AI Insights" as paid add-on (per-PR pricing)
4. This aligns with 73% of SaaS moving to hybrid by 2025

---

## 9. Positioning Against "It's Expensive"

### Story 1: Cost vs Value

> "Tformance costs $299/month. Your team's salary costs $200,000/month. If we help you ship 1% faster, that's $2,000/month in value. 7x ROI."

### Story 2: Per-Developer Math

> "At $299/month for 30 developers, that's $10/dev/month. Less than a Spotify subscription. For visibility into whether your AI investment is working."

### Story 3: Alternative Cost

> "Jellyfish charges $50/seat. LinearB charges $40/seat. We charge $6-10/seat equivalent. Same insights, 80% less cost."

### Story 4: The Trial Path

> "Start with a 30-day trial, full features, your whole team. No credit card required. Prove the value before you pay a cent."

---

## 10. Summary

| Question | Answer |
|----------|--------|
| **Is $30K/year for 100 engineers expensive?** | No - it's 0.12% of eng payroll. But **perceived** as expensive because of per-seat anxiety |
| **Per-repo pricing?** | Risky - monorepos game it. No industry precedent |
| **Per-PR pricing?** | Works as **add-on** for AI insights, not as primary model |
| **Best model for MVP?** | **Tiered flat rate** - simple, trial-to-paid conversion, undercuts competitors |
| **How to justify price?** | ROI story: 1% efficiency gain = 8x return on tool cost |

**Final recommendation:** Launch with **tiered flat rate** (Trial → $99 / $299 / $699 / Custom), then evolve to hybrid with AI insights as usage-based add-on.

---

## References

- [Slack's Fair Billing Policy](https://slack.com/help/articles/218915077-Slacks-Fair-Billing-Policy) - Per-active-user model
- [SaaS Pricing Models Guide](https://www.revenera.com/blog/software-monetization/saas-pricing-models-guide/) - Model comparison
- [Per-Seat vs Usage-Based Pricing](https://helloadvisr.com/foundation/per-seat-vs-usage-based-pricing-which-is-right-for-saas/) - Decision framework
- [Hybrid Pricing in SaaS](https://www.chargebee.com/blog/hybrid-pricing-model-in-saas/) - 73% adoption trend
- [OpenView SaaS Benchmarks](https://openviewpartners.com/) - 38% higher retention with hybrid
- [Bain: Per-Seat Not Dead](https://www.bain.com/insights/per-seat-software-pricing-isnt-dead-but-new-models-are-gaining-steam/) - Industry analysis
- [Stack Overflow 2025 Survey](https://survey.stackoverflow.co/2025/) - "Prohibitive pricing" as #2 rejection factor
- [ICONIQ Engineering Efficiency Report](https://medium.com/iconiq-growth/how-does-your-engineering-organization-stack-up-the-2021-iconiq-engineering-efficiency-report-b9c08c34250d) - Budget benchmarks
- [Per User Pricing: Kill Growth](https://www.scalecrush.io/blog/saas-per-user-pricing) - Per-seat criticism
- [Jellyfish Alternatives](https://www.chronoplatform.com/blog/jellyfish-alternatives) - Competitor analysis
- [GitLab Pricing](https://about.gitlab.com/pricing/) - Developer tool pricing reference
- [GitHub Pricing](https://github.com/pricing) - Developer tool pricing reference

---

*Created: January 2026*
