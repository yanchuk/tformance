"""
Tests for Slack survey message templates.

Block Kit message builders for PR surveys and reveal messages.
"""

from django.test import TestCase

from apps.metrics.factories import (
    PRSurveyFactory,
    PullRequestFactory,
    TeamFactory,
    TeamMemberFactory,
)


class TestAuthorSurveyBlocks(TestCase):
    """Tests for build_author_survey_blocks."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.author = TeamMemberFactory(team=self.team, display_name="Alice")
        self.pr = PullRequestFactory(
            team=self.team,
            author=self.author,
            title="Fix login bug",
            state="merged",
        )
        self.survey = PRSurveyFactory(team=self.team, pull_request=self.pr, author=self.author)

    def test_returns_valid_blocks_list(self):
        """Test that build_author_survey_blocks returns a list of blocks."""
        from apps.integrations.services.slack_surveys import build_author_survey_blocks

        blocks = build_author_survey_blocks(self.pr, self.survey)

        self.assertIsInstance(blocks, list)
        self.assertGreater(len(blocks), 0)
        # Should have at least a section and an actions block
        self.assertGreaterEqual(len(blocks), 2)

    def test_contains_pr_title_in_mrkdwn(self):
        """Test that the blocks contain the PR title in markdown format."""
        from apps.integrations.services.slack_surveys import build_author_survey_blocks

        blocks = build_author_survey_blocks(self.pr, self.survey)

        # Convert blocks to string to search for PR title
        blocks_str = str(blocks)
        self.assertIn("Fix login bug", blocks_str)
        # Should be in bold markdown format
        self.assertIn("*Fix login bug*", blocks_str)

    def test_has_yes_no_buttons_with_correct_action_ids(self):
        """Test that the blocks have Yes/No buttons with proper action_ids."""
        from apps.integrations.services.slack_surveys import (
            ACTION_AUTHOR_AI_NO,
            ACTION_AUTHOR_AI_YES,
            build_author_survey_blocks,
        )

        blocks = build_author_survey_blocks(self.pr, self.survey)

        # Find the actions block
        actions_block = None
        for block in blocks:
            if block.get("type") == "actions":
                actions_block = block
                break

        self.assertIsNotNone(actions_block, "Should have an actions block")
        elements = actions_block.get("elements", [])
        self.assertEqual(len(elements), 2, "Should have 2 buttons (Yes/No)")

        # Check action IDs
        action_ids = [elem.get("action_id") for elem in elements]
        self.assertIn(ACTION_AUTHOR_AI_YES, action_ids)
        self.assertIn(ACTION_AUTHOR_AI_NO, action_ids)


class TestReviewerSurveyBlocks(TestCase):
    """Tests for build_reviewer_survey_blocks."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.author = TeamMemberFactory(team=self.team, display_name="Alice")
        self.reviewer = TeamMemberFactory(team=self.team, display_name="Bob")
        self.pr = PullRequestFactory(
            team=self.team,
            author=self.author,
            title="Add new feature",
            state="merged",
        )
        self.survey = PRSurveyFactory(team=self.team, pull_request=self.pr, author=self.author)

    def test_returns_valid_blocks(self):
        """Test that build_reviewer_survey_blocks returns valid blocks."""
        from apps.integrations.services.slack_surveys import build_reviewer_survey_blocks

        blocks = build_reviewer_survey_blocks(self.pr, self.survey, self.reviewer)

        self.assertIsInstance(blocks, list)
        self.assertGreater(len(blocks), 0)

    def test_has_quality_buttons_three_options(self):
        """Test that the blocks have 3 quality rating buttons."""
        from apps.integrations.services.slack_surveys import (
            ACTION_QUALITY_1,
            ACTION_QUALITY_2,
            ACTION_QUALITY_3,
            build_reviewer_survey_blocks,
        )

        blocks = build_reviewer_survey_blocks(self.pr, self.survey, self.reviewer)

        # Find quality actions block
        quality_action_ids = []
        for block in blocks:
            if block.get("type") == "actions":
                for elem in block.get("elements", []):
                    action_id = elem.get("action_id", "")
                    if action_id.startswith("quality_"):
                        quality_action_ids.append(action_id)

        self.assertEqual(len(quality_action_ids), 3, "Should have 3 quality buttons")
        self.assertIn(ACTION_QUALITY_1, quality_action_ids)
        self.assertIn(ACTION_QUALITY_2, quality_action_ids)
        self.assertIn(ACTION_QUALITY_3, quality_action_ids)

    def test_has_ai_guess_buttons(self):
        """Test that the blocks have AI guess buttons."""
        from apps.integrations.services.slack_surveys import (
            ACTION_AI_GUESS_NO,
            ACTION_AI_GUESS_YES,
            build_reviewer_survey_blocks,
        )

        blocks = build_reviewer_survey_blocks(self.pr, self.survey, self.reviewer)

        # Find AI guess action IDs
        ai_guess_action_ids = []
        for block in blocks:
            if block.get("type") == "actions":
                for elem in block.get("elements", []):
                    action_id = elem.get("action_id", "")
                    if action_id.startswith("ai_guess_"):
                        ai_guess_action_ids.append(action_id)

        self.assertEqual(len(ai_guess_action_ids), 2, "Should have 2 AI guess buttons")
        self.assertIn(ACTION_AI_GUESS_YES, ai_guess_action_ids)
        self.assertIn(ACTION_AI_GUESS_NO, ai_guess_action_ids)


