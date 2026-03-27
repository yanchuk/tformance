"""Fix PullRequest records where github_pr_id stores GitHub API node ID instead of PR number.

The REST sync (sync.py) had a bug where it stored pr_data["id"] (GitHub's global API
node ID, e.g. 3447770271) instead of pr_data["number"] (the actual PR number, e.g. 31234).
This causes broken GitHub URLs since we construct /pull/{github_pr_id}.

This command:
1. Finds PRs where github_pr_id is suspiciously large (> threshold)
2. Queries GitHub API to find the correct PR number for each
3. Updates or deduplicates records

Usage:
    # Dry run - see what would be fixed
    python manage.py fix_pr_github_ids --dry-run

    # Fix with GitHub token for API access
    python manage.py fix_pr_github_ids --token ghp_xxx

    # Fix specific repo only
    python manage.py fix_pr_github_ids --token ghp_xxx --repo PostHog/posthog
"""

import time

import requests
from django.core.management.base import BaseCommand
from django.db.models import Q


class Command(BaseCommand):
    help = "Fix PullRequest records where github_pr_id is a GitHub API node ID instead of PR number"

    # PR numbers above this threshold are almost certainly API node IDs, not PR numbers.
    # The largest open source repos have ~50k PRs; API node IDs are in the billions.
    ID_THRESHOLD = 1_000_000

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Show what would be fixed without making changes",
        )
        parser.add_argument(
            "--token",
            type=str,
            default="",
            help="GitHub token (defaults to first token from GITHUB_SEEDING_TOKENS env var)",
        )
        parser.add_argument(
            "--repo",
            type=str,
            default="",
            help="Fix only this repo (e.g. PostHog/posthog)",
        )
        parser.add_argument(
            "--threshold",
            type=int,
            default=1_000_000,
            help="IDs above this are considered bad (default: 1000000)",
        )

    def handle(self, *args, **options):
        import os

        from apps.metrics.models import PullRequest

        dry_run = options["dry_run"]
        token = options["token"] or os.environ.get("GITHUB_SEEDING_TOKENS", "").split(",")[0].strip()
        repo_filter = options["repo"]
        threshold = options["threshold"]

        # Step 1: Find bad records
        qs = PullRequest.objects.filter(github_pr_id__gt=threshold)  # noqa: TEAM001 - cross-team data fix
        if repo_filter:
            qs = qs.filter(github_repo=repo_filter)

        bad_count = qs.count()
        if bad_count == 0:
            self.stdout.write(self.style.SUCCESS(f"No PRs with github_pr_id > {threshold:,} found. Nothing to fix."))
            return

        self.stdout.write(f"Found {bad_count} PRs with github_pr_id > {threshold:,}")

        # Group by repo
        repos = qs.values_list("github_repo", flat=True).distinct()
        self.stdout.write(f"Across {len(repos)} repositories:")
        for repo in repos:
            count = qs.filter(github_repo=repo).count()
            self.stdout.write(f"  {repo}: {count} bad PRs")

        if dry_run and not token:
            self.stdout.write(
                self.style.WARNING("\n--dry-run without --token: showing bad records only (no API lookup)")
            )
            for pr in qs[:20]:
                self.stdout.write(
                    f'  [{pr.github_repo}] id={pr.github_pr_id} title="{pr.title[:60]}" merged={pr.merged_at}'
                )
            if bad_count > 20:
                self.stdout.write(f"  ... and {bad_count - 20} more")
            return

        if not token and not dry_run:
            self.stderr.write(self.style.ERROR("--token is required (or set GITHUB_SEEDING_TOKENS env var)"))
            return

        # Step 2: For each repo, fetch PRs from GitHub and build id->number map
        headers = {"Accept": "application/vnd.github.v3+json"}
        if token:
            headers["Authorization"] = f"token {token}"

        fixed = 0
        deleted_dupes = 0
        not_found = 0

        for repo in repos:
            repo_bad_prs = list(qs.filter(github_repo=repo))
            bad_api_ids = {pr.github_pr_id for pr in repo_bad_prs}
            id_to_number = {}

            self.stdout.write(f"\nProcessing {repo} ({len(repo_bad_prs)} bad PRs)...")

            # Paginate through GitHub API to find matching PRs
            page = 1
            max_pages = 50  # Safety limit
            remaining_ids = set(bad_api_ids)

            while remaining_ids and page <= max_pages:
                url = f"https://api.github.com/repos/{repo}/pulls"
                params = {
                    "state": "all",
                    "per_page": 100,
                    "page": page,
                    "sort": "updated",
                    "direction": "desc",
                }

                response = requests.get(url, headers=headers, params=params, timeout=30)

                if response.status_code == 403:
                    self.stderr.write(self.style.ERROR(f"  Rate limited at page {page}. Try again later."))
                    break
                if response.status_code != 200:
                    self.stderr.write(self.style.ERROR(f"  API error {response.status_code} at page {page}"))
                    break

                data = response.json()
                if not data:
                    break

                for pr_data in data:
                    api_id = pr_data["id"]
                    if api_id in remaining_ids:
                        id_to_number[api_id] = pr_data["number"]
                        remaining_ids.discard(api_id)
                        self.stdout.write(
                            f'  Found: API id {api_id} → PR #{pr_data["number"]} ("{pr_data["title"][:50]}")'
                        )

                page += 1
                time.sleep(0.5)  # Be kind to rate limits

            if remaining_ids:
                self.stdout.write(
                    self.style.WARNING(f"  Could not find {len(remaining_ids)} PRs in API (may need more pages)")
                )

            # Step 3: Fix records
            for pr in repo_bad_prs:
                correct_number = id_to_number.get(pr.github_pr_id)
                if not correct_number:
                    not_found += 1
                    continue

                # Check if a record with the correct number already exists
                existing = PullRequest.objects.filter(
                    ~Q(pk=pr.pk),
                    team=pr.team,
                    github_pr_id=correct_number,
                    github_repo=pr.github_repo,
                ).first()

                if existing:
                    # Duplicate exists from GraphQL sync — delete the bad one
                    if dry_run:
                        self.stdout.write(
                            f"  [DRY RUN] Would DELETE duplicate: "
                            f"id={pr.github_pr_id} (correct #{correct_number} already exists)"
                        )
                    else:
                        pr.delete()
                        self.stdout.write(f"  Deleted duplicate: id={pr.github_pr_id} (#{correct_number} exists)")
                    deleted_dupes += 1
                else:
                    # No duplicate — update in place
                    if dry_run:
                        self.stdout.write(f"  [DRY RUN] Would UPDATE: id={pr.github_pr_id} → #{correct_number}")
                    else:
                        pr.github_pr_id = correct_number
                        pr.save(update_fields=["github_pr_id"])
                        self.stdout.write(f"  Updated: id={pr.github_pr_id} → was {correct_number}")
                    fixed += 1

        # Summary
        action = "Would fix" if dry_run else "Fixed"
        self.stdout.write(f"\n{'=' * 50}")
        self.stdout.write(f"{action} {fixed} PRs (updated github_pr_id)")
        self.stdout.write(f"{action} {deleted_dupes} duplicates (deleted)")
        self.stdout.write(f"Not found in API: {not_found}")
        if dry_run:
            self.stdout.write(self.style.WARNING("This was a dry run. Run without --dry-run to apply changes."))
        else:
            self.stdout.write(self.style.SUCCESS("Done! Run snapshot rebuild to update cached URLs."))
