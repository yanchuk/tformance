# LLM-Based AI Detection Architecture

**Last Updated: 2025-12-24**
**Provider: Groq (Llama 3.3 70B)**

## Executive Summary

Use **Groq's Llama 3.3 70B** with **full payload approach** (all data in single prompt) and **batch API** for cost optimization. This is the simplest, most reliable approach for MVP.

**Cost**: ~$0.08/1000 PRs with batch (effectively free)
**Accuracy Target**: 70-90% detection rate (up from 24.4% regex-only)

---

## Decision: Why Groq + Llama 3.3 70B + Full Payload

### Model Selection

| Model | JSON Mode | Speed | Quality | Cost (Batch) | Decision |
|-------|-----------|-------|---------|--------------|----------|
| **Llama 3.3 70B** | Best-effort | 300 T/s | ⭐⭐⭐⭐⭐ | $0.30/M in | ✅ **CHOSEN** |
| GPT-OSS 120B | Strict | 200 T/s | ⭐⭐⭐⭐ | Higher | ❌ Less tested |
| GPT-OSS 20B | Strict | 1000 T/s | ⭐⭐⭐ | Lower | ❌ May miss nuance |
| Llama 3.1 8B | Best-effort | Fast | ⭐⭐ | $0.025/M in | ❌ Too weak |
| Compound | Tools | Varies | ⭐⭐⭐⭐ | Higher | ❌ Overkill |

**Why Llama 3.3 70B:**
- Best reasoning for nuanced cases ("Used for brainstorming" in AI section)
- Proven quality, widely tested
- Best-effort JSON works 99%+ with proper prompting
- Cost difference vs 8B is negligible ($0.08 vs $0.01 per 1000 PRs)

### Approach Selection

| Approach | Complexity | Reliability | For Our Use Case |
|----------|------------|-------------|------------------|
| **Full Payload** | Low ✅ | High ✅ | ✅ **CHOSEN** |
| Tool Calling | Medium | Medium | ❌ Not compatible with JSON mode on Groq |
| MCP/Remote Tools | High | Medium | ❌ Overkill - we have all data upfront |
| Compound (Agentic) | High | Variable | ❌ Overkill for single task |

**Why Full Payload:**
1. **Simplest** - Single API call, no tool handling logic
2. **Reliable** - No multi-turn complexity
3. **Compatible** - Works with JSON mode
4. **Batchable** - Easy to batch 1000s of requests
5. **We have all data** - PR body is self-contained, no fetching needed

### Why NOT Tool Calling

From Groq docs: *"Streaming and tool use are not currently supported with Structured Outputs."*

We need structured JSON output. Tool calling would sacrifice that.

### Why NOT MCP/Remote Tools

MCP is designed for:
- Fetching external data the LLM doesn't have
- Multi-step workflows with decisions

We have:
- All data upfront (PR body)
- Single decision task (is it AI-assisted?)

MCP would add 3-5 round trips for zero benefit.

---

## Cost Analysis

### Pricing (Groq Batch API - 50% off)

| Token Type | Standard | Batch (50% off) |
|------------|----------|-----------------|
| Input (Llama 3.3 70B) | $0.59/M | $0.295/M |
| Output (Llama 3.3 70B) | $0.79/M | $0.395/M |

### Per-PR Cost Estimate

| Component | Tokens | Cost (Batch) |
|-----------|--------|--------------|
| System prompt | ~400 | $0.00012 |
| PR body (avg) | ~600 | $0.00018 |
| Output | ~100 | $0.00004 |
| **Total per PR** | ~1100 | **$0.00008** |

### Batch Costs

| Volume | Cost |
|--------|------|
| 1,000 PRs | **$0.08** |
| 10,000 PRs | **$0.80** |
| 100,000 PRs | **$8.00** |

**This is effectively free.** We can run LLM on ALL PRs, not just ambiguous cases.

---

## Implementation Architecture

### Flow Diagram

