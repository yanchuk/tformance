"""Export real PRs to promptfoo test cases for AI detection evaluation."""

import json
import random

from django.core.management.base import BaseCommand

from apps.metrics.models import PullRequest
from apps.teams.models import Team


class Command(BaseCommand):
    help = "Export real PRs to promptfoo YAML test cases"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=100,
            help="Max PRs to export (default: 100)",
        )
        parser.add_argument(
            "--team",
            type=str,
            help="Filter by team name",
        )
        parser.add_argument(
            "--output",
            type=str,
            default="dev/active/ai-detection-pr-descriptions/experiments/test-cases-real.yaml",
            help="Output file path",
        )
        parser.add_argument(
            "--format",
            type=str,
            default="yaml",
            choices=["yaml", "json"],
            help="Output format (yaml or json)",
        )
        parser.add_argument(
            "--sample",
            action="store_true",
            help="Random sample instead of newest",
        )

    def handle(self, *args, **options):
        limit = options["limit"]
        team_name = options.get("team")
        output_path = options["output"]
        output_format = options["format"]
        sample = options["sample"]

        # Query PRs with body (intentionally cross-team for experiment data export)
        queryset = (
            PullRequest.objects.filter(  # noqa: TEAM001 - Cross-team export for experiments
                body__isnull=False,
            )
            .exclude(body="")
            .select_related("team")
        )

        if team_name:
            queryset = queryset.filter(team__name__icontains=team_name)

        # Get counts by team
        team_counts = {}
        for team in Team.objects.all():
            count = queryset.filter(team=team).count()
            if count > 0:
                team_counts[team.name] = count

        self.stdout.write("\nPRs with body by team:")
        for name, count in sorted(team_counts.items(), key=lambda x: -x[1]):
            self.stdout.write(f"  {name}: {count}")
        self.stdout.write(f"  Total: {sum(team_counts.values())}")

        # Sample or get newest
        if sample:
            all_ids = list(queryset.values_list("id", flat=True))
            sample_ids = random.sample(all_ids, min(limit, len(all_ids)))
            prs = list(queryset.filter(id__in=sample_ids))
        else:
            prs = list(queryset.order_by("-pr_created_at")[:limit])

        # Generate test cases
        test_cases = []
        for pr in prs:
            # Truncate very long bodies
            body = pr.body[:4000] if len(pr.body) > 4000 else pr.body

            test_case = {
                "description": f"[{pr.team.name}] {pr.title[:60]}",
                "vars": {
                    "pr_body": body,
                },
                "metadata": {
                    "team": pr.team.name,
                    "repo": pr.github_repo,
                    "pr_number": pr.github_pr_id,
                    "current_detection": pr.is_ai_assisted,
                    "current_tools": pr.ai_tools_detected,
                },
            }

            # Add assertions based on current detection (for comparison)
            if pr.is_ai_assisted:
                test_case["assert"] = [
                    {"type": "is-json"},
                    {"type": "javascript", "value": "JSON.parse(output).is_ai_assisted === true"},
                ]
            else:
                # For non-detected PRs, we just check valid JSON (LLM might catch more)
                test_case["assert"] = [
                    {"type": "is-json"},
                ]

            test_cases.append(test_case)

        # Count stats
        ai_detected = sum(1 for tc in test_cases if tc["metadata"]["current_detection"])
        self.stdout.write(f"\nExporting {len(test_cases)} PRs ({ai_detected} currently AI-detected)")

        # Write output
        if output_format == "json":
            output = {"tests": test_cases}
            content = json.dumps(output, indent=2)
        else:
            # YAML format
            lines = ["# Real PR test cases exported from database", ""]
            lines.append("tests:")
            for tc in test_cases:
                lines.append(f'  - description: "{tc["description"]}"')
                lines.append("    vars:")
                # Use block scalar for multi-line body
                lines.append("      pr_body: |")
                for line in tc["vars"]["pr_body"].split("\n"):
                    lines.append(f"        {line}")
                lines.append("    assert:")
                for assertion in tc["assert"]:
                    if assertion["type"] == "is-json":
                        lines.append("      - type: is-json")
                    else:
                        lines.append(f"      - type: {assertion['type']}")
                        lines.append(f"        value: {assertion['value']}")
                lines.append(f"    # Current detection: {tc['metadata']['current_detection']}")
                lines.append(f"    # Tools: {tc['metadata']['current_tools']}")
                lines.append("")
            content = "\n".join(lines)

        with open(output_path, "w") as f:
            f.write(content)

        self.stdout.write(self.style.SUCCESS(f"\nExported to {output_path}"))

        # Also output summary stats
        teams = {}
        for tc in test_cases:
            team = tc["metadata"]["team"]
            teams[team] = teams.get(team, {"total": 0, "ai": 0})
            teams[team]["total"] += 1
            if tc["metadata"]["current_detection"]:
                teams[team]["ai"] += 1

        self.stdout.write("\nBreakdown by team:")
        for team, stats in sorted(teams.items()):
            rate = stats["ai"] / stats["total"] * 100 if stats["total"] > 0 else 0
            self.stdout.write(f"  {team}: {stats['ai']}/{stats['total']} ({rate:.1f}%)")
