"""Tests for AI adoption data source helpers.

TDD RED Phase: These tests define the expected behavior for the
AI adoption feature flag helpers.
"""

from django.core.cache import cache
from django.test import RequestFactory, TestCase
from waffle.testutils import override_flag

from apps.metrics.factories import (
    PRSurveyFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)
from apps.metrics.services.ai_adoption_helpers import (
    AI_ADOPTION_SURVEY_FLAG,
    get_pr_ai_status,
    should_use_survey_data,
)
from apps.teams.models import Flag
from apps.users.models import CustomUser


class TestShouldUseSurveyData(TestCase):
    """Tests for should_use_survey_data helper function.

    Uses waffle's override_flag for thread-safe flag testing in parallel execution.
    """

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.user = CustomUser.objects.create_user(
            username="testuser",
            email="test@example.com",
            password="testpass123",
        )
        self.team.members.add(self.user)
        self.request_factory = RequestFactory()
        # Ensure flag exists but is inactive
        Flag.objects.get_or_create(
            name=AI_ADOPTION_SURVEY_FLAG,
            defaults={"everyone": None},
        )
        cache.clear()

    def test_returns_false_when_flag_inactive(self):
        """When flag is inactive, should return False (use detection only)."""
        with override_flag(AI_ADOPTION_SURVEY_FLAG, active=False):
            request = self.request_factory.get("/")
            request.team = self.team
            request.user = self.user

            result = should_use_survey_data(request)

            self.assertFalse(result)

    def test_returns_true_when_flag_active_globally(self):
        """When flag is globally active, should return True."""
        with override_flag(AI_ADOPTION_SURVEY_FLAG, active=True):
            request = self.request_factory.get("/")
            request.team = self.team
            request.user = self.user

            result = should_use_survey_data(request)

            self.assertTrue(result)

    def test_accepts_team_instance_directly(self):
        """Should accept Team instance instead of request."""
        with override_flag(AI_ADOPTION_SURVEY_FLAG, active=False):
            result = should_use_survey_data(self.team)

            self.assertFalse(result)

    def test_accepts_team_instance_with_flag_active(self):
        """Should work with Team instance when flag is active."""
        with override_flag(AI_ADOPTION_SURVEY_FLAG, active=True):
            result = should_use_survey_data(self.team)

            self.assertTrue(result)

    def test_returns_true_when_flag_active_for_team(self):
        """When flag is active for specific team, should return True.

        Note: override_flag with active=True globally activates the flag.
        For team-specific testing, we use the database flag with teams M2M.
        """
        # Create flag for this specific team
        flag, _ = Flag.objects.get_or_create(name=AI_ADOPTION_SURVEY_FLAG)
        flag.everyone = None
        flag.save()
        flag.teams.add(self.team)
        cache.clear()

        request = self.request_factory.get("/")
        request.team = self.team
        request.user = self.user

        result = should_use_survey_data(request)

        self.assertTrue(result)

        # Cleanup
        flag.teams.clear()
        cache.clear()

    def test_returns_false_when_flag_active_for_other_team(self):
        """When flag is active for different team, should return False."""
        other_team = TeamFactory()
        flag, _ = Flag.objects.get_or_create(name=AI_ADOPTION_SURVEY_FLAG)
        flag.everyone = None
        flag.save()
        flag.teams.clear()
        flag.teams.add(other_team)
        cache.clear()

        request = self.request_factory.get("/")
        request.team = self.team  # Our team is NOT in flag
        request.user = self.user

        result = should_use_survey_data(request)

        self.assertFalse(result)

        # Cleanup
        flag.teams.clear()
        cache.clear()


class TestGetPrAiStatus(TestCase):
    """Tests for get_pr_ai_status helper function."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.member = TeamMemberFactory(team=self.team)

    def test_uses_detection_when_use_surveys_false(self):
        """When use_surveys=False, should use effective_is_ai_assisted."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,  # Pattern detection says AI
        )

        result = get_pr_ai_status(pr, use_surveys=False)

        self.assertTrue(result)

    def test_uses_detection_when_use_surveys_false_and_survey_exists(self):
        """When use_surveys=False, should ignore survey data."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=False,  # Pattern detection says no AI
        )
        # Survey says AI was used - should be ignored
        PRSurveyFactory(
            team=self.team,
            pull_request=pr,
            author=self.member,
            author_ai_assisted=True,
        )

        result = get_pr_ai_status(pr, use_surveys=False)

        self.assertFalse(result)

    def test_uses_survey_when_use_surveys_true_and_survey_true(self):
        """When use_surveys=True and survey says AI, should return True."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=False,  # Pattern detection says no AI
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr,
            author=self.member,
            author_ai_assisted=True,  # Survey says AI was used
        )

        result = get_pr_ai_status(pr, use_surveys=True)

        self.assertTrue(result)

    def test_uses_survey_when_use_surveys_true_and_survey_false(self):
        """When use_surveys=True and survey says no AI, should return False."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,  # Pattern detection says AI
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr,
            author=self.member,
            author_ai_assisted=False,  # Survey says no AI
        )

        result = get_pr_ai_status(pr, use_surveys=True)

        self.assertFalse(result)

    def test_falls_back_to_detection_when_no_survey(self):
        """When use_surveys=True but no survey, should fall back to detection."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,  # Pattern detection says AI
        )
        # No survey created

        result = get_pr_ai_status(pr, use_surveys=True)

        self.assertTrue(result)

    def test_falls_back_to_detection_when_survey_none(self):
        """When use_surveys=True but survey.author_ai_assisted is None, fall back."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,  # Pattern detection says AI
        )
        PRSurveyFactory(
            team=self.team,
            pull_request=pr,
            author=self.member,
            author_ai_assisted=None,  # Not answered yet
        )

        result = get_pr_ai_status(pr, use_surveys=True)

        self.assertTrue(result)

    def test_respects_llm_detection_over_pattern(self):
        """Detection should use effective_is_ai_assisted which prioritizes LLM."""
        pr = PullRequestFactory(
            team=self.team,
            author=self.member,
            is_ai_assisted=True,  # Pattern says AI
            llm_summary={"ai": {"is_assisted": False, "confidence": 0.9}},  # LLM says no
        )

        result = get_pr_ai_status(pr, use_surveys=False)

        # LLM takes priority, should return False
        self.assertFalse(result)
