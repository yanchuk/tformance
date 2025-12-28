# AI Impact Report - Data for LLMs

> **Quick Copy for LLMs:**
> ```
> https://raw.githubusercontent.com/yanchuk/tformance/main/docs/report_data_for_llms.md
> ```
>
> Paste this URL into ChatGPT, Claude, or any LLM with web access and ask: *"Read this document and summarize the key findings about AI tool impact on software engineering."*

---

## TL;DR: Review AI Works. Code AI? It's Complicated.

**Industry claims:** 85% adoption (Stack Overflow, JetBrains 2025), massive productivity gains.
**The only RCT:** METR 2025 found AI made devs **19% slower** (with 43-point perception gap).
**Our data:** 167,308 PRs from 101 OSS companies to see what actually happens.

---

### What This Research SHOWS (Statistically Significant)

| Finding | 95% CI | Interpretation |
|---------|--------|----------------|
| Review AI → **-11% cycle time** | -18% to -7% | PRs with Review AI tools merge faster (significant) |
| Review AI → **-54% review time** | -60% to -49% | Code reviews happen much faster (significant) |
| Code AI → **+16% cycle time** | +4% to +25% | PRs with Code AI take longer to merge (significant) |

### What This Research Does NOT Show

| Claim | Why Not |
|-------|---------|
| "Code AI speeds up reviews" | **NOT significant** — CI crosses zero (-32% to +1%) |
| "AI *causes* faster/slower cycles" | **Correlation only** — observational data, not RCT |
| "The typical PR is faster with AI" | **Medians contradict means** — Code AI +100% slower, Review AI +5% slower |
| "All teams benefit from AI" | **Simpson's Paradox** — 60% of teams show AI is SLOWER |
| "We detected all AI usage" | **Detection bias** — Copilot (68% industry adoption) leaves no trace |
| "Review AI = human productivity" | **Bot speed artifact** — CodeRabbit auto-comments in seconds; we measure bot latency, not human review quality |

---

> **IMPORTANT CAVEATS:**
> - **Simpson's Paradox:** While aggregate data shows Review AI is -11% faster, **60% of individual teams show AI is SLOWER**. Aggregate stats can mislead.
> - **Median vs Mean:** The typical (median) PR tells a different story. Medians show Code AI is **+100% slower** and Review AI is **+5% slower** than baseline. Means are heavily skewed by outliers.
> - **Bot Speed Artifact:** Review AI's -54% faster reviews may partly reflect **bot latency, not human productivity**. CodeRabbit auto-comments in seconds — we measure "time to first comment," not review quality.
> - **Detection Bias:** Copilot (68% industry usage) leaves no trace. Our Code AI sample likely over-represents explicitly disclosed/complex PRs.
> - **Clustering Not Modeled:** CIs computed at PR level, not team level. True uncertainty may be wider due to team/repo clustering.
> - **Correlation, not causation:** This is observational data. We cannot prove AI *causes* these effects.
> - **Code AI review time is NOT statistically significant** (95% CI crosses zero).

### Review AI vs Code AI — The Facts

| Category | Tools | Cycle Time | Review Time | Detection Share |
|----------|-------|------------|-------------|-----------------|
| **Review AI** | CodeRabbit, Cubic, Greptile | **-11%** | **-54%** | 73.5% |
| **Code AI** | Cursor, Claude, Copilot, Devin | **+16%** | **-14%** (n.s.) | 26.3%* |

**(n.s.) = not statistically significant** — Code AI review time CI crosses zero (-32% to +1%).

*Code AI real share is likely much higher — Copilot (68% survey adoption) leaves no trace in PRs.

```
                        CYCLE TIME IMPACT (hours to merge)
                    ← FASTER    |    SLOWER →
                                |
         73.4 hrs   ████████████│                 Review AI   ✓ -11%
                                │
         82.2 hrs               │                 Baseline      0%
                                │
         95.6 hrs               │████████████████ Code AI     ⚠ +16%
                                |
                    ────────────┴────────────
                                0%
```

### The Bottom Line

