"""Experiment runner for AI detection experiments.

This module provides tools for running AI detection experiments using LLMs
(via LiteLLM) and comparing results with regex-based detection.

Example:
    runner = ExperimentRunner(config_path="experiments/default.yaml")
    results = runner.run(team=my_team, limit=100)
    print(results.calculate_metrics())
"""

from __future__ import annotations

import json
import os
import re
from dataclasses import dataclass, field
from datetime import datetime
from pathlib import Path
from typing import Any

import litellm
import yaml

from apps.metrics.models import PullRequest
from apps.metrics.services.ai_detector import detect_ai_in_text

# Configure LiteLLM callbacks for PostHog analytics
# This automatically logs all LLM calls as $ai_generation events
if os.environ.get("POSTHOG_API_KEY"):
    litellm.success_callback = ["posthog"]
    litellm.failure_callback = ["posthog"]


@dataclass
class AIDetectionResult:
    """Result from LLM-based AI detection."""

    is_ai_assisted: bool
    tools: list[str]
    confidence: float
    usage_category: str | None = None
    reasoning: str | None = None

    @classmethod
    def from_dict(cls, data: dict) -> AIDetectionResult:
        """Create from LLM response dict."""
        return cls(
            is_ai_assisted=data.get("is_ai_assisted", False),
            tools=data.get("tools", []),
            confidence=data.get("confidence", 0.0),
            usage_category=data.get("usage_category"),
            reasoning=data.get("reasoning"),
        )

    def to_dict(self) -> dict:
        """Convert to dict for serialization."""
        return {
            "is_ai_assisted": self.is_ai_assisted,
            "tools": self.tools,
            "confidence": self.confidence,
            "usage_category": self.usage_category,
            "reasoning": self.reasoning,
        }


@dataclass
class PRResult:
    """Result for a single PR."""

    pr_id: int
    pr_number: int | None
    pr_body: str
    llm_result: AIDetectionResult
    regex_result: dict
    latency_ms: float | None = None

    def to_dict(self) -> dict:
        """Convert to dict for serialization."""
        return {
            "pr_id": self.pr_id,
            "pr_number": self.pr_number,
            "llm_result": self.llm_result.to_dict(),
            "regex_result": self.regex_result,
            "latency_ms": self.latency_ms,
        }


@dataclass
class ExperimentConfig:
    """Configuration for an experiment."""

    experiment_name: str
    model_provider: str = "groq"
    model_name: str = "llama-3.3-70b-versatile"
    temperature: float = 0
    max_tokens: int = 500
    system_prompt: str | None = None
    prompt_file: str | None = None
    description: str | None = None

    @classmethod
    def from_yaml(cls, path: str) -> ExperimentConfig:
        """Load configuration from YAML file."""
        with open(path) as f:
            data = yaml.safe_load(f)

        experiment = data.get("experiment", {})
        model = data.get("model", {})
        prompt = data.get("prompt", {})

        return cls(
            experiment_name=experiment.get("name", "unnamed"),
            description=experiment.get("description"),
            model_provider=model.get("provider", "groq"),
            model_name=model.get("name", "llama-3.3-70b-versatile"),
            temperature=model.get("temperature", 0),
            max_tokens=model.get("max_tokens", 500),
            system_prompt=prompt.get("system"),
            prompt_file=prompt.get("file"),
        )

    @classmethod
    def from_dict(cls, data: dict) -> ExperimentConfig:
        """Create from config dict."""
        experiment = data.get("experiment", {})
        model = data.get("model", {})
        prompt = data.get("prompt", {})

        return cls(
            experiment_name=experiment.get("name", "unnamed"),
            description=experiment.get("description"),
            model_provider=model.get("provider", "groq"),
            model_name=model.get("name", "llama-3.3-70b-versatile"),
            temperature=model.get("temperature", 0),
            max_tokens=model.get("max_tokens", 500),
            system_prompt=prompt.get("system"),
            prompt_file=prompt.get("file"),
        )

    @property
    def litellm_model(self) -> str:
        """Get LiteLLM model string."""
        return f"{self.model_provider}/{self.model_name}"

    def to_dict(self) -> dict:
        """Convert to dict for serialization."""
        return {
            "experiment_name": self.experiment_name,
            "description": self.description,
            "model_provider": self.model_provider,
            "model_name": self.model_name,
            "temperature": self.temperature,
            "max_tokens": self.max_tokens,
        }


