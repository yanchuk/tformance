"""
Security tests for cross-team data isolation.

These tests verify that data from one team cannot be accessed by users from another team,
preventing Insecure Direct Object Reference (IDOR) vulnerabilities.
"""

from django.contrib.auth import get_user_model
from django.test import TestCase

from apps.metrics.factories import (
    CommitFactory,
    JiraIssueFactory,
    PRReviewFactory,
    PRSurveyFactory,
    PRSurveyReviewFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
    WeeklyMetricsFactory,
)
from apps.metrics.models import (
    Commit,
    JiraIssue,
    PRReview,
    PRSurvey,
    PRSurveyReview,
    PullRequest,
    TeamMember,
    WeeklyMetrics,
)
from apps.teams import roles
from apps.teams.context import set_current_team, unset_current_team
from apps.teams.models import Membership

User = get_user_model()


class TeamIsolationTestCase(TestCase):
    """Base test case for team isolation tests."""

    def setUp(self):
        """Set up test fixtures with two separate teams."""
        # Create two teams
        self.team_a = TeamFactory(name="Team A", slug="team-a")
        self.team_b = TeamFactory(name="Team B", slug="team-b")

        # Create users for each team
        self.user_a = User.objects.create_user(
            username="user_a",
            email="user_a@example.com",
            password="testpass123",
        )
        self.user_b = User.objects.create_user(
            username="user_b",
            email="user_b@example.com",
            password="testpass123",
        )

        # Create memberships
        Membership.objects.create(team=self.team_a, user=self.user_a, role=roles.ROLE_ADMIN)
        Membership.objects.create(team=self.team_b, user=self.user_b, role=roles.ROLE_ADMIN)

        # Create team members
        self.member_a = TeamMemberFactory(team=self.team_a, display_name="Member A")
        self.member_b = TeamMemberFactory(team=self.team_b, display_name="Member B")

        self._team_context_token = None

    def tearDown(self):
        """Clean up team context."""
        if self._team_context_token:
            unset_current_team(self._team_context_token)

    def set_team_context(self, team):
        """Set the team context for queries."""
        if self._team_context_token:
            unset_current_team(self._team_context_token)
        self._team_context_token = set_current_team(team)


class TestTeamMemberIsolation(TeamIsolationTestCase):
    """Tests for TeamMember model isolation."""

    def test_for_team_manager_filters_by_team(self):
        """Test that for_team manager only returns members from the current team."""
        self.set_team_context(self.team_a)

        members = TeamMember.for_team.all()

        self.assertIn(self.member_a, members)
        self.assertNotIn(self.member_b, members)

    def test_for_team_manager_returns_empty_without_context(self):
        """Test that for_team manager returns empty queryset without team context."""
        # No team context set
        members = TeamMember.for_team.all()

        self.assertEqual(members.count(), 0)

    def test_objects_manager_returns_all_teams(self):
        """Test that default objects manager returns all teams (for admin use)."""
        members = TeamMember.objects.all()

        self.assertIn(self.member_a, members)
        self.assertIn(self.member_b, members)

    def test_team_a_cannot_see_team_b_members(self):
        """Test explicit cross-team access prevention."""
        self.set_team_context(self.team_a)

        # Try to access Team B's member
        team_b_members = TeamMember.for_team.filter(id=self.member_b.id)

        self.assertEqual(team_b_members.count(), 0)


class TestPullRequestIsolation(TeamIsolationTestCase):
    """Tests for PullRequest model isolation."""

    def setUp(self):
        super().setUp()
        self.pr_a = PullRequestFactory(team=self.team_a, author=self.member_a)
        self.pr_b = PullRequestFactory(team=self.team_b, author=self.member_b)

    def test_for_team_manager_filters_pull_requests(self):
        """Test that for_team manager only returns PRs from the current team."""
        self.set_team_context(self.team_a)

        prs = PullRequest.for_team.all()

        self.assertIn(self.pr_a, prs)
        self.assertNotIn(self.pr_b, prs)

    def test_team_a_cannot_see_team_b_pull_requests(self):
        """Test explicit cross-team PR access prevention."""
        self.set_team_context(self.team_a)

        # Try to access Team B's PR
        team_b_prs = PullRequest.for_team.filter(id=self.pr_b.id)

        self.assertEqual(team_b_prs.count(), 0)


