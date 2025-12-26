# AI Impact Analysis Report - 2025 OSS Projects

**Generated: 2025-12-26**
**Dataset: 60,545 PRs from 25 Open Source Projects**
**AI-Assisted PRs: 11,051 (21.2%)**

---

## Executive Summary

Analysis of 52,224 LLM-analyzed PRs reveals that **AI tools have a nuanced impact on engineering velocity**. While AI consistently **speeds up code review (-31% avg)**, it often **extends overall cycle time (+42% avg)**—suggesting teams may be tackling more complex work with AI assistance.

### Key Finding: AI = More Complex Work, Faster Reviews

| Metric | AI Impact | Interpretation |
|--------|-----------|----------------|
| **Review Time** | -31% faster | AI code is easier/faster to review |
| **Cycle Time** | +42% longer | Teams tackle more complex tasks with AI |
| **PR Size** | -17% smaller | AI enables atomic, focused changes |

---

## Team-by-Team Analysis

### 1. Plane (86.7% AI Adoption) - Highest Adopter
- **Primary Tool**: CodeRabbit (99%)
- **Pattern**: Bot-heavy workflow (CodeRabbit for reviews)
- **Impact**:
  - Cycle Time: +184% (AI PRs take longer overall)
  - Review Time: +2% (essentially same)
  - PR Size: -80% (much smaller, focused PRs)
- **Insight**: High AI adoption correlates with smaller, more frequent PRs

### 2. Antiwork (61.7% AI Adoption) - Best Outcomes
- **Tools**: CodeRabbit (44%), Devin (30%), Claude (12%), Cursor (11%)
- **Impact**:
  - Cycle Time: **-10% faster** ✅
  - Review Time: **-50% faster** ✅
  - PR Size: -11% smaller
- **Insight**: Mixed tool strategy (bot + IDE + LLM) yields best velocity gains

### 3. Cal.com (41.6% AI Adoption) - Agent-Heavy
- **Tools**: Cubic (50%), Devin (38%), CodeRabbit (17%)
- **Impact**:
  - Cycle Time: +41% slower
  - Review Time: -0.4% (essentially same)
  - PR Size: +78% larger
- **Insight**: Autonomous agents (Cubic, Devin) produce larger PRs requiring more review cycles

### 4. PostHog (6.7% AI Adoption) - Emerging Adopter
- **Tools**: Greptile (44%), Claude (26%), Copilot (12%), Cursor (11%)
- **Impact**:
  - Cycle Time: +34% slower
  - Review Time: **-48% faster** ✅
  - PR Size: -20% smaller
- **Insight**: Low adoption but high review velocity improvement

### 5. Vercel (2.1% AI Adoption) - Minimal Adoption
- **Tools**: ChatGPT (42%), Claude (25%), Copilot (17%)
- **Impact**:
  - Cycle Time: +22% slower
  - Review Time: +29% slower
  - PR Size: +14% larger
- **Insight**: Low adoption correlates with traditional coding patterns

---

## AI Tool Market Share (Across All Projects)

| Tool | Market Share | Category |
|------|-------------|----------|
| **CodeRabbit** | 53.5% | Review Bot |
| **Devin** | 17.9% | Autonomous Agent |
| **Cubic** | 12.8% | Autonomous Agent |
| **Claude** | 4.9% | LLM Assistant |
| **Cursor** | 4.7% | AI IDE |
| **Copilot** | 2.0% | Inline Completion |
| **Greptile** | 2.0% | Code Search |
| **ChatGPT** | 1.5% | LLM Assistant |

### Tool Category Breakdown
- **AI Review Bots** (CodeRabbit, Greptile): 55.5%
- **Autonomous Agents** (Devin, Cubic): 30.7%
- **Human-Directed AI** (Claude, Cursor, Copilot, ChatGPT): 13.1%

---

## Monthly Trends

### AI Adoption Over Time
Most teams show **increasing AI adoption** throughout 2025:
- Antiwork: 41.7% (Mar) → 97.1% (Jul) → 59.1% (Dec)
- Cal.com: 0.2% (Feb) → 80.5% (Jun) → 65.8% (Dec)
- PostHog: 1.2% (Jan) → 10.8% (Oct) → 8.7% (Dec)

### Seasonal Patterns
- **Peak AI usage**: June-August (summer push)
- **Lower AI usage**: January-March, December (holiday periods)

---

## Actionable Insights for CTOs

### 1. Mixed Tool Strategy Wins
Teams using **multiple AI tool types** (bot + IDE + LLM) show better outcomes than single-tool teams. Consider:
- **Review bots** (CodeRabbit) for automated code review
- **IDE integrations** (Cursor, Copilot) for inline suggestions
- **LLM assistants** (Claude, ChatGPT) for complex reasoning

### 2. Expect Cycle Time to Increase Initially
AI doesn't automatically speed up delivery. Teams tackling more complex work with AI see **longer cycle times** but **faster reviews**. Set expectations accordingly.

### 3. Autonomous Agents Create Larger PRs
Devin and Cubic produce significantly larger PRs (+50-80% lines). Consider:
- Breaking agent work into smaller tasks
- More frequent review checkpoints
- Human oversight for architecture decisions

### 4. Review Velocity is the Consistent Win
Across all adoption levels, **review time improvements** are the most reliable AI benefit:
- 6/8 teams show faster review times
- Average improvement: -31%
- This suggests AI code is more reviewable (better structured, documented)

### 5. Track AI Adoption as a Leading Indicator
Teams with 40-60% AI adoption show the best balance of velocity and quality. Very high adoption (>80%) may indicate over-reliance on bots.

---

