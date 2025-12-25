"""Groq Batch API service for AI detection.

Uses Groq's batch API for 50% cost savings on bulk PR analysis.
Batch API workflow:
1. Create JSONL file with requests
2. Upload file to Groq
3. Create batch job
4. Poll for completion
5. Download and parse results

Usage:
    processor = GroqBatchProcessor()
    batch_id = processor.submit_batch(prs)
    # ... wait for processing ...
    results = processor.get_results(batch_id)
"""

from __future__ import annotations

import json
import os
import tempfile
from dataclasses import dataclass, field
from pathlib import Path
from typing import TYPE_CHECKING

from groq import Groq

if TYPE_CHECKING:
    from apps.metrics.models import PullRequest

# Import prompts from source of truth
from apps.metrics.services.llm_prompts import (
    PR_ANALYSIS_SYSTEM_PROMPT,
    PROMPT_VERSION,
    build_llm_pr_context,
)

# Default system prompt for AI detection with rich context
DEFAULT_SYSTEM_PROMPT = """You analyze pull requests to detect AI tool usage and identify technologies.
You MUST respond with valid JSON only.

## Input Format

You will receive a PR in this structured format:
```
# PR Metadata
- Title: <PR title>
- Author: <username>
- Repository: <org/repo>
- Size: +<additions>/-<deletions> lines
- Labels: <comma-separated list>
- Linked Issues: <issue numbers if any>

# PR Description
<full body/description text - may contain AI Disclosure section>

# Files Changed (if available)
- [category] filename (+additions/-deletions)
<files are categorized as: frontend, backend, test, config, docs, other>

# Commit Messages (if available)
- <commit message - may contain Co-Authored-By signatures>
<Important: Look for "Co-Authored-By: Claude" or similar AI co-author signatures>

# Review Comments (if available)
- [STATE] reviewer: <comment text>
<Reviewers may discuss or ask about AI tool usage in comments>
```

## Task 1: AI Detection

**POSITIVE signals** (AI was used):
1. Tool mentions: Cursor, Claude, Copilot, Cody, Aider, Devin, Gemini, Windsurf, Tabnine
2. AI Disclosure sections with usage statements
3. Commit signatures: Co-Authored-By with AI emails (@anthropic.com, @cursor.sh)
4. Explicit markers: "Generated with Claude Code", "AI-generated"

**NEGATIVE signals** (AI was NOT used):
1. Explicit denials: "No AI was used", "None", "N/A"
2. AI as product feature (building AI != using AI)
3. Bot authors: dependabot, renovate (tracked separately)

## Task 2: Technology Detection

Analyze the **Files Changed** section to determine:
1. **Primary language**: Most significant language by lines changed
2. **Tech categories**: What areas the PR touches

**Language detection** (from file extensions, SO 2025 Survey):
Top languages:
- JavaScript: .js, .jsx, .mjs → "javascript"
- TypeScript: .ts, .tsx → "typescript"
- Python: .py → "python"
- Java: .java → "java"
- C#: .cs → "csharp"
- C++: .cpp, .cc, .cxx → "cpp"
- PHP: .php → "php"
- Go: .go → "go"
- Rust: .rs → "rust"
- Ruby: .rb → "ruby"
- Swift: .swift → "swift"
- Kotlin: .kt, .kts → "kotlin"
- Scala: .scala → "scala"
- Dart: .dart → "dart"
- Elixir: .ex, .exs → "elixir"
- SQL: .sql → "sql"
- Shell: .sh, .bash → "shell"
- HTML/CSS: .html, .css, .scss → "html_css"
- Vue: .vue → "vue"
- Svelte: .svelte → "svelte"

**Category detection** (from [category] prefix and paths):
- frontend: React, Vue, CSS, HTML components
- backend: API, services, models, database
- test: Test files
- config: Configuration, CI/CD
- docs: Documentation

## Response Format

Return JSON:
```json
{
  "is_ai_assisted": boolean,
  "tools": ["lowercase", "tool", "names"],
  "usage_category": "authored" | "assisted" | "reviewed" | "brainstorm" | null,
  "confidence": 0.0-1.0,
  "reasoning": "1-sentence explanation",
  "primary_language": "<language-name>" | null,
  "tech_categories": ["frontend", "backend", "test", "config", "docs"]
}
```

## Confidence Guidelines
- 0.9-1.0: Explicit "Generated with X" or clear AI disclosure
- 0.7-0.9: AI disclosure section with usage statement
- 0.5-0.7: Implicit or ambiguous usage
- 0.0-0.5: No AI used or explicit denial

## Tool Names (use lowercase)
cursor, claude, copilot, cody, devin, gemini, chatgpt, gpt4, aider, windsurf, tabnine, supermaven, codeium, continue"""


