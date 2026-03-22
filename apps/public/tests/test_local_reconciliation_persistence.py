"""Tests for reconciliation persistence (create/update/repair)."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.metrics.factories import TeamFactory
from apps.metrics.models import Commit, PRCheckRun, PRFile, PRReview, PullRequest, TeamMember
from apps.metrics.seeding.github_authenticated_fetcher import (
    FetchedCheckRun,
    FetchedCommit,
    FetchedFile,
    FetchedPRFull,
    FetchedReview,
)
from apps.public.services.local_reconciliation import LocalReconciliationService


def _make_real_fetched_pr(github_pr_id=100, **overrides):
    """Build a real FetchedPRFull with sensible defaults and children."""
    now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
    defaults = dict(
        github_pr_id=github_pr_id,
        number=github_pr_id,
        github_repo="org/repo",
        title=f"PR #{github_pr_id}",
        body="Test body for PR",
        state="merged",
        is_merged=True,
        is_draft=False,
        created_at=now - timedelta(hours=48),
        updated_at=now,
        merged_at=now - timedelta(hours=1),
        closed_at=now - timedelta(hours=1),
        additions=100,
        deletions=50,
        changed_files=5,
        commits_count=2,
        author_login="dev1",
        author_id=1001,
        author_name="Developer 1",
        author_avatar_url=None,
        head_ref="feature",
        base_ref="main",
        labels=["bug"],
        reviews=[
            FetchedReview(
                github_review_id=2000 + github_pr_id,
                reviewer_login="reviewer1",
                state="APPROVED",
                submitted_at=now - timedelta(hours=24),
                body="LGTM",
            ),
        ],
        commits=[
            FetchedCommit(
                sha=f"sha_{github_pr_id:04d}_001",
                message="feat: implement feature",
                author_login="dev1",
                author_name="Developer 1",
                committed_at=now - timedelta(hours=2),
                additions=100,
                deletions=50,
            ),
        ],
        files=[
            FetchedFile(
                filename="src/app.py",
                status="modified",
                additions=100,
                deletions=50,
            ),
        ],
        check_runs=[
            FetchedCheckRun(
                github_id=3000 + github_pr_id,
                name="pytest",
                status="completed",
                conclusion="success",
                started_at=now - timedelta(hours=1, minutes=30),
                completed_at=now - timedelta(hours=1, minutes=25),
            ),
        ],
        milestone_title="v1.0",
        assignees=["dev1"],
        linked_issues=[42],
    )
    defaults.update(overrides)
    return FetchedPRFull(**defaults)


class MissingPRImportTests(TestCase):
    """Test importing PRs that exist in cache but not in DB."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()

    @patch("apps.public.services.local_reconciliation.PRCache")
    @patch("apps.public.services.local_reconciliation.deserialize_cache_prs")
    def test_missing_pr_imported_with_all_children(self, mock_deserialize, mock_cache_cls):
        """Missing PR from cache should be created with reviews, commits, files, check_runs."""
        cache_pr = _make_real_fetched_pr(100)
        mock_cache = MagicMock()
        mock_cache.prs = [{}]
        mock_cache_cls.load.return_value = mock_cache
        mock_deserialize.return_value = ([cache_pr], 0)

        service = LocalReconciliationService(dry_run=False)
        report = service.analyze_repo(self.team, "org/repo")
        service.apply_repo(self.team, "org/repo", report)

        # PR created
        pr = PullRequest.objects.get(team=self.team, github_pr_id=100, github_repo="org/repo")
        assert pr.title == "PR #100"
        assert pr.state == "merged"

        # Children created
        assert PRReview.objects.filter(pull_request=pr).count() == 1
        assert Commit.objects.filter(pull_request=pr).count() == 1
        assert PRFile.objects.filter(pull_request=pr).count() == 1
        assert PRCheckRun.objects.filter(pull_request=pr).count() == 1


