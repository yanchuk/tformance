"""Export PRs with LLM and regex results for promptfoo evaluation.

Generates a JSON file that can be used with promptfoo for manual verification
of AI detection accuracy.

Usage:
    python manage.py export_to_promptfoo --limit 100 --output comparison.json
    python manage.py export_to_promptfoo --disagreements-only
"""

import json
from pathlib import Path

from django.core.management.base import BaseCommand

from apps.metrics.models import PullRequest
from apps.metrics.services.ai_detector import detect_ai_in_text, get_patterns_version
from apps.metrics.services.llm_prompts import build_llm_pr_context


class Command(BaseCommand):
    help = "Export PRs with LLM and regex results for promptfoo evaluation"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Maximum PRs to export (default: 100)",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="dev/active/ai-detection-pr-descriptions/experiments/comparison-results.json",
            help="Output file path",
        )
        parser.add_argument(
            "--disagreements-only",
            action="store_true",
            help="Only export cases where LLM and regex disagree",
        )
        parser.add_argument(
            "--detected-only",
            action="store_true",
            help="Only export cases where at least one method detected AI",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        output_path = Path(options["output"])
        disagreements_only = options.get("disagreements_only", False)
        detected_only = options.get("detected_only", False)

        # Query PRs with LLM analysis (cross-team for research purposes)
        qs = (
            PullRequest.objects.exclude(llm_summary__isnull=True)  # noqa: TEAM001
            .filter(body__isnull=False)
            .exclude(body="")
            .select_related("author", "team")
            .prefetch_related("files", "commits", "reviews__reviewer", "comments__author")
            .order_by("-pr_created_at")
        )

        results = []
        stats = {"total": 0, "both_detected": 0, "llm_only": 0, "regex_only": 0, "neither": 0}

        for pr in qs[: limit * 3]:  # Over-fetch to account for filtering
            if len(results) >= limit:
                break

            text = (pr.body or "") + " " + (pr.title or "")

            # Get LLM result
            llm_summary = pr.llm_summary or {}
            llm_ai = llm_summary.get("ai", {})
            llm_detected = llm_ai.get("is_assisted", False)
            llm_tools = llm_ai.get("tools", [])
            llm_confidence = llm_ai.get("confidence", 0)
            llm_usage_type = llm_ai.get("usage_type")

            # Get regex result
            regex_result = detect_ai_in_text(text)
            regex_detected = regex_result["is_ai_assisted"]
            regex_tools = regex_result["ai_tools"]

            # Filter based on options
            if disagreements_only and llm_detected == regex_detected:
                continue
            if detected_only and not llm_detected and not regex_detected:
                continue

            # Build user prompt for context
            user_prompt = build_llm_pr_context(pr)

            # Categorize
            if llm_detected and regex_detected:
                category = "both_detected"
            elif llm_detected:
                category = "llm_only"
            elif regex_detected:
                category = "regex_only"
            else:
                category = "neither"

            stats[category] += 1
            stats["total"] += 1

            results.append(
                {
                    "pr_id": pr.id,
                    "github_pr_id": pr.github_pr_id,
                    "repo": pr.github_repo,
                    "title": pr.title,
                    "body": pr.body,
                    "user_prompt": user_prompt,
                    "llm": {
                        "is_assisted": llm_detected,
                        "tools": llm_tools,
                        "confidence": llm_confidence,
                        "usage_type": llm_usage_type,
                        "version": pr.llm_summary_version,
                    },
                    "regex": {
                        "is_assisted": regex_detected,
                        "tools": regex_tools,
                        "version": get_patterns_version(),
                    },
                    "category": category,
                    "full_llm_response": llm_summary,
                }
            )

        # Write output
        output_path.parent.mkdir(parents=True, exist_ok=True)
        with open(output_path, "w") as f:
            json.dump({"stats": stats, "results": results}, f, indent=2, default=str)

        self.stdout.write(f"\nExported {len(results)} PRs to {output_path}")
        self.stdout.write("\nStatistics:")
        self.stdout.write(f"  Both detected:  {stats['both_detected']}")
        self.stdout.write(f"  LLM only:       {stats['llm_only']}")
        self.stdout.write(f"  Regex only:     {stats['regex_only']}")
        self.stdout.write(f"  Neither:        {stats['neither']}")

        # Generate promptfoo config
        promptfoo_config = self._generate_promptfoo_config(output_path)
        config_path = output_path.parent / "view-comparison.yaml"
        with open(config_path, "w") as f:
            f.write(promptfoo_config)
        self.stdout.write(f"\nPromptfoo config: {config_path}")
        self.stdout.write("\nTo view results:")
        self.stdout.write(f"  cd {output_path.parent}")
        self.stdout.write(f"  npx promptfoo view --output {output_path.name}")

    def _generate_promptfoo_config(self, results_path: Path) -> str:
        return f"""# Promptfoo config for viewing comparison results
# Run: npx promptfoo view --output {results_path.name}

description: "LLM vs Regex AI Detection Comparison"

# This config is for viewing pre-computed results, not running new evaluations
# The results are already in {results_path.name}

prompts:
  - "{{{{user_prompt}}}}"

providers:
  # Regex provider (pre-computed results)
  - id: "python:regex_provider.py"
    label: "Regex v1.8.0"

  # LLM results are pre-computed in the JSON file
  # Use the file provider to load them
  - id: "file://{results_path.name}"
    label: "LLM (gpt-oss-20b)"

# Test cases loaded from the results file
tests: "{results_path.name}"
"""
