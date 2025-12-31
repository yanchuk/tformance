"""Tests for LLM response schema validation."""

from django.test import TestCase

from apps.metrics.prompts.schemas import (
    EXAMPLE_MINIMAL_RESPONSE,
    EXAMPLE_VALID_INSIGHT,
    EXAMPLE_VALID_RESPONSE,
    INSIGHT_RESPONSE_SCHEMA,
    PR_ANALYSIS_RESPONSE_SCHEMA,
    SCHEMA_VERSION,
    get_schema_as_json,
    validate_ai_response,
    validate_insight_response,
    validate_llm_response,
)


class TestSchemaVersion(TestCase):
    """Tests for schema versioning."""

    def test_schema_version_format(self):
        """Version should be semver format."""
        parts = SCHEMA_VERSION.split(".")
        self.assertEqual(len(parts), 3)
        for part in parts:
            self.assertTrue(part.isdigit())

    def test_schema_has_title(self):
        """Schema should have a title."""
        self.assertIn("title", PR_ANALYSIS_RESPONSE_SCHEMA)

    def test_schema_has_required_fields(self):
        """Schema should require ai, tech, summary, health."""
        required = PR_ANALYSIS_RESPONSE_SCHEMA["required"]
        self.assertIn("ai", required)
        self.assertIn("tech", required)
        self.assertIn("summary", required)
        self.assertIn("health", required)


class TestValidateLlmResponse(TestCase):
    """Tests for validate_llm_response function."""

    def test_valid_response_passes(self):
        """Example valid response should pass validation."""
        is_valid, errors = validate_llm_response(EXAMPLE_VALID_RESPONSE)
        self.assertTrue(is_valid, f"Expected valid but got errors: {errors}")
        self.assertEqual(len(errors), 0)

    def test_minimal_response_passes(self):
        """Minimal valid response should pass validation."""
        is_valid, errors = validate_llm_response(EXAMPLE_MINIMAL_RESPONSE)
        self.assertTrue(is_valid, f"Expected valid but got errors: {errors}")

    def test_empty_dict_fails(self):
        """Empty response should fail validation."""
        is_valid, errors = validate_llm_response({})
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_missing_ai_fails(self):
        """Response missing 'ai' should fail."""
        response = {
            "tech": EXAMPLE_VALID_RESPONSE["tech"],
            "summary": EXAMPLE_VALID_RESPONSE["summary"],
            "health": EXAMPLE_VALID_RESPONSE["health"],
        }
        is_valid, errors = validate_llm_response(response)
        self.assertFalse(is_valid)
        self.assertTrue(any("ai" in e for e in errors))

    def test_missing_tech_fails(self):
        """Response missing 'tech' should fail."""
        response = {
            "ai": EXAMPLE_VALID_RESPONSE["ai"],
            "summary": EXAMPLE_VALID_RESPONSE["summary"],
            "health": EXAMPLE_VALID_RESPONSE["health"],
        }
        is_valid, errors = validate_llm_response(response)
        self.assertFalse(is_valid)
        self.assertTrue(any("tech" in e for e in errors))

    def test_missing_summary_fails(self):
        """Response missing 'summary' should fail."""
        response = {
            "ai": EXAMPLE_VALID_RESPONSE["ai"],
            "tech": EXAMPLE_VALID_RESPONSE["tech"],
            "health": EXAMPLE_VALID_RESPONSE["health"],
        }
        is_valid, errors = validate_llm_response(response)
        self.assertFalse(is_valid)
        self.assertTrue(any("summary" in e for e in errors))

    def test_missing_health_fails(self):
        """Response missing 'health' should fail."""
        response = {
            "ai": EXAMPLE_VALID_RESPONSE["ai"],
            "tech": EXAMPLE_VALID_RESPONSE["tech"],
            "summary": EXAMPLE_VALID_RESPONSE["summary"],
        }
        is_valid, errors = validate_llm_response(response)
        self.assertFalse(is_valid)
        self.assertTrue(any("health" in e for e in errors))

    def test_extra_fields_rejected(self):
        """Extra top-level fields should be rejected."""
        response = {
            **EXAMPLE_VALID_RESPONSE,
            "extra_field": "not allowed",
        }
        is_valid, errors = validate_llm_response(response)
        self.assertFalse(is_valid)
        self.assertTrue(any("extra_field" in e or "Additional" in e for e in errors))


