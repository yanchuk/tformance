"""Tests for Jira utility functions."""

from django.test import TestCase

from apps.integrations.services.jira_utils import extract_jira_key


class TestExtractJiraKey(TestCase):
    """Tests for extract_jira_key function."""

    def test_simple_key_in_text(self):
        """Test that a simple Jira key at the start of text is extracted."""
        result = extract_jira_key("PROJ-123 fix bug")
        self.assertEqual(result, "PROJ-123")

    def test_key_with_prefix_text(self):
        """Test that a Jira key with prefix text is extracted."""
        result = extract_jira_key("Fix: ABC-456 login issue")
        self.assertEqual(result, "ABC-456")

    def test_key_in_branch_name_format(self):
        """Test that a Jira key in branch name format is extracted."""
        result = extract_jira_key("feature/DEV-789-add-login")
        self.assertEqual(result, "DEV-789")

    def test_multiple_keys_returns_first(self):
        """Test that when multiple keys are present, the first one is returned."""
        result = extract_jira_key("PROJ-1 and PROJ-2")
        self.assertEqual(result, "PROJ-1")

    def test_no_key_found(self):
        """Test that None is returned when no Jira key is found."""
        result = extract_jira_key("fix the bug")
        self.assertIsNone(result)

    def test_empty_string(self):
        """Test that None is returned for empty string."""
        result = extract_jira_key("")
        self.assertIsNone(result)

    def test_none_input(self):
        """Test that None input is handled gracefully and returns None."""
        result = extract_jira_key(None)
        self.assertIsNone(result)

    def test_key_with_numbers_in_project(self):
        """Test that project codes with numbers are correctly extracted."""
        result = extract_jira_key("ABC2-123 test")
        self.assertEqual(result, "ABC2-123")

    def test_lowercase_should_not_match(self):
        """Test that lowercase keys are not matched (Jira keys are uppercase)."""
        result = extract_jira_key("proj-123")
        self.assertIsNone(result)

    def test_key_at_end_of_text(self):
        """Test that a Jira key at the end of text is extracted."""
        result = extract_jira_key("This fixes JIRA-999")
        self.assertEqual(result, "JIRA-999")

    def test_key_in_middle_of_text(self):
        """Test that a Jira key in the middle of text is extracted."""
        result = extract_jira_key("The issue TEST-42 is now fixed")
        self.assertEqual(result, "TEST-42")

    def test_key_with_single_digit(self):
        """Test that a Jira key with single digit number is extracted."""
        result = extract_jira_key("XYZ-1 first issue")
        self.assertEqual(result, "XYZ-1")

    def test_key_with_large_number(self):
        """Test that a Jira key with large number is extracted."""
        result = extract_jira_key("PROJECT-123456 complex issue")
        self.assertEqual(result, "PROJECT-123456")

    def test_key_surrounded_by_special_chars(self):
        """Test that a Jira key surrounded by special characters is extracted."""
        result = extract_jira_key("[TICKET-789] Important fix")
        self.assertEqual(result, "TICKET-789")

    def test_no_match_for_incomplete_key(self):
        """Test that incomplete keys (no number) are not matched."""
        result = extract_jira_key("PROJ- no number here")
        self.assertIsNone(result)

    def test_no_match_for_only_numbers(self):
        """Test that only numbers without project code are not matched."""
        result = extract_jira_key("123 is just a number")
        self.assertIsNone(result)
