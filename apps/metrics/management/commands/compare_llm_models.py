"""Compare LLM models for JSON reliability and quality.

Tests GPT OSS 20B, GPT OSS 120B, and Llama 3.3 70B on the same PRs
to measure JSON success rate and response quality.

Usage:
    python manage.py compare_llm_models --limit 50
"""

import json
import os
import time
from dataclasses import dataclass

from django.core.management.base import BaseCommand
from groq import Groq

from apps.metrics.models import PullRequest
from apps.metrics.services.llm_prompts import (
    PR_ANALYSIS_SYSTEM_PROMPT,
    build_llm_pr_context,
)

MODELS_TO_TEST = [
    ("openai/gpt-oss-20b", "GPT OSS 20B (cheap default)"),
    ("openai/gpt-oss-120b", "GPT OSS 120B (MoE)"),
    ("llama-3.3-70b-versatile", "Llama 3.3 70B (current fallback)"),
]


@dataclass
class ModelResult:
    model: str
    pr_id: int
    success: bool
    latency_ms: float
    error: str | None = None
    response: dict | None = None


class Command(BaseCommand):
    help = "Compare LLM models for JSON reliability"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=20,
            help="Number of PRs to test (default: 20)",
        )
        parser.add_argument(
            "--pr-ids",
            type=str,
            help="Comma-separated PR IDs to test (overrides --limit)",
        )

    def handle(self, *args, **options):
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key:
            self.stderr.write(self.style.ERROR("GROQ_API_KEY not set"))
            return

        client = Groq(api_key=api_key)

        # Get PRs to test
        if options.get("pr_ids"):
            pr_ids = [int(x.strip()) for x in options["pr_ids"].split(",")]
            prs = list(
                PullRequest.objects.filter(id__in=pr_ids)  # noqa: TEAM001
                .select_related("author", "team")
                .prefetch_related("files", "commits", "reviews__reviewer", "comments__author")
            )
        else:
            # Get random unprocessed PRs with decent content
            prs = list(
                PullRequest.objects.filter(  # noqa: TEAM001
                    body__isnull=False,
                    llm_summary__isnull=True,
                )
                .exclude(body="")
                .select_related("author", "team")
                .prefetch_related("files", "commits", "reviews__reviewer", "comments__author")
                .order_by("?")[: options["limit"]]
            )

        self.stdout.write(f"Testing {len(prs)} PRs across {len(MODELS_TO_TEST)} models\n")

        # Test each model
        results: dict[str, list[ModelResult]] = {model: [] for model, _ in MODELS_TO_TEST}

        for i, pr in enumerate(prs, 1):
            self.stdout.write(f"\n[{i}/{len(prs)}] PR #{pr.id}: {pr.title[:50]}...")
            pr_context = build_llm_pr_context(pr)

            for model_id, model_name in MODELS_TO_TEST:
                result = self._test_model(client, model_id, pr.id, pr_context)
                results[model_id].append(result)

                status = "✓" if result.success else "✗"
                self.stdout.write(f"  {status} {model_name}: {result.latency_ms:.0f}ms")
                if result.error:
                    self.stdout.write(f"    Error: {result.error[:80]}")

            # Rate limit protection
            time.sleep(1)

        # Print summary
        self._print_summary(results)

    def _test_model(
        self,
        client: Groq,
        model: str,
        pr_id: int,
        pr_context: str,
    ) -> ModelResult:
        """Test a single model on a single PR."""
        start = time.time()
        try:
            response = client.chat.completions.create(
                model=model,
                messages=[
                    {"role": "system", "content": PR_ANALYSIS_SYSTEM_PROMPT},
                    {"role": "user", "content": pr_context},
                ],
                response_format={"type": "json_object"},
                temperature=0,
                max_tokens=1500,
            )
            latency = (time.time() - start) * 1000

            # Try to parse JSON
            content = response.choices[0].message.content
            data = json.loads(content)

            # Validate required fields
            if "ai" in data and isinstance(data["ai"], dict):
                # v5+ format
                if "is_assisted" not in data["ai"]:
                    return ModelResult(
                        model=model,
                        pr_id=pr_id,
                        success=False,
                        latency_ms=latency,
                        error="Missing ai.is_assisted field",
                        response=data,
                    )
            elif "is_ai_assisted" not in data:
                # v4 format
                return ModelResult(
                    model=model,
                    pr_id=pr_id,
                    success=False,
                    latency_ms=latency,
                    error="Missing is_ai_assisted field",
                    response=data,
                )

            return ModelResult(
                model=model,
                pr_id=pr_id,
                success=True,
                latency_ms=latency,
                response=data,
            )

        except json.JSONDecodeError as e:
            latency = (time.time() - start) * 1000
            return ModelResult(
                model=model,
                pr_id=pr_id,
                success=False,
                latency_ms=latency,
                error=f"JSON parse error: {e}",
            )
        except Exception as e:
            latency = (time.time() - start) * 1000
            return ModelResult(
                model=model,
                pr_id=pr_id,
                success=False,
                latency_ms=latency,
                error=str(e),
            )

    def _print_summary(self, results: dict[str, list[ModelResult]]):
        """Print comparison summary."""
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("MODEL COMPARISON SUMMARY")
        self.stdout.write("=" * 60)

        for model_id, model_name in MODELS_TO_TEST:
            model_results = results[model_id]
            successes = sum(1 for r in model_results if r.success)
            total = len(model_results)
            success_rate = (successes / total * 100) if total > 0 else 0

            avg_latency = sum(r.latency_ms for r in model_results) / total if total else 0

            self.stdout.write(f"\n{model_name}")
            self.stdout.write(f"  Success Rate: {successes}/{total} ({success_rate:.1f}%)")
            self.stdout.write(f"  Avg Latency: {avg_latency:.0f}ms")

            # Show error breakdown
            errors = [r for r in model_results if not r.success]
            if errors:
                self.stdout.write(f"  Failures ({len(errors)}):")
                for err in errors[:5]:
                    self.stdout.write(f"    - PR {err.pr_id}: {err.error[:60]}")
                if len(errors) > 5:
                    self.stdout.write(f"    ... and {len(errors) - 5} more")

        # Recommendation
        self.stdout.write("\n" + "=" * 60)
        self.stdout.write("RECOMMENDATION")
        self.stdout.write("=" * 60)

        best_model = max(
            MODELS_TO_TEST,
            key=lambda m: sum(1 for r in results[m[0]] if r.success),
        )
        self.stdout.write(f"Best reliability: {best_model[1]}")