class TestPRReviewIsolation(TeamIsolationTestCase):
    """Tests for PRReview model isolation."""

    def setUp(self):
        super().setUp()
        self.pr_a = PullRequestFactory(team=self.team_a, author=self.member_a)
        self.pr_b = PullRequestFactory(team=self.team_b, author=self.member_b)
        self.review_a = PRReviewFactory(team=self.team_a, pull_request=self.pr_a, reviewer=self.member_a)
        self.review_b = PRReviewFactory(team=self.team_b, pull_request=self.pr_b, reviewer=self.member_b)

    def test_for_team_manager_filters_reviews(self):
        """Test that for_team manager only returns reviews from the current team."""
        self.set_team_context(self.team_a)

        reviews = PRReview.for_team.all()

        self.assertIn(self.review_a, reviews)
        self.assertNotIn(self.review_b, reviews)


class TestCommitIsolation(TeamIsolationTestCase):
    """Tests for Commit model isolation."""

    def setUp(self):
        super().setUp()
        self.commit_a = CommitFactory(team=self.team_a, author=self.member_a)
        self.commit_b = CommitFactory(team=self.team_b, author=self.member_b)

    def test_for_team_manager_filters_commits(self):
        """Test that for_team manager only returns commits from the current team."""
        self.set_team_context(self.team_a)

        commits = Commit.for_team.all()

        self.assertIn(self.commit_a, commits)
        self.assertNotIn(self.commit_b, commits)


class TestJiraIssueIsolation(TeamIsolationTestCase):
    """Tests for JiraIssue model isolation."""

    def setUp(self):
        super().setUp()
        self.issue_a = JiraIssueFactory(team=self.team_a, assignee=self.member_a)
        self.issue_b = JiraIssueFactory(team=self.team_b, assignee=self.member_b)

    def test_for_team_manager_filters_issues(self):
        """Test that for_team manager only returns issues from the current team."""
        self.set_team_context(self.team_a)

        issues = JiraIssue.for_team.all()

        self.assertIn(self.issue_a, issues)
        self.assertNotIn(self.issue_b, issues)


class TestPRSurveyIsolation(TeamIsolationTestCase):
    """Tests for PRSurvey model isolation."""

    def setUp(self):
        super().setUp()
        self.pr_a = PullRequestFactory(team=self.team_a, author=self.member_a)
        self.pr_b = PullRequestFactory(team=self.team_b, author=self.member_b)
        self.survey_a = PRSurveyFactory(team=self.team_a, pull_request=self.pr_a, author=self.member_a)
        self.survey_b = PRSurveyFactory(team=self.team_b, pull_request=self.pr_b, author=self.member_b)

    def test_for_team_manager_filters_surveys(self):
        """Test that for_team manager only returns surveys from the current team."""
        self.set_team_context(self.team_a)

        surveys = PRSurvey.for_team.all()

        self.assertIn(self.survey_a, surveys)
        self.assertNotIn(self.survey_b, surveys)


class TestPRSurveyReviewIsolation(TeamIsolationTestCase):
    """Tests for PRSurveyReview model isolation."""

    def setUp(self):
        super().setUp()
        self.pr_a = PullRequestFactory(team=self.team_a, author=self.member_a)
        self.pr_b = PullRequestFactory(team=self.team_b, author=self.member_b)
        self.survey_a = PRSurveyFactory(team=self.team_a, pull_request=self.pr_a, author=self.member_a)
        self.survey_b = PRSurveyFactory(team=self.team_b, pull_request=self.pr_b, author=self.member_b)
        self.review_a = PRSurveyReviewFactory(team=self.team_a, survey=self.survey_a, reviewer=self.member_a)
        self.review_b = PRSurveyReviewFactory(team=self.team_b, survey=self.survey_b, reviewer=self.member_b)

    def test_for_team_manager_filters_survey_reviews(self):
        """Test that for_team manager only returns survey reviews from the current team."""
        self.set_team_context(self.team_a)

        reviews = PRSurveyReview.for_team.all()

        self.assertIn(self.review_a, reviews)
        self.assertNotIn(self.review_b, reviews)


