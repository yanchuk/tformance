"""Run LLM AI detection experiment on sample PRs."""

import random

from django.core.management.base import BaseCommand

from apps.metrics.experiments.runner import ExperimentRunner
from apps.metrics.models import PullRequest
from apps.teams.models import Team


class Command(BaseCommand):
    help = "Run LLM AI detection experiment on sample PRs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Max PRs to test (default: 50)",
        )
        parser.add_argument(
            "--team",
            type=str,
            help="Filter by team name",
        )
        parser.add_argument(
            "--sample",
            action="store_true",
            help="Random sample instead of newest",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="dev/active/ai-detection-pr-descriptions/experiments/results",
            help="Output directory for results",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        team_name = options.get("team")
        sample = options["sample"]
        output_dir = options["output"]

        # Get PRs with body (intentionally cross-team for experiment comparison)
        queryset = (
            PullRequest.objects.filter(  # noqa: TEAM001 - Cross-team query for experiments
                body__isnull=False,
            )
            .exclude(body="")
            .select_related("team")
        )

        if team_name:
            queryset = queryset.filter(team__name__icontains=team_name)

        # Show current counts
        team_counts = {}
        for team in Team.objects.all():
            count = queryset.filter(team=team).count()
            if count > 0:
                ai_count = queryset.filter(team=team, is_ai_assisted=True).count()
                team_counts[team.name] = {"total": count, "ai": ai_count}

        self.stdout.write("\nPRs with body by team:")
        for name, stats in sorted(team_counts.items(), key=lambda x: -x[1]["total"]):
            rate = stats["ai"] / stats["total"] * 100 if stats["total"] > 0 else 0
            self.stdout.write(f"  {name}: {stats['total']} ({stats['ai']} AI, {rate:.1f}%)")

        # Select PRs
        if sample:
            all_ids = list(queryset.values_list("id", flat=True))
            sample_ids = random.sample(all_ids, min(limit, len(all_ids)))
            pr_ids = sample_ids
        else:
            pr_ids = list(queryset.order_by("-pr_created_at").values_list("id", flat=True)[:limit])

        self.stdout.write(f"\nRunning LLM detection on {len(pr_ids)} PRs...")

        # Create runner with default config
        config = {
            "experiment": {
                "name": f"comparison-{len(pr_ids)}-prs",
                "description": "Compare LLM vs regex detection",
            },
            "model": {
                "provider": "groq",
                "name": "llama-3.3-70b-versatile",
                "temperature": 0,
                "max_tokens": 500,
            },
            "prompt": {},  # Use default prompt
        }

        runner = ExperimentRunner(config=config)

        # Run experiment
        result = runner.run(pr_ids=pr_ids)

        # Show metrics
        metrics = result.calculate_metrics()
        self.stdout.write("\n=== Results ===")
        self.stdout.write(f"Total PRs: {metrics['total_prs']}")
        self.stdout.write(f"Regex detected: {metrics['regex_detected']} ({metrics['regex_detection_rate'] * 100:.1f}%)")
        self.stdout.write(f"LLM detected: {metrics['llm_detected']} ({metrics['llm_detection_rate'] * 100:.1f}%)")
        self.stdout.write(
            f"Agreement: {metrics['agreements']}/{metrics['total_prs']} ({metrics['agreement_rate'] * 100:.1f}%)"
        )
        self.stdout.write(f"Disagreements: {metrics['disagreements']}")

        # Show disagreements
        disagreements = result.get_disagreements()
        if disagreements:
            self.stdout.write("\n=== Disagreements ===")
            for d in disagreements[:10]:  # Show first 10
                direction = "LLM+" if d["llm_detected"] else "Regex+"
                self.stdout.write(f"\n  [{direction}] PR #{d['pr_number']}")
                self.stdout.write(f"    LLM: {d['llm_detected']} (conf={d['llm_confidence']:.2f})")
                self.stdout.write(f"    LLM tools: {d['llm_tools']}")
                self.stdout.write(f"    Regex: {d['regex_detected']}")
                self.stdout.write(f"    Regex tools: {d['regex_tools']}")
                self.stdout.write(f"    Reasoning: {d['llm_reasoning']}")

        # Save results
        output_path = result.save(output_dir)
        self.stdout.write(self.style.SUCCESS(f"\nSaved results to {output_path}"))
