"""Tests for golden test cases."""

from django.test import TestCase

from apps.metrics.prompts.golden_tests import (
    GOLDEN_TESTS,
    GoldenTest,
    GoldenTestCategory,
    get_negative_tests,
    get_positive_tests,
    get_tests_by_category,
    to_promptfoo_test,
)


class TestGoldenTestDataclass(TestCase):
    """Tests for GoldenTest dataclass."""

    def test_create_minimal_test(self):
        """Should create test with minimal required fields."""
        test = GoldenTest(
            id="test_1",
            description="Test description",
            category=GoldenTestCategory.POSITIVE,
        )
        self.assertEqual(test.id, "test_1")
        self.assertEqual(test.category, GoldenTestCategory.POSITIVE)
        self.assertEqual(test.pr_title, "")
        self.assertEqual(test.pr_body, "")
        self.assertIsNone(test.expected_ai_assisted)

    def test_create_full_test(self):
        """Should create test with all fields."""
        test = GoldenTest(
            id="test_full",
            description="Full test",
            category=GoldenTestCategory.POSITIVE,
            pr_title="Test PR",
            pr_body="Test body",
            additions=100,
            deletions=50,
            expected_ai_assisted=True,
            expected_tools=["cursor", "claude"],
            min_confidence=0.8,
            expected_categories=["backend"],
            expected_pr_type="feature",
            notes="Test notes",
        )
        self.assertEqual(test.expected_tools, ["cursor", "claude"])
        self.assertEqual(test.min_confidence, 0.8)
        self.assertEqual(test.expected_pr_type, "feature")


class TestGoldenTestsCollection(TestCase):
    """Tests for GOLDEN_TESTS collection."""

    def test_golden_tests_not_empty(self):
        """Should have test cases defined."""
        self.assertGreater(len(GOLDEN_TESTS), 0)

    def test_all_tests_have_unique_ids(self):
        """All test IDs should be unique."""
        ids = [t.id for t in GOLDEN_TESTS]
        self.assertEqual(len(ids), len(set(ids)))

    def test_all_tests_have_descriptions(self):
        """All tests should have non-empty descriptions."""
        for test in GOLDEN_TESTS:
            with self.subTest(test_id=test.id):
                self.assertTrue(len(test.description) > 0)

    def test_all_tests_have_valid_category(self):
        """All tests should have a valid GoldenTestCategory."""
        for test in GOLDEN_TESTS:
            with self.subTest(test_id=test.id):
                self.assertIsInstance(test.category, GoldenTestCategory)

    def test_positive_tests_expect_ai_assisted_true(self):
        """Positive tests should expect AI detection."""
        for test in get_positive_tests():
            with self.subTest(test_id=test.id):
                self.assertTrue(
                    test.expected_ai_assisted is True,
                    f"Positive test {test.id} should expect is_assisted=True",
                )

    def test_negative_tests_expect_ai_assisted_false(self):
        """Negative tests should expect no AI detection."""
        for test in get_negative_tests():
            with self.subTest(test_id=test.id):
                self.assertTrue(
                    test.expected_ai_assisted is False,
                    f"Negative test {test.id} should expect is_assisted=False",
                )

    def test_has_positive_tests(self):
        """Should have at least some positive tests."""
        positive = get_positive_tests()
        self.assertGreater(len(positive), 0)

    def test_has_negative_tests(self):
        """Should have at least some negative tests."""
        negative = get_negative_tests()
        self.assertGreater(len(negative), 0)

    def test_has_edge_case_tests(self):
        """Should have at least some edge case tests."""
        edge_cases = get_tests_by_category(GoldenTestCategory.EDGE_CASE)
        self.assertGreater(len(edge_cases), 0)

    def test_id_naming_convention(self):
        """Test IDs should follow naming convention."""
        for test in GOLDEN_TESTS:
            with self.subTest(test_id=test.id):
                # IDs should be lowercase with underscores
                self.assertEqual(test.id, test.id.lower())
                self.assertNotIn(" ", test.id)
                self.assertNotIn("-", test.id)


