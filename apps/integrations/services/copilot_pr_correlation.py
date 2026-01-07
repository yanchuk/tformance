"""
Copilot PR Correlation Service.

Correlates daily Copilot usage (AIUsageDaily) with Pull Requests to mark
PRs as AI-assisted when the author had Copilot activity on the PR creation date.
"""

from apps.metrics.models import AIUsageDaily, PullRequest
from apps.teams.models import Team


def correlate_prs_with_copilot_usage(team: Team, min_suggestions: int = 1) -> int:
    """Correlate PRs with Copilot usage for a team.

    For each PR in the team, check if the author had Copilot usage on the day
    the PR was created. If so, mark the PR as AI-assisted and add 'copilot'
    to ai_tools_detected.

    Args:
        team: The team to correlate PRs for.
        min_suggestions: Minimum suggestions_shown to count as active usage.
            Defaults to 1 (any activity counts).

    Returns:
        Number of PRs updated.
    """
    # Get all PRs that haven't been marked yet or could have copilot added
    prs = PullRequest.objects.filter(team=team).select_related("author")

    # Get all Copilot usage dates per member for this team
    copilot_usage = AIUsageDaily.objects.filter(
        team=team,
        source="copilot",
        suggestions_shown__gte=min_suggestions,
    ).values_list("member_id", "date")

    # Build a set of (member_id, date) tuples for fast lookup
    usage_lookup = {(member_id, usage_date) for member_id, usage_date in copilot_usage}

    updated_count = 0
    for pr in prs:
        if pr.author_id is None or pr.pr_created_at is None:
            continue

        pr_date = pr.pr_created_at.date()
        lookup_key = (pr.author_id, pr_date)

        if lookup_key in usage_lookup:
            # This PR was created on a day the author used Copilot
            needs_update = False

            # Mark as AI assisted if not already set
            if pr.is_ai_assisted is None or pr.is_ai_assisted is False:
                pr.is_ai_assisted = True
                needs_update = True

            # Add copilot to ai_tools_detected if not already present
            current_tools = pr.ai_tools_detected or []
            if "copilot" not in current_tools:
                pr.ai_tools_detected = list(current_tools) + ["copilot"]
                needs_update = True

            if needs_update:
                pr.save(update_fields=["is_ai_assisted", "ai_tools_detected"])
                updated_count += 1

    return updated_count
