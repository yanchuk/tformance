"""Copilot metrics service - stub for testing."""

from decimal import Decimal

import requests

# GitHub API constants
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_API_VERSION = "application/vnd.github+json"


class CopilotMetricsError(Exception):
    """Exception raised when Copilot metrics API calls fail."""

    pass


def _build_copilot_metrics_url(org_slug):
    """Build the Copilot metrics API URL for an organization.

    Args:
        org_slug: GitHub organization slug

    Returns:
        str: Full API endpoint URL
    """
    return f"{GITHUB_API_BASE_URL}/orgs/{org_slug}/copilot/metrics"


def _build_github_headers(access_token):
    """Build headers for GitHub API requests.

    Args:
        access_token: GitHub OAuth access token

    Returns:
        dict: Headers with authorization and API version
    """
    return {
        "Authorization": f"Bearer {access_token}",
        "Accept": GITHUB_API_VERSION,
    }


def check_copilot_availability(access_token, org_slug):
    """Check if organization has Copilot metrics available.

    Args:
        access_token: GitHub OAuth access token
        org_slug: GitHub organization slug

    Returns:
        bool: True if Copilot metrics are available, False otherwise
    """
    url = _build_copilot_metrics_url(org_slug)
    headers = _build_github_headers(access_token)

    response = requests.get(url, headers=headers)

    if response.status_code == 200:
        return True
    elif response.status_code == 403:
        return False

    return False


def fetch_copilot_metrics(access_token, org_slug, since=None, until=None):
    """Fetch Copilot metrics from GitHub API.

    Args:
        access_token: GitHub OAuth access token
        org_slug: GitHub organization slug
        since: Optional start date (ISO 8601 format, e.g., '2025-12-01')
        until: Optional end date (ISO 8601 format, e.g., '2025-12-15')

    Returns:
        list: Raw metrics data from GitHub API

    Raises:
        CopilotMetricsError: If the API call fails or returns an error status
    """
    url = _build_copilot_metrics_url(org_slug)
    headers = _build_github_headers(access_token)

    params = {}
    if since:
        params["since"] = since
    if until:
        params["until"] = until

    try:
        response = requests.get(url, headers=headers, params=params)

        if response.status_code == 403:
            raise CopilotMetricsError(
                f"Copilot metrics unavailable (403): {response.json().get('message', 'Forbidden')}"
            )

        response.raise_for_status()
        return response.json()

    except CopilotMetricsError:
        raise
    except Exception as e:
        raise CopilotMetricsError(f"Failed to fetch Copilot metrics: {str(e)}")


def parse_metrics_response(data):
    """Parse and normalize Copilot metrics API response.

    Transforms the raw GitHub API response into a simplified format
    with flattened metrics for easier storage and analysis.

    Args:
        data: List of daily metric objects from GitHub API

    Returns:
        list: Normalized metrics with flattened structure, one dict per day
    """
    result = []

    for day_data in data:
        # Extract code completions data
        code_completions = day_data.get("copilot_ide_code_completions", {})
        chat_data = day_data.get("copilot_ide_chat", {})
        dotcom_chat_data = day_data.get("copilot_dotcom_chat", {})
        dotcom_prs_data = day_data.get("copilot_dotcom_pull_requests", {})

        normalized = {
            "date": day_data.get("date"),
            "total_active_users": day_data.get("total_active_users"),
            "total_engaged_users": day_data.get("total_engaged_users"),
            "code_completions_total": code_completions.get("total_completions", 0),
            "code_completions_accepted": code_completions.get("total_acceptances", 0),
            "lines_suggested": code_completions.get("total_lines_suggested", 0),
            "lines_accepted": code_completions.get("total_lines_accepted", 0),
            "chat_total": chat_data.get("total_chats", 0),
            "dotcom_chat_total": dotcom_chat_data.get("total_chats", 0),
            "dotcom_prs_total": dotcom_prs_data.get("total_prs", 0),
        }

        result.append(normalized)

    return result


def map_copilot_to_ai_usage(parsed_day_data):
    """Map parsed Copilot metrics to AIUsageDaily model fields.

    Args:
        parsed_day_data: Dict containing normalized metrics from parse_metrics_response

    Returns:
        dict: Mapped fields compatible with AIUsageDaily model
    """
    suggestions_shown = parsed_day_data["code_completions_total"]
    suggestions_accepted = parsed_day_data["code_completions_accepted"]

    # Calculate acceptance rate
    if suggestions_shown > 0:
        acceptance_rate = (Decimal(suggestions_accepted) / Decimal(suggestions_shown) * 100).quantize(Decimal("0.01"))
    else:
        acceptance_rate = None

    return {
        "date": parsed_day_data["date"],
        "source": "copilot",
        "suggestions_shown": suggestions_shown,
        "suggestions_accepted": suggestions_accepted,
        "acceptance_rate": acceptance_rate,
    }
