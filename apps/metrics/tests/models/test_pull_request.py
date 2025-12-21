from decimal import Decimal

from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone as django_timezone

from apps.metrics.models import (
    PullRequest,
    TeamMember,
)
from apps.teams.context import current_team, get_current_team, set_current_team, unset_current_team
from apps.teams.models import Team


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
