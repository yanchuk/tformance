# LLM-Based AI Detection Architecture

**Last Updated: 2025-12-24**

## Problem Statement

Phase 1 regex patterns achieve 24% detection rate on Gumroad PRs. ~10 PRs have ambiguous disclosures like "Used for brainstorming" without specifying the tool. LLM can infer from context (e.g., "Used for" in an "AI Disclosure" section implies AI tool usage).

## Approaches Comparison

### 1. Data Passing Strategies

#### Option A: Full Payload Approach

```python
# All data in single API call
response = claude.messages.create(
    model="claude-sonnet-4-20250514",
    messages=[{
        "role": "user",
        "content": f"""
        PR Title: {pr.title}
        PR Body: {pr.body}
        Commits: {commits_text}
        Reviews: {reviews_text}

        Analyze for AI tool usage...
        """
    }]
)
```

| Aspect | Evaluation |
|--------|------------|
| **Complexity** | Low - Single API call, no infrastructure |
| **Latency** | Low - Single round-trip |
| **Cost** | Variable - Scales with PR size (avg ~2K tokens) |
| **Token Limits** | Risk for large PRs (200K context limit) |
| **Testability** | High - Deterministic input/output |
| **Caching** | Easy - Cache by PR content hash |

#### Option B: Remote Tools / MCP Approach

```python
# LLM fetches data via tools as needed
tools = [
    {"name": "get_pr_body", "description": "Get PR description"},
    {"name": "get_commits", "description": "Get commit messages"},
    {"name": "get_reviews", "description": "Get review comments"},
]

# LLM decides what to fetch
response = claude.messages.create(
    model="claude-sonnet-4-20250514",
    tools=tools,
    messages=[{
        "role": "user",
        "content": f"Analyze PR #{pr_number} for AI tool usage"
    }]
)
# Handle tool calls, provide results, continue conversation
```

| Aspect | Evaluation |
|--------|------------|
| **Complexity** | High - Multi-turn, tool handling logic |
| **Latency** | High - Multiple API calls (3-5 round trips) |
| **Cost** | Variable - Could be lower for simple PRs |
| **Token Limits** | Solved - Fetch only needed data |
| **Testability** | Medium - Need to mock tool responses |
| **Caching** | Complex - Cache tool results separately |

#### Recommendation: **Option A (Full Payload)**

For AI detection, PR body is the primary signal. Most PRs are <5K tokens. The simplicity and testability of full payload outweighs the theoretical efficiency of tools.

---

### 2. Thinking Mode Comparison

#### Option A: Extended Thinking (claude-sonnet-4-20250514 with thinking)

```python
response = claude.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=16000,
    thinking={
        "type": "enabled",
        "budget_tokens": 10000
    },
    messages=[...]
)
```

**Advantages:**
- Shows reasoning chain for ambiguous cases
- Better at handling edge cases ("Used for brainstorming" in AI section)
- More accurate for complex disclosures

**Disadvantages:**
- Higher cost (~10K extra tokens per call)
- Higher latency (~5-10s vs ~1-2s)
- Thinking tokens not cacheable

#### Option B: Standard Mode with Structured Output

```python
response = claude.messages.create(
    model="claude-sonnet-4-20250514",
    max_tokens=1000,
    messages=[{
        "role": "user",
        "content": prompt
    }],
    # Force JSON response
    response_format={"type": "json_object"}
)
```

**Advantages:**
- Lower cost (1K tokens vs 11K)
- Lower latency (~1-2s)
- Easier to parse

**Disadvantages:**
- May miss nuances in ambiguous cases
- Less explainable decisions

#### Recommendation: **Tiered Approach**

1. **Standard Mode First**: Fast, cheap for clear cases
2. **Thinking Mode Fallback**: When confidence < threshold

```python
# First pass: Fast standard mode
result = detect_ai_standard(pr.body)

if result['confidence'] < 0.7 and has_ai_disclosure_section(pr.body):
    # Second pass: Extended thinking for ambiguous cases
    result = detect_ai_with_thinking(pr.body)
```

---

### 3. Training and Validation Strategy

#### Public Data Sources

| Source | Volume | AI Disclosure Rate | Access |
|--------|--------|-------------------|--------|
| Gumroad (antiwork/gumroad) | 1700+ PRs | ~68% have section | OAuth (team) |
| Rails (rails/rails) | 20K+ PRs | Low | Public |
| Django (django/django) | 15K+ PRs | Low | Public |
| Claude Code contributions | Varies | High (Co-Authored-By) | Public |

