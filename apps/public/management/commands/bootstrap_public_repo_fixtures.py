"""Bootstrap PublicRepoProfile rows from fixture manifest.

Creates missing repo profiles without overwriting existing curated fields.
Use --force-overwrite to reset all fields to manifest values.

Usage:
    python manage.py bootstrap_public_repo_fixtures --org polar --org posthog
    python manage.py bootstrap_public_repo_fixtures --org polar --force-overwrite
"""

import logging

from django.core.management.base import BaseCommand

from apps.public.models import PublicOrgProfile, PublicRepoProfile
from apps.public.services.local_fixture_manifest import get_repos_for_orgs

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Bootstrap PublicRepoProfile rows from fixture manifest"

    def add_arguments(self, parser):
        parser.add_argument(
            "--org",
            action="append",
            dest="orgs",
            default=[],
            help="Public org slug to bootstrap (repeatable, required)",
        )
        parser.add_argument(
            "--force-overwrite",
            action="store_true",
            help="Overwrite existing curated fields with manifest values",
        )

    def handle(self, *args, **options):
        org_slugs = options["orgs"]
        force = options["force_overwrite"]

        if not org_slugs:
            raise SystemExit("At least one --org is required.")

        # Validate org profiles exist
        org_profiles = {}
        for slug in org_slugs:
            try:
                org_profiles[slug] = PublicOrgProfile.objects.get(public_slug=slug)
            except PublicOrgProfile.DoesNotExist:
                raise SystemExit(f"PublicOrgProfile not found for slug: {slug}") from None

        repos = get_repos_for_orgs(org_slugs)
        created = 0
        updated = 0
        skipped = 0

        for repo_info in repos:
            org_slug = repo_info["org_slug"]
            org_profile = org_profiles[org_slug]

            defaults = {
                "team": org_profile.team,
                "github_repo": repo_info["github_repo"],
                "display_name": repo_info["repo_slug"].replace("-", " ").title(),
                "is_flagship": repo_info["is_flagship"],
                "is_public": True,
            }

            if force:
                _, was_created = PublicRepoProfile.objects.update_or_create(
                    org_profile=org_profile,
                    repo_slug=repo_info["repo_slug"],
                    defaults=defaults,
                )
                if was_created:
                    created += 1
                else:
                    updated += 1
            else:
                _, was_created = PublicRepoProfile.objects.get_or_create(
                    org_profile=org_profile,
                    repo_slug=repo_info["repo_slug"],
                    defaults=defaults,
                )
                if was_created:
                    created += 1
                else:
                    skipped += 1

        self.stdout.write(
            f"Bootstrap complete. Created: {created}, "
            f"{'Updated' if force else 'Skipped'}: {updated if force else skipped}"
        )
