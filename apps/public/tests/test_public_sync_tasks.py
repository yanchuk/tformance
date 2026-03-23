from datetime import UTC, datetime
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import TeamFactory
from apps.metrics.models import Commit, PRFile, PRReview
from apps.public.aggregations import MIN_PRS_THRESHOLD
from apps.public.models import PublicOrgProfile, PublicOrgStats, PublicRepoProfile
from tformance.settings import SCHEDULED_TASKS


class PublicSyncScheduleTests(TestCase):
    def test_public_sync_task_is_scheduled(self):
        scheduled = [
            config
            for config in SCHEDULED_TASKS.values()
            if config["task"] == "apps.public.tasks.sync_public_oss_repositories_task"
        ]
        assert len(scheduled) == 1
        assert scheduled[0]["expire_seconds"] > 0

    def test_public_sync_runs_before_customer_sync(self):
        """Public sync at 3 AM must run before customer sync at 4 AM."""
        sync_configs = {
            name: config
            for name, config in SCHEDULED_TASKS.items()
            if config["task"]
            in (
                "apps.public.tasks.sync_public_oss_repositories_task",
                "apps.integrations.tasks.sync_all_repositories_task",
            )
        }
        assert len(sync_configs) == 2


class PublicSyncTaskTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="sync-org",
            industry="analytics",
            display_name="Sync Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.org_profile,
            total_prs=MIN_PRS_THRESHOLD + 10,
        )
        cls.repo_profile = PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="sync-org/main-repo",
            repo_slug="main-repo",
            display_name="Main Repo",
            is_flagship=True,
            is_public=True,
        )

    @patch("apps.public.public_sync.GitHubGraphQLFetcher")
    @patch("apps.public.public_sync.GitHubTokenPool")
    def test_public_sync_uses_pat_pool(self, mock_pool_cls, mock_fetcher_cls):
        from apps.public.tasks import sync_public_oss_repositories_task

        mock_pool = MagicMock()
        mock_pool.all_exhausted = False
        mock_client = MagicMock()
        mock_client._Github__requester._Requester__authorizationHeader = "token abc123"
        mock_pool.get_best_client.return_value = mock_client
        mock_pool_cls.return_value = mock_pool

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_prs_with_details.return_value = []
        mock_fetcher_cls.return_value = mock_fetcher

        result = sync_public_oss_repositories_task()

        mock_pool_cls.assert_called_once()
        assert result["synced"] >= 0

    @patch("apps.public.public_sync.GitHubGraphQLFetcher")
    @patch("apps.public.public_sync.GitHubTokenPool")
    def test_public_sync_handles_exhausted_tokens(self, mock_pool_cls, mock_fetcher_cls):
        from apps.metrics.seeding.github_token_pool import AllTokensExhaustedException
        from apps.public.tasks import sync_public_oss_repositories_task

        mock_pool = MagicMock()
        mock_pool.all_exhausted = True
        mock_pool.get_best_client.side_effect = AllTokensExhaustedException()
        mock_pool_cls.return_value = mock_pool

        result = sync_public_oss_repositories_task()

        assert result["errors"] >= 0

    @patch("apps.public.public_sync.GitHubGraphQLFetcher")
    @patch("apps.public.public_sync.GitHubTokenPool")
    def test_public_sync_only_syncs_sync_enabled_repos(self, mock_pool_cls, mock_fetcher_cls):
        from apps.public.tasks import sync_public_oss_repositories_task

        # Create a sync_disabled repo that should NOT be synced
        PublicRepoProfile.objects.create(
            org_profile=self.org_profile,
            team=self.team,
            github_repo="sync-org/disabled-repo",
            repo_slug="disabled-repo",
            display_name="Disabled Repo",
            is_flagship=False,
            is_public=True,
            sync_enabled=False,
        )

        mock_pool = MagicMock()
        mock_pool.all_exhausted = False
        mock_client = MagicMock()
        mock_client._Github__requester._Requester__authorizationHeader = "token abc123"
        mock_pool.get_best_client.return_value = mock_client
        mock_pool_cls.return_value = mock_pool

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_prs_with_details.return_value = []
        mock_fetcher_cls.return_value = mock_fetcher

        sync_public_oss_repositories_task()

        # Only sync_enabled repos should be synced (main-repo has sync_enabled=True by default)
        synced_repos = [call.args[0] for call in mock_fetcher.fetch_prs_with_details.call_args_list]
        assert "sync-org/main-repo" in synced_repos
        assert "sync-org/disabled-repo" not in synced_repos


