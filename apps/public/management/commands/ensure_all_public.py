"""Ensure all REAL_PROJECTS demo orgs/repos have is_public=True.

Fixes the visibility gap where PublicOrgProfile.is_public defaults to False,
causing snapshot_eligible() to skip repos that belong to those orgs.

Usage:
    python manage.py ensure_all_public
    python manage.py ensure_all_public --rebuild
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand

from apps.metrics.seeding.real_projects import REAL_PROJECTS
from apps.public.models import PublicOrgProfile, PublicRepoProfile


class Command(BaseCommand):
    help = "Flip is_public=True for all demo orgs/repos matching REAL_PROJECTS slugs"

    def add_arguments(self, parser):
        parser.add_argument(
            "--rebuild",
            action="store_true",
            help="Run rebuild_public_catalog_snapshots after flipping flags",
        )

    def handle(self, *args, **options):
        demo_slugs = {config.team_slug for config in REAL_PROJECTS.values()}

        # Phase 0: Fix repo slugs containing dots (breaks URL routing)
        bad_repos = PublicRepoProfile.objects.filter(repo_slug__contains=".")
        dot_fixed = bad_repos.count()
        for repo in bad_repos:
            repo.repo_slug = repo.repo_slug.replace(".", "-").lower()
            repo.save(update_fields=["repo_slug", "updated_at"])
        if dot_fixed:
            self.stdout.write(f"Repo slugs fixed (dots): {dot_fixed}")

        # Phase 1: Create missing PublicRepoProfile records from REAL_PROJECTS
        repos_created = 0
        repos_existed = 0
        orgs_not_found = 0

        for config in REAL_PROJECTS.values():
            try:
                org_profile = PublicOrgProfile.objects.get(team__slug=config.team_slug)
            except PublicOrgProfile.DoesNotExist:
                orgs_not_found += 1
                continue

            for i, repo in enumerate(config.repos):
                repo_slug = repo.split("/")[-1].replace(".", "-").lower()
                _, created = PublicRepoProfile.objects.get_or_create(
                    org_profile=org_profile,
                    repo_slug=repo_slug,
                    defaults={
                        "team": org_profile.team,
                        "github_repo": repo,
                        "display_name": repo_slug.replace("-", " ").title(),
                        "github_url": f"https://github.com/{repo}",
                        "is_flagship": i == 0,
                        "is_public": True,
                        "sync_enabled": True,
                    },
                )
                if created:
                    repos_created += 1
                else:
                    repos_existed += 1

        self.stdout.write(
            f"Repos created: {repos_created}, already existed: {repos_existed}, orgs not found: {orgs_not_found}"
        )

        # Phase 2: Flip flags for any that are still False
        orgs_updated = PublicOrgProfile.objects.filter(
            team__slug__in=demo_slugs,
            is_public=False,
        ).update(is_public=True)

        repos_updated = PublicRepoProfile.objects.filter(
            org_profile__team__slug__in=demo_slugs,
            is_public=False,
        ).update(is_public=True)

        sync_updated = PublicRepoProfile.objects.filter(
            org_profile__team__slug__in=demo_slugs,
            sync_enabled=False,
        ).update(sync_enabled=True)

        self.stdout.write(f"Orgs flipped to public: {orgs_updated}")
        self.stdout.write(f"Repos flipped to public: {repos_updated}")
        self.stdout.write(f"Repos re-enabled for sync: {sync_updated}")

        if options["rebuild"]:
            self.stdout.write("Running rebuild_public_catalog_snapshots...")
            call_command("rebuild_public_catalog_snapshots")
