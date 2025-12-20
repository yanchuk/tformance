from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone as django_timezone

from apps.metrics.models import (
    AIUsageDaily,
    Commit,
    Deployment,
    JiraIssue,
    PRCheckRun,
    PRComment,
    PRFile,
    PRReview,
    PRSurvey,
    PRSurveyReview,
    PullRequest,
    TeamMember,
    WeeklyMetrics,
)
from apps.teams.context import current_team, get_current_team, set_current_team, unset_current_team
from apps.teams.models import Team


class TestTeamMemberModel(TestCase):
    """Tests for TeamMember model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team1 = Team.objects.create(name="Team One", slug="team-one")
        self.team2 = Team.objects.create(name="Team Two", slug="team-two")

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_team_member_creation_minimal_fields(self):
        """Test that TeamMember can be created with just display_name and team."""
        member = TeamMember.objects.create(team=self.team1, display_name="John Doe")
        self.assertEqual(member.display_name, "John Doe")
        self.assertEqual(member.team, self.team1)
        self.assertIsNotNone(member.pk)

    def test_team_member_creation_with_all_integration_fields(self):
        """Test that TeamMember can be created with all integration fields."""
        member = TeamMember.objects.create(
            team=self.team1,
            display_name="Jane Smith",
            email="jane@example.com",
            github_username="janesmith",
            github_id="12345",
            jira_account_id="jira-123",
            slack_user_id="U12345",
        )
        self.assertEqual(member.display_name, "Jane Smith")
        self.assertEqual(member.email, "jane@example.com")
        self.assertEqual(member.github_username, "janesmith")
        self.assertEqual(member.github_id, "12345")
        self.assertEqual(member.jira_account_id, "jira-123")
        self.assertEqual(member.slack_user_id, "U12345")

    def test_team_member_role_choices_developer(self):
        """Test that TeamMember role 'developer' works correctly."""
        member = TeamMember.objects.create(team=self.team1, display_name="Dev User", role="developer")
        self.assertEqual(member.role, "developer")

    def test_team_member_role_choices_lead(self):
        """Test that TeamMember role 'lead' works correctly."""
        member = TeamMember.objects.create(team=self.team1, display_name="Lead User", role="lead")
        self.assertEqual(member.role, "lead")

    def test_team_member_role_choices_admin(self):
        """Test that TeamMember role 'admin' works correctly."""
        member = TeamMember.objects.create(team=self.team1, display_name="Admin User", role="admin")
        self.assertEqual(member.role, "admin")

    def test_team_member_role_default_is_developer(self):
        """Test that TeamMember role defaults to 'developer'."""
        member = TeamMember.objects.create(team=self.team1, display_name="Default Role User")
        self.assertEqual(member.role, "developer")

    def test_team_member_is_active_default_is_true(self):
        """Test that TeamMember.is_active defaults to True."""
        member = TeamMember.objects.create(team=self.team1, display_name="Active User")
        self.assertTrue(member.is_active)

    def test_unique_constraint_team_github_id_enforced(self):
        """Test that unique constraint on (team, github_id) is enforced when github_id is not blank."""
        TeamMember.objects.create(team=self.team1, display_name="First User", github_id="github-123")
        # Attempt to create another member with the same github_id in the same team
        with self.assertRaises(IntegrityError):
            TeamMember.objects.create(team=self.team1, display_name="Second User", github_id="github-123")

    def test_unique_constraint_team_email_enforced(self):
        """Test that unique constraint on (team, email) is enforced when email is not blank."""
        TeamMember.objects.create(team=self.team1, display_name="First User", email="user@example.com")
        # Attempt to create another member with the same email in the same team
        with self.assertRaises(IntegrityError):
            TeamMember.objects.create(team=self.team1, display_name="Second User", email="user@example.com")

    def test_same_github_id_allowed_for_different_teams(self):
        """Test that same github_id is allowed for different teams."""
        member1 = TeamMember.objects.create(team=self.team1, display_name="User in Team 1", github_id="github-123")
        member2 = TeamMember.objects.create(team=self.team2, display_name="User in Team 2", github_id="github-123")
        self.assertEqual(member1.github_id, member2.github_id)
        self.assertNotEqual(member1.team, member2.team)

    def test_same_email_allowed_for_different_teams(self):
        """Test that same email is allowed for different teams."""
        member1 = TeamMember.objects.create(team=self.team1, display_name="User in Team 1", email="shared@example.com")
        member2 = TeamMember.objects.create(team=self.team2, display_name="User in Team 2", email="shared@example.com")
        self.assertEqual(member1.email, member2.email)
        self.assertNotEqual(member1.team, member2.team)

    def test_blank_github_id_allowed_multiple_times_per_team(self):
        """Test that blank github_id is allowed multiple times per team (no unique constraint)."""
        member1 = TeamMember.objects.create(team=self.team1, display_name="User Without GitHub 1", github_id="")
        member2 = TeamMember.objects.create(team=self.team1, display_name="User Without GitHub 2", github_id="")
        # Both should be created successfully
        self.assertEqual(member1.github_id, "")
        self.assertEqual(member2.github_id, "")
        self.assertEqual(member1.team, member2.team)

    def test_blank_email_allowed_multiple_times_per_team(self):
        """Test that blank email is allowed multiple times per team (no unique constraint)."""
        member1 = TeamMember.objects.create(team=self.team1, display_name="User Without Email 1", email="")
        member2 = TeamMember.objects.create(team=self.team1, display_name="User Without Email 2", email="")
        # Both should be created successfully
        self.assertEqual(member1.email, "")
        self.assertEqual(member2.email, "")
        self.assertEqual(member1.team, member2.team)

    def test_for_team_manager_filters_by_current_team(self):
        """Test that TeamMember.for_team manager filters by current team context."""
        # Create members for both teams
        member1 = TeamMember.objects.create(team=self.team1, display_name="Team 1 Member")
        member2 = TeamMember.objects.create(team=self.team2, display_name="Team 2 Member")

        # Set team1 as current and verify filtering
        set_current_team(self.team1)
        team1_members = list(TeamMember.for_team.all())
        self.assertEqual(len(team1_members), 1)
        self.assertEqual(team1_members[0].pk, member1.pk)

        # Set team2 as current and verify filtering
        set_current_team(self.team2)
        team2_members = list(TeamMember.for_team.all())
        self.assertEqual(len(team2_members), 1)
        self.assertEqual(team2_members[0].pk, member2.pk)

    def test_for_team_manager_with_context_manager(self):
        """Test that TeamMember.for_team works with context manager."""
        # Create members for both teams
        TeamMember.objects.create(team=self.team1, display_name="Team 1 Member")
        TeamMember.objects.create(team=self.team2, display_name="Team 2 Member")

        with current_team(self.team1):
            self.assertEqual(TeamMember.for_team.count(), 1)

        with current_team(self.team2):
            self.assertEqual(TeamMember.for_team.count(), 1)

    def test_for_team_manager_returns_empty_when_no_team_set(self):
        """Test that TeamMember.for_team returns empty queryset when no team is set."""
        TeamMember.objects.create(team=self.team1, display_name="Team 1 Member")

        unset_current_team()
        self.assertIsNone(get_current_team())
        self.assertEqual(TeamMember.for_team.count(), 0)

    def test_team_member_str_returns_display_name(self):
        """Test that TeamMember.__str__ returns display_name."""
        member = TeamMember.objects.create(team=self.team1, display_name="John Doe")
        self.assertEqual(str(member), "John Doe")

    def test_team_member_has_created_at_from_base_model(self):
        """Test that TeamMember inherits created_at from BaseModel."""
        member = TeamMember.objects.create(team=self.team1, display_name="Test User")
        self.assertIsNotNone(member.created_at)

    def test_team_member_has_updated_at_from_base_model(self):
        """Test that TeamMember inherits updated_at from BaseModel."""
        member = TeamMember.objects.create(team=self.team1, display_name="Test User")
        self.assertIsNotNone(member.updated_at)

    def test_team_member_has_team_foreign_key_from_base_team_model(self):
        """Test that TeamMember has team ForeignKey from BaseTeamModel."""
        member = TeamMember.objects.create(team=self.team1, display_name="Test User")
        self.assertEqual(member.team, self.team1)
        self.assertIsInstance(member.team, Team)

    def test_team_member_updated_at_changes_on_save(self):
        """Test that updated_at timestamp changes when model is saved."""
        member = TeamMember.objects.create(team=self.team1, display_name="Test User")
        original_updated_at = member.updated_at

        # Update and save
        member.display_name = "Updated Name"
        member.save()

        # Refresh from database
        member.refresh_from_db()
        self.assertGreater(member.updated_at, original_updated_at)


class TestPullRequestModel(TestCase):
    """Tests for PullRequest model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team1 = Team.objects.create(name="Team One", slug="team-one")
        self.team2 = Team.objects.create(name="Team Two", slug="team-two")
        self.author = TeamMember.objects.create(team=self.team1, display_name="John Doe", github_username="johndoe")

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_pull_request_creation_with_required_fields(self):
        """Test that PullRequest can be created with just required fields."""
        pr = PullRequest.objects.create(team=self.team1, github_pr_id=123, github_repo="org/repo", state="open")
        self.assertEqual(pr.github_pr_id, 123)
        self.assertEqual(pr.github_repo, "org/repo")
        self.assertEqual(pr.state, "open")
        self.assertEqual(pr.team, self.team1)
        self.assertIsNotNone(pr.pk)

    def test_pull_request_creation_with_all_fields(self):
        """Test that PullRequest can be created with all fields including author FK."""
        pr_created = django_timezone.now()
        merged = django_timezone.now()
        first_review = django_timezone.now()

        pr = PullRequest.objects.create(
            team=self.team1,
            github_pr_id=456,
            github_repo="org/repo",
            title="Add new feature",
            author=self.author,
            state="merged",
            pr_created_at=pr_created,
            merged_at=merged,
            first_review_at=first_review,
            cycle_time_hours=Decimal("24.50"),
            review_time_hours=Decimal("3.25"),
            additions=150,
            deletions=50,
            is_revert=True,
            is_hotfix=True,
        )
        self.assertEqual(pr.github_pr_id, 456)
        self.assertEqual(pr.title, "Add new feature")
        self.assertEqual(pr.author, self.author)
        self.assertEqual(pr.state, "merged")
        self.assertEqual(pr.pr_created_at, pr_created)
        self.assertEqual(pr.merged_at, merged)
        self.assertEqual(pr.first_review_at, first_review)
        self.assertEqual(pr.cycle_time_hours, Decimal("24.50"))
        self.assertEqual(pr.review_time_hours, Decimal("3.25"))
        self.assertEqual(pr.additions, 150)
        self.assertEqual(pr.deletions, 50)
        self.assertTrue(pr.is_revert)
        self.assertTrue(pr.is_hotfix)

    def test_pull_request_state_choice_open(self):
        """Test that PullRequest state 'open' works correctly."""
        pr = PullRequest.objects.create(team=self.team1, github_pr_id=1, github_repo="org/repo", state="open")
        self.assertEqual(pr.state, "open")

    def test_pull_request_state_choice_merged(self):
        """Test that PullRequest state 'merged' works correctly."""
        pr = PullRequest.objects.create(team=self.team1, github_pr_id=2, github_repo="org/repo", state="merged")
        self.assertEqual(pr.state, "merged")

    def test_pull_request_state_choice_closed(self):
        """Test that PullRequest state 'closed' works correctly."""
        pr = PullRequest.objects.create(team=self.team1, github_pr_id=3, github_repo="org/repo", state="closed")
        self.assertEqual(pr.state, "closed")

    def test_unique_constraint_team_pr_id_repo_enforced(self):
        """Test that unique constraint on (team, github_pr_id, github_repo) is enforced."""
        PullRequest.objects.create(team=self.team1, github_pr_id=100, github_repo="org/repo", state="open")
        # Attempt to create another PR with same team, pr_id, and repo
        with self.assertRaises(IntegrityError):
            PullRequest.objects.create(team=self.team1, github_pr_id=100, github_repo="org/repo", state="open")

    def test_same_pr_id_allowed_for_different_repos(self):
        """Test that same PR ID is allowed for different repos in same team."""
        pr1 = PullRequest.objects.create(team=self.team1, github_pr_id=100, github_repo="org/repo1", state="open")
        pr2 = PullRequest.objects.create(team=self.team1, github_pr_id=100, github_repo="org/repo2", state="open")
        self.assertEqual(pr1.github_pr_id, pr2.github_pr_id)
        self.assertNotEqual(pr1.github_repo, pr2.github_repo)

    def test_same_pr_id_and_repo_allowed_for_different_teams(self):
        """Test that same PR ID and repo is allowed for different teams."""
        pr1 = PullRequest.objects.create(team=self.team1, github_pr_id=100, github_repo="org/repo", state="open")
        pr2 = PullRequest.objects.create(team=self.team2, github_pr_id=100, github_repo="org/repo", state="open")
        self.assertEqual(pr1.github_pr_id, pr2.github_pr_id)
        self.assertEqual(pr1.github_repo, pr2.github_repo)
        self.assertNotEqual(pr1.team, pr2.team)

    def test_pull_request_default_additions_is_zero(self):
        """Test that PullRequest.additions defaults to 0."""
        pr = PullRequest.objects.create(team=self.team1, github_pr_id=200, github_repo="org/repo", state="open")
        self.assertEqual(pr.additions, 0)

    def test_pull_request_default_deletions_is_zero(self):
        """Test that PullRequest.deletions defaults to 0."""
        pr = PullRequest.objects.create(team=self.team1, github_pr_id=201, github_repo="org/repo", state="open")
        self.assertEqual(pr.deletions, 0)

    def test_pull_request_default_is_revert_is_false(self):
        """Test that PullRequest.is_revert defaults to False."""
        pr = PullRequest.objects.create(team=self.team1, github_pr_id=202, github_repo="org/repo", state="open")
        self.assertFalse(pr.is_revert)

    def test_pull_request_default_is_hotfix_is_false(self):
        """Test that PullRequest.is_hotfix defaults to False."""
        pr = PullRequest.objects.create(team=self.team1, github_pr_id=203, github_repo="org/repo", state="open")
        self.assertFalse(pr.is_hotfix)

    def test_pull_request_author_fk_with_set_null(self):
        """Test that PullRequest.author FK uses SET_NULL when TeamMember is deleted."""
        pr = PullRequest.objects.create(
            team=self.team1, github_pr_id=300, github_repo="org/repo", state="open", author=self.author
        )
        self.assertEqual(pr.author, self.author)

        # Delete the author
        self.author.delete()

        # Refresh PR from database
        pr.refresh_from_db()
        self.assertIsNone(pr.author)

    def test_pull_request_synced_at_auto_updates_on_save(self):
        """Test that PullRequest.synced_at auto-updates when model is saved."""
        pr = PullRequest.objects.create(team=self.team1, github_pr_id=400, github_repo="org/repo", state="open")
        original_synced_at = pr.synced_at
        self.assertIsNotNone(original_synced_at)

        # Update and save
        pr.state = "merged"
        pr.save()

        # Refresh from database
        pr.refresh_from_db()
        self.assertGreaterEqual(pr.synced_at, original_synced_at)

    def test_pull_request_str_returns_useful_representation(self):
        """Test that PullRequest.__str__ returns a useful representation."""
        pr = PullRequest.objects.create(
            team=self.team1, github_pr_id=500, github_repo="org/repo", title="Fix bug", state="open"
        )
        str_repr = str(pr)
        # Should contain key identifying information
        self.assertIn("org/repo", str_repr)
        self.assertIn("500", str_repr)

    def test_pull_request_has_created_at_from_base_model(self):
        """Test that PullRequest inherits created_at from BaseModel."""
        pr = PullRequest.objects.create(team=self.team1, github_pr_id=600, github_repo="org/repo", state="open")
        self.assertIsNotNone(pr.created_at)

    def test_pull_request_has_updated_at_from_base_model(self):
        """Test that PullRequest inherits updated_at from BaseModel."""
        pr = PullRequest.objects.create(team=self.team1, github_pr_id=601, github_repo="org/repo", state="open")
        self.assertIsNotNone(pr.updated_at)

    def test_pull_request_for_team_manager_filters_by_current_team(self):
        """Test that PullRequest.for_team manager filters by current team context."""
        # Create PRs for both teams
        pr1 = PullRequest.objects.create(team=self.team1, github_pr_id=700, github_repo="org/repo", state="open")
        pr2 = PullRequest.objects.create(team=self.team2, github_pr_id=701, github_repo="org/repo", state="open")

        # Set team1 as current and verify filtering
        set_current_team(self.team1)
        team1_prs = list(PullRequest.for_team.all())
        self.assertEqual(len(team1_prs), 1)
        self.assertEqual(team1_prs[0].pk, pr1.pk)

        # Set team2 as current and verify filtering
        set_current_team(self.team2)
        team2_prs = list(PullRequest.for_team.all())
        self.assertEqual(len(team2_prs), 1)
        self.assertEqual(team2_prs[0].pk, pr2.pk)

    def test_pull_request_for_team_manager_with_context_manager(self):
        """Test that PullRequest.for_team works with context manager."""
        # Create PRs for both teams
        PullRequest.objects.create(team=self.team1, github_pr_id=800, github_repo="org/repo", state="open")
        PullRequest.objects.create(team=self.team2, github_pr_id=801, github_repo="org/repo", state="open")

        with current_team(self.team1):
            self.assertEqual(PullRequest.for_team.count(), 1)

        with current_team(self.team2):
            self.assertEqual(PullRequest.for_team.count(), 1)

    def test_pull_request_for_team_manager_returns_empty_when_no_team_set(self):
        """Test that PullRequest.for_team returns empty queryset when no team is set."""
        PullRequest.objects.create(team=self.team1, github_pr_id=900, github_repo="org/repo", state="open")

        unset_current_team()
        self.assertIsNone(get_current_team())
        self.assertEqual(PullRequest.for_team.count(), 0)

    def test_pull_request_creation_with_jira_key(self):
        """Test that PullRequest can be created with a jira_key."""
        pr = PullRequest.objects.create(
            team=self.team1,
            github_pr_id=1001,
            github_repo="org/repo",
            state="open",
            jira_key="PROJ-123",
        )
        self.assertEqual(pr.jira_key, "PROJ-123")
        self.assertIsNotNone(pr.pk)

    def test_pull_request_jira_key_defaults_to_empty_string(self):
        """Test that PullRequest.jira_key defaults to empty string when not provided."""
        pr = PullRequest.objects.create(
            team=self.team1,
            github_pr_id=1002,
            github_repo="org/repo",
            state="open",
        )
        self.assertEqual(pr.jira_key, "")

    def test_pull_request_jira_key_can_be_filtered(self):
        """Test that PullRequest objects can be filtered by jira_key."""
        # Create PRs with different jira_keys
        pr1 = PullRequest.objects.create(
            team=self.team1,
            github_pr_id=1003,
            github_repo="org/repo",
            state="open",
            jira_key="PROJ-100",
        )
        PullRequest.objects.create(
            team=self.team1,
            github_pr_id=1004,
            github_repo="org/repo",
            state="open",
            jira_key="PROJ-101",
        )
        pr3 = PullRequest.objects.create(
            team=self.team1,
            github_pr_id=1005,
            github_repo="org/repo",
            state="open",
            jira_key="",
        )

        # Filter by specific jira_key
        proj_100_prs = PullRequest.objects.filter(jira_key="PROJ-100")
        self.assertEqual(proj_100_prs.count(), 1)
        self.assertEqual(proj_100_prs.first().pk, pr1.pk)

        # Filter by empty jira_key
        no_jira_prs = PullRequest.objects.filter(jira_key="")
        self.assertEqual(no_jira_prs.count(), 1)
        self.assertEqual(no_jira_prs.first().pk, pr3.pk)

    def test_pull_request_jira_key_max_length(self):
        """Test that PullRequest.jira_key respects max_length of 50."""
        # Create a jira_key exactly 50 characters long
        long_jira_key = "PROJ-" + "1" * 45  # Total 50 chars
        pr = PullRequest.objects.create(
            team=self.team1,
            github_pr_id=1006,
            github_repo="org/repo",
            state="open",
            jira_key=long_jira_key,
        )
        self.assertEqual(len(pr.jira_key), 50)
        self.assertEqual(pr.jira_key, long_jira_key)


