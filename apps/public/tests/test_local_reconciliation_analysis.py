"""Tests for read-only DB-vs-cache reconciliation analysis."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.metrics.factories import TeamFactory
from apps.metrics.models import Commit, PRReview, PullRequest, TeamMember
from apps.public.models import PublicOrgProfile
from apps.public.services.local_reconciliation import LocalReconciliationService, RepoReconciliationReport


def _make_fetched_pr(github_pr_id, **overrides):
    """Build a minimal FetchedPRFull-compatible mock."""
    now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
    defaults = {
        "github_pr_id": github_pr_id,
        "number": github_pr_id,
        "github_repo": "org/repo",
        "title": f"PR #{github_pr_id}",
        "body": "Test body",
        "state": "merged",
        "is_merged": True,
        "is_draft": False,
        "created_at": now - timedelta(hours=48),
        "updated_at": now,
        "merged_at": now - timedelta(hours=1),
        "closed_at": now - timedelta(hours=1),
        "additions": 100,
        "deletions": 50,
        "changed_files": 5,
        "commits_count": 2,
        "author_login": "dev1",
        "author_id": 1000 + github_pr_id,
        "author_name": "Developer",
        "author_avatar_url": None,
        "head_ref": "feature",
        "base_ref": "main",
        "labels": [],
        "commits": [],
        "reviews": [],
        "files": [],
        "check_runs": [],
        "jira_key_from_title": None,
        "jira_key_from_branch": None,
        "milestone_title": None,
        "assignees": [],
        "linked_issues": [],
    }
    defaults.update(overrides)
    return MagicMock(**defaults)


class ReadyRepoClassificationTests(TestCase):
    """Test that repos with sufficient DB coverage are classified as ready."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="test-org",
            industry="analytics",
            display_name="Test Org",
            is_public=True,
        )
        # Create 10 PRs in DB (>= 70% of 10 cache PRs)
        now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
        member = TeamMember.objects.create(team=cls.team, github_username="dev1", github_id=1000)
        for i in range(10):
            pr = PullRequest.objects.create(
                team=cls.team,
                github_pr_id=100 + i,
                github_repo="org/repo",
                title=f"PR #{100 + i}",
                body="Test body",
                state="merged",
                merged_at=now - timedelta(days=i),
                pr_created_at=now - timedelta(days=i + 2),
                additions=100,
                deletions=50,
                is_draft=False,
                labels=[],
                milestone_title="",
                assignees=[],
                linked_issues=[],
                author=member,
            )
            # Add children so no gaps
            PRReview.objects.create(
                team=cls.team,
                pull_request=pr,
                github_review_id=2000 + i,
                reviewer=member,
                state="approved",
                submitted_at=now - timedelta(days=i, hours=1),
            )
            Commit.objects.create(
                team=cls.team,
                github_sha=f"sha_{i:04d}",
                github_repo="org/repo",
                pull_request=pr,
                author=member,
                message=f"commit {i}",
                committed_at=now - timedelta(days=i),
            )

    @patch("apps.public.services.local_reconciliation.PRCache")
    @patch("apps.public.services.local_reconciliation.deserialize_cache_prs")
    def test_ready_repo_has_zero_gaps(self, mock_deserialize, mock_cache_cls):
        """A repo where DB has all cache PRs and full children → ready."""
        cache_prs = [_make_fetched_pr(100 + i) for i in range(10)]
        # Give each cache PR 1 review and 1 commit to match DB
        for i, pr in enumerate(cache_prs):
            pr.reviews = [MagicMock(github_review_id=2000 + i)]
            pr.commits = [MagicMock(sha=f"sha_{i:04d}")]
            pr.files = []
            pr.check_runs = []

        mock_cache = MagicMock()
        mock_cache.prs = [{}] * 10  # Raw dicts
        mock_cache_cls.load.return_value = mock_cache
        mock_deserialize.return_value = (cache_prs, 0)

        service = LocalReconciliationService(dry_run=True)
        report = service.analyze_repo(self.team, "org/repo")

        assert isinstance(report, RepoReconciliationReport)
        assert report.missing_pr_count == 0
        assert report.stale_pr_count == 0
        assert report.partial_pr_count == 0
        assert report.db_pr_count == 10
        assert report.cache_pr_count == 10


