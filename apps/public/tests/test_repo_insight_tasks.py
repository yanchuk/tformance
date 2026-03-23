from decimal import Decimal
from unittest.mock import MagicMock, patch

from django.test import TestCase
from django.utils import timezone

from apps.metrics.factories import TeamFactory
from apps.public.aggregations import MIN_PRS_THRESHOLD
from apps.public.models import (
    PublicOrgProfile,
    PublicOrgStats,
    PublicRepoInsight,
    PublicRepoProfile,
    PublicRepoStats,
)
from tformance.settings import SCHEDULED_TASKS


class RepoInsightScheduleTests(TestCase):
    def test_weekly_insight_task_is_scheduled(self):
        scheduled = [
            config
            for config in SCHEDULED_TASKS.values()
            if config["task"] == "apps.public.tasks.generate_public_repo_insights_weekly"
        ]
        assert len(scheduled) == 1


class RepoInsightServiceTests(TestCase):
    @classmethod
    def setUpTestData(cls):
        cls.team = TeamFactory()
        cls.org_profile = PublicOrgProfile.objects.create(
            team=cls.team,
            public_slug="insight-org",
            industry="analytics",
            display_name="Insight Org",
            is_public=True,
        )
        PublicOrgStats.objects.create(
            org_profile=cls.org_profile,
            total_prs=MIN_PRS_THRESHOLD + 10,
        )
        cls.repo_profile = PublicRepoProfile.objects.create(
            org_profile=cls.org_profile,
            team=cls.team,
            github_repo="insight-org/repo",
            repo_slug="repo",
            display_name="Insight Repo",
            is_flagship=True,
        )
        cls.repo_stats = PublicRepoStats.objects.create(
            repo_profile=cls.repo_profile,
            total_prs=200,
            total_prs_in_window=50,
            ai_assisted_pct=Decimal("42.00"),
            median_cycle_time_hours=Decimal("18.5"),
            median_review_time_hours=Decimal("6.2"),
            active_contributors_30d=12,
            last_computed_at=timezone.now(),
        )

    def test_build_insight_payload_contains_required_fields(self):
        from apps.public.repo_insight_service import build_insight_payload

        payload = build_insight_payload(self.repo_profile, self.repo_stats)

        assert "repo_name" in payload
        assert "total_prs" in payload
        assert "ai_assisted_pct" in payload
        assert payload["repo_name"] == "Insight Repo"

    def test_build_user_prompt_includes_metrics(self):
        from apps.public.repo_insight_service import _build_user_prompt, build_insight_payload

        payload = build_insight_payload(self.repo_profile, self.repo_stats)
        prompt = _build_user_prompt(payload)

        assert "Insight Repo" in prompt
        assert "42.0%" in prompt
        assert "18.5 hours" in prompt

    @patch("apps.public.repo_insight_service.Groq")
    def test_submit_insights_batch_creates_batch(self, mock_groq_cls):
        from apps.public.repo_insight_service import submit_insights_batch

        mock_client = MagicMock()
        mock_file_response = MagicMock()
        mock_file_response.id = "file-123"
        mock_client.files.create.return_value = mock_file_response

        mock_batch = MagicMock()
        mock_batch.id = "batch-456"
        mock_client.batches.create.return_value = mock_batch
        mock_groq_cls.return_value = mock_client

        batch_id = submit_insights_batch([(self.repo_profile, self.repo_stats)])

        assert batch_id == "batch-456"
        mock_client.files.create.assert_called_once()
        mock_client.batches.create.assert_called_once()

    @patch("apps.public.repo_insight_service.Groq")
    def test_submit_insights_batch_returns_none_on_empty(self, mock_groq_cls):
        from apps.public.repo_insight_service import submit_insights_batch

        result = submit_insights_batch([])
        assert result is None

    @patch("apps.public.repo_insight_service.Groq")
    def test_process_insights_batch_stores_results(self, mock_groq_cls):
        import json

        from apps.public.repo_insight_service import process_insights_batch

        mock_client = MagicMock()

        # Mock batch status: completed
        mock_batch = MagicMock()
        mock_batch.status = "completed"
        mock_batch.output_file_id = "output-789"
        mock_client.batches.retrieve.return_value = mock_batch

        # Mock results file content
        result_line = json.dumps(
            {
                "custom_id": f"repo-insight-{self.repo_profile.id}",
                "response": {
                    "body": {"choices": [{"message": {"content": "This repo shows strong AI adoption at 42%."}}]}
                },
            }
        )
        mock_content = MagicMock()
        mock_content.text.return_value = result_line
        mock_client.files.content.return_value = mock_content
        mock_groq_cls.return_value = mock_client

        result = process_insights_batch(
            "batch-456",
            [(self.repo_profile, self.repo_stats)],
        )

        assert result["generated"] == 1
        assert result["errors"] == 0

        insight = PublicRepoInsight.objects.filter(
            repo_profile=self.repo_profile,
            is_current=True,
        ).first()
        assert insight is not None
        assert "42%" in insight.content

    @patch("apps.public.repo_insight_service.Groq")
    def test_new_insight_replaces_previous_current(self, mock_groq_cls):
        import json

        from apps.public.repo_insight_service import process_insights_batch

        # Create an existing "current" insight
        old_insight = PublicRepoInsight.objects.create(
            repo_profile=self.repo_profile,
            content="Old insight",
            insight_type="weekly",
            is_current=True,
            batch_id="old-batch",
        )

        mock_client = MagicMock()
        mock_batch = MagicMock()
        mock_batch.status = "completed"
        mock_batch.output_file_id = "output-789"
        mock_client.batches.retrieve.return_value = mock_batch

        result_line = json.dumps(
            {
                "custom_id": f"repo-insight-{self.repo_profile.id}",
                "response": {"body": {"choices": [{"message": {"content": "New insight text."}}]}},
            }
        )
        mock_content = MagicMock()
        mock_content.text.return_value = result_line
        mock_client.files.content.return_value = mock_content
        mock_groq_cls.return_value = mock_client

        process_insights_batch("batch-new", [(self.repo_profile, self.repo_stats)])

        new_insight = PublicRepoInsight.objects.filter(
            repo_profile=self.repo_profile,
            is_current=True,
        ).first()
        assert new_insight is not None
        assert new_insight.content == "New insight text."

        old_insight.refresh_from_db()
        assert old_insight.is_current is False

    @patch("apps.public.repo_insight_service.Groq")
    def test_failed_batch_keeps_previous_insight(self, mock_groq_cls):
        from apps.public.repo_insight_service import process_insights_batch

        existing = PublicRepoInsight.objects.create(
            repo_profile=self.repo_profile,
            content="Existing insight",
            insight_type="weekly",
            is_current=True,
            batch_id="existing-batch",
        )

        mock_client = MagicMock()
        mock_batch = MagicMock()
        mock_batch.status = "failed"
        mock_batch.output_file_id = None
        mock_client.batches.retrieve.return_value = mock_batch
        mock_groq_cls.return_value = mock_client

        result = process_insights_batch(
            "batch-fail",
            [(self.repo_profile, self.repo_stats)],
        )

        assert result["generated"] == 0
        existing.refresh_from_db()
        assert existing.is_current is True

    @patch("apps.public.repo_insight_service.Groq")
    def test_submit_batch_failure_returns_none(self, mock_groq_cls):
        from apps.public.repo_insight_service import submit_insights_batch

        mock_client = MagicMock()
        mock_client.files.create.side_effect = Exception("API error")
        mock_groq_cls.return_value = mock_client

        result = submit_insights_batch([(self.repo_profile, self.repo_stats)])
        assert result is None