```
┌─────────────────────────────────────────────────────────────────────────┐
│                         AI DETECTION FLOW                                │
├─────────────────────────────────────────────────────────────────────────┤
│                                                                          │
│   PR Synced from GitHub                                                  │
│          │                                                               │
│          ▼                                                               │
│   ┌──────────────────┐                                                  │
│   │  Regex Detection  │  ← Free, instant, catches 24%                   │
│   │   (Synchronous)   │                                                  │
│   └────────┬─────────┘                                                  │
│            │                                                             │
│            ▼                                                             │
│   ┌──────────────────┐                                                  │
│   │ Queue for Groq   │  ← PRs with body text, not yet LLM processed    │
│   │  Batch Processing │                                                  │
│   └────────┬─────────┘                                                  │
│            │                                                             │
│            ▼  (Nightly Celery task)                                     │
│   ┌──────────────────┐                                                  │
│   │  Groq Batch API   │  ← $0.08/1000 PRs                               │
│   │  Llama 3.3 70B    │    24h completion window                        │
│   │  Full Payload     │    JSON response format                         │
│   └────────┬─────────┘                                                  │
│            │                                                             │
│            ▼                                                             │
│   ┌──────────────────┐                                                  │
│   │  Update PR Model  │  ← is_ai_assisted, ai_tools, usage_category    │
│   │  (bulk_update)    │     llm_detection_at timestamp                  │
│   └──────────────────┘                                                  │
│                                                                          │
└─────────────────────────────────────────────────────────────────────────┘
```

### Code Implementation

#### 1. Groq Service (`apps/integrations/services/groq_ai_detector.py`)

```python
import json
import os
from dataclasses import dataclass

from groq import Groq


@dataclass
class AIDetectionResult:
    is_ai_assisted: bool
    tools: list[str]
    usage_category: str | None  # "authored", "assisted", "reviewed", "brainstorm"
    confidence: float
    reasoning: str | None = None


SYSTEM_PROMPT = """You are an AI detection system analyzing pull requests to identify if AI coding assistants were used.

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

## Response Format

Return JSON with these fields:
- is_ai_assisted: boolean
- tools: list of lowercase tool names detected (e.g., ["cursor", "claude"])
- usage_category: "authored" | "assisted" | "reviewed" | "brainstorm" | null
- confidence: float 0.0-1.0
- reasoning: brief 1-sentence explanation"""

DETECTION_SCHEMA = {
    "type": "object",
    "properties": {
        "is_ai_assisted": {"type": "boolean"},
        "tools": {"type": "array", "items": {"type": "string"}},
        "usage_category": {
            "type": ["string", "null"],
            "enum": ["authored", "assisted", "reviewed", "brainstorm", None],
        },
        "confidence": {"type": "number"},
        "reasoning": {"type": ["string", "null"]},
    },
    "required": ["is_ai_assisted", "tools", "confidence"],
}


def detect_ai_with_groq(pr_body: str) -> AIDetectionResult:
    """Detect AI usage in a PR using Groq's Llama 3.3 70B.

    Single synchronous call - use for real-time detection or testing.
    For batch processing, use create_batch_detection_file() instead.
    """
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    response = client.chat.completions.create(
        model="llama-3.3-70b-versatile",
        messages=[
            {"role": "system", "content": SYSTEM_PROMPT},
            {"role": "user", "content": f"Analyze this PR description:\n\n{pr_body}"},
        ],
        response_format={
            "type": "json_schema",
            "json_schema": {
                "name": "ai_detection",
                "strict": False,  # Best-effort for Llama
                "schema": DETECTION_SCHEMA,
            },
        },
        temperature=0,
        max_tokens=500,
    )

    result = json.loads(response.choices[0].message.content)

    return AIDetectionResult(
        is_ai_assisted=result["is_ai_assisted"],
        tools=result.get("tools", []),
        usage_category=result.get("usage_category"),
        confidence=result.get("confidence", 0.5),
        reasoning=result.get("reasoning"),
    )


def create_batch_request(pr_id: int, pr_body: str) -> dict:
    """Create a single batch request for Groq batch API."""
    return {
        "custom_id": f"pr-{pr_id}",
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": "llama-3.3-70b-versatile",
            "messages": [
                {"role": "system", "content": SYSTEM_PROMPT},
                {"role": "user", "content": f"Analyze this PR description:\n\n{pr_body}"},
            ],
            "response_format": {
                "type": "json_schema",
                "json_schema": {
                    "name": "ai_detection",
                    "strict": False,
                    "schema": DETECTION_SCHEMA,
                },
            },
            "temperature": 0,
            "max_tokens": 500,
        },
    }


def create_batch_file(prs: list[tuple[int, str]], output_path: str) -> str:
    """Create JSONL file for Groq batch API.

    Args:
        prs: List of (pr_id, pr_body) tuples
        output_path: Path to write JSONL file

    Returns:
        Path to created file
    """
    import json

    with open(output_path, "w") as f:
        for pr_id, pr_body in prs:
            request = create_batch_request(pr_id, pr_body)
            f.write(json.dumps(request) + "\n")

    return output_path


def submit_batch_job(file_path: str, completion_window: str = "24h") -> str:
    """Submit batch file to Groq and return batch ID.

    Args:
        file_path: Path to JSONL batch file
        completion_window: "24h" to "7d"

    Returns:
        Batch job ID for polling
    """
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    # Upload file
    with open(file_path, "rb") as f:
        uploaded_file = client.files.create(file=f, purpose="batch")

    # Create batch job
    batch = client.batches.create(
        completion_window=completion_window,
        endpoint="/v1/chat/completions",
        input_file_id=uploaded_file.id,
    )

    return batch.id


def get_batch_results(batch_id: str) -> dict[int, AIDetectionResult] | None:
    """Get results from completed batch job.

    Returns:
        Dict mapping pr_id to detection result, or None if not complete
    """
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    batch = client.batches.retrieve(batch_id)

    if batch.status != "completed":
        return None

    # Download results
    content = client.files.content(batch.output_file_id)

    results = {}
    for line in content.text.strip().split("\n"):
        item = json.loads(line)
        pr_id = int(item["custom_id"].replace("pr-", ""))
        response_data = json.loads(item["response"]["body"]["choices"][0]["message"]["content"])

        results[pr_id] = AIDetectionResult(
            is_ai_assisted=response_data["is_ai_assisted"],
            tools=response_data.get("tools", []),
            usage_category=response_data.get("usage_category"),
            confidence=response_data.get("confidence", 0.5),
            reasoning=response_data.get("reasoning"),
        )

    return results
```

