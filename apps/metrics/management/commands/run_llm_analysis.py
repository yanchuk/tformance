"""Run LLM analysis on PRs to populate llm_summary field.

This command calls Groq API directly (NOT promptfoo) and stores results
in the database for display in the app UI.

Usage:
    python manage.py run_llm_analysis --limit 50
    python manage.py run_llm_analysis --team "Gumroad" --limit 100
    python manage.py run_llm_analysis --reprocess  # Re-analyze with newer prompt version

Output:
    - Results stored in PullRequest.llm_summary (JSONField)
    - Version tracked in PullRequest.llm_summary_version
    - View in app or query: SELECT llm_summary FROM metrics_pullrequest WHERE llm_summary IS NOT NULL
"""

import json
import time

from django.core.management.base import BaseCommand

from apps.metrics.models import PullRequest
from apps.metrics.services.llm_prompts import (
    PR_ANALYSIS_SYSTEM_PROMPT,
    PROMPT_VERSION,
    build_llm_pr_context,
)
from apps.teams.models import Team


class Command(BaseCommand):
    help = "Run LLM analysis on PRs to populate llm_summary with health assessment (stores in DB, not promptfoo)"

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=50,
            help="Maximum number of PRs to process (default: 50)",
        )
        parser.add_argument(
            "--team",
            type=str,
            help="Only process PRs from this team name",
        )
        parser.add_argument(
            "--reprocess",
            action="store_true",
            help="Re-analyze PRs even if they have llm_summary (for prompt upgrades)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be processed without making API calls",
        )

    def handle(self, *args, **options):
        import os

        from groq import Groq

        limit = options["limit"]
        team_name = options.get("team")
        reprocess = options["reprocess"]
        dry_run = options["dry_run"]

        # Check for API key
        api_key = os.environ.get("GROQ_API_KEY")
        if not api_key and not dry_run:
            self.stderr.write(self.style.ERROR("GROQ_API_KEY environment variable not set"))
            return

        # Build queryset - admin command processes across teams
        qs = PullRequest.objects.filter(body__isnull=False).exclude(body="")  # noqa: TEAM001

        if team_name:
            try:
                team = Team.objects.get(name=team_name)
                qs = qs.filter(team=team)
                self.stdout.write(f"Filtering to team: {team_name}")
            except Team.DoesNotExist:
                self.stderr.write(self.style.ERROR(f"Team not found: {team_name}"))
                return

        if not reprocess:
            # Only process PRs without llm_summary or with older version
            qs = qs.filter(llm_summary__isnull=True) | qs.exclude(llm_summary_version=PROMPT_VERSION)

        # Prefetch related data for v6.2.0 - avoid N+1 queries
        prs = list(
            qs.select_related("author")
            .prefetch_related("files", "commits", "reviews__reviewer", "comments__author")
            .order_by("-pr_created_at")[:limit]
        )

        self.stdout.write(f"Found {len(prs)} PRs to process (limit: {limit})")
        self.stdout.write(f"Using prompt version: {PROMPT_VERSION}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\n=== DRY RUN - No API calls ===\n"))
            for pr in prs[:10]:
                self.stdout.write(f"  - PR #{pr.github_pr_id}: {pr.title[:50]}...")
            if len(prs) > 10:
                self.stdout.write(f"  ... and {len(prs) - 10} more")
            return

        if not prs:
            self.stdout.write(self.style.SUCCESS("No PRs need processing"))
            return

        # Initialize Groq client
        client = Groq(api_key=api_key)

        # Process PRs one by one (synchronous for simplicity)
        success_count = 0
        error_count = 0

        for i, pr in enumerate(prs):
            self.stdout.write(f"\n[{i + 1}/{len(prs)}] PR #{pr.github_pr_id}: {pr.title[:50]}...")

            try:
                # Build user prompt with unified context builder (v6.2.0)
                user_prompt = build_llm_pr_context(pr)

                # Call Groq API
                response = client.chat.completions.create(
                    model="llama-3.3-70b-versatile",
                    messages=[
                        {"role": "system", "content": PR_ANALYSIS_SYSTEM_PROMPT},
                        {"role": "user", "content": user_prompt},
                    ],
                    response_format={"type": "json_object"},
                    temperature=0,
                    max_tokens=800,
                )

                # Parse response
                content = response.choices[0].message.content
                llm_summary = json.loads(content)

                # Update PR
                pr.llm_summary = llm_summary
                pr.llm_summary_version = PROMPT_VERSION
                pr.save(update_fields=["llm_summary", "llm_summary_version"])

                # Show result
                health = llm_summary.get("health", {})
                ai = llm_summary.get("ai", {})
                self.stdout.write(
                    self.style.SUCCESS(
                        f"  ✓ AI: {ai.get('is_assisted')}, "
                        f"Scope: {health.get('scope')}, "
                        f"Risk: {health.get('risk_level')}"
                    )
                )
                success_count += 1

                # Rate limiting - 30 requests per minute for free tier
                time.sleep(2.1)

            except Exception as e:
                self.stdout.write(self.style.ERROR(f"  ✗ Error: {e}"))
                error_count += 1
                # Back off on errors
                time.sleep(5)

        self.stdout.write(f"\n{'=' * 50}")
        self.stdout.write(self.style.SUCCESS(f"Processed: {success_count} success, {error_count} errors"))