class TestAiSchemaValidation(TestCase):
    """Tests for AI portion of schema."""

    def test_valid_ai_data(self):
        """Valid AI data should pass."""
        ai_data = {
            "is_assisted": True,
            "tools": ["cursor", "claude"],
            "usage_type": "authored",
            "confidence": 0.95,
        }
        is_valid, errors = validate_ai_response(ai_data)
        self.assertTrue(is_valid, f"Errors: {errors}")

    def test_missing_is_assisted_fails(self):
        """Missing is_assisted should fail."""
        ai_data = {
            "tools": [],
            "confidence": 0.0,
        }
        is_valid, errors = validate_ai_response(ai_data)
        self.assertFalse(is_valid)
        self.assertTrue(any("is_assisted" in e for e in errors))

    def test_missing_tools_fails(self):
        """Missing tools should fail."""
        ai_data = {
            "is_assisted": False,
            "confidence": 0.0,
        }
        is_valid, errors = validate_ai_response(ai_data)
        self.assertFalse(is_valid)
        self.assertTrue(any("tools" in e for e in errors))

    def test_missing_confidence_fails(self):
        """Missing confidence should fail."""
        ai_data = {
            "is_assisted": False,
            "tools": [],
        }
        is_valid, errors = validate_ai_response(ai_data)
        self.assertFalse(is_valid)
        self.assertTrue(any("confidence" in e for e in errors))

    def test_confidence_out_of_range_fails(self):
        """Confidence > 1.0 should fail."""
        ai_data = {
            "is_assisted": True,
            "tools": ["cursor"],
            "confidence": 1.5,  # Invalid
        }
        is_valid, errors = validate_ai_response(ai_data)
        self.assertFalse(is_valid)

    def test_confidence_negative_fails(self):
        """Confidence < 0 should fail."""
        ai_data = {
            "is_assisted": True,
            "tools": ["cursor"],
            "confidence": -0.1,  # Invalid
        }
        is_valid, errors = validate_ai_response(ai_data)
        self.assertFalse(is_valid)

    def test_invalid_usage_type_fails(self):
        """Invalid usage_type should fail."""
        ai_data = {
            "is_assisted": True,
            "tools": ["cursor"],
            "usage_type": "invalid_type",  # Not in enum
            "confidence": 0.9,
        }
        is_valid, errors = validate_ai_response(ai_data)
        self.assertFalse(is_valid)

    def test_null_usage_type_allowed(self):
        """Null usage_type should be allowed."""
        ai_data = {
            "is_assisted": False,
            "tools": [],
            "usage_type": None,
            "confidence": 0.0,
        }
        is_valid, errors = validate_ai_response(ai_data)
        self.assertTrue(is_valid, f"Errors: {errors}")

    def test_tools_must_be_array(self):
        """Tools must be an array, not string."""
        ai_data = {
            "is_assisted": True,
            "tools": "cursor",  # Should be array
            "confidence": 0.9,
        }
        is_valid, errors = validate_ai_response(ai_data)
        self.assertFalse(is_valid)


class TestTechSchemaValidation(TestCase):
    """Tests for tech portion of schema."""

    def test_invalid_category_fails(self):
        """Invalid category should fail."""
        response = {
            **EXAMPLE_VALID_RESPONSE,
            "tech": {
                "languages": ["python"],
                "frameworks": ["django"],
                "categories": ["invalid_category"],  # Not in enum
            },
        }
        is_valid, errors = validate_llm_response(response)
        self.assertFalse(is_valid)

    def test_all_valid_categories(self):
        """All valid categories should pass."""
        response = {
            **EXAMPLE_VALID_RESPONSE,
            "tech": {
                "languages": ["python"],
                "frameworks": ["django"],
                "categories": ["backend", "frontend", "devops", "mobile", "data"],
            },
        }
        is_valid, errors = validate_llm_response(response)
        self.assertTrue(is_valid, f"Errors: {errors}")