#### 2. Celery Tasks (`apps/metrics/tasks.py`)

```python
from celery import shared_task
from django.utils import timezone

from apps.integrations.services.groq_ai_detector import (
    create_batch_file,
    submit_batch_job,
    get_batch_results,
)
from apps.metrics.models import PullRequest


@shared_task
def queue_prs_for_llm_detection():
    """Nightly task to queue PRs needing LLM detection."""

    # Get PRs with body that haven't been LLM processed
    prs = PullRequest.objects.filter(
        body__isnull=False,
        llm_detection_at__isnull=True,
    ).exclude(body="").values_list("id", "body")[:10000]  # Batch limit

    if not prs:
        return "No PRs to process"

    # Create batch file
    file_path = f"/tmp/ai_detection_batch_{timezone.now().isoformat()}.jsonl"
    create_batch_file(list(prs), file_path)

    # Submit batch job
    batch_id = submit_batch_job(file_path)

    # Schedule polling task
    poll_llm_detection_batch.apply_async(
        args=[batch_id],
        countdown=3600,  # Start checking after 1 hour
    )

    return f"Submitted batch {batch_id} with {len(prs)} PRs"


@shared_task
def poll_llm_detection_batch(batch_id: str, attempts: int = 0):
    """Poll for batch completion and update PRs."""

    results = get_batch_results(batch_id)

    if results is None:
        if attempts < 24:  # Max 24 hours
            poll_llm_detection_batch.apply_async(
                args=[batch_id, attempts + 1],
                countdown=3600,
            )
            return f"Batch {batch_id} still processing, attempt {attempts + 1}"
        else:
            return f"Batch {batch_id} timed out after 24 attempts"

    # Update PRs with results
    now = timezone.now()
    for pr_id, result in results.items():
        PullRequest.objects.filter(id=pr_id).update(
            is_ai_assisted=result.is_ai_assisted,
            ai_tools_detected=result.tools,
            llm_detection_at=now,
        )

    return f"Updated {len(results)} PRs from batch {batch_id}"
```

#### 3. Management Command (`apps/metrics/management/commands/backfill_ai_detection.py`)

```python
from django.core.management.base import BaseCommand

from apps.integrations.services.groq_ai_detector import detect_ai_with_groq
from apps.metrics.models import PullRequest
from apps.metrics.services.ai_detector import detect_ai_in_text
from apps.teams.models import Team


class Command(BaseCommand):
    help = "Backfill AI detection for existing PRs"

    def add_arguments(self, parser):
        parser.add_argument("--team", type=str, help="Team name to filter")
        parser.add_argument("--dry-run", action="store_true", help="Preview changes")
        parser.add_argument("--use-llm", action="store_true", help="Use Groq LLM")
        parser.add_argument("--limit", type=int, default=100, help="Max PRs to process")

    def handle(self, *args, **options):
        qs = PullRequest.objects.filter(body__isnull=False).exclude(body="")

        if options["team"]:
            team = Team.objects.get(name=options["team"])
            qs = qs.filter(team=team)

        prs = qs[:options["limit"]]

        changes = []
        for pr in prs:
            # Current detection
            old_ai = pr.is_ai_assisted
            old_tools = pr.ai_tools_detected or []

            # New detection
            if options["use_llm"]:
                result = detect_ai_with_groq(pr.body)
                new_ai = result.is_ai_assisted
                new_tools = result.tools
            else:
                result = detect_ai_in_text(f"{pr.title}\n\n{pr.body}")
                new_ai = result["is_ai_assisted"]
                new_tools = result["ai_tools"]

            if new_ai != old_ai or set(new_tools) != set(old_tools):
                changes.append({
                    "pr_id": pr.id,
                    "number": pr.number,
                    "old_ai": old_ai,
                    "new_ai": new_ai,
                    "old_tools": old_tools,
                    "new_tools": new_tools,
                })

                if not options["dry_run"]:
                    pr.is_ai_assisted = new_ai
                    pr.ai_tools_detected = new_tools
                    pr.save(update_fields=["is_ai_assisted", "ai_tools_detected"])

        # Report
        self.stdout.write(f"\n{'DRY RUN - ' if options['dry_run'] else ''}Changes:")
        for c in changes:
            self.stdout.write(
                f"  PR #{c['number']}: {c['old_ai']} -> {c['new_ai']}, "
                f"tools: {c['old_tools']} -> {c['new_tools']}"
            )

        self.stdout.write(f"\nTotal: {len(changes)} PRs would be updated")
```