| Recommendation | Why |
|---------------|-----|
| **Review AI correlates with faster cycles** | Associated with -11% cycle time, -54% review time. Statistically significant. |
| **Code AI shows mixed correlations** | Associated with +16% cycle time. Review time improvement (-14%) is NOT significant. |
| **12.1% is a floor, not ceiling** | Silent tools (Copilot autocomplete) leave no trace. Real usage is likely 40-60%. |

**Note:** These are correlations from observational data, not causal findings. Your results may vary based on team, codebase, and workflow.

---

### ⚠️ Median Reality Check: The Typical PR Experience

**Headlines use means. But medians tell a different story:**

| Metric | Mean (Aggregate) | Median (Typical PR) | Which to Trust? |
|--------|------------------|---------------------|-----------------|
| **Code AI Cycle Time** | +16% slower | **+100% slower** | Median = typical PR |
| **Review AI Cycle Time** | -11% faster | **+5% slower** | Median = typical PR |
| **Skew Factor** | — | 8-14x | Means distorted by outliers |

**Why the huge gap?**
- A few PRs take 500+ hours (long-running features, blocked PRs)
- These outliers drag means up dramatically
- Median = the PR at the 50th percentile = what most PRs experience

**Bottom line:** If you want to know "what happens to a typical PR," medians are more relevant. If you care about total team throughput including outliers, means matter.

**For the typical PR:**
- Code AI PRs take **2x longer** than baseline
- Review AI PRs are **slightly slower** than baseline (not faster)

This directly contradicts mean-based headlines and is the most honest interpretation for individual PR expectations.

---

### How We Got These Numbers

```
GitHub GraphQL API  →  PR Metadata  →  LLM Analysis  →  Metrics
   167,308 PRs         (title,body,     (Llama 3.3      (cycle time,
   101 companies        commits,         70B via         review time,
                        comments)        Groq)           PR size)
```

**Detection Method:** LLM extracts AI tool mentions + 25 regex patterns as fallback.
**Key Limitation:** We only detect *disclosed* AI usage. Copilot autocomplete = invisible.

---

### 🚀 Want Better Insights for YOUR Team?

This OSS study has inherent limitations. **tformance** solves them with native integrations:

| Limitation | OSS Study | With tformance Integrations |
|------------|-----------|---------------------------|
| **Invisible Copilot** | Can't detect (68% of usage) | **GitHub Copilot API** → actual acceptance rates, lines generated |
| **No complexity control** | Assume all PRs equal | **Jira** → story points, issue type, sprint velocity |
| **Unknown task type** | LLM inference | **Jira** → bug vs feature vs refactor (ground truth) |
| **No perception data** | Just measure time | **Slack Surveys** → "Did AI help?" per PR |
| **Aggregate only** | Compare different devs | **Within-developer analysis** → same dev, AI vs non-AI PRs |
| **Bot vs human reviews** | Can't separate | **Surveys** → who actually reviewed? |

**What you get with full integrations:**

1. **GitHub + Copilot** → Actual AI usage intensity (not just "detected/not")
2. **Jira** → Task complexity, story points, issue types, blocked time
3. **Slack Surveys** → Per-PR feedback: complexity, AI tools used, perceived help
4. **Combined Analysis** → "AI helps on complex features, hurts on simple bugs" (actionable)

**The key insight:** This report shows *correlations* in OSS data. With your team's full data (Copilot + Jira + Surveys), tformance can show *controlled associations* — much closer to answering "Does AI actually help MY team?"

