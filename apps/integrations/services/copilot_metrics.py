"""Copilot metrics service - stub for testing."""

import json
import logging
from datetime import date, timedelta
from decimal import Decimal

import requests
from django.conf import settings

logger = logging.getLogger(__name__)

# GitHub API constants
GITHUB_API_BASE_URL = "https://api.github.com"
GITHUB_API_VERSION = "application/vnd.github+json"

# Copilot pricing constants
COPILOT_SEAT_PRICE = Decimal("19.00")  # Monthly cost per seat in USD


class CopilotMetricsError(Exception):
    """Exception raised when Copilot metrics API calls fail."""

    pass


class InsufficientLicensesError(CopilotMetricsError):
    """Exception raised when org has fewer than 5 Copilot licenses.

    GitHub requires 5+ Copilot licenses to access the usage metrics API.
    This error should NOT trigger task retries - it's a permanent condition
    until the org purchases more licenses.
    """

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


def _make_github_api_request(url, headers, params=None, error_prefix="GitHub API"):
    """Make a GitHub API request with consistent error handling.

    Args:
        url: Full API endpoint URL
        headers: Request headers
        params: Optional query parameters
        error_prefix: Prefix for error messages

    Returns:
        dict or list: Parsed JSON response

    Raises:
        CopilotMetricsError: If the API call fails or returns an error status
    """
    from apps.integrations.exceptions import TokenRevokedError

    try:
        response = requests.get(url, headers=headers, params=params, timeout=30)

        # Edge case #16: Check for 401 (token revoked) before other errors
        if response.status_code == 401:
            # Try to get error message from JSON, fallback if response isn't valid JSON
            try:
                error_message = response.json().get("message", "Bad credentials")
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in 401 response from %s", url)
                error_message = "Bad credentials"
            raise TokenRevokedError(
                f"GitHub OAuth token was revoked. Please reconnect via Integrations settings. (401: {error_message})"
            )

        if response.status_code == 403:
            # Try to get error message from JSON, fallback if response isn't valid JSON
            try:
                error_message = response.json().get("message", "Forbidden")
            except json.JSONDecodeError:
                logger.warning("Invalid JSON in 403 response from %s", url)
                error_message = "Forbidden"
            raise CopilotMetricsError(f"{error_prefix} unavailable (403): {error_message}")

        if response.status_code == 422:
            # 422 Unprocessable Entity - typically means insufficient Copilot licenses
            # GitHub requires 5+ licenses to access the Copilot metrics API
            try:
                error_message = response.json().get("message", "Unprocessable Entity")
            except json.JSONDecodeError:
                error_message = "Unprocessable Entity"
            logger.info(
                "Copilot metrics unavailable for org (422): %s - likely insufficient licenses",
                error_message,
            )
            raise InsufficientLicensesError(
                f"Your organization needs 5+ Copilot licenses to access usage metrics. (422: {error_message})"
            )

        response.raise_for_status()

        # Parse JSON response with error handling
        try:
            return response.json()
        except json.JSONDecodeError as e:
            logger.error("Invalid JSON response from %s: %s", url, e)
            raise CopilotMetricsError(f"Invalid response from {error_prefix}") from e

    except CopilotMetricsError:
        raise
    except TokenRevokedError:
        # Let TokenRevokedError propagate without wrapping
        raise
    except Exception as e:
        raise CopilotMetricsError(f"Failed to fetch {error_prefix}: {str(e)}") from e


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

    response = requests.get(url, headers=headers, timeout=30)

    if response.status_code == 200:
        return True
    elif response.status_code == 403:
        return False

    return False


def fetch_copilot_metrics(access_token, org_slug, since=None, until=None):
    """Fetch Copilot metrics from GitHub API or mock data.

    When COPILOT_USE_MOCK_DATA setting is True, returns mock data instead of
    making real API calls. This is useful for development and testing when
    you don't have access to a GitHub organization with 5+ Copilot licenses.

    Args:
        access_token: GitHub OAuth access token (ignored in mock mode)
        org_slug: GitHub organization slug (ignored in mock mode)
        since: Optional start date (ISO 8601 format, e.g., '2025-12-01')
        until: Optional end date (ISO 8601 format, e.g., '2025-12-15')

    Returns:
        list: Raw metrics data from GitHub API or mock generator

    Raises:
        CopilotMetricsError: If the API call fails or returns an error status
    """
    # Check if mock mode is enabled
    use_mock = getattr(settings, "COPILOT_USE_MOCK_DATA", False)

    if use_mock:
        from apps.integrations.services.copilot_mock_data import CopilotMockDataGenerator

        mock_seed = getattr(settings, "COPILOT_MOCK_SEED", 42)
        mock_scenario = getattr(settings, "COPILOT_MOCK_SCENARIO", "mixed_usage")

        # Use provided dates or default to last 28 days
        end_date = until or date.today().isoformat()
        start_date = since or (date.today() - timedelta(days=28)).isoformat()

        generator = CopilotMockDataGenerator(seed=mock_seed)
        return generator.generate(since=start_date, until=end_date, scenario=mock_scenario)

    # Real API call
    url = _build_copilot_metrics_url(org_slug)
    headers = _build_github_headers(access_token)

    params = {}
    if since:
        params["since"] = since
    if until:
        params["until"] = until

    return _make_github_api_request(url, headers, params, error_prefix="Copilot metrics")


