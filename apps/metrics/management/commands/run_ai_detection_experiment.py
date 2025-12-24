"""Management command to run AI detection experiments."""

from django.core.management.base import BaseCommand

from apps.metrics.experiments.runner import ExperimentRunner
from apps.teams.models import Team


class Command(BaseCommand):
    """Run AI detection experiment with LLM and compare to regex baseline."""

    help = "Run AI detection experiment on PRs using LLM"

    def add_arguments(self, parser):
        parser.add_argument(
            "--config",
            type=str,
            help="Path to experiment YAML config file",
        )
        parser.add_argument(
            "--team",
            type=str,
            help="Team name to run experiment on",
        )
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Maximum PRs to process (default: 50)",
        )
        parser.add_argument(
            "--output-dir",
            type=str,
            default="dev/active/ai-detection-pr-descriptions/experiments/results",
            help="Directory to save results",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview what would be processed without calling LLM",
        )
        parser.add_argument(
            "--experiment-name",
            type=str,
            help="Override experiment name from config",
        )

    def handle(self, *args, **options):
        config_path = options.get("config")
        team_name = options.get("team")
        limit = options["limit"]
        output_dir = options["output_dir"]
        dry_run = options["dry_run"]
        experiment_name = options.get("experiment_name")

        # Build config
        if config_path:
            runner = ExperimentRunner(config_path=config_path)
        else:
            # Default config
            runner = ExperimentRunner(
                config={
                    "experiment": {"name": experiment_name or "cli-experiment"},
                    "model": {
                        "provider": "groq",
                        "name": "llama-3.3-70b-versatile",
                        "temperature": 0,
                    },
                    "prompt": {"system": None},  # Uses default
                }
            )

        # Get team
        team = None
        if team_name:
            try:
                team = Team.objects.get(name=team_name)
            except Team.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Team '{team_name}' not found"))
                return

        if dry_run:
            self.stdout.write(self.style.WARNING("\n=== DRY RUN MODE ==="))
            self._preview_run(runner, team, limit)
            return

        # Run experiment
        self.stdout.write(f"\nRunning experiment: {runner.config.experiment_name}")
        self.stdout.write(f"Model: {runner.config.litellm_model}")
        self.stdout.write(f"Limit: {limit} PRs")
        if team:
            self.stdout.write(f"Team: {team.name}")
        self.stdout.write("")

        results = runner.run(team=team, limit=limit)

        # Calculate and display metrics
        metrics = results.calculate_metrics()
        self.stdout.write(self.style.SUCCESS("\n=== Results ==="))
        self.stdout.write(f"Total PRs: {metrics['total_prs']}")
        self.stdout.write(f"LLM detected: {metrics['llm_detected']} ({metrics['llm_detection_rate']:.1%})")
        self.stdout.write(f"Regex detected: {metrics['regex_detected']} ({metrics['regex_detection_rate']:.1%})")
        self.stdout.write(f"Agreements: {metrics['agreements']} ({metrics['agreement_rate']:.1%})")
        self.stdout.write(f"Disagreements: {metrics['disagreements']}")

        # Show disagreements
        disagreements = results.get_disagreements()
        if disagreements:
            self.stdout.write(self.style.WARNING("\n=== Disagreements ==="))
            for d in disagreements[:10]:  # Show first 10
                self.stdout.write(f"  PR #{d['pr_number']}: LLM={d['llm_detected']}, Regex={d['regex_detected']}")
                self.stdout.write(f"    LLM tools: {d['llm_tools']}, confidence: {d['llm_confidence']:.2f}")
                self.stdout.write(f"    Reasoning: {d['llm_reasoning']}")

        # Save results
        saved_path = results.save(output_dir)
        self.stdout.write(self.style.SUCCESS(f"\nResults saved to: {saved_path}"))

    def _preview_run(self, runner, team, limit):
        """Preview what would be processed without calling LLM."""
        from apps.metrics.models import PullRequest

        if team:
            prs = PullRequest.objects.filter(
                team=team,
                body__isnull=False,
            ).exclude(body="")[:limit]
        else:
            # For dry-run preview, we need to show PRs without team filter
            prs = PullRequest.objects.filter(  # noqa: TEAM001 - Preview mode only
                body__isnull=False
            ).exclude(body="")[:limit]

        self.stdout.write(f"\nWould process {prs.count()} PRs:")
        for pr in prs[:5]:
            body_preview = (pr.body or "")[:100].replace("\n", " ")
            self.stdout.write(f"  PR #{pr.github_pr_id}: {body_preview}...")

        if prs.count() > 5:
            self.stdout.write(f"  ... and {prs.count() - 5} more")

        self.stdout.write("\nExperiment config:")
        self.stdout.write(f"  Name: {runner.config.experiment_name}")
        self.stdout.write(f"  Model: {runner.config.litellm_model}")
        self.stdout.write(f"  Temperature: {runner.config.temperature}")