class TestToPromptfooTest(TestCase):
    """Tests for to_promptfoo_test conversion function."""

    def setUp(self):
        """Set up test fixtures."""
        self.schema_assertion = {
            "type": "javascript",
            "value": "true",  # Simplified for testing
            "description": "Schema validation",
        }

    def test_basic_conversion(self):
        """Should convert basic test to promptfoo format."""
        test = GoldenTest(
            id="test_basic",
            description="Basic test",
            category=GoldenTestCategory.POSITIVE,
            pr_title="Test Title",
            pr_body="Test Body",
        )
        result = to_promptfoo_test(test, self.schema_assertion)

        self.assertIn("description", result)
        self.assertIn("[test_basic]", result["description"])
        self.assertEqual(result["vars"]["pr_title"], "Test Title")
        self.assertEqual(result["vars"]["pr_body"], "Test Body")

    def test_includes_is_json_assertion(self):
        """Should always include is-json assertion."""
        test = GoldenTest(
            id="test_json",
            description="JSON test",
            category=GoldenTestCategory.POSITIVE,
        )
        result = to_promptfoo_test(test, self.schema_assertion)

        assertions = result["assert"]
        json_assertions = [a for a in assertions if a.get("type") == "is-json"]
        self.assertEqual(len(json_assertions), 1)

    def test_includes_schema_assertion(self):
        """Should include schema validation assertion."""
        test = GoldenTest(
            id="test_schema",
            description="Schema test",
            category=GoldenTestCategory.POSITIVE,
        )
        result = to_promptfoo_test(test, self.schema_assertion)

        self.assertIn(self.schema_assertion, result["assert"])

    def test_ai_assisted_true_assertion(self):
        """Should add assertion for expected_ai_assisted=True."""
        test = GoldenTest(
            id="test_ai_true",
            description="AI true test",
            category=GoldenTestCategory.POSITIVE,
            expected_ai_assisted=True,
        )
        result = to_promptfoo_test(test, self.schema_assertion)

        assertions = result["assert"]
        ai_assertions = [a for a in assertions if "is_assisted === true" in a.get("value", "")]
        self.assertEqual(len(ai_assertions), 1)

    def test_ai_assisted_false_assertion(self):
        """Should add assertion for expected_ai_assisted=False."""
        test = GoldenTest(
            id="test_ai_false",
            description="AI false test",
            category=GoldenTestCategory.NEGATIVE,
            expected_ai_assisted=False,
        )
        result = to_promptfoo_test(test, self.schema_assertion)

        assertions = result["assert"]
        ai_assertions = [a for a in assertions if "is_assisted === false" in a.get("value", "")]
        self.assertEqual(len(ai_assertions), 1)

    def test_expected_tools_assertions(self):
        """Should add assertions for expected tools."""
        test = GoldenTest(
            id="test_tools",
            description="Tools test",
            category=GoldenTestCategory.POSITIVE,
            expected_ai_assisted=True,
            expected_tools=["cursor", "claude"],
        )
        result = to_promptfoo_test(test, self.schema_assertion)

        assertions = result["assert"]
        tool_assertions = [a for a in assertions if "tools.includes" in a.get("value", "")]
        self.assertEqual(len(tool_assertions), 2)

    def test_not_expected_tools_assertions(self):
        """Should add negative assertions for tools that shouldn't appear."""
        test = GoldenTest(
            id="test_not_tools",
            description="Not tools test",
            category=GoldenTestCategory.NEGATIVE,
            expected_ai_assisted=False,
            expected_not_tools=["gemini"],
        )
        result = to_promptfoo_test(test, self.schema_assertion)

        assertions = result["assert"]
        not_tool_assertions = [a for a in assertions if "!JSON.parse(output).ai.tools.includes" in a.get("value", "")]
        self.assertEqual(len(not_tool_assertions), 1)

    def test_min_confidence_assertion(self):
        """Should add confidence threshold assertion."""
        test = GoldenTest(
            id="test_confidence",
            description="Confidence test",
            category=GoldenTestCategory.POSITIVE,
            expected_ai_assisted=True,
            min_confidence=0.8,
        )
        result = to_promptfoo_test(test, self.schema_assertion)

        assertions = result["assert"]
        confidence_assertions = [a for a in assertions if "confidence >= 0.8" in a.get("value", "")]
        self.assertEqual(len(confidence_assertions), 1)

    def test_expected_categories_assertions(self):
        """Should add assertions for expected tech categories."""
        test = GoldenTest(
            id="test_categories",
            description="Categories test",
            category=GoldenTestCategory.TECH_DETECTION,
            expected_categories=["backend", "frontend"],
        )
        result = to_promptfoo_test(test, self.schema_assertion)

        assertions = result["assert"]
        category_assertions = [a for a in assertions if "categories.includes" in a.get("value", "")]
        self.assertEqual(len(category_assertions), 2)

    def test_expected_pr_type_assertion(self):
        """Should add assertion for expected PR type."""
        test = GoldenTest(
            id="test_pr_type",
            description="PR type test",
            category=GoldenTestCategory.SUMMARY,
            expected_pr_type="feature",
        )
        result = to_promptfoo_test(test, self.schema_assertion)

        assertions = result["assert"]
        type_assertions = [a for a in assertions if 'summary.type === "feature"' in a.get("value", "")]
        self.assertEqual(len(type_assertions), 1)

    def test_vars_include_additions_deletions(self):
        """Should include additions and deletions in vars."""
        test = GoldenTest(
            id="test_sizes",
            description="Size test",
            category=GoldenTestCategory.POSITIVE,
            additions=100,
            deletions=50,
        )
        result = to_promptfoo_test(test, self.schema_assertion)

        self.assertEqual(result["vars"]["additions"], 100)
        self.assertEqual(result["vars"]["deletions"], 50)