class MissingPRDetectionTests(TestCase):
    """Test detection of PRs in cache but not in DB."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()

    @patch("apps.public.services.local_reconciliation.PRCache")
    @patch("apps.public.services.local_reconciliation.deserialize_cache_prs")
    def test_cache_pr_not_in_db_is_missing(self, mock_deserialize, mock_cache_cls):
        """A cache PR with no matching DB row → missing."""
        cache_prs = [_make_fetched_pr(999)]
        mock_cache = MagicMock()
        mock_cache.prs = [{}]
        mock_cache_cls.load.return_value = mock_cache
        mock_deserialize.return_value = (cache_prs, 0)

        service = LocalReconciliationService(dry_run=True)
        report = service.analyze_repo(self.team, "org/repo")

        assert report.missing_pr_count == 1
        assert report.db_pr_count == 0
        assert report.cache_pr_count == 1


class StalePRDetectionTests(TestCase):
    """Test detection of stale PRs via material field comparison."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.member = TeamMember.objects.create(team=cls.team, github_username="dev1", github_id=1000)
        now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
        cls.pr = PullRequest.objects.create(
            team=cls.team,
            github_pr_id=500,
            github_repo="org/repo",
            title="Old title",
            body="Old body",
            state="merged",
            merged_at=now,
            pr_created_at=now - timedelta(days=2),
            additions=10,
            deletions=5,
            author=cls.member,
        )

    @patch("apps.public.services.local_reconciliation.PRCache")
    @patch("apps.public.services.local_reconciliation.deserialize_cache_prs")
    def test_different_title_means_stale(self, mock_deserialize, mock_cache_cls):
        """Cache PR with different title than DB → stale."""
        cache_pr = _make_fetched_pr(
            500,
            title="Updated title",
            body="Old body",
            additions=10,
            deletions=5,
        )
        mock_cache = MagicMock()
        mock_cache.prs = [{}]
        mock_cache_cls.load.return_value = mock_cache
        mock_deserialize.return_value = ([cache_pr], 0)

        service = LocalReconciliationService(dry_run=True)
        report = service.analyze_repo(self.team, "org/repo")

        assert report.stale_pr_count == 1
        assert report.missing_pr_count == 0


class PartialPRDetectionTests(TestCase):
    """Test detection of PRs with missing child records."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.member = TeamMember.objects.create(team=cls.team, github_username="dev1", github_id=1000)
        now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
        # PR exists in DB but with no children
        cls.pr = PullRequest.objects.create(
            team=cls.team,
            github_pr_id=600,
            github_repo="org/repo",
            title="PR with missing children",
            body="Test body",
            state="merged",
            merged_at=now,
            pr_created_at=now - timedelta(days=2),
            additions=100,
            deletions=50,
            author=cls.member,
        )

    @patch("apps.public.services.local_reconciliation.PRCache")
    @patch("apps.public.services.local_reconciliation.deserialize_cache_prs")
    def test_pr_with_missing_reviews_is_partial(self, mock_deserialize, mock_cache_cls):
        """PR in DB but cache has reviews that DB doesn't → partial."""
        cache_pr = _make_fetched_pr(
            600,
            title="PR with missing children",
            body="Test body",
            additions=100,
            deletions=50,
        )
        cache_pr.reviews = [MagicMock(github_review_id=3000)]
        cache_pr.commits = [MagicMock(sha="abc123")]
        cache_pr.files = [MagicMock(filename="src/app.py")]
        cache_pr.check_runs = []

        mock_cache = MagicMock()
        mock_cache.prs = [{}]
        mock_cache_cls.load.return_value = mock_cache
        mock_deserialize.return_value = ([cache_pr], 0)

        service = LocalReconciliationService(dry_run=True)
        report = service.analyze_repo(self.team, "org/repo")

        assert report.partial_pr_count == 1
        assert report.missing_pr_count == 0
        assert report.stale_pr_count == 0


class AnalysisNoWritesTests(TestCase):
    """Ensure analysis mode never writes to the database."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()

    @patch("apps.public.services.local_reconciliation.PRCache")
    @patch("apps.public.services.local_reconciliation.deserialize_cache_prs")
    def test_analysis_creates_no_records(self, mock_deserialize, mock_cache_cls):
        """Analysis should not create any PullRequest or child records."""
        cache_prs = [_make_fetched_pr(777)]
        mock_cache = MagicMock()
        mock_cache.prs = [{}]
        mock_cache_cls.load.return_value = mock_cache
        mock_deserialize.return_value = (cache_prs, 0)

        pr_count_before = PullRequest.objects.count()
        review_count_before = PRReview.objects.count()

        service = LocalReconciliationService(dry_run=True)
        service.analyze_repo(self.team, "org/repo")

        assert PullRequest.objects.count() == pr_count_before
        assert PRReview.objects.count() == review_count_before


class CorruptedCacheTests(TestCase):
    """Test that corrupted cache entries are skipped gracefully."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()

    @patch("apps.public.services.local_reconciliation.PRCache")
    @patch("apps.public.services.local_reconciliation.deserialize_cache_prs")
    def test_skipped_cache_entries_counted(self, mock_deserialize, mock_cache_cls):
        """Corrupted cache entries should be skipped with warning count."""
        good_pr = _make_fetched_pr(100)
        mock_cache = MagicMock()
        mock_cache.prs = [{}, {}]  # 2 raw dicts but 1 good + 1 skipped
        mock_cache_cls.load.return_value = mock_cache
        mock_deserialize.return_value = ([good_pr], 1)  # 1 skipped

        service = LocalReconciliationService(dry_run=True)
        report = service.analyze_repo(self.team, "org/repo")

        assert report.skipped_cache_errors == 1
        assert report.cache_pr_count == 1  # Only successfully deserialized