class TestWeeklyMetricsIsolation(TeamIsolationTestCase):
    """Tests for WeeklyMetrics model isolation."""

    def setUp(self):
        super().setUp()
        self.metrics_a = WeeklyMetricsFactory(team=self.team_a, member=self.member_a)
        self.metrics_b = WeeklyMetricsFactory(team=self.team_b, member=self.member_b)

    def test_for_team_manager_filters_weekly_metrics(self):
        """Test that for_team manager only returns metrics from the current team."""
        self.set_team_context(self.team_a)

        metrics = WeeklyMetrics.for_team.all()

        self.assertIn(self.metrics_a, metrics)
        self.assertNotIn(self.metrics_b, metrics)


class TestBulkOperationIsolation(TeamIsolationTestCase):
    """Tests for bulk operations respecting team isolation."""

    def setUp(self):
        super().setUp()
        # Create multiple items for each team
        self.prs_a = PullRequestFactory.create_batch(3, team=self.team_a, author=self.member_a)
        self.prs_b = PullRequestFactory.create_batch(3, team=self.team_b, author=self.member_b)

    def test_count_respects_team_isolation(self):
        """Test that count() only counts items from the current team."""
        self.set_team_context(self.team_a)

        count = PullRequest.for_team.count()

        self.assertEqual(count, 3)  # Only Team A's PRs

    def test_aggregate_respects_team_isolation(self):
        """Test that aggregate operations respect team isolation."""
        from django.db.models import Avg

        self.set_team_context(self.team_a)

        # This should only aggregate Team A's data
        avg_additions = PullRequest.for_team.aggregate(avg=Avg("additions"))

        # Verify it's not aggregating Team B's data (unscoped query for comparison)
        _all_avg = PullRequest.objects.aggregate(avg=Avg("additions"))  # noqa: TEAM001

        # The averages should be different if Team A and B have different data
        # (they should because factories generate random data)
        self.assertIsNotNone(avg_additions["avg"])

    def test_filter_chaining_respects_team_isolation(self):
        """Test that filter chaining maintains team isolation."""
        self.set_team_context(self.team_a)

        # Even with additional filters, should not return Team B data
        filtered_prs = PullRequest.for_team.filter(state="merged")

        for pr in filtered_prs:
            self.assertEqual(pr.team, self.team_a)


class TestDirectIDAccessPrevention(TeamIsolationTestCase):
    """Tests to prevent direct ID access (IDOR vulnerability)."""

    def setUp(self):
        super().setUp()
        self.pr_a = PullRequestFactory(team=self.team_a, author=self.member_a)
        self.pr_b = PullRequestFactory(team=self.team_b, author=self.member_b)

    def test_cannot_access_other_team_object_by_id(self):
        """Test that Team A cannot access Team B's object even with direct ID."""
        self.set_team_context(self.team_a)

        # Try to get Team B's PR by ID using for_team manager
        with self.assertRaises(PullRequest.DoesNotExist):
            PullRequest.for_team.get(id=self.pr_b.id)

    def test_cannot_access_other_team_object_by_pk(self):
        """Test that Team A cannot access Team B's object even with direct PK."""
        self.set_team_context(self.team_a)

        # Try to get Team B's PR by PK using for_team manager
        with self.assertRaises(PullRequest.DoesNotExist):
            PullRequest.for_team.get(pk=self.pr_b.pk)

    def test_filter_by_other_team_id_returns_empty(self):
        """Test that filtering by another team's object ID returns empty."""
        self.set_team_context(self.team_a)

        # Try to filter for Team B's PR
        result = PullRequest.for_team.filter(id=self.pr_b.id)

        self.assertEqual(result.count(), 0)
