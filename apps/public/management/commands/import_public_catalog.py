"""Import DB-driven public catalog rows from CSV.

Usage:
    python manage.py import_public_catalog /path/to/public_catalog.csv
    python manage.py import_public_catalog /path/to/public_catalog.csv --dry-run
"""

from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.db import transaction

from apps.metrics.seeding.real_projects import INDUSTRIES
from apps.public.models import PublicOrgProfile, PublicRepoProfile
from apps.teams.models import Team


REQUIRED_COLUMNS = {
    "org_public_slug",
    "org_display_name",
    "org_industry",
    "org_description",
    "org_github_org_url",
    "org_logo_url",
    "team_slug",
    "team_name",
    "org_is_public",
    "repo_github_repo",
    "repo_slug",
    "repo_display_name",
    "repo_description",
    "repo_github_url",
    "is_flagship",
    "repo_is_public",
    "sync_enabled",
    "insights_enabled",
    "initial_backfill_days",
    "display_order",
}


class Command(BaseCommand):
    help = "Import public org and repo catalog rows from CSV"

    def add_arguments(self, parser):
        parser.add_argument("csv_path", help="Path to catalog CSV")
        parser.add_argument("--dry-run", action="store_true", help="Validate and summarize without writing")

    def handle(self, *args, **options):
        csv_path = Path(options["csv_path"])
        dry_run = options["dry_run"]

        if not csv_path.exists():
            raise CommandError(f"CSV not found: {csv_path}")

        rows = list(self._load_rows(csv_path))
        summary = self._import_rows(rows, dry_run=dry_run)

        prefix = "Dry run complete" if dry_run else "Import complete"
        self.stdout.write(
            (
                f"{prefix}: teams created={summary['teams_created']}, teams updated={summary['teams_updated']}, "
                f"orgs created={summary['orgs_created']}, orgs updated={summary['orgs_updated']}, "
                f"repos created={summary['repos_created']}, repos updated={summary['repos_updated']}"
            )
        )

    def _load_rows(self, csv_path: Path):
        with csv_path.open(newline="", encoding="utf-8") as handle:
            reader = csv.DictReader(handle)
            if not reader.fieldnames:
                raise CommandError("CSV has no header row")

            missing = REQUIRED_COLUMNS.difference(reader.fieldnames)
            if missing:
                missing_str = ", ".join(sorted(missing))
                raise CommandError(f"CSV missing required columns: {missing_str}")

            for index, row in enumerate(reader, start=2):
                normalized = {key: (value or "").strip() for key, value in row.items()}
                self._validate_row(normalized, line_number=index)
                yield normalized

    def _validate_row(self, row: dict[str, str], *, line_number: int):
        industry = row["org_industry"]
        if industry not in INDUSTRIES:
            raise CommandError(f"Unknown org_industry '{industry}' on line {line_number}")

        if "/" not in row["repo_github_repo"]:
            raise CommandError(f"repo_github_repo must be owner/repo on line {line_number}")

        self._parse_bool(row["org_is_public"], field="org_is_public", line_number=line_number)
        self._parse_bool(row["is_flagship"], field="is_flagship", line_number=line_number)
        self._parse_bool(row["repo_is_public"], field="repo_is_public", line_number=line_number)
        self._parse_bool(row["sync_enabled"], field="sync_enabled", line_number=line_number)
        self._parse_bool(row["insights_enabled"], field="insights_enabled", line_number=line_number)
        self._parse_int(row["initial_backfill_days"], field="initial_backfill_days", line_number=line_number)
        self._parse_int(row["display_order"], field="display_order", line_number=line_number)

    def _import_rows(self, rows: list[dict[str, str]], *, dry_run: bool) -> dict[str, int]:
        summary = {
            "teams_created": 0,
            "teams_updated": 0,
            "orgs_created": 0,
            "orgs_updated": 0,
            "repos_created": 0,
            "repos_updated": 0,
        }

        with transaction.atomic():
            for row in rows:
                team, team_created, team_updated = self._upsert_team(row, dry_run=dry_run)
                org, org_created, org_updated = self._upsert_org(team, row, dry_run=dry_run)
                _, repo_created, repo_updated = self._upsert_repo(org, row, dry_run=dry_run)

                summary["teams_created"] += int(team_created)
                summary["teams_updated"] += int(team_updated)
                summary["orgs_created"] += int(org_created)
                summary["orgs_updated"] += int(org_updated)
                summary["repos_created"] += int(repo_created)
                summary["repos_updated"] += int(repo_updated)

            if dry_run:
                transaction.set_rollback(True)

        return summary

    def _upsert_team(self, row: dict[str, str], *, dry_run: bool):
        team, created = Team.objects.get_or_create(
            slug=row["team_slug"],
            defaults={"name": row["team_name"]},
        )
        updated = False
        if not created and team.name != row["team_name"]:
            team.name = row["team_name"]
            updated = True
            if not dry_run:
                team.save(update_fields=["name"])
        return team, created, updated

    def _upsert_org(self, team: Team, row: dict[str, str], *, dry_run: bool):
        defaults = {
            "team": team,
            "industry": row["org_industry"],
            "description": row["org_description"],
            "github_org_url": row["org_github_org_url"],
            "logo_url": row["org_logo_url"],
            "is_public": self._parse_bool(row["org_is_public"]),
            "display_name": row["org_display_name"],
        }
        org, created = PublicOrgProfile.objects.get_or_create(
            public_slug=row["org_public_slug"],
            defaults=defaults,
        )
        updated = False
        if not created:
            for field, value in defaults.items():
                if getattr(org, field) != value:
                    setattr(org, field, value)
                    updated = True
            if updated and not dry_run:
                org.save()
        return org, created, updated

    def _upsert_repo(self, org: PublicOrgProfile, row: dict[str, str], *, dry_run: bool):
        defaults = {
            "github_repo": row["repo_github_repo"],
            "display_name": row["repo_display_name"],
            "description": row["repo_description"],
            "github_url": row["repo_github_url"],
            "is_flagship": self._parse_bool(row["is_flagship"]),
            "is_public": self._parse_bool(row["repo_is_public"]),
            "sync_enabled": self._parse_bool(row["sync_enabled"]),
            "insights_enabled": self._parse_bool(row["insights_enabled"]),
            "initial_backfill_days": self._parse_int(row["initial_backfill_days"]),
            "display_order": self._parse_int(row["display_order"]),
        }
        repo, created = PublicRepoProfile.objects.get_or_create(
            org_profile=org,
            repo_slug=row["repo_slug"],
            defaults=defaults,
        )
        updated = False
        if not created:
            for field, value in defaults.items():
                if getattr(repo, field) != value:
                    setattr(repo, field, value)
                    updated = True
            if updated and not dry_run:
                repo.save()
        return repo, created, updated

    @staticmethod
    def _parse_bool(value: str, *, field: str | None = None, line_number: int | None = None) -> bool:
        normalized = value.strip().lower()
        if normalized in {"true", "1", "yes"}:
            return True
        if normalized in {"false", "0", "no", ""}:
            return False

        location = ""
        if field and line_number:
            location = f" for {field} on line {line_number}"
        raise CommandError(f"Invalid boolean value '{value}'{location}")

    @staticmethod
    def _parse_int(value: str, *, field: str | None = None, line_number: int | None = None) -> int:
        try:
            return int(value)
        except (TypeError, ValueError) as exc:
            location = ""
            if field and line_number:
                location = f" for {field} on line {line_number}"
            raise CommandError(f"Invalid integer value '{value}'{location}") from exc