@dataclass
class ExperimentResult:
    """Results from running an experiment."""

    experiment_name: str
    config: dict
    started_at: str
    completed_at: str
    results: dict[int, PRResult] = field(default_factory=dict)

    def calculate_metrics(self) -> dict:
        """Calculate aggregate metrics from results."""
        total = len(self.results)
        if total == 0:
            return {
                "total_prs": 0,
                "llm_detected": 0,
                "regex_detected": 0,
                "llm_detection_rate": 0,
                "regex_detection_rate": 0,
                "agreements": 0,
                "disagreements": 0,
                "agreement_rate": 0,
            }

        llm_detected = sum(1 for r in self.results.values() if r.llm_result.is_ai_assisted)
        regex_detected = sum(1 for r in self.results.values() if r.regex_result.get("is_ai_assisted", False))

        agreements = 0
        disagreements = 0
        for r in self.results.values():
            llm_positive = r.llm_result.is_ai_assisted
            regex_positive = r.regex_result.get("is_ai_assisted", False)
            if llm_positive == regex_positive:
                agreements += 1
            else:
                disagreements += 1

        return {
            "total_prs": total,
            "llm_detected": llm_detected,
            "regex_detected": regex_detected,
            "llm_detection_rate": llm_detected / total,
            "regex_detection_rate": regex_detected / total,
            "agreements": agreements,
            "disagreements": disagreements,
            "agreement_rate": agreements / total if total > 0 else 0,
        }

    def get_disagreements(self) -> list[dict]:
        """Get list of PRs where LLM and regex disagree."""
        disagreements = []
        for pr_id, r in self.results.items():
            llm_detected = r.llm_result.is_ai_assisted
            regex_detected = r.regex_result.get("is_ai_assisted", False)
            if llm_detected != regex_detected:
                disagreements.append(
                    {
                        "pr_id": pr_id,
                        "pr_number": r.pr_number,
                        "llm_detected": llm_detected,
                        "regex_detected": regex_detected,
                        "llm_tools": r.llm_result.tools,
                        "regex_tools": r.regex_result.get("ai_tools", []),
                        "llm_confidence": r.llm_result.confidence,
                        "llm_reasoning": r.llm_result.reasoning,
                    }
                )
        return disagreements

    def to_json(self) -> str:
        """Export results to JSON string."""
        data = {
            "experiment_name": self.experiment_name,
            "config": self.config,
            "started_at": self.started_at,
            "completed_at": self.completed_at,
            "metrics": self.calculate_metrics(),
            "results": {str(k): v.to_dict() for k, v in self.results.items()},
        }
        return json.dumps(data, indent=2, default=str)

    def save(self, output_dir: str) -> str:
        """Save results to output directory."""
        path = Path(output_dir) / self.experiment_name
        path.mkdir(parents=True, exist_ok=True)

        # Save full results
        results_path = path / "results.json"
        with open(results_path, "w") as f:
            f.write(self.to_json())

        # Save summary
        summary_path = path / "summary.json"
        with open(summary_path, "w") as f:
            json.dump(
                {
                    "experiment_name": self.experiment_name,
                    "metrics": self.calculate_metrics(),
                    "started_at": self.started_at,
                    "completed_at": self.completed_at,
                },
                f,
                indent=2,
            )

        # Save disagreements
        disagreements = self.get_disagreements()
        if disagreements:
            import csv

            disagreements_path = path / "disagreements.csv"
            with open(disagreements_path, "w", newline="") as f:
                writer = csv.DictWriter(f, fieldnames=disagreements[0].keys())
                writer.writeheader()
                writer.writerows(disagreements)

        return str(path)


def load_prompt_from_file(path: str) -> str:
    """Load prompt content from a markdown file."""
    file_path = Path(path)
    if not file_path.exists():
        raise FileNotFoundError(f"Prompt file not found: {path}")

    return file_path.read_text()


def parse_llm_response(response: str) -> AIDetectionResult:
    """Parse LLM response, handling various formats.

    Handles:
    - Plain JSON
    - JSON in markdown code blocks
    - Invalid JSON (returns conservative default)
    """
    # Try to extract JSON from markdown code block
    json_match = re.search(r"```(?:json)?\s*\n?(.*?)\n?```", response, re.DOTALL)
    if json_match:
        response = json_match.group(1)

    try:
        data = json.loads(response.strip())
        return AIDetectionResult.from_dict(data)
    except json.JSONDecodeError:
        # Return conservative default on parse failure
        return AIDetectionResult(
            is_ai_assisted=False,
            tools=[],
            confidence=0.0,
            reasoning="Failed to parse LLM response",
        )


def create_batch_request(
    pr_id: int,
    pr_body: str,
    system_prompt: str,
    model: str = "llama-3.3-70b-versatile",
) -> dict:
    """Create a single batch request for Groq batch API."""
    return {
        "custom_id": f"pr-{pr_id}",
        "method": "POST",
        "url": "/v1/chat/completions",
        "body": {
            "model": model,
            "messages": [
                {"role": "system", "content": system_prompt},
                {"role": "user", "content": f"Analyze this PR description:\n\n{pr_body}"},
            ],
            "response_format": {"type": "json_object"},
            "temperature": 0,
            "max_tokens": 500,
        },
    }


