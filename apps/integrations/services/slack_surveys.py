"""
Slack survey message templates using Block Kit.

Build message blocks for PR surveys, thank you messages, and reveal messages.
"""

from typing import TypedDict

from apps.metrics.models import PRSurvey, PullRequest, TeamMember


class AccuracyStats(TypedDict):
    """Type definition for accuracy statistics."""

    correct: int
    total: int
    percentage: float


# Action ID constants
ACTION_AUTHOR_AI_YES = "author_ai_yes"
ACTION_AUTHOR_AI_NO = "author_ai_no"
ACTION_QUALITY_1 = "quality_1"  # Could be better
ACTION_QUALITY_2 = "quality_2"  # OK
ACTION_QUALITY_3 = "quality_3"  # Super
ACTION_AI_GUESS_YES = "ai_guess_yes"
ACTION_AI_GUESS_NO = "ai_guess_no"


def _create_button(text: str, action_id: str, value: str, style: str | None = None) -> dict:
    """Create a Block Kit button element.

    Args:
        text: Button text
        action_id: Action ID for the button
        value: Value to send when clicked
        style: Optional button style (e.g., "primary")

    Returns:
        Button element dict
    """
    button = {
        "type": "button",
        "text": {"type": "plain_text", "text": text},
        "action_id": action_id,
        "value": value,
    }
    if style:
        button["style"] = style
    return button


def build_author_survey_blocks(pr: PullRequest, survey: PRSurvey) -> list:
    """Build Block Kit blocks for author survey DM.

    Message:
    Hey {author_name}! 🎉
    Your PR was just merged: *{pr_title}*
    Quick question: Was this PR AI-assisted?
    [Yes] [No]

    Args:
        pr: The pull request that was merged
        survey: The PRSurvey instance

    Returns:
        List of Block Kit blocks
    """
    author_name = pr.author.display_name if pr.author else "there"

    message = (
        f"Hey {author_name}! 🎉\n\nYour PR was just merged:\n*{pr.title}*\n\nQuick question: Was this PR AI-assisted?"
    )

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": message,
            },
        },
        {
            "type": "actions",
            "block_id": f"survey_{survey.id}",
            "elements": [
                _create_button("Yes", ACTION_AUTHOR_AI_YES, str(survey.id), style="primary"),
                _create_button("No", ACTION_AUTHOR_AI_NO, str(survey.id)),
            ],
        },
    ]

    return blocks


def build_reviewer_survey_blocks(pr: PullRequest, survey: PRSurvey, reviewer: TeamMember) -> list:
    """Build Block Kit blocks for reviewer survey DM.

    Message:
    Hey {reviewer_name}! 👀
    You reviewed this PR that just merged: *{pr_title}* by {author_name}
    How would you rate the code quality?
    [Could be better] [OK] [Super]
    Bonus: Was this PR AI-assisted?
    [Yes, I think so] [No, I don't think so]

    Args:
        pr: The pull request that was merged
        survey: The PRSurvey instance
        reviewer: The reviewer who is receiving this survey

    Returns:
        List of Block Kit blocks
    """
    reviewer_name = reviewer.display_name
    author_name = pr.author.display_name if pr.author else "Unknown"

    message = (
        f"Hey {reviewer_name}! 👀\n\n"
        f"You reviewed this PR that just merged:\n*{pr.title}* by {author_name}\n\n"
        f"How would you rate the code quality?"
    )

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": message,
            },
        },
        {
            "type": "actions",
            "block_id": f"quality_{survey.id}",
            "elements": [
                _create_button("Could be better", ACTION_QUALITY_1, str(survey.id)),
                _create_button("OK", ACTION_QUALITY_2, str(survey.id)),
                _create_button("Super", ACTION_QUALITY_3, str(survey.id), style="primary"),
            ],
        },
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Bonus: Was this PR AI-assisted?",
            },
        },
        {
            "type": "actions",
            "block_id": f"ai_guess_{survey.id}",
            "elements": [
                _create_button("Yes, I think so", ACTION_AI_GUESS_YES, str(survey.id)),
                _create_button("No, I don't think so", ACTION_AI_GUESS_NO, str(survey.id)),
            ],
        },
    ]

    return blocks


def build_author_thanks_blocks() -> list:
    """Build thank you message after author responds.

    Message:
    Thanks! Your response has been recorded. 👍

    Returns:
        List of Block Kit blocks
    """
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Thanks! Your response has been recorded. 👍",
            },
        }
    ]

    return blocks


def build_reviewer_thanks_blocks() -> list:
    """Build thank you message after reviewer responds.

    Message:
    Thanks for your feedback!

    Returns:
        List of Block Kit blocks
    """
    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": "Thanks for your feedback!",
            },
        }
    ]

    return blocks


def build_reveal_correct_blocks(reviewer: TeamMember, was_ai_assisted: bool, accuracy_stats: AccuracyStats) -> list:
    """Build reveal message when guess was correct.

    Message:
    🎯 Nice detective work, {reviewer_name}!
    You guessed correctly - this PR *was/wasn't* AI-assisted.
    Your accuracy: {correct}/{total} ({percentage}%)

    Args:
        reviewer: The reviewer who guessed
        was_ai_assisted: Whether the PR was AI-assisted
        accuracy_stats: Dict with 'correct', 'total', 'percentage' keys

    Returns:
        List of Block Kit blocks
    """
    reviewer_name = reviewer.display_name
    correct = accuracy_stats["correct"]
    total = accuracy_stats["total"]
    percentage = accuracy_stats["percentage"]

    ai_text = "was" if was_ai_assisted else "wasn't"

    message = (
        f"🎯 Nice detective work, {reviewer_name}!\n\n"
        f"You guessed correctly - this PR *{ai_text}* AI-assisted.\n\n"
        f"Your accuracy: {correct}/{total} ({percentage}%)"
    )

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": message,
            },
        }
    ]

    return blocks


def build_reveal_wrong_blocks(reviewer: TeamMember, was_ai_assisted: bool, accuracy_stats: AccuracyStats) -> list:
    """Build reveal message when guess was wrong.

    Message:
    🤔 Interesting, {reviewer_name}!
    This PR was actually *AI-assisted/not AI-assisted*.
    Your accuracy: {correct}/{total} ({percentage}%)
    AI is getting sneaky! 🤖 / Humans can still surprise you! 👨‍💻

    Args:
        reviewer: The reviewer who guessed
        was_ai_assisted: Whether the PR was actually AI-assisted
        accuracy_stats: Dict with 'correct', 'total', 'percentage' keys

    Returns:
        List of Block Kit blocks
    """
    reviewer_name = reviewer.display_name
    correct = accuracy_stats["correct"]
    total = accuracy_stats["total"]
    percentage = accuracy_stats["percentage"]

    if was_ai_assisted:
        ai_text = "AI-assisted"
        footer_emoji = "AI is getting sneaky! 🤖"
    else:
        ai_text = "not AI-assisted"
        footer_emoji = "Humans can still surprise you! 👨‍💻"

    message = (
        f"🤔 Interesting, {reviewer_name}!\n\n"
        f"This PR was actually *{ai_text}*.\n\n"
        f"Your accuracy: {correct}/{total} ({percentage}%)\n\n"
        f"{footer_emoji}"
    )

    blocks = [
        {
            "type": "section",
            "text": {
                "type": "mrkdwn",
                "text": message,
            },
        }
    ]

    return blocks
