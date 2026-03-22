"""Tests for the public sync orchestration pipeline (Task 2).

Covers: manager methods, SyncOrchestrator, backfill/incremental logic,
checkpoint resume, error paths, Redis lock, snapshots, insights guard.
"""

from unittest.mock import MagicMock, patch

from django.core.cache import cache
from django.test import TestCase
from django.utils import timezone

from apps.public.models import (
    PublicOrgProfile,
    PublicRepoProfile,
    PublicRepoStats,
    PublicRepoSyncState,
)
from apps.teams.models import Team


class ManagerMethodTests(TestCase):
    """Step 2.0: sync_eligible() and snapshot_eligible() manager methods."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Mgr Team", slug="mgr-team")
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="mgr-org",
            industry="analytics",
            display_name="Mgr Org",
            is_public=True,
        )
        cls.private_org = PublicOrgProfile.objects.create(
            team=Team.objects.create(name="Private Team", slug="private-team"),
            public_slug="private-org",
            industry="analytics",
            display_name="Private Org",
            is_public=False,
        )

    def test_sync_eligible_returns_public_and_sync_enabled_repos(self):
        # sync_enabled=True, is_public=True → eligible
        eligible = PublicRepoProfile.objects.create(
            org_profile=self.org,
            github_repo="mgr-org/eligible",
            repo_slug="eligible",
            display_name="Eligible",
            sync_enabled=True,
            is_public=True,
        )
        # sync_enabled=False → not eligible
        PublicRepoProfile.objects.create(
            org_profile=self.org,
            github_repo="mgr-org/disabled",
            repo_slug="disabled",
            display_name="Disabled",
            sync_enabled=False,
            is_public=True,
        )
        # is_public=False → not eligible
        PublicRepoProfile.objects.create(
            org_profile=self.org,
            github_repo="mgr-org/private",
            repo_slug="private",
            display_name="Private",
            sync_enabled=True,
            is_public=False,
        )
        result = PublicRepoProfile.objects.sync_eligible()
        assert list(result.values_list("pk", flat=True)) == [eligible.pk]

    def test_snapshot_eligible_returns_public_repos_with_public_orgs(self):
        # public repo + public org → eligible
        eligible = PublicRepoProfile.objects.create(
            org_profile=self.org,
            github_repo="mgr-org/snap-eligible",
            repo_slug="snap-eligible",
            display_name="Snap Eligible",
            is_public=True,
        )
        # public repo + private org → not eligible
        PublicRepoProfile.objects.create(
            org_profile=self.private_org,
            github_repo="private-org/snap-private",
            repo_slug="snap-private",
            display_name="Snap Private",
            is_public=True,
        )
        result = PublicRepoProfile.objects.snapshot_eligible()
        assert list(result.values_list("pk", flat=True)) == [eligible.pk]


class SyncOrchestratorBackfillTests(TestCase):
    """Steps 2.1-2.2: Orchestrator backfill logic."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Orch Team", slug="orch-team")
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="orch-org",
            industry="analytics",
            display_name="Orch Org",
            is_public=True,
        )

    def _make_repo(self, slug, **kwargs):
        defaults = {
            "org_profile": self.org,
            "github_repo": f"orch-org/{slug}",
            "repo_slug": slug,
            "display_name": slug.title(),
            "is_public": True,
            "sync_enabled": True,
        }
        defaults.update(kwargs)
        return PublicRepoProfile.objects.create(**defaults)

    @patch("apps.public.public_sync.sync_public_repo")
    def test_pending_backfill_repo_uses_initial_backfill_days(self, mock_sync):
        mock_sync.return_value = {"fetched": 10, "created": 10, "skipped": 0, "errors": 0}
        repo = self._make_repo("backfill-days", initial_backfill_days=180)
        assert repo.sync_state.status == "pending_backfill"

        from apps.public.services.sync_orchestrator import SyncOrchestrator

        orch = SyncOrchestrator(token_pool=MagicMock())
        orch.sync_repo(repo)

        # Verify sync_public_repo was called with ~180 days and max 2000
        call_kwargs = mock_sync.call_args
        assert call_kwargs[1]["days"] >= 179
        assert call_kwargs[1]["max_prs"] == 2000

    @patch("apps.public.public_sync.sync_public_repo")
    def test_backfill_transitions_to_ready_on_success(self, mock_sync):
        mock_sync.return_value = {"fetched": 100, "created": 100, "skipped": 0, "errors": 0}
        repo = self._make_repo("backfill-ready")

        from apps.public.services.sync_orchestrator import SyncOrchestrator

        orch = SyncOrchestrator(token_pool=MagicMock())
        orch.sync_repo(repo)

        repo.sync_state.refresh_from_db()
        assert repo.sync_state.status == "ready"
        assert repo.sync_state.last_backfill_completed_at is not None
        assert repo.sync_state.last_successful_sync_at is not None

    @patch("apps.public.public_sync.sync_public_repo")
    def test_backfill_stores_checkpoint_when_cap_hit(self, mock_sync):
        mock_sync.return_value = {"fetched": 2000, "created": 2000, "skipped": 0, "errors": 0}
        repo = self._make_repo("backfill-cap")

        from apps.public.services.sync_orchestrator import SyncOrchestrator

        orch = SyncOrchestrator(token_pool=MagicMock())
        orch.sync_repo(repo)

        repo.sync_state.refresh_from_db()
        assert repo.sync_state.status == "pending_backfill"
        assert repo.sync_state.checkpoint_payload != {}
        assert "prs_fetched_so_far" in repo.sync_state.checkpoint_payload

    @patch("apps.public.public_sync.sync_public_repo")
    def test_backfill_resumes_from_checkpoint_on_next_run(self, mock_sync):
        mock_sync.return_value = {"fetched": 50, "created": 50, "skipped": 0, "errors": 0}
        repo = self._make_repo("backfill-resume")
        # Pre-populate checkpoint
        repo.sync_state.checkpoint_payload = {
            "prs_fetched_so_far": 2000,
        }
        repo.sync_state.save()

        from apps.public.services.sync_orchestrator import SyncOrchestrator

        orch = SyncOrchestrator(token_pool=MagicMock())
        orch.sync_repo(repo)

        call_kwargs = mock_sync.call_args[1]
        # Days should use full initial_backfill_days (not a checkpoint date)
        assert call_kwargs["days"] == 180
        # max_prs should be increased to skip past already-persisted PRs
        assert call_kwargs["max_prs"] == 2000 + 2000  # already_fetched + BACKFILL_PR_CAP

    @patch("apps.public.public_sync.sync_public_repo")
    def test_backfill_increases_max_prs_on_resume(self, mock_sync):
        """P1 Fix: resumed backfill must increase max_prs to make forward progress."""
        mock_sync.return_value = {"fetched": 4000, "created": 2000, "skipped": 0, "errors": 0}
        repo = self._make_repo("backfill-progress")
        repo.sync_state.checkpoint_payload = {"prs_fetched_so_far": 2000}
        repo.sync_state.save()

        from apps.public.services.sync_orchestrator import BACKFILL_PR_CAP, SyncOrchestrator

        orch = SyncOrchestrator(token_pool=MagicMock())
        orch.sync_repo(repo)

        call_kwargs = mock_sync.call_args[1]
        assert call_kwargs["max_prs"] == 2000 + BACKFILL_PR_CAP

    @patch("apps.public.public_sync.sync_public_repo")
    def test_backfill_completes_after_resume_when_under_cap(self, mock_sync):
        """P1 Fix: when resumed backfill fetches fewer than extended cap, backfill completes."""
        # First run capped at 2000. Second run: max_prs=4000, but only 3500 exist.
        mock_sync.return_value = {"fetched": 3500, "created": 1500, "skipped": 0, "errors": 0}
        repo = self._make_repo("backfill-complete")
        repo.sync_state.checkpoint_payload = {"prs_fetched_so_far": 2000}
        repo.sync_state.save()

        from apps.public.services.sync_orchestrator import SyncOrchestrator

        orch = SyncOrchestrator(token_pool=MagicMock())
        orch.sync_repo(repo)

        repo.sync_state.refresh_from_db()
        assert repo.sync_state.status == "ready"
        assert repo.sync_state.checkpoint_payload == {}

    @patch("apps.public.public_sync.sync_public_repo")
    def test_backfill_clears_checkpoint_on_completion(self, mock_sync):
        mock_sync.return_value = {"fetched": 50, "created": 50, "skipped": 0, "errors": 0}
        repo = self._make_repo("backfill-clear")
        repo.sync_state.checkpoint_payload = {"resume_from_date": "2025-10-01T00:00:00+00:00"}
        repo.sync_state.save()

        from apps.public.services.sync_orchestrator import SyncOrchestrator

        orch = SyncOrchestrator(token_pool=MagicMock())
        orch.sync_repo(repo)

        repo.sync_state.refresh_from_db()
        assert repo.sync_state.status == "ready"
        assert repo.sync_state.checkpoint_payload == {}