class TestPullRequestIterationFields(TestCase):
    """Tests for PullRequest iteration metric fields."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.metrics.factories import TeamFactory, TeamMemberFactory

        self.team = TeamFactory()
        self.author = TeamMemberFactory(team=self.team)

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_pull_request_iteration_fields_exist(self):
        """Test that all 4 new iteration metric fields exist and can be set."""
        from apps.metrics.factories import PullRequestFactory

        pr = PullRequestFactory(
            team=self.team,
            author=self.author,
            review_rounds=3,
            avg_fix_response_hours=Decimal("4.50"),
            commits_after_first_review=5,
            total_comments=12,
        )

        self.assertEqual(pr.review_rounds, 3)
        self.assertEqual(pr.avg_fix_response_hours, Decimal("4.50"))
        self.assertEqual(pr.commits_after_first_review, 5)
        self.assertEqual(pr.total_comments, 12)

    def test_pull_request_iteration_fields_nullable(self):
        """Test that all iteration fields accept None values."""
        from apps.metrics.factories import PullRequestFactory

        pr = PullRequestFactory(
            team=self.team,
            author=self.author,
            review_rounds=None,
            avg_fix_response_hours=None,
            commits_after_first_review=None,
            total_comments=None,
        )

        self.assertIsNone(pr.review_rounds)
        self.assertIsNone(pr.avg_fix_response_hours)
        self.assertIsNone(pr.commits_after_first_review)
        self.assertIsNone(pr.total_comments)


class TestPRReviewModel(TestCase):
    """Tests for PRReview model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = Team.objects.create(name="Test Team", slug="test-team")
        self.author = TeamMember.objects.create(team=self.team, display_name="Author", github_username="author")
        self.reviewer = TeamMember.objects.create(team=self.team, display_name="Reviewer", github_username="reviewer")
        self.pull_request = PullRequest.objects.create(
            team=self.team, github_pr_id=1, github_repo="org/repo", state="open", author=self.author
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_pr_review_creation_linked_to_pull_request(self):
        """Test that PRReview can be created linked to a PullRequest."""
        review = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        self.assertEqual(review.pull_request, self.pull_request)
        self.assertEqual(review.reviewer, self.reviewer)
        self.assertEqual(review.state, "approved")
        self.assertIsNotNone(review.pk)

    def test_pr_review_state_choice_approved(self):
        """Test that PRReview state 'approved' works correctly."""
        review = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        self.assertEqual(review.state, "approved")

    def test_pr_review_state_choice_changes_requested(self):
        """Test that PRReview state 'changes_requested' works correctly."""
        review = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="changes_requested"
        )
        self.assertEqual(review.state, "changes_requested")

    def test_pr_review_state_choice_commented(self):
        """Test that PRReview state 'commented' works correctly."""
        review = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="commented"
        )
        self.assertEqual(review.state, "commented")

    def test_pr_review_cascade_delete_when_pull_request_deleted(self):
        """Test that PRReview is cascade deleted when PullRequest is deleted."""
        review = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        review_id = review.pk

        # Delete the pull request
        self.pull_request.delete()

        # Verify review is also deleted
        with self.assertRaises(PRReview.DoesNotExist):
            PRReview.objects.get(pk=review_id)

    def test_pr_review_reviewer_fk_with_set_null(self):
        """Test that PRReview.reviewer FK uses SET_NULL when TeamMember is deleted."""
        review = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        self.assertEqual(review.reviewer, self.reviewer)

        # Delete the reviewer
        self.reviewer.delete()

        # Refresh review from database
        review.refresh_from_db()
        self.assertIsNone(review.reviewer)

    def test_pr_review_submitted_at_can_be_set(self):
        """Test that PRReview.submitted_at can be set."""
        submitted = django_timezone.now()
        review = PRReview.objects.create(
            team=self.team,
            pull_request=self.pull_request,
            reviewer=self.reviewer,
            state="approved",
            submitted_at=submitted,
        )
        self.assertEqual(review.submitted_at, submitted)

    def test_pr_review_str_returns_useful_representation(self):
        """Test that PRReview.__str__ returns a useful representation."""
        review = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        str_repr = str(review)
        # Should contain key identifying information
        self.assertIsNotNone(str_repr)
        self.assertIsInstance(str_repr, str)

    def test_pr_review_has_created_at_from_base_model(self):
        """Test that PRReview inherits created_at from BaseModel."""
        review = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        self.assertIsNotNone(review.created_at)

    def test_pr_review_has_updated_at_from_base_model(self):
        """Test that PRReview inherits updated_at from BaseModel."""
        review = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        self.assertIsNotNone(review.updated_at)

    def test_pr_review_for_team_manager_filters_by_current_team(self):
        """Test that PRReview.for_team manager filters by current team context."""
        # Create another team and related objects
        team2 = Team.objects.create(name="Team Two", slug="team-two")
        author2 = TeamMember.objects.create(team=team2, display_name="Author 2", github_username="author2")
        reviewer2 = TeamMember.objects.create(team=team2, display_name="Reviewer 2", github_username="reviewer2")
        pr2 = PullRequest.objects.create(
            team=team2, github_pr_id=2, github_repo="org/repo", state="open", author=author2
        )

        # Create reviews for both teams
        review1 = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        review2 = PRReview.objects.create(team=team2, pull_request=pr2, reviewer=reviewer2, state="approved")

        # Set team1 as current and verify filtering
        set_current_team(self.team)
        team1_reviews = list(PRReview.for_team.all())
        self.assertEqual(len(team1_reviews), 1)
        self.assertEqual(team1_reviews[0].pk, review1.pk)

        # Set team2 as current and verify filtering
        set_current_team(team2)
        team2_reviews = list(PRReview.for_team.all())
        self.assertEqual(len(team2_reviews), 1)
        self.assertEqual(team2_reviews[0].pk, review2.pk)

    def test_pr_review_for_team_manager_with_context_manager(self):
        """Test that PRReview.for_team works with context manager."""
        # Create another team and related objects
        team2 = Team.objects.create(name="Team Two", slug="team-two")
        author2 = TeamMember.objects.create(team=team2, display_name="Author 2", github_username="author2")
        reviewer2 = TeamMember.objects.create(team=team2, display_name="Reviewer 2", github_username="reviewer2")
        pr2 = PullRequest.objects.create(
            team=team2, github_pr_id=3, github_repo="org/repo", state="open", author=author2
        )

        # Create reviews for both teams
        PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        PRReview.objects.create(team=team2, pull_request=pr2, reviewer=reviewer2, state="approved")

        with current_team(self.team):
            self.assertEqual(PRReview.for_team.count(), 1)

        with current_team(team2):
            self.assertEqual(PRReview.for_team.count(), 1)

    def test_pr_review_for_team_manager_returns_empty_when_no_team_set(self):
        """Test that PRReview.for_team returns empty queryset when no team is set."""
        PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )

        unset_current_team()
        self.assertIsNone(get_current_team())
        self.assertEqual(PRReview.for_team.count(), 0)

    def test_pr_review_multiple_reviews_on_same_pr(self):
        """Test that multiple reviews can be created for the same pull request."""
        reviewer2 = TeamMember.objects.create(team=self.team, display_name="Reviewer 2", github_username="reviewer2")

        review1 = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=self.reviewer, state="approved"
        )
        review2 = PRReview.objects.create(
            team=self.team, pull_request=self.pull_request, reviewer=reviewer2, state="changes_requested"
        )

        # Both reviews should exist for the same PR
        self.assertEqual(review1.pull_request, review2.pull_request)
        self.assertNotEqual(review1.reviewer, review2.reviewer)
        self.assertEqual(self.pull_request.reviews.count(), 2)


