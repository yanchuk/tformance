"""Tests for feedback template tags."""

import json

from django.test import TestCase

from apps.feedback.templatetags.feedback_tags import to_json_attr


class TestToJsonAttrFilter(TestCase):
    """Tests for the to_json_attr template filter."""

    def test_converts_dict_to_json(self):
        """Test that a Python dict is converted to JSON string."""
        data = {"key": "value", "nested": {"a": 1}}
        result = to_json_attr(data)
        self.assertEqual(result, '{"key": "value", "nested": {"a": 1}}')
        # Verify it's valid JSON
        parsed = json.loads(result)
        self.assertEqual(parsed, data)

    def test_converts_list_to_json(self):
        """Test that a Python list is converted to JSON string."""
        data = [1, 2, {"key": "value"}]
        result = to_json_attr(data)
        self.assertEqual(result, '[1, 2, {"key": "value"}]')
        parsed = json.loads(result)
        self.assertEqual(parsed, data)

    def test_handles_none_value(self):
        """Test that None returns empty object string."""
        result = to_json_attr(None)
        self.assertEqual(result, "{}")

    def test_handles_empty_dict(self):
        """Test that empty dict returns empty object string."""
        result = to_json_attr({})
        self.assertEqual(result, "{}")

    def test_handles_valid_json_string(self):
        """Test that a valid JSON string is passed through."""
        json_str = '{"already": "json"}'
        result = to_json_attr(json_str)
        self.assertEqual(result, json_str)

    def test_handles_invalid_json_string(self):
        """Test that an invalid JSON string is wrapped as JSON."""
        invalid_str = "not json"
        result = to_json_attr(invalid_str)
        self.assertEqual(result, '"not json"')

    def test_handles_special_characters(self):
        """Test that special characters are properly escaped."""
        data = {"message": 'Hello "world" with <html> & entities'}
        result = to_json_attr(data)
        # Verify the result is valid JSON
        parsed = json.loads(result)
        self.assertEqual(parsed["message"], 'Hello "world" with <html> & entities')

    def test_handles_llm_summary_structure(self):
        """Test with realistic LLM summary data structure."""
        llm_summary = {
            "summary": {"title": "Test PR", "description": "Does something"},
            "pr_type": "feature",
            "health": {"scope": "small", "risk_level": "low"},
            "ai": {"is_assisted": True, "tools": ["copilot"]},
        }
        result = to_json_attr(llm_summary)
        parsed = json.loads(result)
        self.assertEqual(parsed["summary"]["title"], "Test PR")
        self.assertEqual(parsed["ai"]["is_assisted"], True)

    def test_handles_unicode(self):
        """Test that unicode characters are handled correctly."""
        data = {"message": "Hello \u4e16\u754c"}  # Hello 世界
        result = to_json_attr(data)
        parsed = json.loads(result)
        self.assertEqual(parsed["message"], "Hello 世界")

    def test_handles_non_serializable_returns_empty(self):
        """Test that non-JSON-serializable objects return empty object."""

        class NotSerializable:
            pass

        result = to_json_attr(NotSerializable())
        self.assertEqual(result, "{}")