→ **Get started:** [tformance.com](https://tformance.com)

---

## Table of Contents

1. [Report Summary](#report-summary)
2. [Key Finding: Code AI vs Review AI](#key-finding-code-ai-vs-review-ai)
3. [Top AI Tools Detected](#top-ai-tools-detected)
4. [Industry Context & Comparison](#industry-context--comparison)
5. [Detailed Methodology](#detailed-methodology)
6. [Formulas & Calculations](#formulas--calculations)
7. [Assumptions](#assumptions)
8. [Risks & Limitations](#risks--limitations)
9. [References & Sources](#references--sources)
10. [Data Files](#data-files)

---

## Report Summary

**Full Report:** [https://tformance.com](https://tformance.com)
**Data Date:** December 27, 2025
**Research Period:** January 1 - December 25, 2025

| Metric | Value | Notes |
|--------|-------|-------|
| Total PRs Analyzed | 167,308 | From GitHub GraphQL API |
| OSS Companies | 101 | 74 with 500+ PRs for detailed analysis |
| AI-Assisted PRs | 20,260 | Detected via LLM + regex |
| AI Adoption Rate | 12.1% | Floor estimate (disclosed only) |
| LLM Analyzed PRs | 109,240 (65.3%) | PRs with non-empty body |
| Detection Agreement | 93.4% | LLM vs regex pattern match |

---

## Key Finding: Code AI vs Review AI

We categorize AI tools into two types with **dramatically different impacts**:

### Category Definitions

| Category | Definition | Examples | Detection Method |
|----------|------------|----------|------------------|
| **Code AI** | Tools that write/generate code | Cursor, Copilot, Claude, Devin, ChatGPT, Aider | PR body mentions, commit messages, co-author tags |
| **Review AI** | Tools that review/comment on code | CodeRabbit, Cubic, Greptile, Sourcery | Bot comments, review signatures |

### Category Distribution

| Category | Tool Mentions | Percentage | Unique PRs |
|----------|---------------|------------|------------|
| Review AI | 18,534 | 73.5% | 11,302 |
| Code AI | 6,631 | 26.3% | 3,056 |
| Unknown | 52 | 0.2% | — |
| **Total** | **25,217** | **100%** | — |

> **Understanding the Numbers:** Tool mentions (25,217) can exceed unique PRs because one PR can mention multiple tools. Category metrics use unique PRs (125,573 merged PRs from teams with 500+ PRs).

### Impact Comparison (vs Non-AI Baseline)

| Metric | No AI (Baseline) | Code AI | Code AI Δ | Review AI | Review AI Δ |
|--------|------------------|---------|-----------|-----------|-------------|
| Sample Size | 111,215 PRs | 3,056 PRs | — | 11,302 PRs | — |
| Avg Cycle Time | 82.2 hrs | 95.6 hrs | **+16%** | 73.4 hrs | **-11%** |
| Median Cycle Time | 5.7 hrs | 11.4 hrs | +100% | 6.0 hrs | +5% |
| Avg Review Time | 40.8 hrs | 34.9 hrs | **-14%** | 18.7 hrs | **-54%** |
| Median Review Time | 0.6 hrs | 0.3 hrs | -50% | 0.1 hrs | -83% |
| Avg PR Size | 723 lines | 519 lines | -28% | 481 lines | -33% |

**95% Confidence Intervals (1000 bootstrap samples):**
| Metric | Code AI Δ (95% CI) | Review AI Δ (95% CI) |
|--------|--------------------|-----------------------|
| Cycle Time | +16% (+4% to +25%) | -11% (-18% to -7%) |
| Review Time | -14% (-32% to +1%) **(n.s.)** | -54% (-60% to -49%) |

**(n.s.) = not statistically significant.** The Code AI review time confidence interval crosses zero (-32% to +1%), meaning we cannot rule out that the true effect is zero or even positive. Interpret the -14% figure with caution.

**MEDIAN WARNING:** The typical (median) PR tells a different story than means:

| Metric | Baseline | Code AI | Review AI |
|--------|----------|---------|-----------|
| **Mean Cycle Time** | 82.2h | 95.6h (+16%) | 73.4h (-11%) |
| **Median Cycle Time** | 5.7h | 11.4h (**+100%**) | 6.0h (**+5%**) |
| **Skew Factor** | 14x | 8x | 12x |

The median shows Code AI PRs take **twice as long** as baseline, and Review AI PRs are **5% slower** — contradicting the mean-based headlines. Means are heavily influenced by long-tail outliers (a few PRs taking 500+ hours).

**Why this matters:** If you're trying to predict the "typical" PR experience, use medians. If you care about total team throughput (including outliers), means are more relevant.

### Key Insight

**Review AI correlates with efficiency gains.** PRs with automated code reviews (CodeRabbit, Cubic) show:
- 11% faster mean cycle time (statistically significant)
- 54% faster mean review time (statistically significant)

**Code AI shows mixed correlations.** PRs mentioning code generation tools (Cursor, Claude, Devin) show:
- +16% longer mean cycle time
- -14% shorter mean review time **(but NOT statistically significant)**

**Hypothesis:** AI-generated code may require more iteration/refinement before review-readiness, explaining the longer cycle time. However, these are correlations — we cannot prove AI *causes* these effects.

### Size-Normalized Analysis

PR size is a potential confounding variable. Normalizing review time **per 100 lines of code** controls for this:

| Category | PRs | Review Hours / 100 Lines | vs Baseline |
|----------|-----|--------------------------|-------------|
| Baseline (No AI) | 96,903 | 321.4 hrs | — |
| Code AI | 3,502 | 236.5 hrs | **-26%** |
| Review AI | 12,290 | 122.8 hrs | **-62%** |

**Conclusion:** Even after controlling for PR size, Review AI shows 62% faster reviews per 100 lines. Code AI also shows improvement (-26%) when size-normalized, suggesting the raw metrics may understate its benefits.

### Within-Team Analysis

Comparing AI vs non-AI PRs **within the same team** controls for team-level differences:

| Metric | Value |
|--------|-------|
| Teams analyzed (10+ PRs in both groups) | 50 |
| Teams where AI is faster | 20 (40%) |
| Teams where AI is slower | 30 (60%) |

**Top 5 where AI is faster:**
- OpenReplay: -93% (AI: 3.0h vs Non-AI: 43.4h)
- Coolify: -86% (AI: 33.8h vs Non-AI: 233.0h)
- Comp AI: -84% (AI: 1.5h vs Non-AI: 8.9h)
- LobeChat: -75% (AI: 20.8h vs Non-AI: 83.6h)
- Unleash: -72% (AI: 9.8h vs Non-AI: 35.4h)

**Top 5 where AI is slower:**
- Excalidraw: +327% (AI: 519.9h vs Non-AI: 121.8h)
- Flagsmith: +322% (AI: 511.0h vs Non-AI: 121.2h)
- Ghost: +179% (AI: 123.8h vs Non-AI: 44.5h)
- Open WebUI: +158% (AI: 91.1h vs Non-AI: 35.3h)
- n8n: +116% (AI: 162.3h vs Non-AI: 75.2h)

**⚠️ Simpson's Paradox:** The aggregate shows Review AI is -11% faster overall, but 60% of individual teams see AI as slower. This can happen when AI adoption correlates with other factors (e.g., teams that already ship fast adopt AI more). Aggregate stats can mislead — always check within-team patterns.

---

## Top AI Tools Detected

### Complete Tool Rankings

| Rank | Tool | Count | Category | % of Total |
|------|------|-------|----------|------------|
| 1 | CodeRabbit | 11,104 | Review AI | 44.0% |
| 2 | Cubic | 6,943 | Review AI | 27.5% |
| 3 | Devin | 1,795 | Code AI | 7.1% |
| 4 | Cursor | 1,429 | Code AI | 5.7% |
| 5 | Claude | 1,229 | Code AI | 4.9% |
| 6 | Copilot | 823 | Code AI | 3.3% |
| 7 | Greptile | 469 | Review AI | 1.9% |
| 8 | ChatGPT | 455 | Code AI | 1.8% |
| 9 | Claude Code | 310 | Code AI | 1.2% |
| 10 | Gemini | 196 | Code AI | 0.8% |
| 11 | AI Generic | 159 | Code AI | 0.6% |
| 12 | Ellipsis | 98 | Code AI | 0.4% |
| 13 | Codegen | 33 | Code AI | 0.1% |
| 14 | Sourcery | 16 | Review AI | 0.1% |
| 15 | Continue | 11 | Code AI | <0.1% |

### Detection Bias Warning

**Copilot is massively underrepresented:**
- Industry surveys: 68% of developers use Copilot (Stack Overflow 2025)
- Our detection: Only 823 mentions (3.3% of tool mentions)
- **Reason:** Copilot autocomplete leaves NO trace in PR metadata

**ChatGPT is massively underrepresented:**
- Industry surveys: 82% use ChatGPT for coding tasks
- Our detection: Only 455 mentions (1.8% of tool mentions)
- **Reason:** ChatGPT research/debugging leaves NO trace in PRs

---

## Industry Context & Comparison

### Adoption Rate Comparison

| Source | Sample | Adoption Rate | What It Measures | Data Type |
|--------|--------|---------------|------------------|-----------|
| **Our Report** | 167,308 PRs | 12.1% | Explicit AI disclosure in PRs | Behavioral |
| Stack Overflow 2025 | 65,000+ devs | 84% | "Using or planning to use AI" | Survey |
| Stack Overflow 2025 | 65,000+ devs | 51% | Using AI daily at work | Survey |
| JetBrains 2025 | 24,534 devs | 85% | "Regularly use AI for coding" | Survey |
| JetBrains 2025 | 24,534 devs | 62% | Use AI coding assistant/agent | Survey |
| METR 2025 (RCT) | 16 devs, 246 issues | +19% slower | Task completion with AI | Experiment |

### The Iceberg Analogy

```
Survey Data (84%): ████████████████████████████████████████ ← What devs SAY they use
                   ↑ Ceiling (includes silent use, planning)

Our Data (12.1%):  █████ ← What we can DETECT
                   ↑ Floor (explicit mentions only)

True Usage (~40-60%): ████████████████████ ← Estimated actual
```

### METR RCT Study Alignment

The only **randomized controlled trial** in the space (METR 2025):

| Finding | Value | Implication |
|---------|-------|-------------|
| AI impact on task time | **+19% slower** | AI made experienced devs slower |
| Developer perception | **-20% (believed faster)** | Devs thought they were faster |
| Perception gap | **43 percentage points** | Massive disconnect from reality |

**Our Code AI data (+16% cycle time) aligns with METR's +19% finding.**

### Study Design Caveat

⚠️ **Important distinction:**
- **METR used an RCT (causal)** — randomized assignment proves causation
- **This report is observational (correlational)** — we observe what happens but cannot prove AI *caused* faster/slower cycles

Confounders like team culture, PR complexity, or developer experience could explain differences. The within-team and size-normalized analyses help control for some confounders, but true causation requires controlled experiments.

---

## Detailed Methodology

### 1. Data Collection

```
GitHub GraphQL API
       ↓
PR Metadata Extraction:
  - Title, body, comments
  - Commits (messages, authors)
  - Reviews (body, author)
  - File changes (additions, deletions)
  - Timestamps (created, merged)
       ↓
Store in PostgreSQL
```

**API Fields Collected:**
- `title`, `body`, `createdAt`, `mergedAt`, `closedAt`
- `additions`, `deletions`, `changedFiles`
- `commits.nodes[].message`, `commits.nodes[].authors`
- `reviews.nodes[].body`, `reviews.nodes[].author`
- `comments.nodes[].body`, `comments.nodes[].author`

### 2. AI Detection (Dual Method)

#### Method A: LLM Analysis (Primary)
- **Model:** Llama 3.3 70B via Groq API
- **Prompt:** Structured extraction for AI tool mentions
- **Output:** `{is_assisted: bool, confidence: float, tools: [str]}`
- **Threshold:** `confidence >= 0.5` for positive detection

#### Method B: Regex Patterns (Secondary)
- **Patterns:** 25+ regex patterns
- **Sources:** PR body, commit messages, co-author tags, bot signatures
- **Examples:**
  ```regex
  /generated (by|with|using) (cursor|copilot|claude)/i
  /\[bot\].*coderabbit/i
  /Co-authored-by:.*\[bot\]/i
  ```

#### Detection Priority
```python
# LLM detection takes priority over regex
if llm_summary and llm_summary.ai.tools:
    return llm_summary.ai.tools  # Primary
else:
    return regex_detected_tools   # Fallback
```

### 3. Metric Calculations

See [Formulas & Calculations](#formulas--calculations) below.

### 4. Category Assignment

```python
CODE_AI_TOOLS = [
    "cursor", "copilot", "claude", "claude_code", "chatgpt",
    "gemini", "windsurf", "codeium", "devin", "aider",
    "codegen", "continue", "bito", "amazon_q", "codex"
]

REVIEW_AI_TOOLS = [
    "coderabbit", "greptile", "cubic", "sourcery",
    "codacy", "codeant", "ellipsis"
]

def get_tool_category(tool: str) -> str:
    tool_lower = tool.lower()
    if tool_lower in CODE_AI_TOOLS:
        return "code"
    elif tool_lower in REVIEW_AI_TOOLS:
        return "review"
    else:
        return "unknown"
```

### 5. Sample Filtering

| Filter | Threshold | Reason |
|--------|-----------|--------|
| Minimum PRs per team | 500 | Statistical significance |
| Date range | Jan 1 - Dec 25, 2025 | Full year analysis |
| PR state | Merged only | Completed work only |
| Cycle time | > 0 hours | Valid data only |

---

## Formulas & Calculations

### Cycle Time
```
Cycle Time (hours) = (merged_at - created_at) / 3600

Where:
  merged_at = Unix timestamp when PR was merged
  created_at = Unix timestamp when PR was created
```

### Review Time
```
Review Time (hours) = (first_approval_at - created_at) / 3600

Where:
  first_approval_at = Unix timestamp of first approving review
  created_at = Unix timestamp when PR was created
```

### PR Size
```
PR Size (lines) = additions + deletions

Where:
  additions = Lines added in the PR
  deletions = Lines removed in the PR
```

### AI Adoption Rate
```
AI Adoption Rate (%) = (AI-Assisted PRs / Total PRs) × 100

Where:
  AI-Assisted PRs = PRs with is_ai_assisted = true
  Total PRs = All PRs in the sample
```

### Category Delta (Impact)
```
Delta (%) = ((Category_Avg - Baseline_Avg) / Baseline_Avg) × 100

Example for Code AI Cycle Time:
  Delta = ((95.6 - 82.2) / 82.2) × 100 = +16.3% ≈ +16%
```

### Confidence Intervals (95%)

**For Adoption Rate (Proportion CI):**
```
CI = ± 1.96 × √(p × (1-p) / n)

Where:
  p = AI adoption rate (0.121)
  n = Sample size (167,308)

CI = ± 1.96 × √(0.121 × 0.879 / 167308) = ±0.16%
```

**For Cycle/Review Time Deltas (Bootstrap CI):**
```
Method: Non-parametric bootstrap (1000 resamples)
1. Resample PRs with replacement
2. Compute delta for each resample
3. Take 2.5th and 97.5th percentiles

Note: Bootstrap is at PR level, not team level.
      CIs may be narrower than true uncertainty
      due to unmodeled team/repo clustering.
```

### Statistical Significance (Chi-Square)
```
Used for team structure comparisons (focused vs distributed)
Result: p < 0.0001 (highly significant)
```

---

## Assumptions

### Explicit Assumptions

| # | Assumption | Risk Level | Mitigation |
|---|------------|------------|------------|
| A1 | Disclosed AI usage represents true AI usage patterns | HIGH | Acknowledged as floor estimate |
| A2 | LLM detection is accurate for explicit mentions | MEDIUM | 93.4% agreement with regex validation |
| A3 | Merged PRs represent completed work | LOW | Standard industry practice |
| A4 | OSS patterns apply to enterprise | HIGH | Clearly stated as OSS-only |
| A5 | Tool categories are mutually exclusive | LOW | Primary function classification |
| A6 | Cycle time is a valid productivity proxy | MEDIUM | Industry-standard DORA metric |

### Implicit Assumptions

1. **GitHub API data is accurate** — We trust GitHub's reported timestamps and metadata
2. **Bot signatures are consistent** — Review bots use identifiable patterns
3. **Team boundaries are meaningful** — GitHub org/repo mapping reflects real teams
4. **2025 data is representative** — No major industry shifts during the year

---

## Risks & Limitations

### High-Risk Limitations

| Risk | Description | Impact | Status |
|------|-------------|--------|--------|
| **Selection Bias** | Sample is popular OSS projects, not random | May not represent enterprise or small projects | ACKNOWLEDGED |
| **Detection Bias** | Silent tools (Copilot autocomplete) undetectable | Code AI massively underrepresented | ACKNOWLEDGED |
| **Causation Gap** | Correlation ≠ causation | Cannot prove AI causes faster/slower work | DISCLAIMED |
| **Simpson's Paradox** | Aggregate stats may hide subgroup patterns | Team-level analysis provided | MITIGATED |

### Medium-Risk Limitations

| Risk | Description | Impact |
|------|-------------|--------|
| **Survivorship Bias** | Only analyzing successful, active projects | May miss patterns in failing projects |
| **Temporal Bias** | 2025 only, AI landscape changing rapidly | May not reflect 2024 or 2026 patterns |
| **OSS Culture Bias** | OSS may have different disclosure norms | Enterprise disclosure rates unknown |
| **Bot vs Human PRs** | Some AI PRs are fully automated | May conflate human-assisted vs bot work |

### Low-Risk Limitations

| Risk | Description |
|------|-------------|
| **Regex False Positives** | Pattern matching may over-detect |
| **LLM Hallucination** | LLM may invent tool mentions |
| **Timezone Issues** | Timestamps in UTC, local work patterns unknown |

### What This Data CANNOT Tell You

1. **Causation** — We cannot prove AI tools cause faster/slower delivery
2. **Code Quality** — We do not measure bugs, reverts, or defects (future work)
3. **Developer Experience** — We do not measure satisfaction or fatigue
4. **Total AI Usage** — We only detect disclosed usage
5. **Enterprise Patterns** — OSS may differ from private codebases

---

## References & Sources

### Primary Data Sources

| Source | URL | Access Date |
|--------|-----|-------------|
| GitHub GraphQL API | https://docs.github.com/en/graphql | Dec 2025 |
| tformance Database | Internal PostgreSQL | Dec 27, 2025 |

### Industry Reports

| Report | URL | Key Finding |
|--------|-----|-------------|
| Stack Overflow Developer Survey 2025 | https://survey.stackoverflow.co/2025 | 84% AI adoption, 46% distrust |
| JetBrains State of Developer Ecosystem 2025 | https://www.jetbrains.com/lp/devecosystem-2025/ | 85% AI adoption, 88% save time |
| METR AI Coding RCT 2025 | https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/ | AI makes devs 19% slower (RCT) |

### Competitor Reports

| Report | URL | Focus |
|--------|-----|-------|
| Greptile State of AI Coding 2025 | https://greptile.com/blog/state-of-ai-coding-2025 | +76% dev output (ecosystem) |
| CodeRabbit AI Code Quality Report | https://coderabbit.ai/blog | AI PRs have 1.7x more issues |
| Qodo State of AI Code Quality 2025 | https://qodo.ai/reports/state-of-ai-code-quality | 82% daily AI use |

### Academic & Research

| Paper/Study | URL | Relevance |
|-------------|-----|-----------|
| METR RCT Study | https://metr.org/blog/2025-07-10-early-2025-ai-experienced-os-dev-study/ | Only RCT in space |
| DORA Metrics | https://dora.dev | Industry-standard metrics framework |

### Tool Documentation

| Tool | URL | Category |
|------|-----|----------|
| CodeRabbit | https://coderabbit.ai | Review AI |
| Cursor | https://cursor.sh | Code AI |
| GitHub Copilot | https://github.com/features/copilot | Code AI |
| Greptile | https://greptile.com | Review AI |

---

## Data Pipeline: Sample Selection

Why do our category metrics show 125k PRs instead of 167k? Here's the data funnel:

```
167,308 total PRs (all 101 OSS companies)
    │
    ├─▶ 5,346 excluded: teams with <500 PRs (too small for stats)
    │
    └─▶ 161,962 PRs from 74 teams with 500+ PRs
            │
            ├─▶ 36,290 excluded: unmerged PRs (no cycle_time)
            │   └─ Cycle time requires merge timestamp
            │
            └─▶ 125,573 merged PRs
                    └─ Used for cycle time & review time analysis
                    └─ This is what category_metrics.csv contains
```

**Why exclude unmerged PRs?** Cycle time (PR creation → merge) is undefined for PRs that never merged. Draft PRs, abandoned PRs, and still-open PRs are excluded from timing analysis but counted in adoption rates.

**Why 500+ PR threshold?** Small teams produce unreliable statistics. We require 500+ PRs per team to ensure meaningful comparisons.

---

## Data Files

### Available Data (GitHub)

| File | Path | Contents |
|------|------|----------|
| Overall Stats | `docs/data/overall_stats.txt` | Summary metrics |
| AI Categories | `docs/data/ai_categories.csv` | Category breakdown |
| Category Metrics | `docs/data/category_metrics.csv` | Impact by category (with medians & CIs) |
| Tool Categories | `docs/data/ai_tools_with_categories.csv` | Tool-level data |
| Team Summary | `docs/data/team_summary.csv` | Per-team metrics |
| Monthly Trends | `docs/data/monthly_trends.csv` | Monthly adoption |
| AI Tools Monthly | `docs/data/ai_tools_monthly.csv` | Tool usage by month |
| Normalized Metrics | `docs/data/normalized_metrics.csv` | Size-normalized review times |
| Within-Team Comparison | `docs/data/within_team_comparison.csv` | AI vs non-AI within teams |

### Raw Data URLs

```
https://raw.githubusercontent.com/yanchuk/tformance/main/docs/data/overall_stats.txt
https://raw.githubusercontent.com/yanchuk/tformance/main/docs/data/ai_categories.csv
https://raw.githubusercontent.com/yanchuk/tformance/main/docs/data/category_metrics.csv
https://raw.githubusercontent.com/yanchuk/tformance/main/docs/data/ai_tools_with_categories.csv
https://raw.githubusercontent.com/yanchuk/tformance/main/docs/data/team_summary.csv
https://raw.githubusercontent.com/yanchuk/tformance/main/docs/data/monthly_trends.csv
https://raw.githubusercontent.com/yanchuk/tformance/main/docs/data/ai_tools_monthly.csv
https://raw.githubusercontent.com/yanchuk/tformance/main/docs/data/normalized_metrics.csv
https://raw.githubusercontent.com/yanchuk/tformance/main/docs/data/within_team_comparison.csv
```

### Data Schema

#### ai_categories.csv
```csv
category,count,percentage
code,6631,26.3
review,18534,73.5
unknown,52,0.2
```

#### category_metrics.csv
```csv
category,count,avg_cycle_hours,median_cycle_hours,avg_review_hours,median_review_hours,avg_size,median_size,cycle_delta_pct,review_delta_pct
none,111215,82.2,5.7,40.8,0.6,723,49,,
code,3056,95.6,11.4,34.9,0.3,519,66,16,-14
review,11302,73.4,6.0,18.7,0.1,481,53,-11,-54
```

---

## CTO Recommendations

> **Important disclaimer:** These are correlations from observational data, not causal findings from a controlled experiment. Your results may vary based on team composition, codebase complexity, and workflow. The only RCT in this space (METR 2025) found AI made experienced devs 19% slower.

Based on this analysis:

1. **Review AI correlates with faster cycles** — CodeRabbit/Cubic show -11% cycle time, -54% review time (statistically significant). Consider piloting with low risk.

2. **Code AI shows mixed correlations** — +16% cycle time (significant), -14% review time (NOT significant). Results vary widely by team (60% of teams are slower with AI).

3. **Measure your own data** — These are OSS patterns; your enterprise may differ. Run your own before/after analysis.

4. **Don't trust surveys** — METR RCT shows 43-point perception gap; behavioral data tells different story than self-reports.

5. **Expect detection floor** — If you detect 12% AI usage, actual is likely 40-60% (Copilot autocomplete leaves no trace).

---

## About the Author

**Oleksii Ianchuk** — Technical Product Manager

8 years building developer tools. Technical Product Lead at **Mailtrap** — shipped Email API/SMTP, ran pricing experiments, onboarded enterprise accounts.

*"We used Copilot, Cursor, and every AI tool we could get. But I couldn't answer: 'Is this actually helping us ship faster?'"*

**Connect:** [GitHub](https://github.com/yanchuk) • [LinkedIn](https://www.linkedin.com/in/yanch/)

---

## Contact & Updates

**Report:** [https://tformance.com](https://tformance.com)
**Data API:** Coming soon
**Methodology Questions:** See GitHub issues

---

*Document Version: 2.0 | Generated: December 27, 2025 | License: CC BY 4.0*