class SyncOrchestratorIncrementalTests(TestCase):
    """Step 2.3: Incremental sync for ready repos."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Inc Team", slug="inc-team")
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="inc-org",
            industry="analytics",
            display_name="Inc Org",
            is_public=True,
        )

    def _make_ready_repo(self, slug, last_synced_days_ago=3):
        from datetime import timedelta

        repo = PublicRepoProfile.objects.create(
            org_profile=self.org,
            github_repo=f"inc-org/{slug}",
            repo_slug=slug,
            display_name=slug.title(),
            is_public=True,
            sync_enabled=True,
        )
        repo.sync_state.status = "ready"
        repo.sync_state.last_synced_updated_at = timezone.now() - timedelta(days=last_synced_days_ago)
        repo.sync_state.last_successful_sync_at = timezone.now() - timedelta(days=last_synced_days_ago)
        repo.sync_state.save()
        return repo

    @patch("apps.public.public_sync.sync_public_repo")
    def test_ready_repo_uses_overlap_window(self, mock_sync):
        mock_sync.return_value = {"fetched": 10, "created": 5, "skipped": 5, "errors": 0}
        repo = self._make_ready_repo("overlap", last_synced_days_ago=3)

        from apps.public.services.sync_orchestrator import SyncOrchestrator

        orch = SyncOrchestrator(token_pool=MagicMock())
        orch.sync_repo(repo)

        call_kwargs = mock_sync.call_args[1]
        # 3 days ago + 14 day overlap = ~17 days
        assert 16 <= call_kwargs["days"] <= 18
        assert call_kwargs["max_prs"] == 500

    @patch("apps.public.public_sync.sync_public_repo")
    def test_incremental_overlap_is_14_days(self, mock_sync):
        """P1 Fix: overlap window must be 14 days to catch long-lived PRs."""
        mock_sync.return_value = {"fetched": 10, "created": 5, "skipped": 5, "errors": 0}
        repo = self._make_ready_repo("overlap-14d", last_synced_days_ago=1)

        from apps.public.services.sync_orchestrator import OVERLAP_DAYS, SyncOrchestrator

        orch = SyncOrchestrator(token_pool=MagicMock())
        orch.sync_repo(repo)

        call_kwargs = mock_sync.call_args[1]
        # 1 day gap + 14 day overlap = 15 days
        assert OVERLAP_DAYS == 14
        assert 14 <= call_kwargs["days"] <= 16

    @patch("apps.public.public_sync.sync_public_repo")
    def test_missed_window_triggers_recovery_backfill(self, mock_sync):
        mock_sync.return_value = {"fetched": 100, "created": 100, "skipped": 0, "errors": 0}
        repo = self._make_ready_repo("missed", last_synced_days_ago=45)

        from apps.public.services.sync_orchestrator import SyncOrchestrator

        orch = SyncOrchestrator(token_pool=MagicMock())
        orch.sync_repo(repo)

        call_kwargs = mock_sync.call_args[1]
        # 45 + 7 = 52 days, max_prs=2000
        assert call_kwargs["days"] >= 50
        assert call_kwargs["max_prs"] == 2000

    @patch("apps.public.public_sync.sync_public_repo")
    def test_sync_state_updated_after_successful_sync(self, mock_sync):
        mock_sync.return_value = {"fetched": 10, "created": 5, "skipped": 5, "errors": 0}
        repo = self._make_ready_repo("updated")

        from apps.public.services.sync_orchestrator import SyncOrchestrator

        orch = SyncOrchestrator(token_pool=MagicMock())
        orch.sync_repo(repo)

        repo.sync_state.refresh_from_db()
        assert repo.sync_state.last_successful_sync_at is not None
        assert repo.sync_state.last_attempted_sync_at is not None
        assert repo.sync_state.status == "ready"

    @patch("apps.public.public_sync.sync_public_repo")
    def test_sync_state_records_error_on_failure(self, mock_sync):
        mock_sync.side_effect = RuntimeError("GitHub API timeout")
        repo = self._make_ready_repo("error")

        from apps.public.services.sync_orchestrator import SyncOrchestrator

        orch = SyncOrchestrator(token_pool=MagicMock())
        orch.sync_repo(repo)

        repo.sync_state.refresh_from_db()
        assert repo.sync_state.status == "failed"
        assert "GitHub API timeout" in repo.sync_state.last_error
        assert repo.sync_state.last_attempted_sync_at is not None


class SyncOrchestratorErrorPathTests(TestCase):
    """Step 2.4: Error path tests."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Err Team", slug="err-team")
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="err-org",
            industry="analytics",
            display_name="Err Org",
            is_public=True,
        )

    @patch("apps.public.public_sync.sync_public_repo")
    def test_token_exhaustion_marks_single_repo_failed_not_batch(self, mock_sync):
        from apps.metrics.seeding.github_token_pool import AllTokensExhaustedException

        mock_sync.side_effect = AllTokensExhaustedException("All tokens exhausted")
        repo = PublicRepoProfile.objects.create(
            org_profile=self.org,
            github_repo="err-org/token-fail",
            repo_slug="token-fail",
            display_name="Token Fail",
        )

        from apps.public.services.sync_orchestrator import SyncOrchestrator

        orch = SyncOrchestrator(token_pool=MagicMock())
        result = orch.sync_repo(repo)

        repo.sync_state.refresh_from_db()
        assert repo.sync_state.status == "failed"
        assert "exhausted" in repo.sync_state.last_error.lower()
        # Should return error result, not raise
        assert result.get("errors", 0) > 0

    def test_orchestrator_creates_sync_state_if_missing(self):
        repo = PublicRepoProfile.objects.create(
            org_profile=self.org,
            github_repo="err-org/no-state",
            repo_slug="no-state",
            display_name="No State",
        )
        # Delete auto-created sync state
        PublicRepoSyncState.objects.filter(repo_profile=repo).delete()

        from apps.public.services.sync_orchestrator import SyncOrchestrator

        orch = SyncOrchestrator(token_pool=MagicMock())
        with patch("apps.public.public_sync.sync_public_repo") as mock_sync:
            mock_sync.return_value = {"fetched": 5, "created": 5, "skipped": 0, "errors": 0}
            orch.sync_repo(repo)

        # Should have created sync state
        assert PublicRepoSyncState.objects.filter(repo_profile=repo).exists()


