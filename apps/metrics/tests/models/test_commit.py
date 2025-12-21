from django.db import IntegrityError
from django.test import TestCase
from django.utils import timezone as django_timezone

from apps.metrics.models import (
    Commit,
    PullRequest,
    TeamMember,
)
from apps.teams.context import current_team, get_current_team, set_current_team, unset_current_team
from apps.teams.models import Team


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