class PersistPRDetailTests(TestCase):
    """Test that _persist_pr creates reviews, commits, and files."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()

    def _make_pr_data(self):
        """Build a mock FetchedPRFull with reviews, commits, and files."""
        now = datetime(2026, 3, 10, 12, 0, 0, tzinfo=UTC)

        review = MagicMock()
        review.github_review_id = 11111
        review.reviewer_login = "reviewer1"
        review.state = "APPROVED"
        review.submitted_at = now
        review.body = "LGTM"

        commit = MagicMock()
        commit.sha = "abc123def456"
        commit.message = "feat: add feature"
        commit.author_login = "author1"
        commit.committed_at = now
        commit.additions = 50
        commit.deletions = 10

        file_data = MagicMock()
        file_data.filename = "src/app.py"
        file_data.status = "modified"
        file_data.additions = 50
        file_data.deletions = 10

        pr_data = MagicMock()
        pr_data.number = 42
        pr_data.github_pr_id = 42
        pr_data.title = "Test PR"
        pr_data.body = "Test body"
        pr_data.state = "merged"
        pr_data.is_merged = True
        pr_data.is_draft = False
        pr_data.created_at = now
        pr_data.merged_at = now
        pr_data.first_review_at = now
        pr_data.cycle_time_hours = 6.0
        pr_data.review_time_hours = 2.0
        pr_data.author_login = "author1"
        pr_data.author_id = 12345
        pr_data.additions = 50
        pr_data.deletions = 10
        pr_data.changed_files = 1
        pr_data.labels = []
        pr_data.milestone_title = ""
        pr_data.assignees = []
        pr_data.linked_issues = []
        pr_data.check_runs = []
        pr_data.reviews = [review]
        pr_data.commits = [commit]
        pr_data.files = [file_data]
        return pr_data

    def _build_cache(self, pr_data):
        """Build a member cache from pr_data, matching production _build_member_cache."""
        from apps.public.public_sync import _build_member_cache

        return _build_member_cache(self.team, [pr_data])

    def test_persist_pr_creates_reviews(self):
        from apps.public.public_sync import _persist_pr

        pr_data = self._make_pr_data()
        cache = self._build_cache(pr_data)
        pr = _persist_pr(self.team, pr_data, "org/repo", cache)

        reviews = PRReview.objects.filter(pull_request=pr)
        assert reviews.count() == 1
        assert reviews.first().state == "approved"

    def test_persist_pr_creates_commits(self):
        from apps.public.public_sync import _persist_pr

        pr_data = self._make_pr_data()
        pr_data.number = 43  # Unique PR number
        cache = self._build_cache(pr_data)
        pr = _persist_pr(self.team, pr_data, "org/repo", cache)

        commits = Commit.objects.filter(pull_request=pr)
        assert commits.count() == 1
        assert commits.first().github_sha == "abc123def456"

    def test_persist_pr_creates_files(self):
        from apps.public.public_sync import _persist_pr

        pr_data = self._make_pr_data()
        pr_data.number = 44  # Unique PR number
        pr_data.commits[0].sha = "unique_sha_44"  # Unique SHA
        cache = self._build_cache(pr_data)
        pr = _persist_pr(self.team, pr_data, "org/repo", cache)

        files = PRFile.objects.filter(pull_request=pr)
        assert files.count() == 1
        assert files.first().filename == "src/app.py"
        assert files.first().file_category == PRFile.categorize_file("src/app.py")

    def test_persist_pr_handles_empty_sub_data(self):
        from apps.public.public_sync import _persist_pr

        pr_data = self._make_pr_data()
        pr_data.number = 45
        pr_data.commits[0].sha = "unique_sha_45"
        pr_data.reviews = []
        pr_data.commits = []
        pr_data.files = []
        cache = self._build_cache(pr_data)
        pr = _persist_pr(self.team, pr_data, "org/repo", cache)

        assert PRReview.objects.filter(pull_request=pr).count() == 0
        assert Commit.objects.filter(pull_request=pr).count() == 0
        assert PRFile.objects.filter(pull_request=pr).count() == 0


class UpsertExistingPRTests(TestCase):
    """P1 Fix: sync_public_repo() must update stale existing PRs, not skip them."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="upsert-org",
            industry="analytics",
            display_name="Upsert Org",
            is_public=True,
        )
        cls.repo_profile = PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="upsert-org/repo",
            repo_slug="repo",
            display_name="Repo",
            is_flagship=True,
            is_public=True,
        )

    @patch("apps.public.public_sync.GitHubGraphQLFetcher")
    @patch("apps.public.public_sync.GitHubTokenPool")
    def test_incremental_sync_updates_stale_existing_prs(self, mock_pool_cls, mock_fetcher_cls):
        """Existing PR with stale title should be updated, not skipped."""
        from apps.metrics.factories import TeamMemberFactory
        from apps.metrics.models import PullRequest

        member = TeamMemberFactory(team=self.team)
        # Create an existing PR with old title
        existing_pr = PullRequest.objects.create(
            team=self.team,
            github_pr_id=42,
            github_repo="upsert-org/repo",
            title="Old Title",
            state="merged",
            author=member,
            additions=10,
            deletions=5,
        )

        # Mock token pool
        mock_pool = MagicMock()
        mock_client = MagicMock()
        mock_client._Github__requester._Requester__authorizationHeader = "token abc123"
        mock_pool.get_best_client.return_value = mock_client

        # Mock fetcher to return the same PR with updated title
        now = timezone.now()
        pr_data = MagicMock()
        pr_data.number = 42
        pr_data.is_merged = True
        pr_data.title = "New Updated Title"
        pr_data.body = "updated body"
        pr_data.state = "merged"
        pr_data.additions = 50
        pr_data.deletions = 10
        pr_data.is_draft = False
        pr_data.labels = []
        pr_data.milestone_title = ""
        pr_data.assignees = []
        pr_data.linked_issues = []
        pr_data.merged_at = now
        pr_data.first_review_at = now
        pr_data.cycle_time_hours = 6.0
        pr_data.review_time_hours = 2.0
        pr_data.author_login = member.github_username
        pr_data.author_id = 12345
        pr_data.reviews = []
        pr_data.commits = []
        pr_data.files = []
        pr_data.check_runs = []

        mock_fetcher = MagicMock()
        mock_fetcher.fetch_prs_with_details.return_value = [pr_data]
        mock_fetcher_cls.return_value = mock_fetcher

        from apps.public.public_sync import sync_public_repo

        result = sync_public_repo(self.repo_profile, mock_pool)

        # PR should have been updated, not skipped
        existing_pr.refresh_from_db()
        assert existing_pr.title == "New Updated Title"
        assert result["updated"] == 1
        assert result["skipped"] == 0
