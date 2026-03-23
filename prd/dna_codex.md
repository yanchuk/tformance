# Tformance Product DNA

> **VALIDATION STATUS (2026-03-22)**
>
> This document has not been validated with customers. Key premises challenged:
>
> | Premise | Status | Issue |
> |---------|--------|-------|
> | "AI Detection is the wedge" (Section: Core Capabilities §3) | INVALID | Founder's own company rejected PR-level detection, chose usegitai.com (git-level). METR research shows devs perceive 24% speedup while actually 19% slower. Detection layer and feasibility both questionable. |
> | Public proof surfaces as primary acquisition (Section: Product Loop §7) | PREMATURE | ~14K lines invested, 0 signups. Built "for fun." Pages should come after product-market fit. |
> | Flat-rate pricing ($99/$299/$699) | CONTRADICTED | PRD-MVP says per-seat ($10-25/seat). Neither validated with buyers. Docs need alignment after customer conversations. |
>
> **DO NOT REWRITE before completing 15-20 CTO conversations.** See `docs/sales/outreach-tracker.md`.

## Purpose

This document defines what Tformance is, who it is for, and the product decisions that should stay stable as features change.

## Product Identity

Tformance is an engineering analytics product for CTOs and engineering leaders who need to understand two things at the same time:

1. How their team is actually delivering.
2. Whether AI coding tools are improving that delivery or just increasing output and review load.

The product is not a generic BI layer, a developer surveillance tool, or an enterprise planning suite. It is a practical decision system for smaller engineering organizations that want credible answers fast.

## Core User Problem

The first buyer does not lack dashboards. They lack defensible answers.

They are being asked:
- Are our engineers using the AI tools we are paying for?
- Is AI improving cycle time, throughput, or quality?
- Where is work actually getting stuck: coding, review, planning, or coordination?
- Which teams or repositories are improving, and which are carrying hidden friction?

Today, most smaller engineering organizations answer those questions with anecdotes, point tools, or expensive enterprise platforms built for much larger companies. That leaves a gap between "we bought the tools" and "we know what changed."

## Why Now

Three forces make the product timely:

1. AI adoption has outpaced measurement. Many teams already use Copilot, Cursor, Claude, or similar tools, but leadership still cannot prove ROI.
2. Review burden is rising. Faster code generation can create more pull requests, more iteration, and more reviewer pressure.
3. The market is splitting. Enterprise platforms are getting broader and more expensive, while smaller teams still need a focused, affordable answer.

This creates room for a product that is narrower, faster to adopt, and sharper in its point of view.

## Product Loop

Tformance should reinforce a single operating loop:

1. A buyer discovers Tformance through public proof, comparison content, referrals, or outbound.
2. They connect GitHub and reach a useful dashboard quickly, without a heavy setup project.
3. Tformance turns raw PR activity into delivery metrics, AI usage signals, and early explanations of bottlenecks.
4. The buyer uses those insights to make concrete decisions about tools, review practices, team workflows, and follow-on integrations.
5. Optional Jira and Slack connections deepen context and create more durable weekly habits.
6. The team sees clearer value over time, which supports conversion, renewal, and expansion.
7. Public benchmark pages and customer stories create more proof, which feeds the next acquisition cycle.

The loop matters because Tformance wins when proof, onboarding, and ongoing insight feel like one system rather than separate motions.

## Core Capabilities

### 1. GitHub-First Team Discovery

GitHub is the required starting point. Tformance should discover teams, repositories, and pull-request activity from the systems engineering leaders already trust.

### 2. Delivery Metrics That Explain Flow

The product must surface the metrics leaders actually use to reason about engineering flow:
- PR throughput
- cycle time
- review time
- review rounds
- quality and rework signals
- team and individual trends

### 3. AI Detection And Correlation

This is the wedge. Tformance should connect AI usage signals to delivery outcomes so a leader can compare AI-assisted work and non-AI work with more confidence than self-report alone.

### 4. Fast Time To Value

The product should get a buyer from signup to first useful dashboard quickly, then deepen value in the background through historical sync, optional integrations, and richer analysis.

### 5. Layered Visibility