class TestCommitModel(TestCase):
    """Tests for Commit model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team1 = Team.objects.create(name="Team One", slug="team-one")
        self.team2 = Team.objects.create(name="Team Two", slug="team-two")
        self.author = TeamMember.objects.create(team=self.team1, display_name="Alice", github_username="alice")
        self.pull_request = PullRequest.objects.create(
            team=self.team1, github_pr_id=1, github_repo="org/repo", state="open"
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_commit_creation_with_required_fields(self):
        """Test that Commit can be created with required fields."""
        commit = Commit.objects.create(team=self.team1, github_sha="abc123def456", github_repo="org/repo")
        self.assertEqual(commit.github_sha, "abc123def456")
        self.assertEqual(commit.github_repo, "org/repo")
        self.assertEqual(commit.team, self.team1)
        self.assertIsNotNone(commit.pk)

    def test_commit_creation_with_all_fields(self):
        """Test that Commit can be created with all fields."""
        committed = django_timezone.now()
        commit = Commit.objects.create(
            team=self.team1,
            github_sha="def789ghi012",
            github_repo="org/repo",
            author=self.author,
            message="Fix critical bug",
            additions=100,
            deletions=20,
            committed_at=committed,
            pull_request=self.pull_request,
        )
        self.assertEqual(commit.github_sha, "def789ghi012")
        self.assertEqual(commit.github_repo, "org/repo")
        self.assertEqual(commit.author, self.author)
        self.assertEqual(commit.message, "Fix critical bug")
        self.assertEqual(commit.additions, 100)
        self.assertEqual(commit.deletions, 20)
        self.assertEqual(commit.committed_at, committed)
        self.assertEqual(commit.pull_request, self.pull_request)

    def test_unique_constraint_team_sha_enforced(self):
        """Test that unique constraint on (team, github_sha) is enforced."""
        Commit.objects.create(team=self.team1, github_sha="unique123", github_repo="org/repo")
        # Attempt to create another commit with same team and sha
        with self.assertRaises(IntegrityError):
            Commit.objects.create(team=self.team1, github_sha="unique123", github_repo="org/repo2")

    def test_same_sha_allowed_for_different_teams(self):
        """Test that same SHA is allowed for different teams."""
        commit1 = Commit.objects.create(team=self.team1, github_sha="shared456", github_repo="org/repo")
        commit2 = Commit.objects.create(team=self.team2, github_sha="shared456", github_repo="org/repo")
        self.assertEqual(commit1.github_sha, commit2.github_sha)
        self.assertNotEqual(commit1.team, commit2.team)

    def test_commit_optional_pull_request_fk(self):
        """Test that Commit.pull_request FK is optional (null=True, blank=True)."""
        commit = Commit.objects.create(team=self.team1, github_sha="noPR789", github_repo="org/repo")
        self.assertIsNone(commit.pull_request)

    def test_commit_pull_request_fk_with_set_null(self):
        """Test that Commit.pull_request FK uses SET_NULL when PullRequest is deleted."""
        commit = Commit.objects.create(
            team=self.team1, github_sha="withPR123", github_repo="org/repo", pull_request=self.pull_request
        )
        self.assertEqual(commit.pull_request, self.pull_request)

        # Delete the pull request
        self.pull_request.delete()

        # Refresh commit from database
        commit.refresh_from_db()
        self.assertIsNone(commit.pull_request)

    def test_commit_author_fk_with_set_null(self):
        """Test that Commit.author FK uses SET_NULL when TeamMember is deleted."""
        commit = Commit.objects.create(
            team=self.team1, github_sha="authorTest456", github_repo="org/repo", author=self.author
        )
        self.assertEqual(commit.author, self.author)

        # Delete the author
        self.author.delete()

        # Refresh commit from database
        commit.refresh_from_db()
        self.assertIsNone(commit.author)

    def test_commit_default_additions_is_zero(self):
        """Test that Commit.additions defaults to 0."""
        commit = Commit.objects.create(team=self.team1, github_sha="defaultAdd789", github_repo="org/repo")
        self.assertEqual(commit.additions, 0)

    def test_commit_default_deletions_is_zero(self):
        """Test that Commit.deletions defaults to 0."""
        commit = Commit.objects.create(team=self.team1, github_sha="defaultDel012", github_repo="org/repo")
        self.assertEqual(commit.deletions, 0)

    def test_commit_str_returns_useful_representation(self):
        """Test that Commit.__str__ returns a useful representation."""
        commit = Commit.objects.create(
            team=self.team1, github_sha="abc123def456ghi789", github_repo="org/repo", message="Initial commit"
        )
        str_repr = str(commit)
        # Should contain key identifying information (likely SHA or first part of it)
        self.assertIsNotNone(str_repr)
        self.assertIsInstance(str_repr, str)

    def test_commit_has_created_at_from_base_model(self):
        """Test that Commit inherits created_at from BaseModel."""
        commit = Commit.objects.create(team=self.team1, github_sha="created345", github_repo="org/repo")
        self.assertIsNotNone(commit.created_at)

    def test_commit_has_updated_at_from_base_model(self):
        """Test that Commit inherits updated_at from BaseModel."""
        commit = Commit.objects.create(team=self.team1, github_sha="updated678", github_repo="org/repo")
        self.assertIsNotNone(commit.updated_at)

    def test_commit_for_team_manager_filters_by_current_team(self):
        """Test that Commit.for_team manager filters by current team context."""
        # Create commits for both teams
        commit1 = Commit.objects.create(team=self.team1, github_sha="team1commit1", github_repo="org/repo")
        commit2 = Commit.objects.create(team=self.team2, github_sha="team2commit1", github_repo="org/repo")

        # Set team1 as current and verify filtering
        set_current_team(self.team1)
        team1_commits = list(Commit.for_team.all())
        self.assertEqual(len(team1_commits), 1)
        self.assertEqual(team1_commits[0].pk, commit1.pk)

        # Set team2 as current and verify filtering
        set_current_team(self.team2)
        team2_commits = list(Commit.for_team.all())
        self.assertEqual(len(team2_commits), 1)
        self.assertEqual(team2_commits[0].pk, commit2.pk)

    def test_commit_for_team_manager_with_context_manager(self):
        """Test that Commit.for_team works with context manager."""
        # Create commits for both teams
        Commit.objects.create(team=self.team1, github_sha="contextcommit1", github_repo="org/repo")
        Commit.objects.create(team=self.team2, github_sha="contextcommit2", github_repo="org/repo")

        with current_team(self.team1):
            self.assertEqual(Commit.for_team.count(), 1)

        with current_team(self.team2):
            self.assertEqual(Commit.for_team.count(), 1)

    def test_commit_for_team_manager_returns_empty_when_no_team_set(self):
        """Test that Commit.for_team returns empty queryset when no team is set."""
        Commit.objects.create(team=self.team1, github_sha="nocontextcommit", github_repo="org/repo")

        unset_current_team()
        self.assertIsNone(get_current_team())
        self.assertEqual(Commit.for_team.count(), 0)


class TestJiraIssueModel(TestCase):
    """Tests for JiraIssue model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team1 = Team.objects.create(name="Team One", slug="team-one")
        self.team2 = Team.objects.create(name="Team Two", slug="team-two")
        self.assignee = TeamMember.objects.create(
            team=self.team1, display_name="Alice Developer", jira_account_id="alice-jira-123"
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_jira_issue_creation_with_required_fields(self):
        """Test that JiraIssue can be created with required fields (jira_key, jira_id, team)."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-123", jira_id="10001")
        self.assertEqual(issue.jira_key, "PROJ-123")
        self.assertEqual(issue.jira_id, "10001")
        self.assertEqual(issue.team, self.team1)
        self.assertIsNotNone(issue.pk)

    def test_jira_issue_creation_with_all_fields(self):
        """Test that JiraIssue can be created with all fields."""
        created = django_timezone.now()
        resolved = django_timezone.now()

        issue = JiraIssue.objects.create(
            team=self.team1,
            jira_key="PROJ-456",
            jira_id="10002",
            summary="Implement new feature",
            issue_type="Story",
            status="Done",
            assignee=self.assignee,
            story_points=Decimal("5.0"),
            sprint_id="sprint-100",
            sprint_name="Sprint 10",
            issue_created_at=created,
            resolved_at=resolved,
            cycle_time_hours=Decimal("72.50"),
        )
        self.assertEqual(issue.jira_key, "PROJ-456")
        self.assertEqual(issue.jira_id, "10002")
        self.assertEqual(issue.summary, "Implement new feature")
        self.assertEqual(issue.issue_type, "Story")
        self.assertEqual(issue.status, "Done")
        self.assertEqual(issue.assignee, self.assignee)
        self.assertEqual(issue.story_points, Decimal("5.0"))
        self.assertEqual(issue.sprint_id, "sprint-100")
        self.assertEqual(issue.sprint_name, "Sprint 10")
        self.assertEqual(issue.issue_created_at, created)
        self.assertEqual(issue.resolved_at, resolved)
        self.assertEqual(issue.cycle_time_hours, Decimal("72.50"))

    def test_unique_constraint_team_jira_id_enforced(self):
        """Test that unique constraint on (team, jira_id) is enforced."""
        JiraIssue.objects.create(team=self.team1, jira_key="PROJ-100", jira_id="unique-jira-1")
        # Attempt to create another issue with same team and jira_id
        with self.assertRaises(IntegrityError):
            JiraIssue.objects.create(team=self.team1, jira_key="PROJ-101", jira_id="unique-jira-1")

    def test_same_jira_id_allowed_for_different_teams(self):
        """Test that same jira_id is allowed for different teams."""
        issue1 = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-200", jira_id="shared-jira-1")
        issue2 = JiraIssue.objects.create(team=self.team2, jira_key="PROJ-200", jira_id="shared-jira-1")
        self.assertEqual(issue1.jira_id, issue2.jira_id)
        self.assertNotEqual(issue1.team, issue2.team)

    def test_jira_issue_assignee_fk_with_set_null(self):
        """Test that JiraIssue.assignee FK uses SET_NULL when TeamMember is deleted."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-300", jira_id="10003", assignee=self.assignee)
        self.assertEqual(issue.assignee, self.assignee)

        # Delete the assignee
        self.assignee.delete()

        # Refresh issue from database
        issue.refresh_from_db()
        self.assertIsNone(issue.assignee)

    def test_jira_issue_assignee_can_be_null(self):
        """Test that JiraIssue.assignee can be null (unassigned)."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-301", jira_id="10004")
        self.assertIsNone(issue.assignee)

    def test_jira_issue_story_points_can_be_decimal(self):
        """Test that JiraIssue.story_points can be decimal values (0.5, 1.5, 3.0, etc.)."""
        issue_half = JiraIssue.objects.create(
            team=self.team1, jira_key="PROJ-400", jira_id="10005", story_points=Decimal("0.5")
        )
        self.assertEqual(issue_half.story_points, Decimal("0.5"))

        issue_one_half = JiraIssue.objects.create(
            team=self.team1, jira_key="PROJ-401", jira_id="10006", story_points=Decimal("1.5")
        )
        self.assertEqual(issue_one_half.story_points, Decimal("1.5"))

        issue_three = JiraIssue.objects.create(
            team=self.team1, jira_key="PROJ-402", jira_id="10007", story_points=Decimal("3.0")
        )
        self.assertEqual(issue_three.story_points, Decimal("3.0"))

    def test_jira_issue_story_points_can_be_null(self):
        """Test that JiraIssue.story_points can be null (not estimated)."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-403", jira_id="10008")
        self.assertIsNone(issue.story_points)

    def test_jira_issue_synced_at_auto_updates_on_save(self):
        """Test that JiraIssue.synced_at auto-updates when model is saved."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-500", jira_id="10009")
        original_synced_at = issue.synced_at
        self.assertIsNotNone(original_synced_at)

        # Update and save
        issue.status = "In Progress"
        issue.save()

        # Refresh from database
        issue.refresh_from_db()
        self.assertGreaterEqual(issue.synced_at, original_synced_at)

    def test_jira_issue_for_team_manager_filters_by_current_team(self):
        """Test that JiraIssue.for_team manager filters by current team context."""
        # Create issues for both teams
        issue1 = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-600", jira_id="10010")
        issue2 = JiraIssue.objects.create(team=self.team2, jira_key="PROJ-601", jira_id="10011")

        # Set team1 as current and verify filtering
        set_current_team(self.team1)
        team1_issues = list(JiraIssue.for_team.all())
        self.assertEqual(len(team1_issues), 1)
        self.assertEqual(team1_issues[0].pk, issue1.pk)

        # Set team2 as current and verify filtering
        set_current_team(self.team2)
        team2_issues = list(JiraIssue.for_team.all())
        self.assertEqual(len(team2_issues), 1)
        self.assertEqual(team2_issues[0].pk, issue2.pk)

    def test_jira_issue_for_team_manager_with_context_manager(self):
        """Test that JiraIssue.for_team works with context manager."""
        # Create issues for both teams
        JiraIssue.objects.create(team=self.team1, jira_key="PROJ-700", jira_id="10012")
        JiraIssue.objects.create(team=self.team2, jira_key="PROJ-701", jira_id="10013")

        with current_team(self.team1):
            self.assertEqual(JiraIssue.for_team.count(), 1)

        with current_team(self.team2):
            self.assertEqual(JiraIssue.for_team.count(), 1)

    def test_jira_issue_for_team_manager_returns_empty_when_no_team_set(self):
        """Test that JiraIssue.for_team returns empty queryset when no team is set."""
        JiraIssue.objects.create(team=self.team1, jira_key="PROJ-800", jira_id="10014")

        unset_current_team()
        self.assertIsNone(get_current_team())
        self.assertEqual(JiraIssue.for_team.count(), 0)

    def test_jira_issue_str_returns_jira_key(self):
        """Test that JiraIssue.__str__ returns jira_key."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-900", jira_id="10015")
        self.assertEqual(str(issue), "PROJ-900")

    def test_jira_issue_has_created_at_from_base_model(self):
        """Test that JiraIssue inherits created_at from BaseModel."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1000", jira_id="10016")
        self.assertIsNotNone(issue.created_at)

    def test_jira_issue_has_updated_at_from_base_model(self):
        """Test that JiraIssue inherits updated_at from BaseModel."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1001", jira_id="10017")
        self.assertIsNotNone(issue.updated_at)

    def test_jira_issue_updated_at_changes_on_save(self):
        """Test that updated_at timestamp changes when JiraIssue is saved."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1002", jira_id="10018")
        original_updated_at = issue.updated_at

        # Update and save
        issue.summary = "Updated summary"
        issue.save()

        # Refresh from database
        issue.refresh_from_db()
        self.assertGreater(issue.updated_at, original_updated_at)

    def test_jira_issue_has_team_foreign_key_from_base_team_model(self):
        """Test that JiraIssue has team ForeignKey from BaseTeamModel."""
        issue = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1003", jira_id="10019")
        self.assertEqual(issue.team, self.team1)
        self.assertIsInstance(issue.team, Team)

    def test_jira_issue_issue_type_choices(self):
        """Test that JiraIssue.issue_type can store different issue types."""
        story = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1100", jira_id="10020", issue_type="Story")
        self.assertEqual(story.issue_type, "Story")

        bug = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1101", jira_id="10021", issue_type="Bug")
        self.assertEqual(bug.issue_type, "Bug")

        task = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1102", jira_id="10022", issue_type="Task")
        self.assertEqual(task.issue_type, "Task")

        epic = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1103", jira_id="10023", issue_type="Epic")
        self.assertEqual(epic.issue_type, "Epic")

    def test_jira_issue_status_choices(self):
        """Test that JiraIssue.status can store different status values."""
        todo = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1200", jira_id="10024", status="To Do")
        self.assertEqual(todo.status, "To Do")

        in_progress = JiraIssue.objects.create(
            team=self.team1, jira_key="PROJ-1201", jira_id="10025", status="In Progress"
        )
        self.assertEqual(in_progress.status, "In Progress")

        done = JiraIssue.objects.create(team=self.team1, jira_key="PROJ-1202", jira_id="10026", status="Done")
        self.assertEqual(done.status, "Done")

    def test_jira_issue_verbose_name(self):
        """Test that JiraIssue has correct verbose_name."""
        self.assertEqual(JiraIssue._meta.verbose_name, "Jira Issue")

    def test_jira_issue_verbose_name_plural(self):
        """Test that JiraIssue has correct verbose_name_plural."""
        self.assertEqual(JiraIssue._meta.verbose_name_plural, "Jira Issues")


class TestJiraIssuePRLinking(TestCase):
    """Tests for JiraIssue-PullRequest bidirectional linking via jira_key."""

    def setUp(self):
        """Set up test fixtures using factories."""
        from apps.metrics.factories import TeamFactory

        self.team1 = TeamFactory()
        self.team2 = TeamFactory()

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_related_prs_returns_prs_with_matching_jira_key(self):
        """Test that related_prs returns PRs with matching jira_key."""
        from apps.metrics.factories import JiraIssueFactory, PullRequestFactory

        # Create JiraIssue with jira_key="PROJ-123"
        jira_issue = JiraIssueFactory(team=self.team1, jira_key="PROJ-123")

        # Create PR with jira_key="PROJ-123" (same team)
        pr_matching = PullRequestFactory(team=self.team1, jira_key="PROJ-123")

        # Create PR with jira_key="PROJ-456" (same team, different key)
        pr_different = PullRequestFactory(team=self.team1, jira_key="PROJ-456")

        # Assert related_prs contains only the matching PR
        related = list(jira_issue.related_prs)
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0].pk, pr_matching.pk)
        self.assertNotIn(pr_different, related)

    def test_related_prs_returns_empty_queryset_when_no_matches(self):
        """Test that related_prs returns empty queryset when no matches."""
        from apps.metrics.factories import JiraIssueFactory, PullRequestFactory

        # Create JiraIssue with jira_key="PROJ-789"
        jira_issue = JiraIssueFactory(team=self.team1, jira_key="PROJ-789")

        # Create PR with different jira_key
        PullRequestFactory(team=self.team1, jira_key="PROJ-999")

        # Assert related_prs is empty
        related = list(jira_issue.related_prs)
        self.assertEqual(len(related), 0)

    def test_related_prs_respects_team_isolation(self):
        """Test that related_prs respects team isolation."""
        from apps.metrics.factories import JiraIssueFactory, PullRequestFactory

        # Create JiraIssue with jira_key="PROJ-123" in team1
        jira_issue = JiraIssueFactory(team=self.team1, jira_key="PROJ-123")

        # Create PR with jira_key="PROJ-123" in team1
        pr_team1 = PullRequestFactory(team=self.team1, jira_key="PROJ-123")

        # Create PR with jira_key="PROJ-123" in team2 (different team!)
        pr_team2 = PullRequestFactory(team=self.team2, jira_key="PROJ-123")

        # Assert related_prs only contains the PR from team1
        related = list(jira_issue.related_prs)
        self.assertEqual(len(related), 1)
        self.assertEqual(related[0].pk, pr_team1.pk)
        self.assertNotIn(pr_team2, related)

    def test_related_prs_returns_multiple_prs_for_same_jira_key(self):
        """Test that related_prs returns multiple PRs for same jira_key."""
        from apps.metrics.factories import JiraIssueFactory, PullRequestFactory

        # Create JiraIssue with jira_key="PROJ-100"
        jira_issue = JiraIssueFactory(team=self.team1, jira_key="PROJ-100")

        # Create 3 PRs all with jira_key="PROJ-100"
        pr1 = PullRequestFactory(team=self.team1, jira_key="PROJ-100")
        pr2 = PullRequestFactory(team=self.team1, jira_key="PROJ-100")
        pr3 = PullRequestFactory(team=self.team1, jira_key="PROJ-100")

        # Assert related_prs contains all 3 PRs
        related = list(jira_issue.related_prs)
        self.assertEqual(len(related), 3)
        self.assertIn(pr1, related)
        self.assertIn(pr2, related)
        self.assertIn(pr3, related)


class TestAIUsageDailyModel(TestCase):
    """Tests for AIUsageDaily model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team1 = Team.objects.create(name="Team One", slug="team-one")
        self.team2 = Team.objects.create(name="Team Two", slug="team-two")
        self.member1 = TeamMember.objects.create(team=self.team1, display_name="Alice", github_username="alice")
        self.member2 = TeamMember.objects.create(team=self.team2, display_name="Bob", github_username="bob")
        self.test_date = django_timezone.now().date()

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_ai_usage_daily_creation_with_required_fields(self):
        """Test that AIUsageDaily can be created with required fields."""
        usage = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        self.assertEqual(usage.team, self.team1)
        self.assertEqual(usage.member, self.member1)
        self.assertEqual(usage.date, self.test_date)
        self.assertEqual(usage.source, "copilot")
        self.assertIsNotNone(usage.pk)

    def test_ai_usage_daily_source_choice_copilot(self):
        """Test that AIUsageDaily source 'copilot' works correctly."""
        usage = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        self.assertEqual(usage.source, "copilot")

    def test_ai_usage_daily_source_choice_cursor(self):
        """Test that AIUsageDaily source 'cursor' works correctly."""
        usage = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="cursor")
        self.assertEqual(usage.source, "cursor")

    def test_ai_usage_daily_creation_with_all_fields(self):
        """Test that AIUsageDaily can be created with all fields."""
        usage = AIUsageDaily.objects.create(
            team=self.team1,
            member=self.member1,
            date=self.test_date,
            source="copilot",
            active_hours=Decimal("8.50"),
            suggestions_shown=150,
            suggestions_accepted=120,
            acceptance_rate=Decimal("80.00"),
        )
        self.assertEqual(usage.active_hours, Decimal("8.50"))
        self.assertEqual(usage.suggestions_shown, 150)
        self.assertEqual(usage.suggestions_accepted, 120)
        self.assertEqual(usage.acceptance_rate, Decimal("80.00"))

    def test_ai_usage_daily_unique_constraint_team_member_date_source_enforced(self):
        """Test that unique constraint on (team, member, date, source) is enforced."""
        AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        # Attempt to create another usage with same team, member, date, and source
        with self.assertRaises(IntegrityError):
            AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")

    def test_ai_usage_daily_same_member_date_source_allowed_different_teams(self):
        """Test that same member+date+source is allowed in different teams."""
        usage1 = AIUsageDaily.objects.create(
            team=self.team1, member=self.member1, date=self.test_date, source="copilot"
        )
        usage2 = AIUsageDaily.objects.create(
            team=self.team2, member=self.member2, date=self.test_date, source="copilot"
        )
        self.assertEqual(usage1.date, usage2.date)
        self.assertEqual(usage1.source, usage2.source)
        self.assertNotEqual(usage1.team, usage2.team)

    def test_ai_usage_daily_same_member_date_different_sources_allowed(self):
        """Test that same member+date with different sources is allowed."""
        usage1 = AIUsageDaily.objects.create(
            team=self.team1, member=self.member1, date=self.test_date, source="copilot"
        )
        usage2 = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="cursor")
        self.assertEqual(usage1.member, usage2.member)
        self.assertEqual(usage1.date, usage2.date)
        self.assertNotEqual(usage1.source, usage2.source)

    def test_ai_usage_daily_member_cascade_delete(self):
        """Test that AIUsageDaily is cascade deleted when TeamMember is deleted."""
        usage = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        usage_id = usage.pk

        # Delete the member
        self.member1.delete()

        # Verify usage is also deleted
        with self.assertRaises(AIUsageDaily.DoesNotExist):
            AIUsageDaily.objects.get(pk=usage_id)

    def test_ai_usage_daily_default_suggestions_shown_is_zero(self):
        """Test that AIUsageDaily.suggestions_shown defaults to 0."""
        usage = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        self.assertEqual(usage.suggestions_shown, 0)

    def test_ai_usage_daily_default_suggestions_accepted_is_zero(self):
        """Test that AIUsageDaily.suggestions_accepted defaults to 0."""
        usage = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        self.assertEqual(usage.suggestions_accepted, 0)

    def test_ai_usage_daily_acceptance_rate_can_be_decimal(self):
        """Test that AIUsageDaily.acceptance_rate can store decimal values."""
        usage = AIUsageDaily.objects.create(
            team=self.team1,
            member=self.member1,
            date=self.test_date,
            source="copilot",
            acceptance_rate=Decimal("75.25"),
        )
        self.assertEqual(usage.acceptance_rate, Decimal("75.25"))

    def test_ai_usage_daily_active_hours_can_be_decimal(self):
        """Test that AIUsageDaily.active_hours can store decimal values."""
        usage = AIUsageDaily.objects.create(
            team=self.team1, member=self.member1, date=self.test_date, source="copilot", active_hours=Decimal("3.75")
        )
        self.assertEqual(usage.active_hours, Decimal("3.75"))

    def test_ai_usage_daily_synced_at_auto_updates_on_save(self):
        """Test that AIUsageDaily.synced_at auto-updates when model is saved."""
        usage = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        original_synced_at = usage.synced_at
        self.assertIsNotNone(original_synced_at)

        # Update and save
        usage.suggestions_shown = 100
        usage.save()

        # Refresh from database
        usage.refresh_from_db()
        self.assertGreaterEqual(usage.synced_at, original_synced_at)

    def test_ai_usage_daily_for_team_manager_filters_by_current_team(self):
        """Test that AIUsageDaily.for_team manager filters by current team context."""
        # Create usage for both teams
        usage1 = AIUsageDaily.objects.create(
            team=self.team1, member=self.member1, date=self.test_date, source="copilot"
        )
        usage2 = AIUsageDaily.objects.create(
            team=self.team2, member=self.member2, date=self.test_date, source="copilot"
        )

        # Set team1 as current and verify filtering
        set_current_team(self.team1)
        team1_usage = list(AIUsageDaily.for_team.all())
        self.assertEqual(len(team1_usage), 1)
        self.assertEqual(team1_usage[0].pk, usage1.pk)

        # Set team2 as current and verify filtering
        set_current_team(self.team2)
        team2_usage = list(AIUsageDaily.for_team.all())
        self.assertEqual(len(team2_usage), 1)
        self.assertEqual(team2_usage[0].pk, usage2.pk)

    def test_ai_usage_daily_for_team_manager_with_context_manager(self):
        """Test that AIUsageDaily.for_team works with context manager."""
        # Create usage for both teams
        AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        AIUsageDaily.objects.create(team=self.team2, member=self.member2, date=self.test_date, source="copilot")

        with current_team(self.team1):
            self.assertEqual(AIUsageDaily.for_team.count(), 1)

        with current_team(self.team2):
            self.assertEqual(AIUsageDaily.for_team.count(), 1)

    def test_ai_usage_daily_for_team_manager_returns_empty_when_no_team_set(self):
        """Test that AIUsageDaily.for_team returns empty queryset when no team is set."""
        AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")

        unset_current_team()
        self.assertIsNone(get_current_team())
        self.assertEqual(AIUsageDaily.for_team.count(), 0)

    def test_ai_usage_daily_has_created_at_from_base_model(self):
        """Test that AIUsageDaily inherits created_at from BaseModel."""
        usage = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        self.assertIsNotNone(usage.created_at)

    def test_ai_usage_daily_has_updated_at_from_base_model(self):
        """Test that AIUsageDaily inherits updated_at from BaseModel."""
        usage = AIUsageDaily.objects.create(team=self.team1, member=self.member1, date=self.test_date, source="copilot")
        self.assertIsNotNone(usage.updated_at)