def detect_ai_with_litellm(
    pr_body: str,
    model: str,
    system_prompt: str,
    temperature: float = 0,
    max_tokens: int = 500,
    metadata: dict | None = None,
) -> AIDetectionResult:
    """Detect AI usage using LiteLLM.

    Args:
        pr_body: The PR description text to analyze
        model: LiteLLM model string (e.g., "groq/llama-3.3-70b-versatile")
        system_prompt: The system prompt for detection
        temperature: Model temperature (0 for deterministic)
        max_tokens: Maximum tokens in response
        metadata: Optional metadata for PostHog tracking (pr_id, experiment_name, etc.)

    Returns:
        AIDetectionResult with detection outcome
    """
    # Build metadata for PostHog tracking
    posthog_metadata = {
        "detection_type": "ai_pr_detection",
        **(metadata or {}),
    }

    response = litellm.completion(
        model=model,
        messages=[
            {"role": "system", "content": system_prompt},
            {"role": "user", "content": f"Analyze this PR description:\n\n{pr_body}"},
        ],
        temperature=temperature,
        max_tokens=max_tokens,
        response_format={"type": "json_object"},
        metadata=posthog_metadata,  # Sent to PostHog
    )

    content = response.choices[0].message.content
    return parse_llm_response(content)


# Default system prompt if none provided
DEFAULT_SYSTEM_PROMPT = """You are an AI detection system analyzing pull requests.
Your task is to identify if AI coding assistants were used.
You MUST respond with valid JSON only.

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


class ExperimentRunner:
    """Runner for AI detection experiments.

    Runs LLM-based detection on PRs and compares with regex baseline.

    Example:
        runner = ExperimentRunner(config_path="experiments/default.yaml")
        results = runner.run(team=my_team, limit=100)
        print(results.calculate_metrics())
    """

    def __init__(
        self,
        config_path: str | None = None,
        config: dict | None = None,
    ):
        """Initialize runner with config file or dict.

        Args:
            config_path: Path to YAML config file
            config: Config dict (alternative to config_path)
        """
        if config_path:
            self.config = ExperimentConfig.from_yaml(config_path)
            self._config_dict = yaml.safe_load(Path(config_path).read_text())
        elif config:
            self.config = ExperimentConfig.from_dict(config)
            self._config_dict = config
        else:
            raise ValueError("Must provide config_path or config")

        # Load system prompt
        if self.config.system_prompt:
            self.system_prompt = self.config.system_prompt
        elif self.config.prompt_file:
            self.system_prompt = load_prompt_from_file(self.config.prompt_file)
        else:
            self.system_prompt = DEFAULT_SYSTEM_PROMPT

    def run(
        self,
        pr_ids: list[int] | None = None,
        team: Any = None,
        limit: int = 100,
    ) -> ExperimentResult:
        """Run experiment on specified PRs.

        Args:
            pr_ids: List of PR IDs to process
            team: Team model to get PRs from
            limit: Maximum PRs to process

        Returns:
            ExperimentResult with all detection results
        """
        started_at = datetime.now().isoformat()

        # Get PRs to process
        if pr_ids:
            prs = PullRequest.objects.filter(id__in=pr_ids)
        elif team:
            prs = PullRequest.objects.filter(
                team=team,
                body__isnull=False,
            ).exclude(body="")[:limit]
        else:
            raise ValueError("Must provide pr_ids or team")

        results: dict[int, PRResult] = {}

        for pr in prs:
            # Run LLM detection
            import time

            start_time = time.time()
            llm_result = detect_ai_with_litellm(
                pr_body=pr.body or "",
                model=self.config.litellm_model,
                system_prompt=self.system_prompt,
                temperature=self.config.temperature,
                max_tokens=self.config.max_tokens,
                metadata={
                    "experiment_name": self.config.experiment_name,
                    "pr_id": pr.id,
                    "pr_number": pr.github_pr_id,
                    "repo": pr.github_repo,
                },
            )
            latency_ms = (time.time() - start_time) * 1000

            # Run regex detection for comparison
            regex_result = detect_ai_in_text(f"{pr.title}\n\n{pr.body}")

            results[pr.id] = PRResult(
                pr_id=pr.id,
                pr_number=pr.github_pr_id,
                pr_body=pr.body or "",
                llm_result=llm_result,
                regex_result=regex_result,
                latency_ms=latency_ms,
            )

        completed_at = datetime.now().isoformat()

        return ExperimentResult(
            experiment_name=self.config.experiment_name,
            config=self.config.to_dict(),
            started_at=started_at,
            completed_at=completed_at,
            results=results,
        )

    def run_single(self, pr_body: str) -> AIDetectionResult:
        """Run detection on a single PR body (for testing)."""
        return detect_ai_with_litellm(
            pr_body=pr_body,
            model=self.config.litellm_model,
            system_prompt=self.system_prompt,
            temperature=self.config.temperature,
            max_tokens=self.config.max_tokens,
        )
