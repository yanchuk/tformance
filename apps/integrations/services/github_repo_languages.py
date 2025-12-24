"""GitHub repository language fetching service.

Fetches language breakdown from GitHub API to improve LLM technology detection.
Languages are stored on TrackedRepository and refreshed monthly.
"""

from __future__ import annotations

import logging
from typing import TYPE_CHECKING

from django.utils import timezone

from apps.integrations.services.github_client import get_github_client

if TYPE_CHECKING:
    from apps.integrations.models import TrackedRepository

logger = logging.getLogger(__name__)


def fetch_repo_languages(repo: TrackedRepository) -> dict[str, int]:
    """Fetch language breakdown from GitHub API.

    Args:
        repo: TrackedRepository instance with access to credentials

    Returns:
        Dict mapping language name to bytes of code (e.g., {"Python": 150000})

    Raises:
        ValueError: If no GitHub credential available
    """
    credential = repo.integration.credential
    if not credential or not credential.access_token:
        raise ValueError(f"No GitHub credential for repo {repo.full_name}")

    client = get_github_client(credential.access_token)
    gh_repo = client.get_repo(repo.full_name)

    # GitHub API: GET /repos/{owner}/{repo}/languages
    # Returns: {"Python": 150000, "JavaScript": 5000, ...}
    return gh_repo.get_languages()


def update_repo_languages(repo: TrackedRepository) -> dict[str, int]:
    """Fetch and store language breakdown for a repository.

    Args:
        repo: TrackedRepository to update

    Returns:
        Language dict that was stored
    """
    languages = fetch_repo_languages(repo)

    # Find primary language (most bytes)
    primary_language = ""
    if languages:
        primary_language = max(languages, key=lambda k: languages[k])

    # Update repository
    repo.languages = languages
    repo.primary_language = primary_language
    repo.languages_updated_at = timezone.now()
    repo.save(update_fields=["languages", "primary_language", "languages_updated_at"])

    logger.info(
        "Updated languages for %s: primary=%s, total=%d languages",
        repo.full_name,
        primary_language,
        len(languages),
    )

    return languages


def get_top_languages(repo: TrackedRepository, limit: int = 5) -> list[str]:
    """Get top N languages for a repository by bytes.

    Args:
        repo: TrackedRepository with languages data
        limit: Max number of languages to return

    Returns:
        List of language names, sorted by bytes descending
    """
    if not repo.languages:
        return []

    sorted_langs = sorted(repo.languages.items(), key=lambda x: x[1], reverse=True)
    return [lang for lang, _ in sorted_langs[:limit]]
