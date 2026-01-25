---
name: writing-well
description: Clear writing principles from "On Writing Well" by William Zinsser. Triggers on writing, copy, copywriting, landing page, marketing, content, headline, tagline, CTA, call to action, button text, error message, about page, blog post, email copy, microcopy, product description, notification text, empty state, onboarding copy.
---

# Writing Well: Clear, Human Copy

## Purpose

Guide clear, concise, human writing for all public-facing content. Based on William Zinsser's "On Writing Well" - the definitive guide to nonfiction writing.

## When to Use This Skill

Automatically activates when:
- Writing landing page copy
- Creating marketing content or product descriptions
- Writing email copy or newsletters
- Crafting headlines, taglines, or CTAs
- Writing error messages and UI microcopy
- Creating about pages or team bios
- Writing blog posts or documentation for end-users
- Crafting onboarding flows and empty states
- Any user-facing text in `templates/web/**` or `templates/emails/**`

---

## Core Principles

### 1. Simplicity

Strip every sentence to its cleanest components.

**The rule:** Clear thinking leads to clear writing. If you can't explain it simply, you don't understand it well enough.

```
# Bad - Cluttered
We leverage cutting-edge AI technology to facilitate the optimization
of your team's software development workflow efficiency.

# Good - Simple
We help your team ship better code, faster.
```

**Short words beat long words:**
| Instead of | Use |
|------------|-----|
| utilize | use |
| facilitate | help |
| implement | do, build |
| leverage | use |
| optimize | improve |
| functionality | feature |
| methodology | method |
| regarding | about |

### 2. Clutter Removal

Cut up to 50% of your first draft. Every word must do useful work.

**Kill these phrases:**
- "in order to" → "to"
- "the fact that" → cut entirely
- "it is interesting to note that" → cut entirely
- "at this point in time" → "now"
- "in the event that" → "if"
- "for the purpose of" → "for" or "to"
- "a large number of" → "many"
- "in the near future" → "soon"
- "whether or not" → "whether"
- "due to the fact that" → "because"

**Question every word:**
- Can I cut this word without losing meaning?
- Am I using two words where one works?
- Does this adjective add anything?
- Is this adverb necessary?

### 3. Unity

Every piece needs one clear focus.

**Pick and stick to:**
- **One tense** - Don't shift between past and present
- **One pronoun** - "You" or "we" or "I", not all three
- **One mood** - Casual or formal, not both
- **One idea** - One provocative thought per piece

```
# Bad - Mixed pronouns and mood
At Tformance, we believe one should always track their metrics.
Users can see how you're performing against benchmarks.

# Good - Unified "you" and casual tone
Track your metrics. See how you stack up against top teams.
```

### 4. Active Voice

Active verbs push sentences forward. Passive constructions sap energy.

```
# Passive
The metrics are calculated by our system every 24 hours.
A notification will be sent when syncing is completed.

# Active
Our system calculates your metrics every 24 hours.
We'll notify you when syncing finishes.
```

**Active voice characteristics:**
- Subject does the action
- Fewer words
- More direct
- More engaging

### 5. Be Yourself

Write like a human having a conversation, not a corporation issuing statements.

**The test:** Would you say this at a dinner party?

```
# Corporate-speak
We are committed to delivering value through our comprehensive
suite of engineering analytics solutions.

# Human
We show you what's slowing your team down so you can fix it.
```

**Warmth and humanity are your most valuable qualities.** Readers can tell when a writer is having a good time.

### 6. Strong Leads

Your first sentence is the most important. It must capture attention and pull readers forward.

**Good leads:**
- Ask a question they want answered
- State something provocative
- Present a surprising fact
- Address a pain point directly

```
# Weak lead
Tformance is a comprehensive analytics platform for engineering teams.

# Strong leads
"How much of that code was written by AI?" (Question)
"Most teams don't know if AI tools are helping or hurting them." (Provocation)
"Teams using AI tools ship 40% faster—when used correctly." (Surprising fact)
```

### 7. Strong Endings

When you're ready to stop, stop. Don't summarize, don't repeat, don't add one more thought.

**End with:**
- A surprising insight
- A call to action
- A quote that resonates
- A thought that lingers

```
# Weak ending
In conclusion, Tformance provides comprehensive analytics that help
engineering teams understand their performance metrics and AI tool usage.

# Strong ending
Your code tells a story. We help you read it.
```

---

## Quick Checklist