## AI Detection Method Analysis: LLM vs Pattern

We use two detection methods:
1. **LLM Detection**: Groq/Llama 3.3 analyzes PR content for AI signatures
2. **Pattern Detection**: Regex patterns match known AI tool signatures

### Detection Method Comparison

| Metric | Count | % of Total |
|--------|-------|------------|
| Total PRs Analyzed | 60,216 | 100% |
| LLM Detected AI | 11,284 | 18.7% |
| Pattern Detected AI | 10,200 | 16.9% |
| **Both Methods Agree** | 9,687 | 16.1% |
| LLM-Only Detection | 1,597 | 2.7% |
| Pattern-Only Detection | 513 | 0.9% |

**Finding**: LLM catches **3x more unique AI PRs** than patterns miss (1,597 vs 513).

### Repository-Level Detection Breakdown (100+ PRs)

| Repository | Total | LLM AI% | Pattern AI% | LLM Advantage |
|------------|-------|---------|-------------|---------------|
| makeplane/plane | 1,717 | 86.1% | 85.6% | +0.5% |
| antiwork/helper | 919 | 66.1% | 66.3% | -0.2% |
| antiwork/flexile | 1,304 | 60.4% | 58.4% | +2.0% |
| dubinc/dub | 1,354 | 55.4% | 56.0% | -0.6% |
| antiwork/gumroad | 2,145 | 51.3% | 47.9% | **+3.4%** |
| formbricks/formbricks | 1,669 | 49.6% | 46.9% | +2.7% |
| calcom/cal.com | 5,670 | 40.4% | 32.8% | **+7.6%** |
| triggerdotdev/trigger.dev | 1,054 | 34.9% | 35.5% | -0.6% |
| resend/react-email | 703 | 32.3% | 32.1% | +0.2% |
| Infisical/infisical | 1,694 | 23.9% | 20.5% | **+3.4%** |
| hoppscotch/hoppscotch | 435 | 17.2% | 13.6% | +3.6% |
| novuhq/novu | 2,175 | 15.4% | 13.5% | +1.9% |
| supabase/supabase | 2,190 | 14.6% | 14.3% | +0.3% |
| trycompai/comp | 1,699 | 13.0% | 12.9% | +0.1% |
| coollabsio/coolify | 1,177 | 13.2% | 9.3% | **+3.9%** |
| PostHog/posthog | 1,742 | 9.7% | 4.4% | **+5.3%** |
| twentyhq/twenty | 5,217 | 4.9% | 1.1% | **+3.8%** |
| langchain-ai/langchain | 3,762 | 3.2% | 3.6% | -0.4% |
| denoland/deno | 2,080 | 2.9% | 0.4% | **+2.5%** |
| vercel/ai | 4,549 | 2.1% | 5.2% | **-3.1%** |

### Where LLM Detection Excels

**LLM catches 1,597 AI PRs that patterns miss.** Top tools in LLM-only detections:

| Tool | LLM-Only Count | Why Patterns Miss |
|------|----------------|-------------------|
| CodeRabbit | 458 | Implicit mentions, comment-only |
| Greptile | 403 | Context-based detection |
| Copilot | 161 | Vague acknowledgments |
| Claude | 142 | Conversational mentions |
| Cursor | 100 | IDE workflow descriptions |

**Usage types in LLM-only detections:**
- `reviewed` (38%): AI reviewed but didn't write code
- `assisted` (32%): AI helped with implementation
- `authored` (29%): AI wrote significant portions

### Where Pattern Detection Excels

**Patterns catch 515 AI PRs that LLM misses.** These are typically:

| Tool | Pattern-Only Count | Why LLM Misses |
|------|-------------------|----------------|
| ChatGPT | 201 | Boilerplate mentions LLM ignores |
| Claude | 103 | False negatives in short descriptions |
| CodeRabbit | 88 | Bot comments not in LLM context |

**Repos with most pattern-only detections:**
1. vercel/ai (157) - AI-focused repo, many tool mentions
2. langchain-ai/langchain (65) - LLM library, references ≠ usage
3. langchain-ai/langchainjs (43) - Same pattern

### Detection Confidence Analysis

For PRs where both methods agree on AI:

| Confidence Level | Count | % |
|-----------------|-------|---|
| High (≥0.8) | 66 | 0.7% |
| Medium (0.5-0.8) | 4,119 | 42.5% |
| Low (<0.5) | 3,373 | 34.8% |
| No score | 2,129 | 22.0% |

**Insight**: Most AI detections are medium-confidence. Consider increasing confidence threshold for precision-focused use cases.

### Recommendations for Detection Improvement

1. **Combine methods**: Use LLM for nuanced detection, patterns for bot signatures
2. **Repo-specific tuning**: AI-focused repos (vercel/ai, langchain) need different rules
3. **Increase context**: Include more PR comments/reviews in LLM analysis
4. **Add negative patterns**: Filter false positives in AI library repos

---

## Data Quality Notes

- **Empty body PRs**: 6,669 (11%) excluded from LLM analysis
- **LLM coverage**: 86.3% of eligible PRs analyzed
- **Detection method**: LLM-based (Groq/Llama 3.3) with regex fallback
- **AI confidence threshold**: 50% minimum

---

## Methodology

1. **Data Collection**: GitHub GraphQL API, 25 OSS projects, 2025 PRs only
2. **AI Detection**: LLM analysis of PR title, body, comments, commits
3. **Tool Attribution**: Pattern matching from PR descriptions
4. **Metrics**: Cycle time (created → merged), Review time (created → first review)
5. **Detection Comparison**: Both LLM and pattern methods run independently