class TestThanksBlocks(TestCase):
    """Tests for thank you message blocks."""

    def test_author_thanks_returns_message(self):
        """Test that build_author_thanks_blocks returns a message."""
        from apps.integrations.services.slack_surveys import build_author_thanks_blocks

        blocks = build_author_thanks_blocks()

        self.assertIsInstance(blocks, list)
        self.assertGreater(len(blocks), 0)

    def test_reviewer_thanks_returns_message(self):
        """Test that build_reviewer_thanks_blocks returns a message."""
        from apps.integrations.services.slack_surveys import build_reviewer_thanks_blocks

        blocks = build_reviewer_thanks_blocks()

        self.assertIsInstance(blocks, list)
        self.assertGreater(len(blocks), 0)


class TestRevealBlocks(TestCase):
    """Tests for reveal message blocks."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.reviewer = TeamMemberFactory(team=self.team, display_name="Bob")

    def test_reveal_correct_for_ai_assisted_pr(self):
        """Test build_reveal_correct_blocks for AI-assisted PR."""
        from apps.integrations.services.slack_surveys import build_reveal_correct_blocks

        accuracy_stats = {"correct": 8, "total": 10, "percentage": 80}
        blocks = build_reveal_correct_blocks(self.reviewer, was_ai_assisted=True, accuracy_stats=accuracy_stats)

        self.assertIsInstance(blocks, list)
        self.assertGreater(len(blocks), 0)
        # Should mention it was AI-assisted
        blocks_str = str(blocks)
        self.assertIn("was", blocks_str.lower())
        self.assertIn("8", blocks_str)
        self.assertIn("10", blocks_str)

    def test_reveal_wrong_for_non_ai_pr(self):
        """Test build_reveal_wrong_blocks for non-AI-assisted PR."""
        from apps.integrations.services.slack_surveys import build_reveal_wrong_blocks

        accuracy_stats = {"correct": 6, "total": 10, "percentage": 60}
        blocks = build_reveal_wrong_blocks(self.reviewer, was_ai_assisted=False, accuracy_stats=accuracy_stats)

        self.assertIsInstance(blocks, list)
        self.assertGreater(len(blocks), 0)
        # Should mention it wasn't AI-assisted
        blocks_str = str(blocks)
        self.assertIn("not", blocks_str.lower())
        self.assertIn("6", blocks_str)
        self.assertIn("10", blocks_str)


class TestActionIDConstants(TestCase):
    """Test that action ID constants are properly defined."""

    def test_action_ids_match_constants(self):
        """Test that all action ID constants are defined and unique."""
        from apps.integrations.services.slack_surveys import (
            ACTION_AI_GUESS_NO,
            ACTION_AI_GUESS_YES,
            ACTION_AUTHOR_AI_NO,
            ACTION_AUTHOR_AI_YES,
            ACTION_QUALITY_1,
            ACTION_QUALITY_2,
            ACTION_QUALITY_3,
        )

        # All should be strings
        self.assertIsInstance(ACTION_AUTHOR_AI_YES, str)
        self.assertIsInstance(ACTION_AUTHOR_AI_NO, str)
        self.assertIsInstance(ACTION_QUALITY_1, str)
        self.assertIsInstance(ACTION_QUALITY_2, str)
        self.assertIsInstance(ACTION_QUALITY_3, str)
        self.assertIsInstance(ACTION_AI_GUESS_YES, str)
        self.assertIsInstance(ACTION_AI_GUESS_NO, str)

        # All should be unique
        action_ids = [
            ACTION_AUTHOR_AI_YES,
            ACTION_AUTHOR_AI_NO,
            ACTION_QUALITY_1,
            ACTION_QUALITY_2,
            ACTION_QUALITY_3,
            ACTION_AI_GUESS_YES,
            ACTION_AI_GUESS_NO,
        ]
        self.assertEqual(len(action_ids), len(set(action_ids)), "All action IDs should be unique")


class TestSurveyIDInButtons(TestCase):
    """Test that survey ID is included in button values."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.author = TeamMemberFactory(team=self.team, display_name="Alice")
        self.reviewer = TeamMemberFactory(team=self.team, display_name="Bob")
        self.pr = PullRequestFactory(team=self.team, author=self.author, state="merged")
        self.survey = PRSurveyFactory(team=self.team, pull_request=self.pr, author=self.author)

    def test_author_survey_includes_survey_id_in_values(self):
        """Test that author survey buttons include survey ID in values."""
        from apps.integrations.services.slack_surveys import build_author_survey_blocks

        blocks = build_author_survey_blocks(self.pr, self.survey)

        # Find button values
        for block in blocks:
            if block.get("type") == "actions":
                for elem in block.get("elements", []):
                    value = elem.get("value")
                    if value:
                        # Value should be the survey ID as a string
                        self.assertEqual(value, str(self.survey.id))

    def test_reviewer_survey_includes_survey_id_in_values(self):
        """Test that reviewer survey buttons include survey ID in values."""
        from apps.integrations.services.slack_surveys import build_reviewer_survey_blocks

        blocks = build_reviewer_survey_blocks(self.pr, self.survey, self.reviewer)

        # Find button values
        button_values = []
        for block in blocks:
            if block.get("type") == "actions":
                for elem in block.get("elements", []):
                    value = elem.get("value")
                    if value:
                        button_values.append(value)

        # All buttons should have the survey ID
        self.assertTrue(all(v == str(self.survey.id) for v in button_values))