class StalePRUpdateTests(TestCase):
    """Test updating stale PRs with changed fields only."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.member = TeamMember.objects.create(team=cls.team, github_username="dev1", github_id=1001)
        now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
        cls.pr = PullRequest.objects.create(
            team=cls.team,
            github_pr_id=200,
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
    def test_stale_pr_updates_changed_fields(self, mock_deserialize, mock_cache_cls):
        """Stale PR should have only changed fields updated."""
        cache_pr = _make_real_fetched_pr(
            200,
            title="Updated title",
            body="Updated body",
            additions=10,
            deletions=5,
        )
        mock_cache = MagicMock()
        mock_cache.prs = [{}]
        mock_cache_cls.load.return_value = mock_cache
        mock_deserialize.return_value = ([cache_pr], 0)

        service = LocalReconciliationService(dry_run=False)
        report = service.analyze_repo(self.team, "org/repo")
        service.apply_repo(self.team, "org/repo", report)

        self.pr.refresh_from_db()
        assert self.pr.title == "Updated title"
        assert self.pr.body == "Updated body"


class PartialPRRepairTests(TestCase):
    """Test repairing PRs with missing child records."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.member = TeamMember.objects.create(team=cls.team, github_username="dev1", github_id=1001)
        now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
        cls.pr = PullRequest.objects.create(
            team=cls.team,
            github_pr_id=300,
            github_repo="org/repo",
            title="PR #300",
            body="Test body for PR",
            state="merged",
            merged_at=now - timedelta(hours=1),
            pr_created_at=now - timedelta(hours=48),
            additions=100,
            deletions=50,
            is_draft=False,
            labels=["bug"],
            milestone_title="v1.0",
            assignees=["dev1"],
            linked_issues=[42],
            author=cls.member,
        )

    @patch("apps.public.services.local_reconciliation.PRCache")
    @patch("apps.public.services.local_reconciliation.deserialize_cache_prs")
    def test_partial_pr_gets_missing_children(self, mock_deserialize, mock_cache_cls):
        """PR in DB with no children should get reviews/commits/files/check_runs added."""
        cache_pr = _make_real_fetched_pr(300)
        mock_cache = MagicMock()
        mock_cache.prs = [{}]
        mock_cache_cls.load.return_value = mock_cache
        mock_deserialize.return_value = ([cache_pr], 0)

        service = LocalReconciliationService(dry_run=False)
        report = service.analyze_repo(self.team, "org/repo")
        assert report.partial_pr_count == 1

        service.apply_repo(self.team, "org/repo", report)

        assert PRReview.objects.filter(pull_request=self.pr).count() >= 1
        assert Commit.objects.filter(pull_request=self.pr).count() >= 1
        assert PRFile.objects.filter(pull_request=self.pr).count() >= 1
        assert PRCheckRun.objects.filter(pull_request=self.pr).count() >= 1