---

## Migration: Add LLM Detection Timestamp

```python
# apps/metrics/migrations/0018_add_llm_detection_timestamp.py

from django.db import migrations, models


class Migration(migrations.Migration):
    dependencies = [
        ("metrics", "0017_add_pr_github_metadata"),
    ]

    operations = [
        migrations.AddField(
            model_name="pullrequest",
            name="llm_detection_at",
            field=models.DateTimeField(null=True, blank=True),
        ),
    ]
```

---

## Testing Strategy

### Unit Tests

```python
class TestGroqAIDetector(TestCase):
    def test_detect_cursor_usage(self):
        body = "## AI Disclosure\nCursor (Claude 4.5 Sonnet) used for implementation"
        result = detect_ai_with_groq(body)
        self.assertTrue(result.is_ai_assisted)
        self.assertIn("cursor", result.tools)

    def test_detect_negative_disclosure(self):
        body = "## AI Disclosure\nNo AI was used for this PR"
        result = detect_ai_with_groq(body)
        self.assertFalse(result.is_ai_assisted)

    def test_detect_ambiguous_usage(self):
        body = "## AI Disclosure\nUsed for brainstorming the approach"
        result = detect_ai_with_groq(body)
        # Should infer AI usage from context
        self.assertTrue(result.is_ai_assisted)
        self.assertEqual(result.usage_category, "brainstorm")
```

### Integration Tests

```python
class TestBatchProcessing(TestCase):
    def test_batch_file_creation(self):
        prs = [(1, "Test body 1"), (2, "Test body 2")]
        path = create_batch_file(prs, "/tmp/test_batch.jsonl")

        with open(path) as f:
            lines = f.readlines()

        self.assertEqual(len(lines), 2)
        self.assertIn("pr-1", lines[0])
```

---

## Rollout Plan

### Phase 1: Setup (Day 1)
- [ ] Add `groq` package: `uv add groq`
- [ ] Create `GROQ_API_KEY` secret
- [ ] Create migration for `llm_detection_at`
- [ ] Implement Groq service with tests

### Phase 2: Validation (Day 2)
- [ ] Run backfill command with `--dry-run --use-llm --limit 50`
- [ ] Manually verify 20 detections
- [ ] Compare regex vs LLM results
- [ ] Fix any prompt issues

### Phase 3: Production (Day 3)
- [ ] Run backfill on Gumroad team
- [ ] Add Celery periodic task for nightly batch
- [ ] Monitor batch job completions
- [ ] Track detection rate improvement

---

## Success Metrics

| Metric | Regex Only | With Groq LLM | Target |
|--------|------------|---------------|--------|
| Detection Rate | 24.4% | TBD | 70%+ |
| False Positive Rate | TBD | TBD | <2% |
| Cost per 1000 PRs | $0 | $0.08 | <$1 |
| Processing Time | Instant | 24h (batch) | <48h |

---

## Appendix: Alternative Approaches Rejected

### 1. Claude API (Anthropic)
- **Cost**: $3.50/1000 PRs (44x more expensive than Groq)
- **Rejected**: Too expensive for running on all PRs

### 2. GPT-OSS with Strict Mode
- **Benefit**: Guaranteed JSON schema adherence
- **Rejected**: Less proven for nuanced reasoning, Llama 3.3 is better for ambiguous cases

### 3. Tool Calling Approach
- **Rejected**: Not compatible with Groq's structured outputs feature

### 4. MCP/Remote Tools
- **Rejected**: Overkill complexity, we have all data upfront
