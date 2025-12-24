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
from dataclasses import dataclass
from pathlib import Path
from typing import TYPE_CHECKING

from groq import Groq

if TYPE_CHECKING:
    from apps.metrics.models import PullRequest

# Default system prompt for AI detection with rich context
DEFAULT_SYSTEM_PROMPT = """You are an AI detection system analyzing pull requests.
Your task is to identify if AI coding assistants were used to write or assist with the code.
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
<full body/description text>
```

## Detection Rules

POSITIVE signals (AI was used to write/assist code):
1. **Tool mentions**: Cursor, Claude, Copilot, Cody, Aider, Devin, Gemini, Windsurf, Tabnine
2. **AI Disclosure sections**: Look for headings like "AI Disclosure", "AI Usage", "Tools Used"
   - Usage statements: "Used for", "Used to", "Helped with", "Assisted with"
   - Model names: Sonnet, Opus, Haiku, GPT-4, Claude 4.5
3. **Commit signatures**: Co-Authored-By with AI emails (@anthropic.com, @cursor.sh)
4. **Explicit markers**: "Generated with Claude Code", "AI-generated", "written by AI"
5. **IDE references**: "in Cursor", "via Cursor", "using Cursor IDE"

NEGATIVE signals (AI was NOT used):
1. **Explicit denials**: "No AI was used", "None", "N/A", "Not used"
2. **AI as product feature** (building AI != using AI):
   - "Add AI to dashboard", "Integrate Claude API", "Gemini SDK support"
3. **Past references**: "Devin's previous PR", "as Claude mentioned" (referring to people/past work)
4. **Bot authors** (already tracked separately): dependabot, renovate

## Response Format

Return JSON:
```json
{
  "is_ai_assisted": boolean,
  "tools": ["lowercase", "tool", "names"],
  "usage_category": "authored" | "assisted" | "reviewed" | "brainstorm" | null,
  "confidence": 0.0-1.0,
  "reasoning": "1-sentence explanation"
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
    """Result from batch processing a single PR."""

    pr_id: int
    is_ai_assisted: bool
    tools: list[str]
    confidence: float
    usage_category: str | None = None
    reasoning: str | None = None
    error: str | None = None

    @classmethod
    def from_response(cls, custom_id: str, response_body: dict) -> BatchResult:
        """Parse from Groq batch response."""
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
            return cls(
                pr_id=pr_id,
                is_ai_assisted=data.get("is_ai_assisted", False),
                tools=data.get("tools", []),
                confidence=data.get("confidence", 0.0),
                usage_category=data.get("usage_category"),
                reasoning=data.get("reasoning"),
            )
        except (json.JSONDecodeError, KeyError, IndexError) as e:
            return cls(
                pr_id=pr_id,
                is_ai_assisted=False,
                tools=[],
                confidence=0.0,
                error=f"Failed to parse response: {e}",
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
    ):
        """Initialize processor.

        Args:
            api_key: Groq API key (defaults to GROQ_API_KEY env var)
            model: Model to use for detection
            system_prompt: Custom system prompt (uses default if not provided)
        """
        self.client = Groq(api_key=api_key or os.environ.get("GROQ_API_KEY"))
        self.model = model
        self.system_prompt = system_prompt or DEFAULT_SYSTEM_PROMPT

    def _format_pr_context(self, pr: PullRequest) -> str:
        """Format PR with rich context for LLM analysis.

        Includes metadata that helps with detection accuracy:
        - Title often contains AI tool mentions
        - Size helps identify AI-typical large PRs
        - Labels may include "ai-generated" tags
        - Author context for bot detection
        """
        # Get author username
        author = "unknown"
        if pr.author:
            author = pr.author.github_username or pr.author.display_name or "unknown"

        # Format labels
        labels = ", ".join(pr.labels) if pr.labels else "none"

        # Format linked issues
        issues = ", ".join(f"#{i}" for i in pr.linked_issues) if pr.linked_issues else "none"

        # Build structured context
        context = f"""# PR Metadata
- Title: {pr.title or "No title"}
- Author: {author}
- Repository: {pr.github_repo}
- Size: +{pr.additions}/-{pr.deletions} lines
- Labels: {labels}
- Linked Issues: {issues}

# PR Description
{pr.body}"""

        return context

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

                # Format PR with rich context
                pr_context = self._format_pr_context(pr)

                request = {
                    "custom_id": f"pr-{pr.id}",
                    "method": "POST",
                    "url": "/v1/chat/completions",
                    "body": {
                        "model": self.model,
                        "messages": [
                            {"role": "system", "content": self.system_prompt},
                            {
                                "role": "user",
                                "content": f"Analyze this PR for AI tool usage:\n\n{pr_context}",
                            },
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