def parse_metrics_response(data):
    """Parse and normalize Copilot metrics API response.

    Transforms the raw GitHub API response into a simplified format
    with flattened metrics for easier storage and analysis.

    Args:
        data: List of daily metric objects from GitHub API

    Returns:
        list: Normalized metrics with flattened structure, one dict per day containing:
            - date: ISO date string
            - total_active_users: Count of active users
            - total_engaged_users: Count of engaged users
            - code_completions_total: Total suggestions shown
            - code_completions_accepted: Total suggestions accepted
            - lines_suggested: Total lines of code suggested
            - lines_accepted: Total lines of code accepted
            - chat_total: Total IDE chat interactions
            - dotcom_chat_total: Total dotcom chat interactions
            - dotcom_prs_total: Total dotcom PR summaries
            - languages: List of dicts with per-language breakdown:
                - name: Language name (e.g., "python", "typescript")
                - suggestions_shown: Completions shown for this language
                - suggestions_accepted: Completions accepted
                - lines_suggested: Lines suggested
                - lines_accepted: Lines accepted
            - editors: List of dicts with per-editor breakdown:
                - name: Editor name (e.g., "vscode", "jetbrains")
                - suggestions_shown: Completions shown in this editor
                - suggestions_accepted: Completions accepted
                - active_users: Users active in this editor
    """
    result = []

    for day_data in data:
        # Extract code completions data
        code_completions = day_data.get("copilot_ide_code_completions", {})
        chat_data = day_data.get("copilot_ide_chat", {})
        dotcom_chat_data = day_data.get("copilot_dotcom_chat", {})
        dotcom_prs_data = day_data.get("copilot_dotcom_pull_requests", {})

        # Aggregate languages from nested editors > models > languages structure
        # Official GitHub API has metrics nested; top-level languages only has name/engaged_users
        languages = _aggregate_languages_from_editors(code_completions.get("editors", []))

        # Aggregate editors with totals from nested models > languages
        editors = _aggregate_editors_from_nested(code_completions.get("editors", []))

        # Aggregate top-level totals from nested structure
        totals = _aggregate_totals_from_editors(code_completions.get("editors", []))

        normalized = {
            "date": day_data.get("date"),
            "total_active_users": day_data.get("total_active_users"),
            "total_engaged_users": day_data.get("total_engaged_users"),
            "code_completions_total": totals["total_suggestions"],
            "code_completions_accepted": totals["total_acceptances"],
            "lines_suggested": totals["total_lines_suggested"],
            "lines_accepted": totals["total_lines_accepted"],
            "chat_total": chat_data.get("total_chats", 0),
            "dotcom_chat_total": dotcom_chat_data.get("total_chats", 0),
            "dotcom_prs_total": dotcom_prs_data.get("total_prs", 0),
            "languages": languages,
            "editors": editors,
        }

        result.append(normalized)

    return result


def _aggregate_totals_from_editors(editors: list[dict]) -> dict:
    """Aggregate totals from nested editors > models > languages structure.

    Official GitHub Copilot Metrics API doesn't have top-level totals.
    This function aggregates from the nested structure.

    Args:
        editors: List of editor dicts with nested models > languages.

    Returns:
        dict with aggregated totals:
            - total_suggestions
            - total_acceptances
            - total_lines_suggested
            - total_lines_accepted
    """
    total_suggestions = 0
    total_acceptances = 0
    total_lines_suggested = 0
    total_lines_accepted = 0

    for editor in editors:
        for model in editor.get("models", []):
            for lang in model.get("languages", []):
                total_suggestions += lang.get("total_code_suggestions", 0)
                total_acceptances += lang.get("total_code_acceptances", 0)
                total_lines_suggested += lang.get("total_code_lines_suggested", 0)
                total_lines_accepted += lang.get("total_code_lines_accepted", 0)

    return {
        "total_suggestions": total_suggestions,
        "total_acceptances": total_acceptances,
        "total_lines_suggested": total_lines_suggested,
        "total_lines_accepted": total_lines_accepted,
    }


