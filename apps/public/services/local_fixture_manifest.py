"""Locked fixture manifest for local public repo reconciliation.

Maps public_slug → repos for the configured fixture set.
Do NOT modify without updating tests and documentation.
"""

FIXTURE_MANIFEST = {
    "polar": {
        "repos": [
            {"github_repo": "polarsource/polar", "repo_slug": "polar", "is_flagship": True},
            {"github_repo": "polarsource/polar-adapters", "repo_slug": "polar-adapters", "is_flagship": False},
            {"github_repo": "polarsource/polar-js", "repo_slug": "polar-js", "is_flagship": False},
            {"github_repo": "polarsource/polar-python", "repo_slug": "polar-python", "is_flagship": False},
        ],
    },
    "posthog": {
        "repos": [
            {"github_repo": "PostHog/posthog", "repo_slug": "posthog", "is_flagship": True},
            {"github_repo": "PostHog/posthog.com", "repo_slug": "posthog-com", "is_flagship": False},
            {"github_repo": "PostHog/posthog-js", "repo_slug": "posthog-js", "is_flagship": False},
            {"github_repo": "PostHog/posthog-python", "repo_slug": "posthog-python", "is_flagship": False},
        ],
    },
}


def get_repos_for_orgs(org_slugs):
    """Resolve org slugs to flat list of repo dicts with org_slug added.

    Args:
        org_slugs: List of public_slug values (e.g., ["polar", "posthog"])

    Returns:
        List of dicts: [{github_repo, repo_slug, is_flagship, org_slug}, ...]

    Raises:
        KeyError: If org_slug not in FIXTURE_MANIFEST
    """
    repos = []
    for slug in org_slugs:
        if slug not in FIXTURE_MANIFEST:
            raise KeyError(f"Unknown org slug: '{slug}'. Valid: {list(FIXTURE_MANIFEST.keys())}")
        for repo in FIXTURE_MANIFEST[slug]["repos"]:
            repos.append({**repo, "org_slug": slug})
    return repos


def filter_repos_by_github_repo(repos, github_repos):
    """Narrow a repo list to only those matching specific github_repo values.

    Args:
        repos: List of repo dicts from get_repos_for_orgs()
        github_repos: List of "owner/repo" strings to keep

    Returns:
        Filtered list of repo dicts
    """
    return [r for r in repos if r["github_repo"] in github_repos]