class IdempotencyTests(TestCase):
    """Test that rerunning reconciliation creates zero duplicates."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()

    @patch("apps.public.services.local_reconciliation.PRCache")
    @patch("apps.public.services.local_reconciliation.deserialize_cache_prs")
    def test_rerun_creates_zero_duplicates(self, mock_deserialize, mock_cache_cls):
        """Running apply twice with same data should not create duplicates."""
        cache_pr = _make_real_fetched_pr(400)
        mock_cache = MagicMock()
        mock_cache.prs = [{}]
        mock_cache_cls.load.return_value = mock_cache
        mock_deserialize.return_value = ([cache_pr], 0)

        # First run
        service1 = LocalReconciliationService(dry_run=False)
        report1 = service1.analyze_repo(self.team, "org/repo")
        service1.apply_repo(self.team, "org/repo", report1)

        pr_count_after_first = PullRequest.objects.filter(team=self.team, github_repo="org/repo").count()
        review_count_after_first = PRReview.objects.filter(team=self.team).count()
        commit_count_after_first = Commit.objects.filter(team=self.team).count()

        # Second run
        service2 = LocalReconciliationService(dry_run=False)
        report2 = service2.analyze_repo(self.team, "org/repo")
        # Should detect 0 missing, 0 stale, 0 partial
        assert report2.missing_pr_count == 0

        # Counts unchanged
        assert PullRequest.objects.filter(team=self.team, github_repo="org/repo").count() == pr_count_after_first
        assert PRReview.objects.filter(team=self.team).count() == review_count_after_first
        assert Commit.objects.filter(team=self.team).count() == commit_count_after_first


class TeamMemberReuseTests(TestCase):
    """Test that TeamMembers are reused, not duplicated."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.existing_member = TeamMember.objects.create(team=cls.team, github_username="dev1", github_id=1001)

    @patch("apps.public.services.local_reconciliation.PRCache")
    @patch("apps.public.services.local_reconciliation.deserialize_cache_prs")
    def test_existing_member_reused(self, mock_deserialize, mock_cache_cls):
        """Import should reuse existing TeamMember, not create a new one."""
        cache_pr = _make_real_fetched_pr(500, author_login="dev1")
        mock_cache = MagicMock()
        mock_cache.prs = [{}]
        mock_cache_cls.load.return_value = mock_cache
        mock_deserialize.return_value = ([cache_pr], 0)

        TeamMember.objects.filter(team=self.team).count()

        service = LocalReconciliationService(dry_run=False)
        report = service.analyze_repo(self.team, "org/repo")
        service.apply_repo(self.team, "org/repo", report)

        # dev1 and reviewer1 — reviewer1 is new, dev1 already exists
        assert TeamMember.objects.filter(team=self.team, github_username="dev1").count() == 1


class DeltaReviewImportTests(TestCase):
    """Test that only missing reviews are added, not duplicated."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.member = TeamMember.objects.create(team=cls.team, github_username="dev1", github_id=1001)
        cls.reviewer = TeamMember.objects.create(team=cls.team, github_username="reviewer1", github_id=2001)
        now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
        cls.pr = PullRequest.objects.create(
            team=cls.team,
            github_pr_id=600,
            github_repo="org/repo",
            title="PR #600",
            body="Test body for PR",
            state="merged",
            merged_at=now - timedelta(hours=1),
            pr_created_at=now - timedelta(hours=48),
            additions=100,
            deletions=50,
            is_draft=False,
            labels=["bug"],
            milestone_title="v1.0",
            assignees=["dev1"],
            linked_issues=[42],
            author=cls.member,
        )
        # Existing review
        PRReview.objects.create(
            team=cls.team,
            pull_request=cls.pr,
            github_review_id=2600,
            reviewer=cls.reviewer,
            state="approved",
            submitted_at=now - timedelta(hours=24),
        )

    @patch("apps.public.services.local_reconciliation.PRCache")
    @patch("apps.public.services.local_reconciliation.deserialize_cache_prs")
    def test_delta_reviews_only_adds_new(self, mock_deserialize, mock_cache_cls):
        """Only new reviews should be added, existing ones preserved."""
        now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)
        cache_pr = _make_real_fetched_pr(
            600,
            reviews=[
                FetchedReview(
                    github_review_id=2600,  # Existing
                    reviewer_login="reviewer1",
                    state="APPROVED",
                    submitted_at=now - timedelta(hours=24),
                    body="LGTM",
                ),
                FetchedReview(
                    github_review_id=2601,  # New
                    reviewer_login="reviewer2",
                    state="COMMENTED",
                    submitted_at=now - timedelta(hours=12),
                    body="Nice work",
                ),
            ],
        )
        mock_cache = MagicMock()
        mock_cache.prs = [{}]
        mock_cache_cls.load.return_value = mock_cache
        mock_deserialize.return_value = ([cache_pr], 0)

        service = LocalReconciliationService(dry_run=False)
        report = service.analyze_repo(self.team, "org/repo")
        service.apply_repo(self.team, "org/repo", report)

        # Should have 2 reviews (1 existing + 1 new, not 3)
        reviews = PRReview.objects.filter(pull_request=self.pr)
        assert reviews.count() == 2
        assert reviews.filter(github_review_id=2601).exists()
