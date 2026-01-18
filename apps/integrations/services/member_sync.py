"""GitHub member synchronization service."""

import logging
from typing import TypedDict

from apps.integrations.services.github_oauth import get_organization_members, get_user_details
from apps.metrics.models import TeamMember
from apps.teams.models import Team

logger = logging.getLogger(__name__)


class SyncResult(TypedDict):
    """Result of GitHub member synchronization."""

    created: int
    updated: int
    unchanged: int
    failed: int


def sync_github_members(team: Team, access_token: str, org_slug: str) -> SyncResult:
    """Synchronize GitHub organization members to TeamMember records.

    Args:
        team: The team to sync members for
        access_token: GitHub access token
        org_slug: GitHub organization slug

    Returns:
        Dictionary with keys: created, updated, unchanged, failed (integers)
    """
    # Get members from GitHub
    github_members = get_organization_members(access_token, org_slug)

    created = 0
    updated = 0
    unchanged = 0
    failed = 0

    for github_member in github_members:
        github_id = str(github_member["id"])
        github_username = github_member["login"]

        # Check if member exists
        try:
            member = TeamMember.objects.get(team=team, github_id=github_id)
            # Existing member - check if username changed
            if member.github_username != github_username:
                member.github_username = github_username
                member.save(update_fields=["github_username"])
                updated += 1
            else:
                unchanged += 1
        except TeamMember.DoesNotExist:
            # New member - fetch full details
            try:
                user_details = get_user_details(access_token, github_username)

                # Extract fields
                display_name = user_details.get("name") or github_username
                email = user_details.get("email") or ""

                # Create new member
                TeamMember.objects.create(
                    team=team,
                    github_id=github_id,
                    github_username=github_username,
                    display_name=display_name,
                    email=email,
                    is_active=True,
                )
                created += 1
            except Exception as e:
                # Log error but continue syncing other members
                logger.error(
                    f"Failed to sync GitHub member {github_username} (id: {github_id}) for team {team.slug}: {e}"
                )
                failed += 1

    return {
        "created": created,
        "updated": updated,
        "unchanged": unchanged,
        "failed": failed,
    }


def sync_single_user_as_member(team: Team, access_token: str, username: str) -> SyncResult:
    """Synchronize a single GitHub user as a TeamMember.

    Args:
        team: The team to sync the member for
        access_token: GitHub access token
        username: GitHub username to sync

    Returns:
        Dictionary with keys: created, updated, unchanged, failed (integers)
    """
    try:
        user_details = get_user_details(access_token, username)
    except Exception as e:
        logger.error(f"Failed to fetch user details for {username}: {e}")
        return {"created": 0, "updated": 0, "unchanged": 0, "failed": 1}

    github_id = str(user_details["id"])
    github_username = user_details["login"]
    display_name = user_details.get("name") or github_username
    email = user_details.get("email") or ""

    # Check if member exists by github_id
    try:
        member = TeamMember.objects.get(team=team, github_id=github_id)
        # Existing member - check if username changed
        if member.github_username != github_username:
            member.github_username = github_username
            member.save(update_fields=["github_username"])
            return {"created": 0, "updated": 1, "unchanged": 0, "failed": 0}
        else:
            return {"created": 0, "updated": 0, "unchanged": 1, "failed": 0}
    except TeamMember.DoesNotExist:
        # Create new member
        TeamMember.objects.create(
            team=team,
            github_id=github_id,
            github_username=github_username,
            display_name=display_name,
            email=email,
            is_active=True,
        )
        return {"created": 1, "updated": 0, "unchanged": 0, "failed": 0}