#### OSS Repositories to Parse (For Training Data)

**IMPORTANT: False Positive Risk in AI Product Repos**
Repos that BUILD AI products (vercel/ai, langchain) frequently mention AI tool names
(Gemini, Claude, etc.) as PRODUCTS they integrate with, NOT as authoring tools.

Preliminary analysis (200 PRs):
- vercel/ai: 7% detected, but mostly false positives (Gemini API mentions)
- langchain: 5% detected, 1 true positive (Claude Code signature)

**Tier 1: High Confidence Signal (Explicit AI Disclosure Culture)**
```python
TIER1_REPOS = [
    # Has AI Disclosure section template
    ("antiwork", "gumroad"),        # PRIMARY - 68% have AI Disclosure section

    # Anthropic projects - likely Claude Code usage
    ("anthropic", "anthropic-cookbook"),
    ("anthropic", "courses"),

    # Companies known to encourage AI tool usage
    ("supabase", "supabase"),       # AI-forward culture
    ("cal-com", "cal.com"),         # Indie dev, likely AI users
]
```

**Tier 2: AI Tool/Framework Repos (High False Positive Risk)**
```python
TIER2_REPOS = [
    # WARNING: Product mentions ≠ AI authoring
    ("vercel", "ai"),               # Gemini/Claude API product mentions
    ("langchain-ai", "langchain"),  # LLM product integrations
    ("openai", "openai-python"),
    ("cursor", "cursor"),           # May have Cursor IDE mentions as product
]
# Strategy: Look ONLY at Co-Authored-By and explicit disclosure signatures
```

**Tier 3: General OSS (Low AI Signal, Good for Negative Examples)**
```python
TIER3_REPOS = [
    ("microsoft", "vscode"),        # ~60K PRs, traditional dev
    ("facebook", "react"),          # Established, formal process
    ("django", "django"),           # Python, traditional
    ("rails", "rails"),             # Ruby, traditional
    ("kubernetes", "kubernetes"),   # Enterprise, formal
]
# Use to calibrate false positive rate
```

**Tier 4: Search-Based Discovery**
```bash
# GitHub search for Claude Code signatures
gh search prs --limit 100 "Co-Authored-By: Claude" --json repository,number

# Search for AI Disclosure sections
gh search prs --limit 100 "AI Disclosure" --json repository,number

# Search for Claude Code signature
gh search prs --limit 100 "Generated with Claude Code" --json repository,number
```

**Organizations to Watch**
```python
AI_FORWARD_ORGS = [
    "anthropic",      # Claude creator
    "vercel",         # AI SDK, Next.js
    "supabase",       # Developer-focused
    "cal-com",        # Open source calendar
    "remotion",       # Video in React
    "trigger-dev",    # Background jobs
    "highlight-io",   # Monitoring
]
```

#### Data Collection Script

```python
# Fetch PRs from OSS repos via GitHub GraphQL API
def fetch_oss_training_data():
    repos = [
        "antiwork/gumroad",
        "anthropic/courses",
        "vercel/ai",
        "langchain-ai/langchain",
    ]

    for repo in repos:
        prs = fetch_prs_graphql(repo, since="2024-01-01", limit=500)
        for pr in prs:
            yield {
                "repo": repo,
                "pr_number": pr.number,
                "title": pr.title,
                "body": pr.body,
                "author": pr.author,
                "commits": [c.message for c in pr.commits],
                # Ground truth labels added manually
            }
```

#### Labeling Strategy

1. **Ground Truth Dataset**: Manually label 200 PRs from Gumroad
   - 100 positive (AI-assisted)
   - 100 negative (not AI-assisted)
   - Focus on ambiguous cases

2. **Annotation Guidelines**:
   ```markdown
   POSITIVE if:
   - Explicit AI tool mention (Cursor, Claude, Copilot)
   - "Used for X" in AI Disclosure section (implies AI)
   - Co-Authored-By AI patterns

   NEGATIVE if:
   - "No AI", "None", "Not used"
   - Reference to AI product (not authoring)
   - No AI disclosure section and no signatures
   ```

3. **Evaluation Metrics**:
   - Precision: Avoid false positives (claiming AI when human-only)
   - Recall: Catch true AI usage
   - Target: 95% precision, 90% recall

---

## System Prompt Design

### V1: Basic Detection Prompt