Before publishing any copy:

- [ ] **Cut 50%** - Read your draft, then cut half. It will be better.
- [ ] **Read aloud** - Does it sound like something you'd say?
- [ ] **One idea** - Can you state the main point in one sentence?
- [ ] **Active voice** - Is the subject doing the action?
- [ ] **Short words** - Any fancy words that could be simpler?
- [ ] **Strong lead** - Does the first sentence grab attention?
- [ ] **Clean ending** - Did you stop when you were done?
- [ ] **"You" test** - Are you talking to the reader, not at them?

---

## Anti-Patterns to Avoid

### 1. Corporate Jargon

```
# Bad
Synergize cross-functional team alignment through data-driven insights.
Leverage our best-in-class platform to optimize workflow efficiency.

# Good
Help your teams work together with real data.
See what's working and what isn't.
```

### 2. Weak Verbs with Adverbs

Adverbs are the writer admitting the verb isn't strong enough.

```
# Weak
We really quickly show your metrics clearly.

# Strong
We surface your metrics instantly.
```

### 3. Hedging and Qualifiers

Commit to what you're saying. Don't hedge.

```
# Hedged
Our platform can potentially help teams possibly improve their metrics.

# Committed
Improve your team's metrics.
```

### 4. Feature Lists Without Benefits

Don't list what it does. Say why it matters.

```
# Features (boring)
- Real-time sync
- Dashboard analytics
- Team management

# Benefits (compelling)
- See changes as they happen
- Spot problems before they ship
- Know who needs help
```

### 5. Empty Superlatives

"Best-in-class", "world-class", "industry-leading" mean nothing.

```
# Empty
Our industry-leading solution provides best-in-class analytics.

# Specific
Teams using Tformance ship 40% faster in their first month.
```

---

## UI Microcopy Patterns

### Buttons and CTAs

Short, action-oriented, first person or imperative.

```
# Good CTAs
Start free trial → (specific action)
See my metrics → (first person, curiosity)
Connect GitHub → (clear next step)

# Bad CTAs
Submit → (generic)
Click here → (obvious)
Learn more → (vague)
```

### Error Messages

Be human. Explain what happened. Say what to do.

```
# Bad
Error: Invalid credentials. Code 401.

# Good
Wrong password. Try again or reset it.
```

### Empty States

Turn emptiness into opportunity.

```
# Bad
No data found.

# Good
Connect your GitHub to see your first metrics.
It takes about 30 seconds.
```

### Confirmation Messages

Be specific about what happened.

```
# Bad
Success!

# Good
Connected to GitHub. We're syncing your repos now.
```

---

## Before/After Examples

### Landing Page Hero

**Before:**
> Tformance is a comprehensive, data-driven engineering analytics platform
> that leverages cutting-edge AI technology to provide actionable insights
> into your software development team's productivity and performance metrics.

**After:**
> See how AI tools are actually affecting your team's code.
> Track real metrics. Make better decisions.

### Feature Description

**Before:**
> Our platform provides real-time synchronization capabilities with GitHub
> repositories, enabling seamless integration of your codebase with our
> comprehensive analytics dashboard for optimal visibility into development workflows.

**After:**
> Connect GitHub in one click. See your team's metrics in minutes.

### CTA Button

**Before:** "Click Here to Get Started with Your Free Trial"

**After:** "Start Free Trial"

### Error Message

**Before:**
> An error has occurred during the authentication process.
> Please verify your credentials and try again.

**After:**
> Couldn't sign you in. Check your password and try again.

---

## Tformance Voice Guidelines

For consistency across all copy:

1. **Direct** - Say it plainly. No hedging.
2. **Helpful** - Solve problems, don't create confusion.
3. **Human** - Write like you talk. Use "you" and "we".
4. **Specific** - Numbers beat adjectives. Facts beat claims.
5. **Brief** - Say it once. Say it well. Stop.

### Tone by Context

| Context | Tone | Example |
|---------|------|---------|
| Marketing | Confident, energetic | "Ship better code" |
| Errors | Calm, helpful | "That didn't work. Try again." |
| Success | Warm, brief | "You're all set!" |
| Onboarding | Encouraging, clear | "One more step. You've got this." |

---

## Reference

For extended examples and SaaS-specific copywriting patterns, see:
→ [EXAMPLES.md](./EXAMPLES.md)

---

**Line Count:** ~350 (within 500-line guideline)
