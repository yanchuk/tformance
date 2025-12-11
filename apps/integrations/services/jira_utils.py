"""Utility functions for Jira integration."""

import re


def extract_jira_key(text: str) -> str | None:
    """
    Extract the first Jira issue key from text.

    Jira keys follow the format: PROJECT-123 where PROJECT is uppercase letters/numbers
    and is followed by a hyphen and numeric ID.

    Args:
        text: Text to search for Jira keys (e.g., "Fix: PROJ-123 login bug")

    Returns:
        The first Jira key found, or None if no key is found.

    Example:
        >>> extract_jira_key("feature/PROJ-123-add-login")
        'PROJ-123'
        >>> extract_jira_key("no jira key here")
        None
    """
    if not text:
        return None

    pattern = r"[A-Z][A-Z0-9]+-\d+"
    match = re.search(pattern, text)

    return match.group(0) if match else None