```markdown
You are an AI detection system analyzing pull requests to identify if AI coding assistants were used.

Analyze the following PR for AI tool involvement. Look for:
1. Explicit tool mentions (Cursor, Claude, Copilot, Cody, Aider, Devin, Gemini, etc.)
2. AI Disclosure sections with positive statements
3. Co-Authored-By AI patterns
4. Phrases like "used AI", "AI-assisted", "generated with"

IMPORTANT: "Used for X" inside an "AI Disclosure" section implies AI tool usage even without explicit tool name.

Negative indicators (NOT AI-assisted):
- "No AI was used", "None", "Not used"
- References to AI as a product feature (not authoring)

PR Title: {title}
PR Body:
{body}

Respond in JSON format:
{
  "is_ai_assisted": boolean,
  "confidence": float (0.0-1.0),
  "tools_detected": ["tool1", "tool2"],
  "reasoning": "Brief explanation"
}
```

### V2: With Context Section Parsing

```markdown
You are an AI detection system. Your task is to determine if AI coding assistants were used to create this pull request.

## Detection Rules

POSITIVE signals (AI was used):
1. Tool names: Cursor, Claude, Copilot, Cody, Aider, Devin, Gemini, Windsurf, Tabnine
2. In "AI Disclosure" section: Any usage statement like "Used for", "Used to", "Helped with"
3. Co-Authored-By with AI names or @anthropic.com/@cursor.sh emails
4. Phrases: "AI-generated", "AI-assisted", "generated with", "written by AI"

NEGATIVE signals (AI was NOT used):
1. Explicit denials: "No AI", "None", "Not used", "N/A"
2. AI as feature: "Add AI to dashboard" (building AI features ≠ using AI to code)
3. Past tense references: "Devin's previous PR" (referencing past work)

## Analysis

PR Title: {title}

PR Body:
---
{body}
---

## Response Format (JSON)

{
  "is_ai_assisted": boolean,
  "confidence": float,  // 0.0-1.0, use 0.5-0.7 for ambiguous cases
  "tools_detected": string[],  // normalized names: "cursor", "claude", "copilot", etc.
  "ai_disclosure_found": boolean,
  "disclosure_type": "positive" | "negative" | "ambiguous" | "none",
  "reasoning": string  // 1-2 sentences explaining decision
}
```

---

## Implementation Plan

### Phase 5.1: Prompt Engineering (Effort: S)

- [ ] Create 50 labeled test cases from Gumroad PRs
- [ ] Design V1 prompt, evaluate on test cases
- [ ] Iterate to V2, compare precision/recall
- [ ] Document edge cases and handling

### Phase 5.2: Service Implementation (Effort: M)

```python
# apps/metrics/services/ai_disclosure_llm.py

from anthropic import Anthropic

class AIDisclosureLLMParser:
    def __init__(self):
        self.client = Anthropic()
        self.cache = {}  # Redis in production

    def parse(self, pr_body: str, use_thinking: bool = False) -> dict:
        cache_key = hashlib.sha256(pr_body.encode()).hexdigest()
        if cached := self.cache.get(cache_key):
            return cached

        response = self._call_claude(pr_body, use_thinking)
        result = json.loads(response.content[0].text)

        self.cache[cache_key] = result
        return result

    def _call_claude(self, pr_body: str, use_thinking: bool) -> Message:
        kwargs = {
            "model": "claude-sonnet-4-20250514",
            "max_tokens": 1000 if not use_thinking else 16000,
            "messages": [{"role": "user", "content": self.prompt.format(body=pr_body)}]
        }
        if use_thinking:
            kwargs["thinking"] = {"type": "enabled", "budget_tokens": 10000}

        return self.client.messages.create(**kwargs)
```

### Phase 5.3: Integration with Sync (Effort: S)

```python
# In github_graphql_sync.py

async def _detect_pr_ai_involvement(author: str, title: str, body: str) -> tuple[bool, list]:
    # First: Regex (fast, free)
    regex_result = detect_ai_in_text(body)
    if regex_result['is_ai_assisted']:
        return True, regex_result['ai_tools']

    # Second: Check for AI Disclosure section
    if 'ai disclosure' not in body.lower():
        return False, []

    # Third: LLM for ambiguous cases
    llm_result = ai_llm_parser.parse(body)
    if llm_result['confidence'] >= 0.7:
        return llm_result['is_ai_assisted'], llm_result['tools_detected']

    # Fourth: Extended thinking for low confidence
    llm_result = ai_llm_parser.parse(body, use_thinking=True)
    return llm_result['is_ai_assisted'], llm_result['tools_detected']
```

