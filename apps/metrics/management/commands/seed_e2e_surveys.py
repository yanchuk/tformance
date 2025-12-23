"""Seed test surveys for E2E testing.

This command creates surveys linked to the admin user (admin@example.com)
so E2E tests can exercise the full survey flow.

Usage:
    python manage.py seed_e2e_surveys

Creates:
    - TeamMember linked to admin@example.com if not exists
    - PRs authored by the admin TeamMember
    - Surveys with valid tokens for E2E testing
    - Reviewer surveys for testing reviewer flow
"""

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from apps.metrics.models import PRSurvey, PRSurveyReview, PullRequest, TeamMember
from apps.metrics.services.survey_tokens import set_survey_token
from apps.teams.models import Team


class Command(BaseCommand):
    help = "Seed test surveys for E2E testing"

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear",
            action="store_true",
            help="Clear existing E2E test surveys before seeding",
        )
        parser.add_argument(
            "--email",
            type=str,
            default="admin@example.com",
            help="Email of the test user to link surveys to",
        )

    def handle(self, *args, **options):
        email = options["email"]

        if options["clear"]:
            self.clear_e2e_surveys()

        team = self.get_or_create_team()
        admin_member = self.get_or_create_admin_member(team, email)
        reviewer_member = self.get_or_create_reviewer_member(team)

        # Create author survey (not yet responded)
        author_survey = self.create_author_survey(team, admin_member, responded=False)
        self.stdout.write(f"  Author survey token (pending): {author_survey.token}")

        # Create reviewer survey (where admin is a reviewer)
        reviewer_survey = self.create_reviewer_survey(team, admin_member, reviewer_member)
        self.stdout.write(f"  Reviewer survey token: {reviewer_survey.token}")

        # Print summary
        self.stdout.write(self.style.SUCCESS("\nE2E Test Surveys created:"))
        self.stdout.write(f"  Team: {team.slug}")
        self.stdout.write(f"  Admin member: {admin_member.display_name} ({admin_member.email})")
        self.stdout.write("\nSurvey URLs (add to http://localhost:8000):")
        self.stdout.write(f"  Author survey: /survey/{author_survey.token}/author/")
        self.stdout.write(f"  Reviewer survey: /survey/{reviewer_survey.token}/reviewer/")

    def clear_e2e_surveys(self):
        """Clear existing E2E test surveys."""
        # Delete surveys for PRs with test-pr-e2e title prefix
        test_prs = PullRequest.objects.filter(title__startswith="[E2E Test]")  # noqa: TEAM001
        count = test_prs.count()
        test_prs.delete()
        self.stdout.write(f"Cleared {count} E2E test PRs and surveys")

    def get_or_create_team(self):
        """Get or create the demo team."""
        team, created = Team.objects.get_or_create(
            slug="demo",
            defaults={"name": "Demo Team"},
        )
        if created:
            self.stdout.write(f"Created team: {team.name}")
        return team

    def get_or_create_admin_member(self, team, email):
        """Get or create TeamMember for admin user."""
        member, created = TeamMember.objects.get_or_create(
            team=team,
            email=email,
            defaults={
                "display_name": "Admin User",
                "github_username": "admin-e2e",
                "github_id": "e2e-admin-id",
            },
        )
        if created:
            self.stdout.write(f"Created TeamMember: {member.display_name}")
        return member

    def get_or_create_reviewer_member(self, team):
        """Get or create a reviewer TeamMember."""
        member, created = TeamMember.objects.get_or_create(
            team=team,
            email="reviewer@example.com",
            defaults={
                "display_name": "Test Reviewer",
                "github_username": "reviewer-e2e",
                "github_id": "e2e-reviewer-id",
            },
        )
        if created:
            self.stdout.write(f"Created reviewer TeamMember: {member.display_name}")
        return member

    def create_author_survey(self, team, author, responded=False):
        """Create a survey where the admin is the author."""
        # Create a PR authored by admin
        pr = PullRequest.objects.create(
            team=team,
            github_repo="test-org/e2e-test-repo",
            author=author,
            title="[E2E Test] Author Survey Test PR",
            github_pr_id=90001,
            state="merged",
            additions=50,
            deletions=20,
            pr_created_at=timezone.now() - timedelta(days=2),
            merged_at=timezone.now() - timedelta(days=1),
        )

        # Create survey
        survey = PRSurvey.objects.create(
            team=team,
            pull_request=pr,
            author=author,
            author_ai_assisted=True if responded else None,
            author_responded_at=timezone.now() if responded else None,
        )

        # Set valid token
        set_survey_token(survey, expiry_days=7)

        self.stdout.write(f"Created author survey for PR: {pr.title}")
        return survey

    def create_reviewer_survey(self, team, reviewer, author):
        """Create a survey where the admin is a reviewer."""
        # Create a PR authored by someone else (where admin can be reviewer)
        pr = PullRequest.objects.create(
            team=team,
            github_repo="test-org/e2e-test-repo",
            author=author,
            title="[E2E Test] Reviewer Survey Test PR",
            github_pr_id=90002,
            state="merged",
            additions=100,
            deletions=30,
            pr_created_at=timezone.now() - timedelta(days=3),
            merged_at=timezone.now() - timedelta(days=2),
        )

        # Create survey (author has responded so reviewer can see reveal)
        survey = PRSurvey.objects.create(
            team=team,
            pull_request=pr,
            author=author,
            author_ai_assisted=True,  # Author said yes to AI
            author_responded_at=timezone.now() - timedelta(days=1),
        )

        # Set valid token
        set_survey_token(survey, expiry_days=7)

        # Create PRSurveyReview entry for the reviewer (not yet responded)
        PRSurveyReview.objects.create(
            team=team,
            survey=survey,
            reviewer=reviewer,
            quality_rating=None,
            ai_guess=None,
            responded_at=None,
        )

        self.stdout.write(f"Created reviewer survey for PR: {pr.title}")
        return survey
