"""
Tests for the Gemini function declarations.
"""

from django.test import TestCase

from apps.insights.services.function_defs import (
    FUNCTION_DECLARATIONS,
    get_function_declarations,
)


class TestFunctionDeclarations(TestCase):
    """Tests for function declarations."""

    def test_get_function_declarations_returns_list(self):
        """Test that get_function_declarations returns a list."""
        result = get_function_declarations()
        self.assertIsInstance(result, list)

    def test_all_declarations_have_required_fields(self):
        """Test that all declarations have name, description, and parameters."""
        for declaration in FUNCTION_DECLARATIONS:
            self.assertIn("name", declaration)
            self.assertIn("description", declaration)
            self.assertIn("parameters", declaration)

    def test_all_declarations_have_string_name(self):
        """Test that all declaration names are non-empty strings."""
        for declaration in FUNCTION_DECLARATIONS:
            self.assertIsInstance(declaration["name"], str)
            self.assertTrue(len(declaration["name"]) > 0)

    def test_all_declarations_have_string_description(self):
        """Test that all declaration descriptions are non-empty strings."""
        for declaration in FUNCTION_DECLARATIONS:
            self.assertIsInstance(declaration["description"], str)
            self.assertTrue(len(declaration["description"]) > 0)

    def test_all_parameters_have_type_object(self):
        """Test that all parameters have type 'object'."""
        for declaration in FUNCTION_DECLARATIONS:
            params = declaration["parameters"]
            self.assertEqual(params["type"], "object")
            self.assertIn("properties", params)

    def test_expected_functions_exist(self):
        """Test that all expected functions are declared."""
        expected_functions = {
            "get_team_metrics",
            "get_ai_adoption_trend",
            "get_developer_stats",
            "get_ai_quality_comparison",
            "get_reviewer_workload",
            "get_recent_prs",
        }

        actual_functions = {d["name"] for d in FUNCTION_DECLARATIONS}

        self.assertEqual(expected_functions, actual_functions)

    def test_days_parameter_is_integer_type(self):
        """Test that days parameter is integer type where used."""
        for declaration in FUNCTION_DECLARATIONS:
            params = declaration["parameters"]["properties"]
            if "days" in params:
                self.assertEqual(params["days"]["type"], "integer")