### Phase 5.4: Batch Processing & Backfill (Effort: M)

- [ ] Create Celery task for async LLM detection
- [ ] Rate limiting (respect API limits)
- [ ] Cost tracking and budgeting
- [ ] Backfill command with dry-run

### Phase 5.5: Monitoring & Iteration (Effort: S)

- [ ] Log LLM decisions for review
- [ ] A/B compare regex vs LLM accuracy
- [ ] Dashboard for detection confidence distribution

---

## Cost Analysis

### Standard Pricing (claude-sonnet-4-20250514)

| Approach | Tokens/PR | Cost/PR | Cost/1000 PRs |
|----------|-----------|---------|---------------|
| Regex only | 0 | $0 | $0 |
| Standard LLM | ~2K total | $0.009 | $9 |
| Extended Thinking | ~12K total | $0.036 | $36 |

### With Prompt Caching + Batch API

Claude API optimizations:
- **Prompt Caching**: System prompt cached, 90% reduction on prompt tokens
- **Batch API**: 50% discount for async processing (24h window)

| Optimization | Input Cost | Output Cost | Effective Discount |
|--------------|------------|-------------|-------------------|
| Standard | $3/M | $15/M | 0% |
| Prompt Cache (cached tokens) | $0.30/M | $15/M | ~85% on prompt |
| Batch API | $1.50/M | $7.50/M | 50% overall |
| Cache + Batch | $0.15/M | $7.50/M | ~90% on prompt |

**Cost with Optimizations:**

Assumptions:
- System prompt: 500 tokens (cached)
- PR body: 1,500 tokens avg (not cached)
- Output: 200 tokens

| Approach | Cost/PR | Cost/1000 PRs | Cost/10K PRs |
|----------|---------|---------------|--------------|
| Batch + Cache | $0.0035 | $3.50 | $35 |
| Tiered (20% LLM) | $0.0007 | $0.70 | $7 |

**Conclusion**: At $3.50/1000 PRs, LLM-for-all is viable. Compare accuracy improvement vs $3.50/1000 additional cost.

---

## Testability Matrix

| Approach | Unit Tests | Integration Tests | E2E Tests |
|----------|------------|-------------------|-----------|
| Full Payload | Easy - Mock Claude response | Medium - Need API | Hard |
| MCP/Tools | Medium - Mock tools | Hard - Multiple calls | Very Hard |
| Thinking Mode | Easy - Mock response | Medium | Hard |
| Tiered | Easy - Mock both layers | Medium | Medium |

---

## Decision Summary

| Decision | Choice | Rationale |
|----------|--------|-----------|
| Data Passing | Full Payload | Simpler, cacheable, PR body is primary signal |
| LLM Model | claude-sonnet-4-20250514 | Best cost/quality balance |
| Thinking Mode | Tiered | Fast for clear cases, thinking for ambiguous |
| Caching | Redis (content hash) | Avoid repeat API calls for same PR |
| Integration | Fallback after regex | Free regex first, paid LLM second |

---

---

## Experiment Design: Regex vs LLM Comparison

### Objective
Determine if LLM-for-all with batch+cache is worth $3.50/1000 PRs vs free regex.

### Experiment Setup

```python
# 1. Collect test dataset from multiple OSS repos
test_repos = [
    "antiwork/gumroad",      # 500 PRs (our primary)
    "vercel/ai",             # 200 PRs (AI SDK)
    "langchain-ai/langchain", # 200 PRs (LLM framework)
    "microsoft/vscode",       # 200 PRs (large, traditional)
]

# 2. Run both detection methods
for pr in test_prs:
    regex_result = detect_ai_in_text(pr.body)
    llm_result = detect_ai_with_llm(pr.body)

    results.append({
        "pr_id": pr.id,
        "repo": pr.repo,
        "regex_detected": regex_result["is_ai_assisted"],
        "regex_tools": regex_result["ai_tools"],
        "llm_detected": llm_result["is_ai_assisted"],
        "llm_tools": llm_result["tools_detected"],
        "llm_confidence": llm_result["confidence"],
        "llm_reasoning": llm_result["reasoning"],
    })

# 3. Manual review of disagreements
disagreements = [r for r in results if r["regex_detected"] != r["llm_detected"]]
# Human labels these as ground truth
```

