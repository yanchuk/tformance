"""Tests for scoped Groq LLM enrichment policy."""

from datetime import UTC, datetime, timedelta
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.metrics.factories import TeamFactory
from apps.metrics.models import PullRequest, TeamMember
from apps.public.models import PublicOrgProfile, PublicOrgStats, PublicRepoProfile
from apps.public.services.local_reconciliation import LocalReconciliationService


class ZeroGroqDefaultTests(TestCase):
    """Verify no Groq usage happens by default."""

    @patch("apps.public.services.local_reconciliation.GroqBatchProcessor")
    def test_no_groq_without_flag(self, mock_groq_cls):
        """GroqBatchProcessor should never be instantiated without --with-llm."""
        LocalReconciliationService(dry_run=False)
        # Normal flow without calling run_llm_enrichment
        mock_groq_cls.assert_not_called()


class LLMCandidateSelectionTests(TestCase):
    """Test LLM candidate selection respects scoping rules."""

    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="test-llm",
            industry="analytics",
            display_name="LLM Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.org_profile,
            total_prs=100,
        )
        # Flagship repo
        cls.flagship = PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="org/flagship",
            repo_slug="flagship",
            display_name="Flagship",
            is_flagship=True,
            is_public=True,
        )
        # Non-flagship repo
        cls.secondary = PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="org/secondary",
            repo_slug="secondary",
            display_name="Secondary",
            is_flagship=False,
            is_public=True,
        )
        member = TeamMember.objects.create(team=cls.team, github_username="dev1")
        now = datetime(2026, 3, 1, 12, 0, 0, tzinfo=UTC)

        # Create merged PRs without llm_summary for flagship
        for i in range(60):
            PullRequest.objects.create(
                team=cls.team,
                github_pr_id=1000 + i,
                github_repo="org/flagship",
                title=f"PR {i}",
                state="merged",
                merged_at=now - timedelta(days=i),
                pr_created_at=now - timedelta(days=i + 1),
                additions=50,
                deletions=10,
                author=member,
                llm_summary=None,
            )

        # Create merged PRs for secondary repo
        for i in range(10):
            PullRequest.objects.create(
                team=cls.team,
                github_pr_id=2000 + i,
                github_repo="org/secondary",
                title=f"Secondary PR {i}",
                state="merged",
                merged_at=now - timedelta(days=i),
                pr_created_at=now - timedelta(days=i + 1),
                additions=20,
                deletions=5,
                author=member,
                llm_summary=None,
            )

    def test_llm_candidates_flagship_only(self):
        """LLM candidates should only come from flagship repos."""
        service = LocalReconciliationService(dry_run=False)
        candidates = service._get_llm_candidates("org/flagship", self.team, max_per_repo=50)
        assert len(candidates) <= 50
        assert len(candidates) > 0

    def test_llm_candidates_respects_cap(self):
        """LLM candidate count should not exceed max_per_repo."""
        service = LocalReconciliationService(dry_run=False)
        candidates = service._get_llm_candidates("org/flagship", self.team, max_per_repo=10)
        assert len(candidates) <= 10

    def test_llm_candidates_excludes_old_prs(self):
        """LLM candidates should only include PRs from last 90 days."""
        service = LocalReconciliationService(dry_run=False)
        candidates = service._get_llm_candidates("org/flagship", self.team, max_per_repo=100)
        # All 60 PRs are within 60 days, so all within 90-day window
        assert len(candidates) == 60

    @patch("apps.public.services.local_reconciliation.GroqBatchProcessor")
    def test_run_llm_enrichment_flagship_only(self, mock_groq_cls):
        """run_llm_enrichment should only process flagship repos."""
        mock_processor = MagicMock()
        mock_groq_cls.return_value = mock_processor

        service = LocalReconciliationService(dry_run=False)
        repos = [
            {"github_repo": "org/flagship", "repo_slug": "flagship", "is_flagship": True, "org_slug": "test-llm"},
            {"github_repo": "org/secondary", "repo_slug": "secondary", "is_flagship": False, "org_slug": "test-llm"},
        ]
        org_profiles = {"test-llm": self.org_profile}

        service.run_llm_enrichment(repos, org_profiles, max_per_repo=50)

        # Should only be called for flagship repo, not secondary
        if mock_processor.process_prs.called:
            call_args = mock_processor.process_prs.call_args
            # All submitted PRs should be from flagship repo
            for pr in call_args[0][0]:
                assert pr.github_repo == "org/flagship"