class TestPRSurveyModel(TestCase):
    """Tests for PRSurvey model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team1 = Team.objects.create(name="Team One", slug="team-one")
        self.team2 = Team.objects.create(name="Team Two", slug="team-two")
        self.author = TeamMember.objects.create(team=self.team1, display_name="Author", github_username="author")
        self.pull_request1 = PullRequest.objects.create(
            team=self.team1, github_pr_id=1, github_repo="org/repo", state="open"
        )
        self.pull_request2 = PullRequest.objects.create(
            team=self.team1, github_pr_id=2, github_repo="org/repo", state="open"
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_pr_survey_creation_with_pull_request(self):
        """Test that PRSurvey can be created with OneToOne to PullRequest."""
        survey = PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)
        self.assertEqual(survey.team, self.team1)
        self.assertEqual(survey.pull_request, self.pull_request1)
        self.assertEqual(survey.author, self.author)
        self.assertIsNotNone(survey.pk)

    def test_pr_survey_one_to_one_enforced(self):
        """Test that OneToOne constraint is enforced (only one survey per PR)."""
        PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)
        # Attempt to create another survey for the same PR
        with self.assertRaises(IntegrityError):
            PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)

    def test_pr_survey_cascade_delete_when_pull_request_deleted(self):
        """Test that PRSurvey is cascade deleted when PullRequest is deleted."""
        survey = PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)
        survey_id = survey.pk

        # Delete the pull request
        self.pull_request1.delete()

        # Verify survey is also deleted
        with self.assertRaises(PRSurvey.DoesNotExist):
            PRSurvey.objects.get(pk=survey_id)

    def test_pr_survey_author_ai_assisted_can_be_null(self):
        """Test that PRSurvey.author_ai_assisted can be null (not responded)."""
        survey = PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)
        self.assertIsNone(survey.author_ai_assisted)

    def test_pr_survey_author_ai_assisted_can_be_true(self):
        """Test that PRSurvey.author_ai_assisted can be True."""
        survey = PRSurvey.objects.create(
            team=self.team1, pull_request=self.pull_request1, author=self.author, author_ai_assisted=True
        )
        self.assertTrue(survey.author_ai_assisted)

    def test_pr_survey_author_ai_assisted_can_be_false(self):
        """Test that PRSurvey.author_ai_assisted can be False."""
        survey = PRSurvey.objects.create(
            team=self.team1, pull_request=self.pull_request1, author=self.author, author_ai_assisted=False
        )
        self.assertFalse(survey.author_ai_assisted)

    def test_pr_survey_author_responded_at_can_be_set(self):
        """Test that PRSurvey.author_responded_at can be set."""
        responded_time = django_timezone.now()
        survey = PRSurvey.objects.create(
            team=self.team1,
            pull_request=self.pull_request1,
            author=self.author,
            author_ai_assisted=True,
            author_responded_at=responded_time,
        )
        self.assertEqual(survey.author_responded_at, responded_time)

    def test_pr_survey_multiple_surveys_different_prs_allowed(self):
        """Test that multiple surveys can be created for different PRs."""
        survey1 = PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)
        survey2 = PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request2, author=self.author)
        self.assertNotEqual(survey1.pull_request, survey2.pull_request)
        self.assertEqual(survey1.author, survey2.author)

    def test_pr_survey_for_team_manager_filters_by_current_team(self):
        """Test that PRSurvey.for_team manager filters by current team context."""
        # Create another team with PR
        pr2 = PullRequest.objects.create(team=self.team2, github_pr_id=3, github_repo="org/repo", state="open")
        author2 = TeamMember.objects.create(team=self.team2, display_name="Author 2", github_username="author2")

        # Create surveys for both teams
        survey1 = PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)
        survey2 = PRSurvey.objects.create(team=self.team2, pull_request=pr2, author=author2)

        # Set team1 as current and verify filtering
        set_current_team(self.team1)
        team1_surveys = list(PRSurvey.for_team.all())
        self.assertEqual(len(team1_surveys), 1)
        self.assertEqual(team1_surveys[0].pk, survey1.pk)

        # Set team2 as current and verify filtering
        set_current_team(self.team2)
        team2_surveys = list(PRSurvey.for_team.all())
        self.assertEqual(len(team2_surveys), 1)
        self.assertEqual(team2_surveys[0].pk, survey2.pk)

    def test_pr_survey_for_team_manager_with_context_manager(self):
        """Test that PRSurvey.for_team works with context manager."""
        # Create another team with PR
        pr2 = PullRequest.objects.create(team=self.team2, github_pr_id=4, github_repo="org/repo", state="open")
        author2 = TeamMember.objects.create(team=self.team2, display_name="Author 2", github_username="author2")

        # Create surveys for both teams
        PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)
        PRSurvey.objects.create(team=self.team2, pull_request=pr2, author=author2)

        with current_team(self.team1):
            self.assertEqual(PRSurvey.for_team.count(), 1)

        with current_team(self.team2):
            self.assertEqual(PRSurvey.for_team.count(), 1)

    def test_pr_survey_for_team_manager_returns_empty_when_no_team_set(self):
        """Test that PRSurvey.for_team returns empty queryset when no team is set."""
        PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)

        unset_current_team()
        self.assertIsNone(get_current_team())
        self.assertEqual(PRSurvey.for_team.count(), 0)

    def test_pr_survey_has_created_at_from_base_model(self):
        """Test that PRSurvey inherits created_at from BaseModel."""
        survey = PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)
        self.assertIsNotNone(survey.created_at)

    def test_pr_survey_has_updated_at_from_base_model(self):
        """Test that PRSurvey inherits updated_at from BaseModel."""
        survey = PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request1, author=self.author)
        self.assertIsNotNone(survey.updated_at)


class TestPRSurveyReviewModel(TestCase):
    """Tests for PRSurveyReview model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team1 = Team.objects.create(name="Team One", slug="team-one")
        self.team2 = Team.objects.create(name="Team Two", slug="team-two")
        self.author = TeamMember.objects.create(team=self.team1, display_name="Author", github_username="author")
        self.reviewer1 = TeamMember.objects.create(
            team=self.team1, display_name="Reviewer 1", github_username="reviewer1"
        )
        self.reviewer2 = TeamMember.objects.create(
            team=self.team1, display_name="Reviewer 2", github_username="reviewer2"
        )
        self.pull_request = PullRequest.objects.create(
            team=self.team1, github_pr_id=1, github_repo="org/repo", state="open"
        )
        self.survey = PRSurvey.objects.create(team=self.team1, pull_request=self.pull_request, author=self.author)

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_pr_survey_review_creation_linked_to_survey(self):
        """Test that PRSurveyReview can be created linked to PRSurvey."""
        review = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer1, quality_rating=3
        )
        self.assertEqual(review.team, self.team1)
        self.assertEqual(review.survey, self.survey)
        self.assertEqual(review.reviewer, self.reviewer1)
        self.assertEqual(review.quality_rating, 3)
        self.assertIsNotNone(review.pk)

    def test_pr_survey_review_quality_choice_1_could_be_better(self):
        """Test that PRSurveyReview quality_rating 1 (Could be better) works correctly."""
        review = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer1, quality_rating=1
        )
        self.assertEqual(review.quality_rating, 1)

    def test_pr_survey_review_quality_choice_2_ok(self):
        """Test that PRSurveyReview quality_rating 2 (OK) works correctly."""
        review = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer1, quality_rating=2
        )
        self.assertEqual(review.quality_rating, 2)

    def test_pr_survey_review_quality_choice_3_super(self):
        """Test that PRSurveyReview quality_rating 3 (Super) works correctly."""
        review = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer1, quality_rating=3
        )
        self.assertEqual(review.quality_rating, 3)

    def test_pr_survey_review_unique_constraint_survey_reviewer_enforced(self):
        """Test that unique constraint on (survey, reviewer) is enforced."""
        PRSurveyReview.objects.create(team=self.team1, survey=self.survey, reviewer=self.reviewer1)
        # Attempt to create another review for same survey and reviewer
        with self.assertRaises(IntegrityError):
            PRSurveyReview.objects.create(team=self.team1, survey=self.survey, reviewer=self.reviewer1)

    def test_pr_survey_review_cascade_delete_when_survey_deleted(self):
        """Test that PRSurveyReview is cascade deleted when PRSurvey is deleted."""
        review = PRSurveyReview.objects.create(team=self.team1, survey=self.survey, reviewer=self.reviewer1)
        review_id = review.pk

        # Delete the survey
        self.survey.delete()

        # Verify review is also deleted
        with self.assertRaises(PRSurveyReview.DoesNotExist):
            PRSurveyReview.objects.get(pk=review_id)

    def test_pr_survey_review_ai_guess_can_be_null(self):
        """Test that PRSurveyReview.ai_guess can be null."""
        review = PRSurveyReview.objects.create(team=self.team1, survey=self.survey, reviewer=self.reviewer1)
        self.assertIsNone(review.ai_guess)

    def test_pr_survey_review_ai_guess_can_be_true(self):
        """Test that PRSurveyReview.ai_guess can be True."""
        review = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer1, ai_guess=True
        )
        self.assertTrue(review.ai_guess)

    def test_pr_survey_review_ai_guess_can_be_false(self):
        """Test that PRSurveyReview.ai_guess can be False."""
        review = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer1, ai_guess=False
        )
        self.assertFalse(review.ai_guess)

    def test_pr_survey_review_guess_correct_scenario(self):
        """Test PRSurveyReview.guess_correct calculation scenario."""
        # Create survey with author_ai_assisted=True
        self.survey.author_ai_assisted = True
        self.survey.save()

        # Reviewer guesses True (correct)
        review_correct = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer1, ai_guess=True, guess_correct=True
        )
        self.assertTrue(review_correct.guess_correct)

        # Reviewer guesses False (incorrect)
        review_incorrect = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer2, ai_guess=False, guess_correct=False
        )
        self.assertFalse(review_incorrect.guess_correct)

    def test_pr_survey_review_multiple_reviews_per_survey_different_reviewers(self):
        """Test that multiple reviews per survey are allowed (different reviewers)."""
        review1 = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer1, quality_rating=3
        )
        review2 = PRSurveyReview.objects.create(
            team=self.team1, survey=self.survey, reviewer=self.reviewer2, quality_rating=2
        )
        # Both reviews should exist for the same survey
        self.assertEqual(review1.survey, review2.survey)
        self.assertNotEqual(review1.reviewer, review2.reviewer)
        self.assertEqual(self.survey.reviews.count(), 2)

    def test_pr_survey_review_responded_at_can_be_set(self):
        """Test that PRSurveyReview.responded_at can be set."""
        responded_time = django_timezone.now()
        review = PRSurveyReview.objects.create(
            team=self.team1,
            survey=self.survey,
            reviewer=self.reviewer1,
            quality_rating=3,
            responded_at=responded_time,
        )
        self.assertEqual(review.responded_at, responded_time)

    def test_pr_survey_review_for_team_manager_filters_by_current_team(self):
        """Test that PRSurveyReview.for_team manager filters by current team context."""
        # Create another team with survey
        pr2 = PullRequest.objects.create(team=self.team2, github_pr_id=2, github_repo="org/repo", state="open")
        author2 = TeamMember.objects.create(team=self.team2, display_name="Author 2", github_username="author2")
        survey2 = PRSurvey.objects.create(team=self.team2, pull_request=pr2, author=author2)
        reviewer2_team2 = TeamMember.objects.create(
            team=self.team2, display_name="Reviewer 2", github_username="reviewer2_team2"
        )

        # Create reviews for both teams
        review1 = PRSurveyReview.objects.create(team=self.team1, survey=self.survey, reviewer=self.reviewer1)
        review2 = PRSurveyReview.objects.create(team=self.team2, survey=survey2, reviewer=reviewer2_team2)

        # Set team1 as current and verify filtering
        set_current_team(self.team1)
        team1_reviews = list(PRSurveyReview.for_team.all())
        self.assertEqual(len(team1_reviews), 1)
        self.assertEqual(team1_reviews[0].pk, review1.pk)

        # Set team2 as current and verify filtering
        set_current_team(self.team2)
        team2_reviews = list(PRSurveyReview.for_team.all())
        self.assertEqual(len(team2_reviews), 1)
        self.assertEqual(team2_reviews[0].pk, review2.pk)

    def test_pr_survey_review_for_team_manager_with_context_manager(self):
        """Test that PRSurveyReview.for_team works with context manager."""
        # Create another team with survey
        pr2 = PullRequest.objects.create(team=self.team2, github_pr_id=3, github_repo="org/repo", state="open")
        author2 = TeamMember.objects.create(team=self.team2, display_name="Author 2", github_username="author2")
        survey2 = PRSurvey.objects.create(team=self.team2, pull_request=pr2, author=author2)
        reviewer2_team2 = TeamMember.objects.create(
            team=self.team2, display_name="Reviewer 2", github_username="reviewer2_team2"
        )

        # Create reviews for both teams
        PRSurveyReview.objects.create(team=self.team1, survey=self.survey, reviewer=self.reviewer1)
        PRSurveyReview.objects.create(team=self.team2, survey=survey2, reviewer=reviewer2_team2)

        with current_team(self.team1):
            self.assertEqual(PRSurveyReview.for_team.count(), 1)

        with current_team(self.team2):
            self.assertEqual(PRSurveyReview.for_team.count(), 1)

    def test_pr_survey_review_for_team_manager_returns_empty_when_no_team_set(self):
        """Test that PRSurveyReview.for_team returns empty queryset when no team is set."""
        PRSurveyReview.objects.create(team=self.team1, survey=self.survey, reviewer=self.reviewer1)

        unset_current_team()
        self.assertIsNone(get_current_team())
        self.assertEqual(PRSurveyReview.for_team.count(), 0)

    def test_pr_survey_review_has_created_at_from_base_model(self):
        """Test that PRSurveyReview inherits created_at from BaseModel."""
        review = PRSurveyReview.objects.create(team=self.team1, survey=self.survey, reviewer=self.reviewer1)
        self.assertIsNotNone(review.created_at)

    def test_pr_survey_review_has_updated_at_from_base_model(self):
        """Test that PRSurveyReview inherits updated_at from BaseModel."""
        review = PRSurveyReview.objects.create(team=self.team1, survey=self.survey, reviewer=self.reviewer1)
        self.assertIsNotNone(review.updated_at)


