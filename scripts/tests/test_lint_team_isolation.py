"""Tests for the team isolation linter."""

import ast
import sys
from pathlib import Path
from unittest import TestCase

# Add scripts directory to path for imports
sys.path.insert(0, str(Path(__file__).parent.parent))

from lint_team_isolation import TEAM_MODELS, TeamIsolationVisitor, lint_file


class TestTeamIsolationVisitor(TestCase):
    """Tests for the AST visitor that detects team isolation violations."""

    def _get_violations(self, source: str) -> list:
        """Helper to get violations from source code."""
        source_lines = source.splitlines()
        tree = ast.parse(source)
        visitor = TeamIsolationVisitor("test.py", source_lines)
        visitor.visit(tree)
        return visitor.violations

    def test_detects_objects_filter_without_team(self):
        """Test that .objects.filter() without team is flagged."""
        source = "PullRequest.objects.filter(state='merged')"
        violations = self._get_violations(source)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].model, "PullRequest")
        self.assertEqual(violations[0].method, "filter")

    def test_detects_objects_get_without_team(self):
        """Test that .objects.get() without team is flagged."""
        source = "TeamMember.objects.get(id=123)"
        violations = self._get_violations(source)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].model, "TeamMember")
        self.assertEqual(violations[0].method, "get")

    def test_detects_objects_all_without_team(self):
        """Test that .objects.all() is flagged."""
        source = "PRSurvey.objects.all()"
        violations = self._get_violations(source)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].model, "PRSurvey")
        self.assertEqual(violations[0].method, "all")

    def test_allows_objects_filter_with_team(self):
        """Test that .objects.filter(team=team) is not flagged."""
        source = "PullRequest.objects.filter(team=team, state='merged')"
        violations = self._get_violations(source)
        self.assertEqual(len(violations), 0)

    def test_allows_objects_get_with_team(self):
        """Test that .objects.get(team=team, ...) is not flagged."""
        source = "TeamMember.objects.get(team=team, github_id='123')"
        violations = self._get_violations(source)
        self.assertEqual(len(violations), 0)

    def test_allows_for_team_manager(self):
        """Test that .for_team.filter() is not flagged."""
        source = "PullRequest.for_team.filter(state='merged')"
        violations = self._get_violations(source)
        self.assertEqual(len(violations), 0)

    def test_allows_noqa_suppression(self):
        """Test that # noqa: TEAM001 suppresses the warning."""
        source = "PullRequest.objects.all()  # noqa: TEAM001"
        violations = self._get_violations(source)
        self.assertEqual(len(violations), 0)

    def test_allows_noqa_suppression_no_space(self):
        """Test that # noqa:TEAM001 (no space) also works."""
        source = "PullRequest.objects.all()  # noqa:TEAM001"
        violations = self._get_violations(source)
        self.assertEqual(len(violations), 0)

    def test_ignores_non_team_models(self):
        """Test that non-team models are not flagged."""
        source = "User.objects.filter(email='test@example.com')"
        violations = self._get_violations(source)
        self.assertEqual(len(violations), 0)

    def test_allows_create_method(self):
        """Test that .objects.create() is not flagged (team FK is required)."""
        source = "PullRequest.objects.create(team=team, title='Test')"
        violations = self._get_violations(source)
        self.assertEqual(len(violations), 0)

    def test_allows_update_or_create_method(self):
        """Test that .objects.update_or_create() is not flagged."""
        source = "PullRequest.objects.update_or_create(team=team, defaults={})"
        violations = self._get_violations(source)
        self.assertEqual(len(violations), 0)

    def test_allows_get_or_create_method(self):
        """Test that .objects.get_or_create() is not flagged."""
        source = "TeamMember.objects.get_or_create(team=team, github_id='123')"
        violations = self._get_violations(source)
        self.assertEqual(len(violations), 0)

    def test_allows_chained_team_filter(self):
        """Test that chained .filter(team=team) on same line is allowed."""
        source = "PullRequest.objects.filter(state='merged').filter(team=team)"
        violations = self._get_violations(source)
        self.assertEqual(len(violations), 0)

    def test_allows_related_in_filter(self):
        """Test that __in= patterns are allowed (assumes team-scoped input)."""
        source = "PRSurveyReview.objects.filter(survey__pull_request__in=prs)"
        violations = self._get_violations(source)
        self.assertEqual(len(violations), 0)

    def test_allows_pull_request_in_filter(self):
        """Test that pull_request__in= is allowed."""
        source = "PRSurvey.objects.filter(pull_request__in=team_prs)"
        violations = self._get_violations(source)
        self.assertEqual(len(violations), 0)

    def test_detects_select_related_without_team(self):
        """Test that .objects.select_related() without team is flagged."""
        source = "TrackedRepository.objects.select_related('integration').get(id=123)"
        violations = self._get_violations(source)
        self.assertEqual(len(violations), 1)
        self.assertEqual(violations[0].model, "TrackedRepository")
        self.assertEqual(violations[0].method, "select_related")

    def test_all_team_models_detected(self):
        """Test that all defined team models are detected."""
        expected_models = {
            "TeamMember",
            "PullRequest",
            "PRReview",
            "Commit",
            "JiraIssue",
            "AIUsageDaily",
            "PRSurvey",
            "PRSurveyReview",
            "WeeklyMetrics",
            "IntegrationCredential",
            "GitHubIntegration",
            "TrackedRepository",
            "JiraIntegration",
            "TrackedJiraProject",
            "SlackIntegration",
            "Player",
            # Added 2026-01-12:
            "PRFile",
            "PRComment",
            "PRCheckRun",
            "CopilotLanguageDaily",
            "CopilotEditorDaily",
            "CopilotSeatSnapshot",
            "ReviewerCorrelation",
            "Deployment",
            "AIFeedback",
            "DailyInsight",
            "LLMFeedback",
            "GitHubAppInstallation",
        }
        self.assertEqual(TEAM_MODELS, expected_models)

    def test_violation_string_format(self):
        """Test the string representation of violations."""
        source = "PullRequest.objects.filter(state='merged')"
        violations = self._get_violations(source)
        violation_str = str(violations[0])
        self.assertIn("TEAM001", violation_str)
        self.assertIn("PullRequest.objects.filter()", violation_str)
        self.assertIn("for_team", violation_str)

    def test_multiple_violations_in_file(self):
        """Test that multiple violations are detected."""
        source = """
pr = PullRequest.objects.get(id=1)
member = TeamMember.objects.filter(github_id='123')
survey = PRSurvey.objects.all()
"""
        violations = self._get_violations(source)
        self.assertEqual(len(violations), 3)
        models = {v.model for v in violations}
        self.assertEqual(models, {"PullRequest", "TeamMember", "PRSurvey"})


class TestLintFile(TestCase):
    """Tests for the lint_file function."""

    def test_lint_file_with_syntax_error(self):
        """Test that files with syntax errors return empty list."""
        # Create a temporary file with syntax error
        import tempfile

        with tempfile.NamedTemporaryFile(mode="w", suffix=".py", delete=False) as f:
            f.write("def broken(\n")  # Syntax error
            temp_path = Path(f.name)

        try:
            violations = lint_file(temp_path)
            self.assertEqual(violations, [])
        finally:
            temp_path.unlink()


if __name__ == "__main__":
    import unittest

    unittest.main()