class TestSummarySchemaValidation(TestCase):
    """Tests for summary portion of schema."""

    def test_invalid_pr_type_fails(self):
        """Invalid PR type should fail."""
        response = {
            **EXAMPLE_VALID_RESPONSE,
            "summary": {
                "title": "Fix bug",
                "description": "Fixes a bug.",
                "type": "invalid_type",  # Not in enum
            },
        }
        is_valid, errors = validate_llm_response(response)
        self.assertFalse(is_valid)

    def test_all_valid_pr_types(self):
        """All valid PR types should pass."""
        for pr_type in ["feature", "bugfix", "refactor", "docs", "test", "chore", "ci"]:
            response = {
                **EXAMPLE_VALID_RESPONSE,
                "summary": {
                    "title": "Test PR",
                    "description": "Test description.",
                    "type": pr_type,
                },
            }
            is_valid, errors = validate_llm_response(response)
            self.assertTrue(is_valid, f"Type '{pr_type}' should be valid but got: {errors}")

    def test_empty_title_fails(self):
        """Empty title should fail."""
        response = {
            **EXAMPLE_VALID_RESPONSE,
            "summary": {
                "title": "",  # Empty
                "description": "Test description.",
                "type": "feature",
            },
        }
        is_valid, errors = validate_llm_response(response)
        self.assertFalse(is_valid)


class TestHealthSchemaValidation(TestCase):
    """Tests for health portion of schema."""

    def test_invalid_review_friction_fails(self):
        """Invalid review_friction should fail."""
        response = {
            **EXAMPLE_VALID_RESPONSE,
            "health": {
                "review_friction": "invalid",  # Not in enum
                "scope": "medium",
                "risk_level": "low",
                "insights": [],
            },
        }
        is_valid, errors = validate_llm_response(response)
        self.assertFalse(is_valid)

    def test_invalid_scope_fails(self):
        """Invalid scope should fail."""
        response = {
            **EXAMPLE_VALID_RESPONSE,
            "health": {
                "review_friction": "low",
                "scope": "invalid",  # Not in enum
                "risk_level": "low",
                "insights": [],
            },
        }
        is_valid, errors = validate_llm_response(response)
        self.assertFalse(is_valid)

    def test_invalid_risk_level_fails(self):
        """Invalid risk_level should fail."""
        response = {
            **EXAMPLE_VALID_RESPONSE,
            "health": {
                "review_friction": "low",
                "scope": "medium",
                "risk_level": "critical",  # Not in enum (should be low/medium/high)
                "insights": [],
            },
        }
        is_valid, errors = validate_llm_response(response)
        self.assertFalse(is_valid)

    def test_all_valid_health_enums(self):
        """All valid health enum combinations should pass."""
        for friction in ["low", "medium", "high"]:
            for scope in ["small", "medium", "large", "xlarge"]:
                for risk in ["low", "medium", "high"]:
                    response = {
                        **EXAMPLE_VALID_RESPONSE,
                        "health": {
                            "review_friction": friction,
                            "scope": scope,
                            "risk_level": risk,
                            "insights": ["Test insight"],
                        },
                    }
                    is_valid, errors = validate_llm_response(response)
                    self.assertTrue(
                        is_valid,
                        f"friction={friction}, scope={scope}, risk={risk} should be valid: {errors}",
                    )


class TestGetSchemaAsJson(TestCase):
    """Tests for get_schema_as_json function."""

    def test_returns_dict(self):
        """Should return a dictionary."""
        schema = get_schema_as_json()
        self.assertIsInstance(schema, dict)

    def test_matches_main_schema(self):
        """Should return the same schema."""
        schema = get_schema_as_json()
        self.assertEqual(schema, PR_ANALYSIS_RESPONSE_SCHEMA)

    def test_has_json_schema_marker(self):
        """Should have $schema field."""
        schema = get_schema_as_json()
        self.assertIn("$schema", schema)