class SyncTaskLockTests(TestCase):
    """Step 2.5: Celery Redis lock on sync task."""

    @patch("apps.public.tasks.SyncOrchestrator")
    @patch("apps.public.public_sync.GitHubTokenPool")
    def test_concurrent_sync_task_skipped_when_locked(self, mock_pool, mock_orch):
        from apps.public.tasks import sync_public_oss_repositories_task

        # Acquire the lock manually via cache.add()
        cache.add("public_sync_lock", "1", timeout=60)
        try:
            result = sync_public_oss_repositories_task()
            assert result.get("skipped") == "locked"
            mock_orch.assert_not_called()
        finally:
            cache.delete("public_sync_lock")

    @patch("apps.public.tasks.SyncOrchestrator")
    @patch("apps.public.public_sync.GitHubTokenPool")
    def test_sync_task_acquires_and_releases_lock(self, mock_pool, mock_orch):
        from apps.public.tasks import sync_public_oss_repositories_task

        mock_orch_instance = MagicMock()
        mock_orch.return_value = mock_orch_instance

        # Ensure lock is clear
        cache.delete("public_sync_lock")
        sync_public_oss_repositories_task()

        # Lock should be released (cache key should be gone)
        acquired = cache.add("public_sync_lock", "1", timeout=5)
        assert acquired, "Lock was not released after task"
        cache.delete("public_sync_lock")