class TestGoldenTestDataConsistency(TestCase):
    """Tests for data consistency in golden tests."""

    def test_file_count_matches_file_paths(self):
        """file_count should match len(file_paths) when both are set."""
        for test in GOLDEN_TESTS:
            if test.file_count > 0 and test.file_paths:
                with self.subTest(test_id=test.id):
                    self.assertEqual(
                        test.file_count,
                        len(test.file_paths),
                        f"{test.id}: file_count={test.file_count} but has {len(test.file_paths)} file_paths",
                    )

    def test_all_tests_have_repo_name(self):
        """All tests should have repo_name set for consistent context."""
        for test in GOLDEN_TESTS:
            with self.subTest(test_id=test.id):
                self.assertIsNotNone(
                    test.repo_name,
                    f"{test.id}: missing repo_name",
                )


class TestGetTestsByCategory(TestCase):
    """Tests for category filtering functions."""

    def test_get_tests_by_category_positive(self):
        """Should return only positive tests."""
        tests = get_tests_by_category(GoldenTestCategory.POSITIVE)
        for test in tests:
            self.assertEqual(test.category, GoldenTestCategory.POSITIVE)

    def test_get_tests_by_category_negative(self):
        """Should return only negative tests."""
        tests = get_tests_by_category(GoldenTestCategory.NEGATIVE)
        for test in tests:
            self.assertEqual(test.category, GoldenTestCategory.NEGATIVE)

    def test_get_positive_tests_same_as_category(self):
        """get_positive_tests should match get_tests_by_category."""
        positive = get_positive_tests()
        by_category = get_tests_by_category(GoldenTestCategory.POSITIVE)
        self.assertEqual(positive, by_category)

    def test_get_negative_tests_same_as_category(self):
        """get_negative_tests should match get_tests_by_category."""
        negative = get_negative_tests()
        by_category = get_tests_by_category(GoldenTestCategory.NEGATIVE)
        self.assertEqual(negative, by_category)