def _aggregate_languages_from_editors(editors: list[dict]) -> list[dict]:
    """Aggregate per-language metrics from nested editors > models > languages.

    Combines metrics across all editors/models for each language.

    Args:
        editors: List of editor dicts with nested models > languages.

    Returns:
        list of language dicts with combined metrics:
            - name: Language name
            - suggestions_shown: Total suggestions across all editors
            - suggestions_accepted: Total acceptances
            - lines_suggested: Total lines suggested
            - lines_accepted: Total lines accepted
    """
    # Use dict to aggregate by language name
    lang_totals: dict[str, dict] = {}

    for editor in editors:
        for model in editor.get("models", []):
            for lang in model.get("languages", []):
                name = lang.get("name", "unknown")
                if name not in lang_totals:
                    lang_totals[name] = {
                        "name": name,
                        "suggestions_shown": 0,
                        "suggestions_accepted": 0,
                        "lines_suggested": 0,
                        "lines_accepted": 0,
                    }
                lang_totals[name]["suggestions_shown"] += lang.get("total_code_suggestions", 0)
                lang_totals[name]["suggestions_accepted"] += lang.get("total_code_acceptances", 0)
                lang_totals[name]["lines_suggested"] += lang.get("total_code_lines_suggested", 0)
                lang_totals[name]["lines_accepted"] += lang.get("total_code_lines_accepted", 0)

    return list(lang_totals.values())


def _aggregate_editors_from_nested(editors: list[dict]) -> list[dict]:
    """Aggregate per-editor metrics from nested models > languages.

    Args:
        editors: List of editor dicts with nested models > languages.

    Returns:
        list of editor dicts with aggregated metrics:
            - name: Editor name
            - suggestions_shown: Total suggestions for this editor
            - suggestions_accepted: Total acceptances
            - active_users: Users active in this editor
    """
    result = []

    for editor in editors:
        total_suggestions = 0
        total_acceptances = 0

        for model in editor.get("models", []):
            for lang in model.get("languages", []):
                total_suggestions += lang.get("total_code_suggestions", 0)
                total_acceptances += lang.get("total_code_acceptances", 0)

        result.append(
            {
                "name": editor.get("name"),
                "suggestions_shown": total_suggestions,
                "suggestions_accepted": total_acceptances,
                "active_users": editor.get("total_engaged_users", 0),
            }
        )

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


def fetch_copilot_seats(access_token, org_slug):
    """Fetch Copilot seat utilization data from GitHub API.

    Args:
        access_token: GitHub OAuth access token
        org_slug: GitHub organization slug

    Returns:
        dict: Seat data including total_seats, seats list, and seat_breakdown

    Raises:
        CopilotMetricsError: If the API call fails or returns an error status
    """
    url = f"{GITHUB_API_BASE_URL}/orgs/{org_slug}/copilot/billing/seats"
    headers = _build_github_headers(access_token)

    return _make_github_api_request(url, headers, error_prefix="Copilot seats")


def get_seat_utilization(seats_data):
    """Calculate Copilot seat utilization metrics.

    Args:
        seats_data: Dict from fetch_copilot_seats containing seat information

    Returns:
        dict: Utilization metrics including total_seats, active_seats, inactive_seats,
              utilization_rate, monthly_cost, and cost_per_active_user
    """
    total_seats = seats_data["total_seats"]
    seat_breakdown = seats_data["seat_breakdown"]
    active_seats = seat_breakdown["active_this_cycle"]
    inactive_seats = seat_breakdown["inactive_this_cycle"]

    # Calculate utilization rate
    if total_seats > 0:
        utilization_rate = (Decimal(active_seats) / Decimal(total_seats) * 100).quantize(Decimal("0.01"))
    else:
        utilization_rate = Decimal("0.00")

    # Calculate monthly costs
    monthly_cost = (Decimal(total_seats) * COPILOT_SEAT_PRICE).quantize(Decimal("0.01"))

    # Calculate cost per active user
    if active_seats > 0:
        cost_per_active_user = (monthly_cost / Decimal(active_seats)).quantize(Decimal("0.01"))
    else:
        cost_per_active_user = None

    return {
        "total_seats": total_seats,
        "active_seats": active_seats,
        "inactive_seats": inactive_seats,
        "utilization_rate": utilization_rate,
        "monthly_cost": monthly_cost,
        "cost_per_active_user": cost_per_active_user,
    }


def fetch_copilot_billing(access_token, org_slug):
    """Fetch Copilot billing data from GitHub API.

    Gets organization-level billing information including seat counts
    and feature configuration.

    Args:
        access_token: GitHub OAuth access token
        org_slug: GitHub organization slug

    Returns:
        dict: Billing data including seat_breakdown and feature flags

    Raises:
        CopilotMetricsError: If the API call fails or returns an error status
    """
    url = f"{GITHUB_API_BASE_URL}/orgs/{org_slug}/copilot/billing"
    headers = _build_github_headers(access_token)

    return _make_github_api_request(url, headers, error_prefix="Copilot billing")