class ComputeStatsSnapshotTests(TestCase):
    """Step 2.6: Snapshots for ALL public repos."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Snap Team", slug="snap-team")
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="snap-org",
            industry="analytics",
            display_name="Snap Org",
            is_public=True,
        )

    @patch("apps.public.repo_snapshot_service.build_repo_snapshot")
    @patch("apps.public.cloudflare.purge_all_cache")
    def test_compute_stats_builds_snapshots_for_non_flagship_repos(self, mock_purge, mock_snapshot):
        # Non-flagship but public repo should get a snapshot
        repo = PublicRepoProfile.objects.create(
            org_profile=self.org,
            github_repo="snap-org/non-flagship",
            repo_slug="non-flagship",
            display_name="Non Flagship",
            is_flagship=False,
            is_public=True,
        )

        from apps.public.tasks import compute_public_stats_task

        compute_public_stats_task()

        # build_repo_snapshot should have been called with our non-flagship repo
        called_profiles = [call.args[0] for call in mock_snapshot.call_args_list]
        assert any(p.pk == repo.pk for p in called_profiles)


class InsightsGuardTests(TestCase):
    """Step 2.7: Insights require both sync_enabled AND insights_enabled."""

    @classmethod
    def setUpTestData(cls):
        cls.team = Team.objects.create(name="Ins Team", slug="ins-team")
        cls.org = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="ins-org",
            industry="analytics",
            display_name="Ins Org",
            is_public=True,
        )

    @patch("apps.public.repo_insight_service.submit_insights_batch")
    @patch("apps.public.repo_insight_service.process_insights_batch")
    def test_insights_skipped_when_sync_disabled_even_if_insights_enabled(self, mock_process, mock_submit):
        repo = PublicRepoProfile.objects.create(
            org_profile=self.org,
            github_repo="ins-org/no-sync",
            repo_slug="no-sync",
            display_name="No Sync",
            is_public=True,
            sync_enabled=False,
            insights_enabled=True,
        )
        # Give it stats so it would normally qualify
        PublicRepoStats.objects.create(repo_profile=repo, total_prs=100)

        from apps.public.tasks import generate_public_repo_insights_weekly

        result = generate_public_repo_insights_weekly()

        # Should not have submitted any batch (no qualifying repos)
        mock_submit.assert_not_called()
        assert result["generated"] == 0
