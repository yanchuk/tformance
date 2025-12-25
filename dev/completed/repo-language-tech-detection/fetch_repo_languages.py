#!/usr/bin/env python
"""Fetch repository language stats from GitHub API.

Usage:
    python dev/active/repo-language-tech-detection/fetch_repo_languages.py

Outputs: repo_languages.json with language breakdown for each repo.
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
sys.path.insert(0, str(Path(__file__).parent.parent.parent.parent))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tformance.settings")

import django

django.setup()

from github import Github

from apps.metrics.models import PullRequest


def get_github_client():
    """Get GitHub client from seeding tokens."""
    tokens = os.environ.get("GITHUB_SEEDING_TOKENS", "")
    if not tokens:
        # Try to read from .env file
        env_path = Path(__file__).parent.parent.parent.parent / ".env"
        if env_path.exists():
            for line in env_path.read_text().splitlines():
                if line.startswith("GITHUB_SEEDING_TOKENS="):
                    tokens = line.split("=", 1)[1].strip().strip('"')
                    break

    if not tokens:
        raise ValueError("No GITHUB_SEEDING_TOKENS found in environment or .env")

    # Use first token
    token = tokens.split(",")[0].strip()
    return Github(token)


def get_unique_repos():
    """Get unique repo names from PRs with LLM data."""
    repos = PullRequest.objects.filter(llm_summary__isnull=False).values_list("github_repo", flat=True).distinct()
    return sorted(set(repos))


def fetch_languages_for_repo(client, repo_name):
    """Fetch language breakdown from GitHub API."""
    try:
        repo = client.get_repo(repo_name)
        return repo.get_languages()
    except Exception as e:
        print(f"  Error fetching {repo_name}: {e}")
        return None


def main():
    output_path = Path(__file__).parent / "repo_languages.json"

    # Check for existing cache
    if output_path.exists():
        print(f"Loading existing cache from {output_path}")
        with open(output_path) as f:
            existing = json.load(f)
        print(f"  Cached: {len(existing)} repos")
    else:
        existing = {}

    # Get repos to fetch
    repos = get_unique_repos()
    print(f"Found {len(repos)} unique repos with LLM data")

    # Fetch missing repos
    client = get_github_client()
    fetched = 0

    for repo_name in repos:
        if repo_name in existing:
            continue

        print(f"Fetching: {repo_name}")
        languages = fetch_languages_for_repo(client, repo_name)
        if languages is not None:
            existing[repo_name] = languages
            fetched += 1

            # Save after each fetch in case of rate limit
            with open(output_path, "w") as f:
                json.dump(existing, f, indent=2, sort_keys=True)

    print(f"\nFetched {fetched} new repos")
    print(f"Total cached: {len(existing)} repos")

    # Print summary
    print("\n=== Repository Language Summary ===")
    for repo_name in sorted(existing.keys()):
        langs = existing[repo_name]
        total = sum(langs.values()) if langs else 0
        if total > 0:
            top = sorted(langs.items(), key=lambda x: -x[1])[:3]
            pcts = ", ".join(f"{l}: {b / total * 100:.0f}%" for l, b in top)
            print(f"  {repo_name}: {pcts}")
        else:
            print(f"  {repo_name}: (no languages)")


if __name__ == "__main__":
    main()