### Metrics to Measure

| Metric | Calculation | Target |
|--------|-------------|--------|
| Regex Precision | TP / (TP + FP) | >95% |
| Regex Recall | TP / (TP + FN) | >80% |
| LLM Precision | TP / (TP + FP) | >98% |
| LLM Recall | TP / (TP + FN) | >95% |
| Agreement Rate | Same / Total | Measure |
| LLM Lift | LLM Recall - Regex Recall | >10% to justify cost |

### Decision Criteria

```
IF llm_lift > 10% AND llm_precision >= regex_precision:
    USE LLM-for-all (with batch+cache)
ELIF llm_lift > 5%:
    USE tiered (regex first, LLM for AI Disclosure sections)
ELSE:
    KEEP regex-only (LLM not worth the cost)
```

### Pattern Improvement Loop

When LLM catches what regex misses:

```python
# 1. Analyze LLM catches
llm_only_detections = [r for r in results
                       if r["llm_detected"] and not r["regex_detected"]]

# 2. Extract patterns from LLM reasoning
for detection in llm_only_detections:
    print(f"PR: {detection['pr_id']}")
    print(f"Body: {pr.body[:200]}")
    print(f"LLM reasoning: {detection['llm_reasoning']}")
    # Human reviews and adds new regex pattern if common

# 3. Add to regex patterns, re-run experiment
```

This creates a feedback loop where LLM discoveries improve regex patterns.

---

## Batch API Implementation

### Using Anthropic Batch API

```python
from anthropic import Anthropic

client = Anthropic()

def create_batch_detection_job(prs: list[PullRequest]) -> str:
    """Create a batch job for AI detection on multiple PRs."""

    requests = []
    for pr in prs:
        requests.append({
            "custom_id": f"pr-{pr.id}",
            "params": {
                "model": "claude-sonnet-4-20250514",
                "max_tokens": 500,
                "messages": [{
                    "role": "user",
                    "content": format_detection_prompt(pr.body)
                }]
            }
        })

    # Create batch job (returns in ~24h, 50% cheaper)
    batch = client.batches.create(requests=requests)
    return batch.id

def poll_batch_results(batch_id: str) -> dict:
    """Poll for batch completion and parse results."""

    while True:
        batch = client.batches.retrieve(batch_id)
        if batch.status == "completed":
            break
        time.sleep(60)  # Check every minute

    # Download results
    results = {}
    for result in batch.results:
        pr_id = result.custom_id.replace("pr-", "")
        response = json.loads(result.message.content[0].text)
        results[pr_id] = response

    return results
```

### Celery Task for Batch Processing

```python
# apps/metrics/tasks.py

@shared_task
def batch_detect_ai_usage(pr_ids: list[int]):
    """Celery task to batch process PRs for AI detection."""

    prs = PullRequest.objects.filter(id__in=pr_ids)

    # Create batch job
    batch_id = create_batch_detection_job(list(prs))

    # Schedule polling task
    poll_batch_results_task.apply_async(
        args=[batch_id, pr_ids],
        countdown=3600  # Start checking after 1 hour
    )

@shared_task
def poll_batch_results_task(batch_id: str, pr_ids: list[int]):
    """Poll for batch results and update PRs."""

    results = poll_batch_results(batch_id)

    for pr_id, detection in results.items():
        PullRequest.objects.filter(id=pr_id).update(
            is_ai_assisted=detection["is_ai_assisted"],
            ai_tools_detected=detection["tools_detected"],
            ai_detection_confidence=detection["confidence"],
        )
```

---

## Next Steps

### Immediate (This Week)
1. Fetch PRs from 4 OSS repos (antiwork/gumroad, vercel/ai, langchain-ai/langchain, microsoft/vscode)
2. Create labeled test dataset (200 PRs with manual ground truth)

### Phase 1: Baseline Comparison
3. Run regex on all test PRs, record results
4. Run LLM (batch) on all test PRs, record results
5. Calculate metrics, identify disagreements
6. Manual review disagreements → ground truth

### Phase 2: Pattern Improvement
7. Analyze LLM-only detections
8. Extract new regex patterns from LLM reasoning
9. Add patterns, re-run comparison
10. Iterate until regex catches 90%+ of what LLM catches

### Phase 3: Production Decision
11. Calculate final lift from LLM
12. If lift > 10%: Implement LLM with batch+cache
13. If lift < 10%: Stay with enhanced regex
14. Document decision with data