def parse_billing_response(billing_data):
    """Parse and normalize Copilot billing API response.

    Extracts seat counts from the billing response and provides
    defaults for missing fields.

    Args:
        billing_data: Dict from fetch_copilot_billing

    Returns:
        dict: Normalized billing data with:
            - total_seats
            - active_this_cycle
            - inactive_this_cycle
            - pending_cancellation
    """
    seat_breakdown = billing_data.get("seat_breakdown", {})

    return {
        "total_seats": seat_breakdown.get("total", 0),
        "active_this_cycle": seat_breakdown.get("active_this_cycle", 0),
        "inactive_this_cycle": seat_breakdown.get("inactive_this_cycle", 0),
        "pending_cancellation": seat_breakdown.get("pending_cancellation", 0),
    }


def sync_copilot_seats_to_snapshot(team, parsed_billing):
    """Sync parsed billing data to CopilotSeatSnapshot model.

    Creates or updates the CopilotSeatSnapshot for the team and current date.

    Args:
        team: Team model instance
        parsed_billing: Dict from parse_billing_response

    Returns:
        CopilotSeatSnapshot: The created or updated snapshot
    """
    from datetime import date

    from apps.metrics.models import CopilotSeatSnapshot

    snapshot, _ = CopilotSeatSnapshot.objects.update_or_create(
        team=team,
        date=date.today(),
        defaults={
            "total_seats": parsed_billing["total_seats"],
            "active_this_cycle": parsed_billing["active_this_cycle"],
            "inactive_this_cycle": parsed_billing["inactive_this_cycle"],
            "pending_cancellation": parsed_billing["pending_cancellation"],
        },
    )

    return snapshot


def sync_copilot_language_data(team, parsed_metrics):
    """Sync parsed language data to CopilotLanguageDaily model.

    Creates or updates CopilotLanguageDaily records for each language
    in each day's metrics.

    Args:
        team: Team model instance
        parsed_metrics: List of dicts from parse_metrics_response

    Returns:
        int: Count of records created/updated
    """
    from datetime import datetime

    from apps.metrics.models import CopilotLanguageDaily

    count = 0
    for day_data in parsed_metrics:
        date_str = day_data["date"]
        record_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        for lang in day_data.get("languages", []):
            CopilotLanguageDaily.objects.update_or_create(
                team=team,
                date=record_date,
                language=lang["name"],
                defaults={
                    "suggestions_shown": lang["suggestions_shown"],
                    "suggestions_accepted": lang["suggestions_accepted"],
                    "lines_suggested": lang["lines_suggested"],
                    "lines_accepted": lang["lines_accepted"],
                },
            )
            count += 1

    return count


def sync_copilot_editor_data(team, parsed_metrics):
    """Sync parsed editor data to CopilotEditorDaily model.

    Creates or updates CopilotEditorDaily records for each editor
    in each day's metrics.

    Args:
        team: Team model instance
        parsed_metrics: List of dicts from parse_metrics_response

    Returns:
        int: Count of records created/updated
    """
    from datetime import datetime

    from apps.metrics.models import CopilotEditorDaily

    count = 0
    for day_data in parsed_metrics:
        date_str = day_data["date"]
        record_date = datetime.strptime(date_str, "%Y-%m-%d").date()

        for editor in day_data.get("editors", []):
            CopilotEditorDaily.objects.update_or_create(
                team=team,
                date=record_date,
                editor=editor["name"],
                defaults={
                    "suggestions_shown": editor["suggestions_shown"],
                    "suggestions_accepted": editor["suggestions_accepted"],
                    "active_users": editor["active_users"],
                },
            )
            count += 1

    return count


def sync_copilot_member_activity(team, seats_data):
    """Sync per-user Copilot activity from Seats API to TeamMember.

    Args:
        team: Team model instance
        seats_data: Dict from fetch_copilot_seats containing seats array

    Returns:
        int: Count of members updated
    """
    from dateutil import parser

    from apps.metrics.models import TeamMember

    seats = seats_data.get("seats", [])
    updated_count = 0

    for seat in seats:
        # Skip seats without activity
        last_activity = seat.get("last_activity_at")
        if not last_activity:
            continue

        # Get assignee username
        assignee = seat.get("assignee", {})
        username = assignee.get("login")
        if not username:
            continue

        # Find matching member for THIS team only
        try:
            member = TeamMember.objects.get(team=team, github_username=username)
        except TeamMember.DoesNotExist:
            continue

        # Update Copilot fields
        member.copilot_last_activity_at = parser.parse(last_activity)
        member.copilot_last_editor = seat.get("last_activity_editor")
        member.save(update_fields=["copilot_last_activity_at", "copilot_last_editor"])
        updated_count += 1

    return updated_count