Developers, leads, and CTOs should not all see the same thing. The product should preserve trust by showing each role the right level of detail.

### 6. Public Proof Surfaces

Public OSS pages, comparison pages, and benchmark content are not side projects. They are proof surfaces that help prospects understand what Tformance can reveal before they commit.

## Product Principles

### Answer Decisions, Not Curiosity

Every major screen should help a leader decide what to do next, not just observe numbers.

### GitHub First, Everything Else Second

The first useful product experience should come from GitHub alone. Jira and Slack should deepen value, not block it.

### Measure AI Against Delivery

AI usage is not the outcome. Delivery quality, speed, and review health are the outcomes. AI measurement only matters when tied to them.

### Earn Trust Through Transparency

Methods, freshness, scope, and limitations should be clear. If the product cannot know something with confidence, it should say so.

### Optimize For Smaller Engineering Organizations

The product should fit teams that need signal quickly and cannot justify enterprise pricing, long onboarding, or a large internal analytics project.

### Self-Serve First, Assisted When Useful

The core experience should work without a sales-heavy process. Human help can accelerate adoption, but it should not be required for the product to make sense.

### Avoid Vanity And Surveillance

Tformance should not rank developers by shallow output metrics or encourage punitive use. The product should reveal delivery patterns and bottlenecks without collapsing into scorekeeping theater.

## In Scope Today

Tformance is currently centered on these product choices:

- GitHub-first onboarding and team discovery
- daily sync plus webhook-assisted freshness where appropriate
- dashboards built around PR and review flow
- AI detection that combines LLM analysis, pattern detection, and optional survey inputs
- optional Jira integration for work and planning context
- optional Slack connection for surveys and engagement loops
- public OSS pages and comparison content as acquisition and proof
- flat-rate pricing that fits SMB engineering teams better than per-seat enterprise tools

## Non-Goals

These are intentionally not the product right now:

- a full engineering management operating system
- heavy workflow automation across the SDLC
- enterprise-first compliance, on-prem, or BYOS deployment as the default motion
- real-time observability or deployment telemetry as the primary wedge
- exhaustive AI vendor coverage before the core AI ROI question is solved
- financial reporting depth aimed at CFO workflows before the CTO problem is won
- metrics that can be gamed easily, such as raw lines of code or simple commit counts

## Roadmap

### Wave 1: Prove The Core Value

Goal: make the product useful and believable for the first ideal customer.

- GitHub-first onboarding with fast dashboard access
- core delivery dashboards and role-based visibility
- multi-layer AI detection for pull requests
- AI-versus-delivery correlation views
- public OSS pages and comparison content as trust-building surfaces
- flat-rate self-serve pricing for small and mid-sized teams

### Wave 2: Explain Why And What To Do

Goal: move from "what happened" to "why it happened" and "what to fix."

- richer Jira context for bottleneck and planning analysis
- stronger insight generation and recommendations
- better quality impact analysis for AI-assisted work
- clearer benchmark and comparison views
- more repeatable weekly usage loops for leaders and teams

### Wave 3: Expand Commercial Depth

Goal: grow deal size and retention without losing the focused product identity.

- premium and enterprise packaging around deeper context and support
- broader security, governance, and admin features where commercially necessary
- more advanced benchmarking and longitudinal analysis
- selective expansion of integrations only where they sharpen the main story

## References

- [PRD-MVP.md](PRD-MVP.md)
- [ARCHITECTURE.md](ARCHITECTURE.md)
- [PRICING-STRATEGY.md](PRICING-STRATEGY.md)
- [COMPETITOR-RESEARCH.md](COMPETITOR-RESEARCH.md)
- [DASHBOARDS.md](DASHBOARDS.md)
- [ONBOARDING.md](ONBOARDING.md)
- [JIRA-ENRICHMENT.md](JIRA-ENRICHMENT.md)
- [../docs/plans/growth-strategy.md](../docs/plans/growth-strategy.md)
- [../docs/plans/2026-03-14-public-repo-pages-gtm-implementation-plan.md](../docs/plans/2026-03-14-public-repo-pages-gtm-implementation-plan.md)
