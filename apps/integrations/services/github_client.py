"""GitHub client service for creating authenticated PyGithub instances."""

from github import Github


def get_github_client(access_token: str) -> Github:
    """
    Create and return an authenticated GitHub client instance.

    Args:
        access_token: GitHub OAuth access token

    Returns:
        Authenticated Github client instance
    """
    return Github(access_token)