class TestWeeklyMetricsModel(TestCase):
    """Tests for WeeklyMetrics model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team1 = Team.objects.create(name="Team One", slug="team-one")
        self.team2 = Team.objects.create(name="Team Two", slug="team-two")
        self.member1 = TeamMember.objects.create(team=self.team1, display_name="Alice", github_username="alice")
        self.member2 = TeamMember.objects.create(team=self.team2, display_name="Bob", github_username="bob")
        # Use a Monday date for week_start
        self.week_start = django_timezone.now().date().replace(day=2)  # Monday, Dec 2, 2024

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_weekly_metrics_creation_with_required_fields(self):
        """Test that WeeklyMetrics can be created with required fields (team, member, week_start)."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        self.assertEqual(metrics.team, self.team1)
        self.assertEqual(metrics.member, self.member1)
        self.assertEqual(metrics.week_start, self.week_start)
        self.assertIsNotNone(metrics.pk)

    def test_weekly_metrics_default_values(self):
        """Test that WeeklyMetrics default values work correctly."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        # Count fields should default to 0
        self.assertEqual(metrics.prs_merged, 0)
        self.assertEqual(metrics.commits_count, 0)
        self.assertEqual(metrics.lines_added, 0)
        self.assertEqual(metrics.lines_removed, 0)
        self.assertEqual(metrics.revert_count, 0)
        self.assertEqual(metrics.hotfix_count, 0)
        self.assertEqual(metrics.issues_resolved, 0)
        self.assertEqual(metrics.ai_assisted_prs, 0)
        self.assertEqual(metrics.surveys_completed, 0)
        self.assertEqual(metrics.story_points_completed, Decimal("0"))
        # Average fields should be null by default
        self.assertIsNone(metrics.avg_cycle_time_hours)
        self.assertIsNone(metrics.avg_review_time_hours)
        self.assertIsNone(metrics.avg_quality_rating)
        self.assertIsNone(metrics.guess_accuracy)

    def test_weekly_metrics_unique_constraint_team_member_week_enforced(self):
        """Test that unique constraint on (team, member, week_start) is enforced."""
        WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        # Attempt to create another metric for the same team, member, and week
        with self.assertRaises(IntegrityError):
            WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)

    def test_weekly_metrics_same_member_week_allowed_different_teams(self):
        """Test that same member+week is allowed in different teams."""
        metrics1 = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        metrics2 = WeeklyMetrics.objects.create(team=self.team2, member=self.member2, week_start=self.week_start)
        self.assertEqual(metrics1.week_start, metrics2.week_start)
        self.assertNotEqual(metrics1.team, metrics2.team)
        self.assertNotEqual(metrics1.member, metrics2.member)

    def test_weekly_metrics_member_cascade_delete(self):
        """Test that WeeklyMetrics is cascade deleted when TeamMember is deleted."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        metrics_id = metrics.pk

        # Delete the member
        self.member1.delete()

        # Verify metrics is also deleted
        with self.assertRaises(WeeklyMetrics.DoesNotExist):
            WeeklyMetrics.objects.get(pk=metrics_id)

    def test_weekly_metrics_creation_with_all_fields(self):
        """Test that WeeklyMetrics can be created with all fields."""
        metrics = WeeklyMetrics.objects.create(
            team=self.team1,
            member=self.member1,
            week_start=self.week_start,
            prs_merged=5,
            avg_cycle_time_hours=Decimal("24.50"),
            avg_review_time_hours=Decimal("3.75"),
            commits_count=25,
            lines_added=1500,
            lines_removed=300,
            revert_count=1,
            hotfix_count=2,
            story_points_completed=Decimal("13.5"),
            issues_resolved=8,
            ai_assisted_prs=3,
            avg_quality_rating=Decimal("2.75"),
            surveys_completed=5,
            guess_accuracy=Decimal("85.50"),
        )
        self.assertEqual(metrics.prs_merged, 5)
        self.assertEqual(metrics.avg_cycle_time_hours, Decimal("24.50"))
        self.assertEqual(metrics.avg_review_time_hours, Decimal("3.75"))
        self.assertEqual(metrics.commits_count, 25)
        self.assertEqual(metrics.lines_added, 1500)
        self.assertEqual(metrics.lines_removed, 300)
        self.assertEqual(metrics.revert_count, 1)
        self.assertEqual(metrics.hotfix_count, 2)
        self.assertEqual(metrics.story_points_completed, Decimal("13.5"))
        self.assertEqual(metrics.issues_resolved, 8)
        self.assertEqual(metrics.ai_assisted_prs, 3)
        self.assertEqual(metrics.avg_quality_rating, Decimal("2.75"))
        self.assertEqual(metrics.surveys_completed, 5)
        self.assertEqual(metrics.guess_accuracy, Decimal("85.50"))

    def test_weekly_metrics_decimal_field_avg_cycle_time_hours(self):
        """Test that WeeklyMetrics.avg_cycle_time_hours can store decimal values."""
        metrics = WeeklyMetrics.objects.create(
            team=self.team1, member=self.member1, week_start=self.week_start, avg_cycle_time_hours=Decimal("48.25")
        )
        self.assertEqual(metrics.avg_cycle_time_hours, Decimal("48.25"))

    def test_weekly_metrics_decimal_field_avg_review_time_hours(self):
        """Test that WeeklyMetrics.avg_review_time_hours can store decimal values."""
        metrics = WeeklyMetrics.objects.create(
            team=self.team1, member=self.member1, week_start=self.week_start, avg_review_time_hours=Decimal("2.50")
        )
        self.assertEqual(metrics.avg_review_time_hours, Decimal("2.50"))

    def test_weekly_metrics_decimal_field_story_points_completed(self):
        """Test that WeeklyMetrics.story_points_completed can store decimal values."""
        metrics = WeeklyMetrics.objects.create(
            team=self.team1, member=self.member1, week_start=self.week_start, story_points_completed=Decimal("8.5")
        )
        self.assertEqual(metrics.story_points_completed, Decimal("8.5"))

    def test_weekly_metrics_decimal_field_avg_quality_rating(self):
        """Test that WeeklyMetrics.avg_quality_rating can store decimal values."""
        metrics = WeeklyMetrics.objects.create(
            team=self.team1, member=self.member1, week_start=self.week_start, avg_quality_rating=Decimal("2.33")
        )
        self.assertEqual(metrics.avg_quality_rating, Decimal("2.33"))

    def test_weekly_metrics_decimal_field_guess_accuracy(self):
        """Test that WeeklyMetrics.guess_accuracy can store decimal values."""
        metrics = WeeklyMetrics.objects.create(
            team=self.team1, member=self.member1, week_start=self.week_start, guess_accuracy=Decimal("92.75")
        )
        self.assertEqual(metrics.guess_accuracy, Decimal("92.75"))

    def test_weekly_metrics_null_handling_avg_cycle_time(self):
        """Test that avg_cycle_time_hours can be null (no PRs merged)."""
        metrics = WeeklyMetrics.objects.create(
            team=self.team1, member=self.member1, week_start=self.week_start, prs_merged=0
        )
        self.assertIsNone(metrics.avg_cycle_time_hours)
        self.assertEqual(metrics.prs_merged, 0)

    def test_weekly_metrics_null_handling_avg_review_time(self):
        """Test that avg_review_time_hours can be null (no reviews)."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        self.assertIsNone(metrics.avg_review_time_hours)

    def test_weekly_metrics_null_handling_avg_quality_rating(self):
        """Test that avg_quality_rating can be null (no survey responses)."""
        metrics = WeeklyMetrics.objects.create(
            team=self.team1, member=self.member1, week_start=self.week_start, surveys_completed=0
        )
        self.assertIsNone(metrics.avg_quality_rating)
        self.assertEqual(metrics.surveys_completed, 0)

    def test_weekly_metrics_null_handling_guess_accuracy(self):
        """Test that guess_accuracy can be null (no guesses made)."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        self.assertIsNone(metrics.guess_accuracy)

    def test_weekly_metrics_zero_vs_null_count_fields(self):
        """Test that count fields use 0 as default, not null."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        # All count fields should be 0, not None
        self.assertEqual(metrics.prs_merged, 0)
        self.assertEqual(metrics.commits_count, 0)
        self.assertEqual(metrics.lines_added, 0)
        self.assertEqual(metrics.lines_removed, 0)
        self.assertEqual(metrics.revert_count, 0)
        self.assertEqual(metrics.hotfix_count, 0)
        self.assertEqual(metrics.issues_resolved, 0)
        self.assertEqual(metrics.ai_assisted_prs, 0)
        self.assertEqual(metrics.surveys_completed, 0)

    def test_weekly_metrics_zero_vs_null_average_fields(self):
        """Test that average fields use null as default, not 0."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        # All average fields should be None, not 0
        self.assertIsNone(metrics.avg_cycle_time_hours)
        self.assertIsNone(metrics.avg_review_time_hours)
        self.assertIsNone(metrics.avg_quality_rating)
        self.assertIsNone(metrics.guess_accuracy)

    def test_weekly_metrics_for_team_manager_filters_by_current_team(self):
        """Test that WeeklyMetrics.for_team manager filters by current team context."""
        # Create metrics for both teams
        metrics1 = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        metrics2 = WeeklyMetrics.objects.create(team=self.team2, member=self.member2, week_start=self.week_start)

        # Set team1 as current and verify filtering
        set_current_team(self.team1)
        team1_metrics = list(WeeklyMetrics.for_team.all())
        self.assertEqual(len(team1_metrics), 1)
        self.assertEqual(team1_metrics[0].pk, metrics1.pk)

        # Set team2 as current and verify filtering
        set_current_team(self.team2)
        team2_metrics = list(WeeklyMetrics.for_team.all())
        self.assertEqual(len(team2_metrics), 1)
        self.assertEqual(team2_metrics[0].pk, metrics2.pk)

    def test_weekly_metrics_for_team_manager_with_context_manager(self):
        """Test that WeeklyMetrics.for_team works with context manager."""
        # Create metrics for both teams
        WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        WeeklyMetrics.objects.create(team=self.team2, member=self.member2, week_start=self.week_start)

        with current_team(self.team1):
            self.assertEqual(WeeklyMetrics.for_team.count(), 1)

        with current_team(self.team2):
            self.assertEqual(WeeklyMetrics.for_team.count(), 1)

    def test_weekly_metrics_for_team_manager_returns_empty_when_no_team_set(self):
        """Test that WeeklyMetrics.for_team returns empty queryset when no team is set."""
        WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)

        unset_current_team()
        self.assertIsNone(get_current_team())
        self.assertEqual(WeeklyMetrics.for_team.count(), 0)

    def test_weekly_metrics_has_created_at_from_base_model(self):
        """Test that WeeklyMetrics inherits created_at from BaseModel."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        self.assertIsNotNone(metrics.created_at)

    def test_weekly_metrics_has_updated_at_from_base_model(self):
        """Test that WeeklyMetrics inherits updated_at from BaseModel."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        self.assertIsNotNone(metrics.updated_at)

    def test_weekly_metrics_has_team_foreign_key_from_base_team_model(self):
        """Test that WeeklyMetrics has team ForeignKey from BaseTeamModel."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        self.assertEqual(metrics.team, self.team1)
        self.assertIsInstance(metrics.team, Team)

    def test_weekly_metrics_updated_at_changes_on_save(self):
        """Test that updated_at timestamp changes when WeeklyMetrics is saved."""
        metrics = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=self.week_start)
        original_updated_at = metrics.updated_at

        # Update and save
        metrics.prs_merged = 10
        metrics.save()

        # Refresh from database
        metrics.refresh_from_db()
        self.assertGreater(metrics.updated_at, original_updated_at)

    def test_weekly_metrics_multiple_weeks_per_member(self):
        """Test that multiple week entries can be created for same member."""
        week1 = self.week_start
        week2 = week1 + django_timezone.timedelta(days=7)  # Next Monday

        metrics1 = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=week1)
        metrics2 = WeeklyMetrics.objects.create(team=self.team1, member=self.member1, week_start=week2)

        self.assertEqual(metrics1.member, metrics2.member)
        self.assertNotEqual(metrics1.week_start, metrics2.week_start)
        self.assertEqual(WeeklyMetrics.objects.filter(team=self.team1, member=self.member1).count(), 2)

    def test_weekly_metrics_verbose_name(self):
        """Test that WeeklyMetrics has correct verbose_name."""
        self.assertEqual(WeeklyMetrics._meta.verbose_name, "Weekly Metrics")

    def test_weekly_metrics_verbose_name_plural(self):
        """Test that WeeklyMetrics has correct verbose_name_plural."""
        self.assertEqual(WeeklyMetrics._meta.verbose_name_plural, "Weekly Metrics")


class TestPullRequestFactory(TestCase):
    """Tests for PullRequestFactory."""

    def test_pull_request_factory_supports_jira_key_parameter(self):
        """Test that PullRequestFactory can create PullRequest with jira_key parameter."""
        from apps.metrics.factories import PullRequestFactory

        pr = PullRequestFactory(jira_key="PROJ-999")
        self.assertEqual(pr.jira_key, "PROJ-999")
        self.assertIsNotNone(pr.pk)

    def test_pull_request_factory_jira_key_defaults_to_empty(self):
        """Test that PullRequestFactory creates PullRequest with empty jira_key by default."""
        from apps.metrics.factories import PullRequestFactory

        pr = PullRequestFactory()
        self.assertEqual(pr.jira_key, "")
        self.assertIsNotNone(pr.pk)


class TestPRCheckRunModel(TestCase):
    """Tests for PRCheckRun model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = Team.objects.create(name="Test Team", slug="test-team")
        self.author = TeamMember.objects.create(team=self.team, display_name="Author", github_username="author")
        self.pull_request = PullRequest.objects.create(
            team=self.team, github_pr_id=1, github_repo="org/repo", state="open", author=self.author
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_pr_check_run_creation(self):
        """Test that PRCheckRun can be created with required fields."""
        check_run = PRCheckRun.objects.create(
            team=self.team,
            github_check_run_id=123456789,
            pull_request=self.pull_request,
            name="pytest",
            status="completed",
            conclusion="success",
        )
        self.assertEqual(check_run.github_check_run_id, 123456789)
        self.assertEqual(check_run.pull_request, self.pull_request)
        self.assertEqual(check_run.name, "pytest")
        self.assertEqual(check_run.status, "completed")
        self.assertEqual(check_run.conclusion, "success")
        self.assertIsNotNone(check_run.pk)

    def test_pr_check_run_pull_request_relationship(self):
        """Test that PRCheckRun has correct foreign key relationship with PullRequest."""
        check_run1 = PRCheckRun.objects.create(
            team=self.team,
            github_check_run_id=111,
            pull_request=self.pull_request,
            name="eslint",
            status="completed",
        )
        check_run2 = PRCheckRun.objects.create(
            team=self.team,
            github_check_run_id=222,
            pull_request=self.pull_request,
            name="build",
            status="in_progress",
        )

        # Test forward relationship
        self.assertEqual(check_run1.pull_request, self.pull_request)
        self.assertEqual(check_run2.pull_request, self.pull_request)

        # Test reverse relationship via related_name='check_runs'
        check_runs = self.pull_request.check_runs.all()
        self.assertEqual(check_runs.count(), 2)
        self.assertIn(check_run1, check_runs)
        self.assertIn(check_run2, check_runs)

    def test_pr_check_run_unique_constraint(self):
        """Test that unique constraint on (team, github_check_run_id) is enforced."""
        PRCheckRun.objects.create(
            team=self.team,
            github_check_run_id=999,
            pull_request=self.pull_request,
            name="test-check",
            status="queued",
        )
        # Attempt to create another check run with same github_check_run_id in same team
        with self.assertRaises(IntegrityError):
            PRCheckRun.objects.create(
                team=self.team,
                github_check_run_id=999,
                pull_request=self.pull_request,
                name="different-check",
                status="completed",
            )

    def test_pr_check_run_str_representation(self):
        """Test that PRCheckRun.__str__ returns sensible format."""
        check_run = PRCheckRun.objects.create(
            team=self.team,
            github_check_run_id=555,
            pull_request=self.pull_request,
            name="pytest",
            status="completed",
            conclusion="failure",
        )
        str_repr = str(check_run)
        # Should contain key identifying information
        self.assertIn("pytest", str_repr)
        # Should indicate it's a check run
        self.assertTrue(len(str_repr) > 0)


class TestPRFileModel(TestCase):
    """Tests for PRFile model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = Team.objects.create(name="Test Team", slug="test-team")
        self.author = TeamMember.objects.create(
            team=self.team,
            display_name="John Doe",
            github_username="johndoe",
            github_id="123",
        )
        self.pull_request = PullRequest.objects.create(
            team=self.team,
            github_pr_id=1,
            github_repo="org/repo",
            title="Test PR",
            author=self.author,
            state="open",
            pr_created_at=django_timezone.now(),
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_pr_file_creation(self):
        """Test that PRFile can be created with all required fields."""
        pr_file = PRFile.objects.create(
            team=self.team,
            pull_request=self.pull_request,
            filename="src/components/Button.tsx",
            status="modified",
            additions=10,
            deletions=5,
            changes=15,
            file_category="frontend",
        )
        self.assertEqual(pr_file.filename, "src/components/Button.tsx")
        self.assertEqual(pr_file.status, "modified")
        self.assertEqual(pr_file.additions, 10)
        self.assertEqual(pr_file.deletions, 5)
        self.assertEqual(pr_file.changes, 15)
        self.assertEqual(pr_file.file_category, "frontend")
        self.assertIsNotNone(pr_file.pk)

    def test_pr_file_pull_request_relationship(self):
        """Test that PRFile has correct foreign key relationship with PullRequest."""
        file1 = PRFile.objects.create(
            team=self.team,
            pull_request=self.pull_request,
            filename="src/app.py",
            status="modified",
            additions=20,
            deletions=10,
            changes=30,
            file_category="backend",
        )
        file2 = PRFile.objects.create(
            team=self.team,
            pull_request=self.pull_request,
            filename="README.md",
            status="modified",
            additions=5,
            deletions=2,
            changes=7,
            file_category="docs",
        )

        # Test forward relationship
        self.assertEqual(file1.pull_request, self.pull_request)
        self.assertEqual(file2.pull_request, self.pull_request)

        # Test reverse relationship via related_name='files'
        files = self.pull_request.files.all()
        self.assertEqual(files.count(), 2)
        self.assertIn(file1, files)
        self.assertIn(file2, files)

    def test_pr_file_unique_constraint(self):
        """Test that unique constraint on (team, pull_request, filename) is enforced."""
        PRFile.objects.create(
            team=self.team,
            pull_request=self.pull_request,
            filename="src/utils.py",
            status="added",
            additions=100,
            deletions=0,
            changes=100,
            file_category="backend",
        )
        # Attempt to create another file with same team, pull_request, and filename
        with self.assertRaises(IntegrityError):
            PRFile.objects.create(
                team=self.team,
                pull_request=self.pull_request,
                filename="src/utils.py",
                status="modified",
                additions=10,
                deletions=5,
                changes=15,
                file_category="backend",
            )

    def test_pr_file_categorize_frontend(self):
        """Test that frontend files are categorized correctly."""
        self.assertEqual(PRFile.categorize_file("src/App.tsx"), "frontend")
        self.assertEqual(PRFile.categorize_file("components/Button.jsx"), "frontend")
        self.assertEqual(PRFile.categorize_file("pages/Home.vue"), "frontend")
        self.assertEqual(PRFile.categorize_file("styles/main.css"), "frontend")
        self.assertEqual(PRFile.categorize_file("styles/app.scss"), "frontend")
        self.assertEqual(PRFile.categorize_file("templates/index.html"), "frontend")

    def test_pr_file_categorize_backend(self):
        """Test that backend files are categorized correctly."""
        self.assertEqual(PRFile.categorize_file("src/app.py"), "backend")
        self.assertEqual(PRFile.categorize_file("main.go"), "backend")
        self.assertEqual(PRFile.categorize_file("src/Main.java"), "backend")
        self.assertEqual(PRFile.categorize_file("app/controllers/user.rb"), "backend")
        self.assertEqual(PRFile.categorize_file("src/lib.rs"), "backend")

    def test_pr_file_categorize_test(self):
        """Test that test files are categorized correctly."""
        self.assertEqual(PRFile.categorize_file("src/app_test.py"), "test")
        self.assertEqual(PRFile.categorize_file("test_utils.py"), "test")
        self.assertEqual(PRFile.categorize_file("tests/integration_test.go"), "test")
        self.assertEqual(PRFile.categorize_file("components/Button.spec.tsx"), "test")
        self.assertEqual(PRFile.categorize_file("app.spec.js"), "test")

    def test_pr_file_categorize_docs(self):
        """Test that documentation files are categorized correctly."""
        self.assertEqual(PRFile.categorize_file("README.md"), "docs")
        self.assertEqual(PRFile.categorize_file("docs/setup.rst"), "docs")
        self.assertEqual(PRFile.categorize_file("CHANGELOG.txt"), "docs")

    def test_pr_file_categorize_config(self):
        """Test that configuration files are categorized correctly."""
        self.assertEqual(PRFile.categorize_file("package.json"), "config")
        self.assertEqual(PRFile.categorize_file("config.yaml"), "config")
        self.assertEqual(PRFile.categorize_file("settings.yml"), "config")
        self.assertEqual(PRFile.categorize_file("pyproject.toml"), "config")
        self.assertEqual(PRFile.categorize_file("setup.ini"), "config")
        self.assertEqual(PRFile.categorize_file(".env"), "config")

    def test_pr_file_categorize_other(self):
        """Test that unrecognized files are categorized as 'other'."""
        self.assertEqual(PRFile.categorize_file("data.csv"), "other")
        self.assertEqual(PRFile.categorize_file("image.png"), "other")
        self.assertEqual(PRFile.categorize_file("unknown.xyz"), "other")


class TestDeploymentModel(TestCase):
    """Tests for Deployment model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = Team.objects.create(name="Test Team", slug="test-team")
        self.creator = TeamMember.objects.create(
            team=self.team,
            display_name="John Doe",
            github_username="johndoe",
            github_id="123",
        )
        self.author = TeamMember.objects.create(
            team=self.team,
            display_name="Jane Smith",
            github_username="janesmith",
            github_id="456",
        )
        self.pull_request = PullRequest.objects.create(
            team=self.team,
            github_pr_id=1,
            github_repo="org/repo",
            title="Test PR",
            author=self.author,
            state="merged",
            pr_created_at=django_timezone.now(),
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_deployment_creation(self):
        """Test that Deployment can be created with all fields."""
        deployment = Deployment.objects.create(
            team=self.team,
            github_deployment_id=123456789,
            github_repo="org/repo",
            environment="production",
            status="success",
            creator=self.creator,
            deployed_at=django_timezone.now(),
            pull_request=self.pull_request,
            sha="a" * 40,
        )
        self.assertEqual(deployment.github_deployment_id, 123456789)
        self.assertEqual(deployment.github_repo, "org/repo")
        self.assertEqual(deployment.environment, "production")
        self.assertEqual(deployment.status, "success")
        self.assertEqual(deployment.creator, self.creator)
        self.assertEqual(deployment.pull_request, self.pull_request)
        self.assertEqual(deployment.sha, "a" * 40)
        self.assertIsNotNone(deployment.deployed_at)
        self.assertIsNotNone(deployment.pk)

    def test_deployment_team_relationship(self):
        """Test that deployment belongs to team."""
        deployment = Deployment.objects.create(
            team=self.team,
            github_deployment_id=987654321,
            github_repo="org/repo",
            environment="staging",
            status="success",
            deployed_at=django_timezone.now(),
            sha="b" * 40,
        )
        self.assertEqual(deployment.team, self.team)

        # Test team filtering
        team2 = Team.objects.create(name="Team Two", slug="team-two")
        deployment2 = Deployment.objects.create(
            team=team2,
            github_deployment_id=111111111,
            github_repo="org/other-repo",
            environment="production",
            status="success",
            deployed_at=django_timezone.now(),
            sha="c" * 40,
        )

        team1_deployments = Deployment.objects.filter(team=self.team)
        self.assertEqual(team1_deployments.count(), 1)
        self.assertIn(deployment, team1_deployments)
        self.assertNotIn(deployment2, team1_deployments)

    def test_deployment_unique_constraint(self):
        """Test that unique constraint on (team, github_deployment_id) is enforced."""
        Deployment.objects.create(
            team=self.team,
            github_deployment_id=999,
            github_repo="org/repo",
            environment="production",
            status="success",
            deployed_at=django_timezone.now(),
            sha="d" * 40,
        )
        # Attempt to create another deployment with same github_deployment_id in same team
        with self.assertRaises(IntegrityError):
            Deployment.objects.create(
                team=self.team,
                github_deployment_id=999,
                github_repo="org/other-repo",
                environment="staging",
                status="failure",
                deployed_at=django_timezone.now(),
                sha="e" * 40,
            )

    def test_deployment_str_representation(self):
        """Test that __str__ returns meaningful string."""
        deployment = Deployment.objects.create(
            team=self.team,
            github_deployment_id=555,
            github_repo="org/frontend",
            environment="production",
            status="success",
            deployed_at=django_timezone.now(),
            sha="f" * 40,
        )
        str_repr = str(deployment)
        # Should contain repo and environment at minimum
        self.assertIn("org/frontend", str_repr)
        self.assertIn("production", str_repr)

    def test_deployment_creator_relationship(self):
        """Test optional FK to TeamMember for creator."""
        # Test with creator
        deployment_with_creator = Deployment.objects.create(
            team=self.team,
            github_deployment_id=777,
            github_repo="org/repo",
            environment="staging",
            status="success",
            creator=self.creator,
            deployed_at=django_timezone.now(),
            sha="g" * 40,
        )
        self.assertEqual(deployment_with_creator.creator, self.creator)

        # Test without creator (null=True)
        deployment_no_creator = Deployment.objects.create(
            team=self.team,
            github_deployment_id=888,
            github_repo="org/repo",
            environment="production",
            status="success",
            deployed_at=django_timezone.now(),
            sha="h" * 40,
        )
        self.assertIsNone(deployment_no_creator.creator)

    def test_deployment_pull_request_relationship(self):
        """Test optional FK to PullRequest."""
        # Test with pull_request
        deployment_with_pr = Deployment.objects.create(
            team=self.team,
            github_deployment_id=333,
            github_repo="org/repo",
            environment="production",
            status="success",
            pull_request=self.pull_request,
            deployed_at=django_timezone.now(),
            sha="i" * 40,
        )
        self.assertEqual(deployment_with_pr.pull_request, self.pull_request)

        # Test without pull_request (null=True)
        deployment_no_pr = Deployment.objects.create(
            team=self.team,
            github_deployment_id=444,
            github_repo="org/repo",
            environment="staging",
            status="success",
            deployed_at=django_timezone.now(),
            sha="j" * 40,
        )
        self.assertIsNone(deployment_no_pr.pull_request)


class TestPRCommentModel(TestCase):
    """Tests for PRComment model."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = Team.objects.create(name="Test Team", slug="test-team")
        self.author = TeamMember.objects.create(
            team=self.team,
            display_name="John Doe",
            github_username="johndoe",
            github_id="123",
        )
        self.reviewer = TeamMember.objects.create(
            team=self.team,
            display_name="Jane Smith",
            github_username="janesmith",
            github_id="456",
        )
        self.pull_request = PullRequest.objects.create(
            team=self.team,
            github_pr_id=1,
            github_repo="org/repo",
            title="Test PR",
            author=self.author,
            state="open",
            pr_created_at=django_timezone.now(),
        )

    def tearDown(self):
        """Clean up team context."""
        unset_current_team()

    def test_pr_comment_creation(self):
        """Test that PRComment can be created with all required fields."""
        comment_created = django_timezone.now()
        comment_updated = comment_created + django_timezone.timedelta(hours=1)

        comment = PRComment.objects.create(
            team=self.team,
            github_comment_id=12345,
            pull_request=self.pull_request,
            author=self.author,
            body="This is a test comment",
            comment_type="issue",
            comment_created_at=comment_created,
            comment_updated_at=comment_updated,
        )
        self.assertEqual(comment.github_comment_id, 12345)
        self.assertEqual(comment.pull_request, self.pull_request)
        self.assertEqual(comment.author, self.author)
        self.assertEqual(comment.body, "This is a test comment")
        self.assertEqual(comment.comment_type, "issue")
        self.assertIsNone(comment.path)
        self.assertIsNone(comment.line)
        self.assertIsNone(comment.in_reply_to_id)
        self.assertEqual(comment.comment_created_at, comment_created)
        self.assertEqual(comment.comment_updated_at, comment_updated)
        self.assertIsNotNone(comment.pk)

    def test_pr_comment_team_relationship(self):
        """Test that PRComment belongs to the correct team."""
        comment = PRComment.objects.create(
            team=self.team,
            github_comment_id=12345,
            pull_request=self.pull_request,
            author=self.author,
            body="Team test comment",
            comment_type="issue",
            comment_created_at=django_timezone.now(),
        )
        self.assertEqual(comment.team, self.team)

    def test_pr_comment_unique_constraint(self):
        """Test that unique constraint on (team, github_comment_id) is enforced."""
        PRComment.objects.create(
            team=self.team,
            github_comment_id=99999,
            pull_request=self.pull_request,
            author=self.author,
            body="First comment",
            comment_type="issue",
            comment_created_at=django_timezone.now(),
        )
        # Attempt to create another comment with same team and github_comment_id
        with self.assertRaises(IntegrityError):
            PRComment.objects.create(
                team=self.team,
                github_comment_id=99999,
                pull_request=self.pull_request,
                author=self.reviewer,
                body="Duplicate comment",
                comment_type="issue",
                comment_created_at=django_timezone.now(),
            )

    def test_pr_comment_str_representation(self):
        """Test that PRComment __str__ returns meaningful string."""
        comment = PRComment.objects.create(
            team=self.team,
            github_comment_id=12345,
            pull_request=self.pull_request,
            author=self.author,
            body="This is a very long comment body that should be truncated in the string representation",
            comment_type="issue",
            comment_created_at=django_timezone.now(),
        )
        str_repr = str(comment)
        self.assertIsNotNone(str_repr)
        self.assertNotEqual(str_repr, "")
        # Should contain some identifying information
        self.assertTrue(
            "comment" in str_repr.lower() or "12345" in str_repr or str(self.pull_request.github_pr_id) in str_repr
        )

    def test_pr_comment_author_relationship(self):
        """Test that PRComment has correct optional FK relationship with TeamMember."""
        # Test with author
        comment_with_author = PRComment.objects.create(
            team=self.team,
            github_comment_id=11111,
            pull_request=self.pull_request,
            author=self.author,
            body="Comment with author",
            comment_type="issue",
            comment_created_at=django_timezone.now(),
        )
        self.assertEqual(comment_with_author.author, self.author)

        # Test without author (null=True)
        comment_no_author = PRComment.objects.create(
            team=self.team,
            github_comment_id=22222,
            pull_request=self.pull_request,
            author=None,
            body="Comment without author",
            comment_type="issue",
            comment_created_at=django_timezone.now(),
        )
        self.assertIsNone(comment_no_author.author)

    def test_pr_comment_pull_request_relationship(self):
        """Test that PRComment has correct required FK relationship with PullRequest."""
        comment1 = PRComment.objects.create(
            team=self.team,
            github_comment_id=33333,
            pull_request=self.pull_request,
            author=self.author,
            body="First comment on PR",
            comment_type="issue",
            comment_created_at=django_timezone.now(),
        )
        comment2 = PRComment.objects.create(
            team=self.team,
            github_comment_id=44444,
            pull_request=self.pull_request,
            author=self.reviewer,
            body="Second comment on PR",
            comment_type="review",
            path="src/app.py",
            line=42,
            comment_created_at=django_timezone.now(),
        )

        # Test forward relationship
        self.assertEqual(comment1.pull_request, self.pull_request)
        self.assertEqual(comment2.pull_request, self.pull_request)

        # Test reverse relationship via related_name='comments'
        comments = self.pull_request.comments.all()
        self.assertEqual(comments.count(), 2)
        self.assertIn(comment1, comments)
        self.assertIn(comment2, comments)

    def test_pr_comment_type_choices(self):
        """Test that PRComment validates comment_type choices (issue vs review)."""
        # Test "issue" type
        issue_comment = PRComment.objects.create(
            team=self.team,
            github_comment_id=55555,
            pull_request=self.pull_request,
            author=self.author,
            body="Issue comment",
            comment_type="issue",
            comment_created_at=django_timezone.now(),
        )
        self.assertEqual(issue_comment.comment_type, "issue")

        # Test "review" type
        review_comment = PRComment.objects.create(
            team=self.team,
            github_comment_id=66666,
            pull_request=self.pull_request,
            author=self.reviewer,
            body="Review comment",
            comment_type="review",
            path="src/utils.py",
            line=10,
            comment_created_at=django_timezone.now(),
        )
        self.assertEqual(review_comment.comment_type, "review")

    def test_pr_comment_review_fields(self):
        """Test that path and line fields work correctly for review comments."""
        # Review comment with path and line
        review_comment = PRComment.objects.create(
            team=self.team,
            github_comment_id=77777,
            pull_request=self.pull_request,
            author=self.reviewer,
            body="Please fix this line",
            comment_type="review",
            path="src/components/Button.tsx",
            line=25,
            comment_created_at=django_timezone.now(),
        )
        self.assertEqual(review_comment.path, "src/components/Button.tsx")
        self.assertEqual(review_comment.line, 25)

        # Issue comment without path and line
        issue_comment = PRComment.objects.create(
            team=self.team,
            github_comment_id=88888,
            pull_request=self.pull_request,
            author=self.author,
            body="General comment",
            comment_type="issue",
            comment_created_at=django_timezone.now(),
        )
        self.assertIsNone(issue_comment.path)
        self.assertIsNone(issue_comment.line)

        # Review comment with in_reply_to_id for threaded comments
        reply_comment = PRComment.objects.create(
            team=self.team,
            github_comment_id=99998,
            pull_request=self.pull_request,
            author=self.author,
            body="Thanks for the feedback",
            comment_type="review",
            path="src/components/Button.tsx",
            line=25,
            in_reply_to_id=77777,
            comment_created_at=django_timezone.now(),
        )
        self.assertEqual(reply_comment.in_reply_to_id, 77777)