@dataclass
class BatchResult:
    """Result from batch processing a single PR.

    Supports both v4 (flat), v5 (nested), and v6 (with health) response formats.
    v5 adds summary field for CTO dashboard display.
    v6 adds health assessment with review friction, scope, and risk.
    """

    pr_id: int
    is_ai_assisted: bool
    tools: list[str]
    confidence: float
    usage_category: str | None = None
    reasoning: str | None = None
    error: str | None = None
    # Technology detection
    primary_language: str | None = None
    tech_categories: list[str] | None = None
    tech_languages: list[str] = field(default_factory=list)
    tech_frameworks: list[str] = field(default_factory=list)
    # PR Summary (v5 prompt)
    summary_title: str | None = None
    summary_description: str | None = None
    summary_type: str | None = None
    # Health Assessment (v6 prompt)
    health_review_friction: str | None = None
    health_scope: str | None = None
    health_risk_level: str | None = None
    health_insights: list[str] = field(default_factory=list)
    # Raw LLM response for storage
    llm_summary: dict = field(default_factory=dict)
    prompt_version: str = PROMPT_VERSION

    @classmethod
    def from_response(cls, custom_id: str, response_body: dict) -> BatchResult:
        """Parse from Groq batch response.

        Handles both v4 (flat) and v5 (nested) response formats.
        """
        pr_id = int(custom_id.replace("pr-", ""))

        # Check for error
        if "error" in response_body:
            return cls(
                pr_id=pr_id,
                is_ai_assisted=False,
                tools=[],
                confidence=0.0,
                error=response_body["error"].get("message", "Unknown error"),
            )

        # Parse successful response
        try:
            content = response_body["choices"][0]["message"]["content"]
            data = json.loads(content)

            # Detect v5 nested format vs v4 flat format
            if "ai" in data and isinstance(data["ai"], dict):
                return cls._parse_v5_response(pr_id, data)
            else:
                return cls._parse_v4_response(pr_id, data)

        except (json.JSONDecodeError, KeyError, IndexError) as e:
            return cls(
                pr_id=pr_id,
                is_ai_assisted=False,
                tools=[],
                confidence=0.0,
                error=f"Failed to parse response: {e}",
            )

    @classmethod
    def _parse_v4_response(cls, pr_id: int, data: dict) -> BatchResult:
        """Parse v4 flat response format."""
        return cls(
            pr_id=pr_id,
            is_ai_assisted=data.get("is_ai_assisted", False),
            tools=data.get("tools", []),
            confidence=data.get("confidence", 0.0),
            usage_category=data.get("usage_category"),
            reasoning=data.get("reasoning"),
            primary_language=data.get("primary_language"),
            tech_categories=data.get("tech_categories", []),
            llm_summary=data,
        )

    @classmethod
    def _parse_v5_response(cls, pr_id: int, data: dict) -> BatchResult:
        """Parse v5/v6 nested response format with ai/tech/summary/health sections."""
        ai = data.get("ai", {})
        tech = data.get("tech", {})
        summary = data.get("summary", {})
        health = data.get("health", {})

        # Get tech categories and primary language
        tech_categories = tech.get("categories", [])
        tech_languages = tech.get("languages", [])
        primary_language = tech_languages[0] if tech_languages else None

        return cls(
            pr_id=pr_id,
            is_ai_assisted=ai.get("is_assisted", False),
            tools=ai.get("tools", []),
            confidence=ai.get("confidence", 0.0),
            usage_category=ai.get("usage_type"),
            # Technology
            primary_language=primary_language,
            tech_categories=tech_categories,
            tech_languages=tech_languages,
            tech_frameworks=tech.get("frameworks", []),
            # Summary
            summary_title=summary.get("title"),
            summary_description=summary.get("description"),
            summary_type=summary.get("type"),
            # Health Assessment (v6)
            health_review_friction=health.get("review_friction"),
            health_scope=health.get("scope"),
            health_risk_level=health.get("risk_level"),
            health_insights=health.get("insights", []),
            # Store full response for llm_summary field
            llm_summary=data,
        )


@dataclass
class BatchStatus:
    """Status of a batch job."""

    batch_id: str
    status: str  # validating, in_progress, completed, failed, cancelled
    total_requests: int
    completed_requests: int
    failed_requests: int
    output_file_id: str | None = None
    error_file_id: str | None = None

    @property
    def is_complete(self) -> bool:
        """Check if batch is done processing."""
        return self.status in ("completed", "failed", "cancelled")

    @property
    def progress_pct(self) -> float:
        """Get completion percentage."""
        if self.total_requests == 0:
            return 0.0
        return (self.completed_requests / self.total_requests) * 100


