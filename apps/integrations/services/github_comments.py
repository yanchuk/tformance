"""GitHub Comment Service - Post survey invitations to merged PRs.

This service posts comments to GitHub PRs with survey invitation links for
authors and reviewers.
"""

import logging

from django.urls import reverse
from github import GithubException

from apps.integrations.services import github_client
from apps.web.meta import absolute_url

logger = logging.getLogger(__name__)


def build_survey_comment_body(pr, survey):
    """Build the comment markdown with @mentions and survey URLs.

    Args:
        pr: PullRequest instance
        survey: PRSurvey instance

    Returns:
        str: Markdown comment body with @mentions and survey links
    """
    # Build @mentions
    author_mention = f"@{pr.author.github_username}" if pr.author else ""

    # Get reviewers (distinct, exclude author)
    reviewers = pr.reviews.exclude(reviewer=pr.author).values_list("reviewer__github_username", flat=True).distinct()
    reviewer_mentions = " ".join(f"@{u}" for u in reviewers if u)

    # Build survey URLs (absolute)
    author_url = absolute_url(reverse("web:survey_author", kwargs={"token": survey.token}))
    reviewer_url = absolute_url(reverse("web:survey_reviewer", kwargs={"token": survey.token}))

    # Build comment body
    lines = [
        "📊 **AI Impact Survey**",
        "",
        f"{author_mention} - Did you use AI assistance for this PR?",
        f"→ [Complete Author Survey]({author_url})",
    ]

    if reviewer_mentions:
        lines.extend(
            [
                "",
                f"{reviewer_mentions} - Rate this PR and guess AI usage:",
                f"→ [Complete Reviewer Survey]({reviewer_url})",
            ]
        )

    lines.extend(["", "_Responses help improve team insights._"])

    return "\n".join(lines)


def post_survey_comment(pr, survey, access_token):
    """Post a survey invitation comment to a GitHub PR.

    Posts a comment to the merged PR on GitHub, @mentioning the author and
    reviewers with links to their respective survey forms.

    Args:
        pr: PullRequest instance
        survey: PRSurvey instance
        access_token: GitHub access token for API authentication

    Returns:
        int: GitHub comment ID

    Raises:
        GithubException: If GitHub API call fails (auth, rate limit, network, etc.)

    Side effects:
        - Posts comment to GitHub PR
        - Updates survey.github_comment_id
    """
    try:
        # Get GitHub client
        client = github_client.get_github_client(access_token)

        # Build comment
        body = build_survey_comment_body(pr, survey)

        # Post to GitHub (PRs are issues in GitHub API)
        repo = client.get_repo(pr.github_repo)
        issue = repo.get_issue(pr.github_pr_id)
        comment = issue.create_comment(body)

        # Store comment ID
        survey.github_comment_id = comment.id
        survey.save()

        logger.info(
            "Posted survey comment to GitHub PR",
            extra={
                "pr_id": pr.id,
                "github_repo": pr.github_repo,
                "github_pr_id": pr.github_pr_id,
                "survey_id": survey.id,
                "comment_id": comment.id,
            },
        )

        return comment.id

    except GithubException as e:
        logger.error(
            "Failed to post survey comment to GitHub PR",
            extra={
                "pr_id": pr.id,
                "github_repo": pr.github_repo,
                "github_pr_id": pr.github_pr_id,
                "survey_id": survey.id,
                "error": str(e),
                "status": e.status if hasattr(e, "status") else None,
            },
        )
        raise
