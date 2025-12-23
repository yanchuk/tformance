"""
Management command to parse AI co-authors from existing commit messages.

Reprocesses commits to detect AI co-authors that weren't parsed during initial sync.

Usage:
    python manage.py parse_ai_coauthors --team Gumroad
    python manage.py parse_ai_coauthors --team Gumroad --dry-run
"""

from django.core.management.base import BaseCommand

from apps.metrics.models import Commit
from apps.metrics.services.ai_detector import parse_co_authors
from apps.teams.models import Team


class Command(BaseCommand):
    help = "Parse AI co-authors from existing commit messages"

    def add_arguments(self, parser):
        parser.add_argument(
            "--team",
            type=str,
            default="Gumroad",
            help="Team name to process (default: Gumroad)",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Preview changes without saving",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Reprocess all commits, even those already flagged",
        )

    def handle(self, *args, **options):
        team_name = options["team"]
        dry_run = options["dry_run"]
        force = options["force"]

        try:
            team = Team.objects.get(name=team_name)
        except Team.DoesNotExist:
            self.stderr.write(self.style.ERROR(f"Team '{team_name}' not found"))
            return

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY RUN - no changes will be saved"))

        # Query commits - reprocess all if force, else only unprocessed
        commits = Commit.objects.filter(team=team) if force else Commit.objects.filter(team=team, ai_co_authors=[])

        total = commits.count()
        self.stdout.write(f"Processing {total} commits for team '{team_name}'...")

        updated = 0
        ai_found = 0
        tools_found = {}

        for commit in commits:
            if not commit.message:
                continue

            result = parse_co_authors(commit.message)

            if result["has_ai_co_authors"]:
                ai_found += 1

                # Track which tools were found
                for tool in result["ai_co_authors"]:
                    tools_found[tool] = tools_found.get(tool, 0) + 1

                # Only save if there's a change
                if not commit.is_ai_assisted or commit.ai_co_authors != result["ai_co_authors"]:
                    commit.is_ai_assisted = True
                    commit.ai_co_authors = result["ai_co_authors"]
                    if not dry_run:
                        commit.save(update_fields=["is_ai_assisted", "ai_co_authors"])
                    updated += 1

        # Summary
        self.stdout.write(f"\nProcessed {total} commits")
        self.stdout.write(f"Found AI co-authors in {ai_found} commits")
        self.stdout.write(f"Updated {updated} commits")

        if tools_found:
            self.stdout.write("\nAI tools detected:")
            for tool, count in sorted(tools_found.items(), key=lambda x: -x[1]):
                self.stdout.write(f"  {tool}: {count}")

        if dry_run:
            self.stdout.write(self.style.WARNING("\nDRY RUN complete - no changes saved"))
        else:
            self.stdout.write(self.style.SUCCESS(f"\nSuccessfully updated {updated} commits"))