class GroqBatchProcessor:
    """Process PRs using Groq's batch API for 50% cost savings."""

    def __init__(
        self,
        api_key: str | None = None,
        model: str = "llama-3.3-70b-versatile",
        system_prompt: str | None = None,
        use_v5_prompt: bool = True,
    ):
        """Initialize processor.

        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
            model: Model to use for detection
            system_prompt: Custom system prompt (uses PR_ANALYSIS_SYSTEM_PROMPT v5 by default)
            use_v5_prompt: If True, use v5 prompt from llm_prompts.py (default)
        """
        self.client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))
        self.model = model
        # Use v5 prompt from llm_prompts.py by default
        if system_prompt:
            self.system_prompt = system_prompt
        elif use_v5_prompt:
            self.system_prompt = PR_ANALYSIS_SYSTEM_PROMPT
        else:
            self.system_prompt = DEFAULT_SYSTEM_PROMPT
        self.prompt_version = PROMPT_VERSION

    # NOTE: _format_pr_context and helper methods removed in v6.2.0
    # Now using unified build_llm_pr_context() from llm_prompts.py

    def create_batch_file(
        self,
        prs: list[PullRequest],
        output_path: str | Path | None = None,
    ) -> Path:
        """Create JSONL file for batch processing.

        Args:
            prs: List of PullRequest objects to process
            output_path: Optional path for output file (creates temp file if not provided)

        Returns:
            Path to created JSONL file
        """
        if output_path:
            path = Path(output_path)
        else:
            fd, temp_path = tempfile.mkstemp(suffix=".jsonl", prefix="groq_batch_")
            os.close(fd)
            path = Path(temp_path)

        with open(path, "w") as f:
            for pr in prs:
                if not pr.body:
                    continue

                # Format PR with unified context builder (includes all PR data)
                pr_context = build_llm_pr_context(pr)

                request = {
                    "custom_id": f"pr-{pr.id}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": self.system_prompt},
                            {"role": "user", "content": pr_context},
                        ],
                        "response_format": {"type": "json_object"},
                        "temperature": 0,
                        "max_tokens": 500,
                    },
                }
                f.write(json.dumps(request) + "\n")

        return path

    def upload_file(self, file_path: str | Path) -> str:
        """Upload batch file to Groq.

        Args:
            file_path: Path to JSONL file

        Returns:
            File ID from Groq
        """
        with open(file_path, "rb") as f:
            response = self.client.files.create(file=f, purpose="batch")
        return response.id

    def submit_batch(
        self,
        prs: list[PullRequest],
        completion_window: str = "24h",
    ) -> str:
        """Submit PRs for batch processing.

        Args:
            prs: List of PullRequest objects to process
            completion_window: Processing window ("24h" to "7d")

        Returns:
            Batch ID for tracking
        """
        # Create and upload batch file
        batch_file = self.create_batch_file(prs)
        try:
            file_id = self.upload_file(batch_file)

            # Create batch job
            batch = self.client.batches.create(
                completion_window=completion_window,
                endpoint="/v1/chat/completions",
                input_file_id=file_id,
            )
            return batch.id
        finally:
            # Clean up temp file
            batch_file.unlink(missing_ok=True)

    def get_status(self, batch_id: str) -> BatchStatus:
        """Get current status of a batch job.

        Args:
            batch_id: Batch ID from submit_batch()

        Returns:
            BatchStatus with current state
        """
        batch = self.client.batches.retrieve(batch_id)

        return BatchStatus(
            batch_id=batch.id,
            status=batch.status,
            total_requests=batch.request_counts.total,
            completed_requests=batch.request_counts.completed,
            failed_requests=batch.request_counts.failed,
            output_file_id=batch.output_file_id,
            error_file_id=batch.error_file_id,
        )

    def get_results(self, batch_id: str) -> list[BatchResult]:
        """Get results from a completed batch.

        Args:
            batch_id: Batch ID from submit_batch()

        Returns:
            List of BatchResult objects

        Raises:
            ValueError: If batch is not complete
        """
        status = self.get_status(batch_id)

        if not status.is_complete:
            raise ValueError(f"Batch {batch_id} is not complete (status: {status.status})")

        if not status.output_file_id:
            raise ValueError(f"Batch {batch_id} has no output file")

        # Download results
        response = self.client.files.content(status.output_file_id)

        # Parse JSONL results (text() is a method, not property)
        results = []
        for line in response.text().strip().split("\n"):
            if not line:
                continue
            data = json.loads(line)
            result = BatchResult.from_response(
                custom_id=data["custom_id"],
                response_body=data.get("response", {}).get("body", {}),
            )
            results.append(result)

        return results

    def cancel_batch(self, batch_id: str) -> BatchStatus:
        """Cancel a batch job.

        Args:
            batch_id: Batch ID to cancel

        Returns:
            Updated BatchStatus
        """
        self.client.batches.cancel(batch_id)
        return self.get_status(batch_id)
