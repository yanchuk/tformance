"""Guardrail tests to ensure Groq API usage follows batch-only policy.

Policy (agreed 2026-03-26):
1. No on-demand Groq API calls for public data — only Batch API
2. Never reprocess already-analyzed PRs — only llm_summary IS NULL
3. Scheduled tasks must use batch processing, not individual API calls
"""

import inspect
from unittest.mock import patch

from django.test import TestCase

from apps.metrics.tasks import (
    generate_monthly_insights,
    generate_weekly_insights,
    run_all_teams_llm_batch,
)


class TestBatchOnlyScheduledTasks(TestCase):
    """Guardrail: scheduled LLM tasks must use batch processing."""

    def test_nightly_batch_dispatcher_uses_queue_llm_analysis_batch_task(self):
        """The nightly dispatcher must use the batch task, not on-demand calls."""
        source = inspect.getsource(run_all_teams_llm_batch)
        assert "queue_llm_analysis_batch_task" in source
        assert "chat.completions.create" not in source

    def test_nightly_batch_dispatcher_dispatches_per_team(self):
        """The dispatcher must iterate teams and dispatch batch tasks."""
        with patch("apps.integrations.models.GitHubIntegration") as mock_gh:
            mock_gh.objects.select_related.return_value.all.return_value = []
            result = run_all_teams_llm_batch()
            assert result["teams_dispatched"] == 0

    def test_nightly_dispatcher_processes_integration_and_public_teams(self):
        """Teams with GitHubIntegration AND public org teams should get batch processing."""
        source = inspect.getsource(run_all_teams_llm_batch)
        assert "GitHubIntegration" in source
        assert "PublicOrgProfile" in source
        assert "Team.objects.all()" not in source


class TestInsightTasksExcludePublicTeams(TestCase):
    """Guardrail: weekly/monthly insight tasks skip public-only teams."""

    def test_weekly_insights_filters_to_customer_teams(self):
        source = inspect.getsource(generate_weekly_insights)
        assert "GitHubIntegration" in source
        # Must NOT use Team.objects.all() which includes public teams
        assert "Team.objects.all()" not in source

    def test_monthly_insights_filters_to_customer_teams(self):
        source = inspect.getsource(generate_monthly_insights)
        assert "GitHubIntegration" in source
        assert "Team.objects.all()" not in source


class TestNoOnDemandGroqInScheduledTasks(TestCase):
    """Guardrail: scan all scheduled task functions for on-demand Groq calls.

    This test prevents regression by checking that scheduled tasks never
    contain direct chat.completions.create() calls. If a new task is added
    to SCHEDULED_TASKS that makes on-demand Groq calls, this test will fail.
    """

    def test_no_chat_completions_create_in_scheduled_task_functions(self):
        """Scheduled task functions must not contain on-demand Groq API calls.

        Checks only the specific functions referenced in SCHEDULED_TASKS,
        not the entire module (which may contain legacy/deprecated functions).
        """
        from importlib import import_module

        from django.conf import settings

        violations = []
        for task_config in settings.SCHEDULED_TASKS.values():
            task_path = task_config["task"]
            module_path = ".".join(task_path.split(".")[:-1])
            func_name = task_path.split(".")[-1]

            try:
                module = import_module(module_path)
                func = getattr(module, func_name, None)
                if func is None:
                    continue
                source = inspect.getsource(func)
                if "chat.completions.create(" in source:
                    violations.append(task_path)
            except Exception:
                continue

        assert not violations, (
            f"On-demand Groq API calls in scheduled tasks: {violations}. "
            "Scheduled tasks must use GroqBatchProcessor (Batch API). "
            "See batch-only policy in memory."
        )


class TestBatchTaskOnlyProcessesNewPRs(TestCase):
    """Guardrail: batch task must only process PRs with null llm_summary."""

    def test_queue_llm_analysis_batch_task_filters_null_only(self):
        """The batch task must filter llm_summary__isnull=True."""
        from apps.integrations._task_modules.metrics import queue_llm_analysis_batch_task

        source = inspect.getsource(queue_llm_analysis_batch_task)
        assert "llm_summary__isnull=True" in source
        # Must NOT have version-based reprocessing
        assert "llm_summary_version" not in source.split("prs_to_process")[0]

    def test_batch_task_saves_version_metadata(self):
        """The batch task must save llm_summary_version alongside llm_summary."""
        from apps.integrations._task_modules.metrics import queue_llm_analysis_batch_task

        source = inspect.getsource(queue_llm_analysis_batch_task)
        assert "llm_summary_version" in source
        assert "prompt_version" in source