class TestInsightSchemaValidation(TestCase):
    """Tests for dashboard insight schema validation."""

    def test_valid_insight_passes(self):
        """Example valid insight should pass validation."""
        is_valid, errors = validate_insight_response(EXAMPLE_VALID_INSIGHT)
        self.assertTrue(is_valid, f"Expected valid but got errors: {errors}")
        self.assertEqual(len(errors), 0)

    def test_empty_dict_fails(self):
        """Empty response should fail validation."""
        is_valid, errors = validate_insight_response({})
        self.assertFalse(is_valid)
        self.assertGreater(len(errors), 0)

    def test_missing_headline_fails(self):
        """Response missing 'headline' should fail."""
        response = {
            "detail": "Some detail",
            "recommendation": "Some recommendation",
            "metric_cards": EXAMPLE_VALID_INSIGHT["metric_cards"],
        }
        is_valid, errors = validate_insight_response(response)
        self.assertFalse(is_valid)
        self.assertTrue(any("headline" in e for e in errors))

    def test_missing_metric_cards_fails(self):
        """Response missing 'metric_cards' should fail."""
        response = {
            "headline": "Test headline with enough length",
            "detail": "Some detail with enough characters.",
            "recommendation": "Some recommendation",
        }
        is_valid, errors = validate_insight_response(response)
        self.assertFalse(is_valid)
        self.assertTrue(any("metric_cards" in e for e in errors))

    def test_wrong_metric_cards_count_fails(self):
        """Response with wrong number of metric cards should fail."""
        response = {
            "headline": "Test headline with enough length",
            "detail": "Some detail with enough characters for validation.",
            "recommendation": "Some recommendation here",
            "metric_cards": [
                {"label": "Test", "value": "10", "trend": "positive"},
                {"label": "Test2", "value": "20", "trend": "negative"},
            ],  # Only 2 cards, need exactly 4
        }
        is_valid, errors = validate_insight_response(response)
        self.assertFalse(is_valid)

    def test_invalid_trend_fails(self):
        """Metric card with invalid trend should fail."""
        response = {
            "headline": "Test headline with enough length",
            "detail": "Some detail with enough characters for validation.",
            "recommendation": "Some recommendation here",
            "metric_cards": [
                {"label": "Test", "value": "10", "trend": "invalid_trend"},
                {"label": "Test2", "value": "20", "trend": "positive"},
                {"label": "Test3", "value": "30", "trend": "negative"},
                {"label": "Test4", "value": "40", "trend": "neutral"},
            ],
        }
        is_valid, errors = validate_insight_response(response)
        self.assertFalse(is_valid)

    def test_all_valid_trends_pass(self):
        """All valid trend values should pass."""
        for trend in ["positive", "negative", "neutral", "warning"]:
            response = {
                "headline": "Test headline with enough length",
                "detail": "Some detail with enough characters for validation.",
                "recommendation": "Some recommendation here",
                "metric_cards": [
                    {"label": "Test1", "value": "10", "trend": trend},
                    {"label": "Test2", "value": "20", "trend": trend},
                    {"label": "Test3", "value": "30", "trend": trend},
                    {"label": "Test4", "value": "40", "trend": trend},
                ],
            }
            is_valid, errors = validate_insight_response(response)
            self.assertTrue(is_valid, f"Trend '{trend}' should be valid: {errors}")

    def test_is_fallback_optional(self):
        """is_fallback field should be optional."""
        response = {
            "headline": "Test headline with enough length",
            "detail": "Some detail with enough characters for validation.",
            "recommendation": "Some recommendation here",
            "metric_cards": [
                {"label": "Test1", "value": "10", "trend": "positive"},
                {"label": "Test2", "value": "20", "trend": "negative"},
                {"label": "Test3", "value": "30", "trend": "neutral"},
                {"label": "Test4", "value": "40", "trend": "warning"},
            ],
            # No is_fallback field - should still pass
        }
        is_valid, errors = validate_insight_response(response)
        self.assertTrue(is_valid, f"Response without is_fallback should be valid: {errors}")

    def test_insight_schema_has_required_fields(self):
        """Insight schema should require headline, detail, recommendation, metric_cards."""
        required = INSIGHT_RESPONSE_SCHEMA["required"]
        self.assertIn("headline", required)
        self.assertIn("detail", required)
        self.assertIn("recommendation", required)
        self.assertIn("metric_cards", required)
