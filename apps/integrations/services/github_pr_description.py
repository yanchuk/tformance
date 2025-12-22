"""GitHub PR Description Survey Service.

Updates PR descriptions with survey voting links.
Uses HTML comment markers to identify and update survey sections.
"""

import re

from github import Github

from apps.metrics.models import PRSurvey

# HTML comment markers for survey section
SURVEY_START_MARKER = "<!-- tformance-survey-start -->"
SURVEY_END_MARKER = "<!-- tformance-survey-end -->"


def build_author_survey_section(survey: PRSurvey, base_url: str) -> str:
    """Build survey section with author question.

    Used when AI has NOT been auto-detected.
    """
    token = survey.token
    author_username = survey.pull_request.author.github_username if survey.pull_request.author else "Author"

    vote1 = f"{base_url}/survey/{token}/reviewer/?vote=1"
    vote2 = f"{base_url}/survey/{token}/reviewer/?vote=2"
    vote3 = f"{base_url}/survey/{token}/reviewer/?vote=3"
    author_yes = f"{base_url}/survey/{token}/author/?vote=yes"
    author_no = f"{base_url}/survey/{token}/author/?vote=no"

    return f"""
**@{author_username}** - Was this PR AI-assisted?
> [Yes]({author_yes}) | [No]({author_no})

**Reviewers** - Rate this code:
> [Could be better]({vote1}) | [OK]({vote2}) | [Super]({vote3})
"""


def build_ai_detected_survey_section(survey: PRSurvey, base_url: str) -> str:
    """Build survey section for AI-detected PRs.

    Used when AI has been auto-detected from commit signatures.
    Skips author question since we already know it's AI-assisted.
    """
    token = survey.token
    vote1 = f"{base_url}/survey/{token}/reviewer/?vote=1"
    vote2 = f"{base_url}/survey/{token}/reviewer/?vote=2"
    vote3 = f"{base_url}/survey/{token}/reviewer/?vote=3"

    return f"""
**AI-assisted PR detected**

**Reviewers** - Rate this code:
> [Could be better]({vote1}) | [OK]({vote2}) | [Super]({vote3})
"""


def build_survey_section(survey: PRSurvey, base_url: str) -> str:
    """Build complete survey section with markers.

    Automatically selects the appropriate template based on
    whether AI was auto-detected.
    """
    # Choose template based on auto-detection
    if survey.author_ai_assisted is True and survey.author_response_source == "auto":
        content = build_ai_detected_survey_section(survey, base_url)
    else:
        content = build_author_survey_section(survey, base_url)

    return f"""{SURVEY_START_MARKER}

---

### tformance Survey
{content}
{SURVEY_END_MARKER}"""


def extract_existing_survey_section(body: str | None) -> str | None:
    """Extract existing survey section from PR body.

    Returns the content between markers, or None if not found.
    """
    if not body:
        return None

    # Pattern to match everything between markers
    pattern = re.escape(SURVEY_START_MARKER) + r"(.*?)" + re.escape(SURVEY_END_MARKER)
    match = re.search(pattern, body, re.DOTALL)

    if match:
        return match.group(0)
    return None


def _remove_existing_survey_section(body: str) -> str:
    """Remove existing survey section from PR body."""
    if not body:
        return ""

    pattern = re.escape(SURVEY_START_MARKER) + r".*?" + re.escape(SURVEY_END_MARKER)
    return re.sub(pattern, "", body, flags=re.DOTALL).strip()


def update_pr_description_with_survey(
    survey: PRSurvey,
    access_token: str,
    base_url: str,
) -> None:
    """Update PR description with survey voting links.

    Appends survey section to PR description, or replaces existing
    survey section if one exists.

    Args:
        survey: The PRSurvey to add to the PR description
        access_token: GitHub access token for API calls
        base_url: Base URL for survey voting links
    """
    pr = survey.pull_request

    # Connect to GitHub
    g = Github(access_token)
    repo = g.get_repo(pr.github_repo)
    github_pr = repo.get_pull(pr.github_pr_id)

    # Get current body and remove existing survey if present
    current_body = github_pr.body or ""
    body_without_survey = _remove_existing_survey_section(current_body)

    # Build new survey section
    survey_section = build_survey_section(survey, base_url)

    # Combine body with survey
    new_body = f"{body_without_survey}\n\n{survey_section}" if body_without_survey else survey_section

    # Update PR
    github_pr.edit(body=new_body)
