"""
Tests for Copilot metrics Jinja2 template rendering with seat_data and delivery_impact.

This module tests the extended Copilot template sections that render:
- Seat utilization data (seat_data)
- Delivery impact comparison (delivery_impact)

These tests are for the RED phase of TDD - they should FAIL until the template
is updated to render the new sections.
"""

from decimal import Decimal
from pathlib import Path

from django.test import TestCase
from jinja2 import Environment, FileSystemLoader


class TestCopilotJinja2TemplateSeatData(TestCase):
    """Tests for seat_data section in copilot_metrics.jinja2 template."""

    def setUp(self):
        """Set up Jinja2 environment."""
        template_dir = Path(__file__).parent.parent / "prompts" / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.template = self.env.get_template("sections/copilot_metrics.jinja2")

    def test_renders_seat_data_section(self):
        """Test that template renders seat utilization data section.

        The seat_data section should include:
        - Total seats count
        - Active seats count
        - Utilization rate percentage
        """
        # Arrange
        copilot_metrics = {
            "active_users": 5,
            "inactive_count": 0,
            "avg_acceptance_rate": 40.0,
            "total_suggestions": 1000,
            "total_acceptances": 400,
            "top_users": [],
            "seat_data": {
                "total_seats": 25,
                "active_seats": 20,
                "inactive_seats": 5,
                "utilization_rate": Decimal("80.00"),
                "monthly_cost": Decimal("475.00"),
                "wasted_spend": Decimal("95.00"),
                "cost_per_active_user": Decimal("23.75"),
            },
            "delivery_impact": None,
        }

        # Act
        result = self.template.render(copilot_metrics=copilot_metrics)

        # Assert
        self.assertIn("Seat Utilization", result)
        self.assertIn("25", result)  # total_seats
        self.assertIn("20", result)  # active_seats
        self.assertIn("80", result)  # utilization_rate

    def test_renders_wasted_spend_warning(self):
        """Test that template shows wasted spend warning when wasted_spend > 0.

        When there are inactive seats, the template should show a warning
        about the wasted monthly spend.
        """
        # Arrange
        copilot_metrics = {
            "active_users": 5,
            "inactive_count": 3,
            "avg_acceptance_rate": 40.0,
            "total_suggestions": 1000,
            "total_acceptances": 400,
            "top_users": [],
            "seat_data": {
                "total_seats": 25,
                "active_seats": 20,
                "inactive_seats": 5,
                "utilization_rate": Decimal("80.00"),
                "monthly_cost": Decimal("475.00"),
                "wasted_spend": Decimal("95.00"),
                "cost_per_active_user": Decimal("23.75"),
            },
            "delivery_impact": None,
        }

        # Act
        result = self.template.render(copilot_metrics=copilot_metrics)

        # Assert
        self.assertIn("95", result)  # wasted_spend amount
        self.assertIn("wasted", result.lower())  # "wasted" keyword in context

    def test_renders_cost_per_active_user(self):
        """Test that template shows cost per active user.

        The cost per active user should be displayed when there are active users.
        """
        # Arrange
        copilot_metrics = {
            "active_users": 5,
            "inactive_count": 0,
            "avg_acceptance_rate": 40.0,
            "total_suggestions": 1000,
            "total_acceptances": 400,
            "top_users": [],
            "seat_data": {
                "total_seats": 10,
                "active_seats": 10,
                "inactive_seats": 0,
                "utilization_rate": Decimal("100.00"),
                "monthly_cost": Decimal("190.00"),
                "wasted_spend": Decimal("0.00"),
                "cost_per_active_user": Decimal("19.00"),
            },
            "delivery_impact": None,
        }

        # Act
        result = self.template.render(copilot_metrics=copilot_metrics)

        # Assert
        self.assertIn("19", result)  # cost_per_active_user
        # Should show cost context
        self.assertTrue("cost" in result.lower() or "per" in result.lower(), "Template should mention cost per user")

    def test_hides_seat_data_when_none(self):
        """Test that no seat section is rendered when seat_data is None.

        When seat_data is None (no CopilotSeatSnapshot exists), the template
        should not render the seat utilization section.
        """
        # Arrange
        copilot_metrics = {
            "active_users": 5,
            "inactive_count": 0,
            "avg_acceptance_rate": 40.0,
            "total_suggestions": 1000,
            "total_acceptances": 400,
            "top_users": [],
            "seat_data": None,
            "delivery_impact": None,
        }

        # Act
        result = self.template.render(copilot_metrics=copilot_metrics)

        # Assert
        self.assertNotIn("Seat Utilization", result)
        self.assertNotIn("total_seats", result)
        self.assertNotIn("wasted_spend", result)


class TestCopilotJinja2TemplateDeliveryImpact(TestCase):
    """Tests for delivery_impact section in copilot_metrics.jinja2 template."""

    def setUp(self):
        """Set up Jinja2 environment."""
        template_dir = Path(__file__).parent.parent / "prompts" / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.template = self.env.get_template("sections/copilot_metrics.jinja2")

    def test_renders_delivery_impact_section(self):
        """Test that template renders delivery impact comparison section.

        The delivery_impact section should include:
        - Number of Copilot-assisted PRs
        - Number of non-Copilot PRs
        - Cycle time comparison
        - Review time comparison
        """
        # Arrange
        copilot_metrics = {
            "active_users": 5,
            "inactive_count": 0,
            "avg_acceptance_rate": 40.0,
            "total_suggestions": 1000,
            "total_acceptances": 400,
            "top_users": [],
            "seat_data": None,
            "delivery_impact": {
                "copilot_prs_count": 45,
                "non_copilot_prs_count": 30,
                "cycle_time_improvement_percent": 25,
                "review_time_improvement_percent": 15,
                "sample_sufficient": True,
            },
        }

        # Act
        result = self.template.render(copilot_metrics=copilot_metrics)

        # Assert
        self.assertIn("Delivery Impact", result)
        self.assertIn("45", result)  # copilot_prs_count
        self.assertIn("30", result)  # non_copilot_prs_count

    def test_shows_improvement_indicators_when_positive(self):
        """Test that template shows 'faster' indicator for positive improvements.

        When cycle_time_improvement_percent is positive, the template should
        indicate that Copilot users are faster.
        """
        # Arrange
        copilot_metrics = {
            "active_users": 5,
            "inactive_count": 0,
            "avg_acceptance_rate": 40.0,
            "total_suggestions": 1000,
            "total_acceptances": 400,
            "top_users": [],
            "seat_data": None,
            "delivery_impact": {
                "copilot_prs_count": 45,
                "non_copilot_prs_count": 30,
                "cycle_time_improvement_percent": 25,
                "review_time_improvement_percent": 15,
                "sample_sufficient": True,
            },
        }

        # Act
        result = self.template.render(copilot_metrics=copilot_metrics)

        # Assert
        self.assertIn("25%", result)  # cycle_time improvement
        self.assertIn("faster", result.lower())  # positive indicator

    def test_shows_slower_indicator_when_negative(self):
        """Test that template shows 'slower' indicator for negative improvements.

        When cycle_time_improvement_percent is negative, the template should
        indicate that Copilot users are slower.
        """
        # Arrange
        copilot_metrics = {
            "active_users": 5,
            "inactive_count": 0,
            "avg_acceptance_rate": 40.0,
            "total_suggestions": 1000,
            "total_acceptances": 400,
            "top_users": [],
            "seat_data": None,
            "delivery_impact": {
                "copilot_prs_count": 45,
                "non_copilot_prs_count": 30,
                "cycle_time_improvement_percent": -10,
                "review_time_improvement_percent": -5,
                "sample_sufficient": True,
            },
        }

        # Act
        result = self.template.render(copilot_metrics=copilot_metrics)

        # Assert
        self.assertIn("10%", result)  # cycle_time (negative value shown as positive)
        self.assertIn("slower", result.lower())  # negative indicator

    def test_shows_sample_warning_when_insufficient(self):
        """Test that template shows warning when sample_sufficient is False.

        When sample_sufficient is False, the template should warn that the
        comparison may not be statistically significant.
        """
        # Arrange
        copilot_metrics = {
            "active_users": 5,
            "inactive_count": 0,
            "avg_acceptance_rate": 40.0,
            "total_suggestions": 1000,
            "total_acceptances": 400,
            "top_users": [],
            "seat_data": None,
            "delivery_impact": {
                "copilot_prs_count": 5,
                "non_copilot_prs_count": 3,
                "cycle_time_improvement_percent": 25,
                "review_time_improvement_percent": 15,
                "sample_sufficient": False,
            },
        }

        # Act
        result = self.template.render(copilot_metrics=copilot_metrics)

        # Assert
        # Should contain a warning about sample size
        self.assertTrue(
            "insufficient" in result.lower()
            or "small sample" in result.lower()
            or "limited data" in result.lower()
            or "not enough" in result.lower(),
            f"Template should warn about insufficient sample size. Got: {result}",
        )

    def test_hides_delivery_impact_when_none(self):
        """Test that no delivery section is rendered when delivery_impact is None.

        When delivery_impact is None (no PR data to compare), the template
        should not render the delivery impact section.
        """
        # Arrange
        copilot_metrics = {
            "active_users": 5,
            "inactive_count": 0,
            "avg_acceptance_rate": 40.0,
            "total_suggestions": 1000,
            "total_acceptances": 400,
            "top_users": [],
            "seat_data": None,
            "delivery_impact": None,
        }

        # Act
        result = self.template.render(copilot_metrics=copilot_metrics)

        # Assert
        self.assertNotIn("Delivery Impact", result)
        self.assertNotIn("copilot_prs_count", result)
        self.assertNotIn("cycle_time_improvement", result)


class TestCopilotJinja2TemplateFullContext(TestCase):
    """Tests for full Copilot template context with all sections."""

    def setUp(self):
        """Set up Jinja2 environment."""
        template_dir = Path(__file__).parent.parent / "prompts" / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.template = self.env.get_template("sections/copilot_metrics.jinja2")

    def test_renders_all_sections_together(self):
        """Test that template renders all sections when all data is present.

        When both seat_data and delivery_impact are provided, the template
        should render all sections in the correct order.
        """
        # Arrange
        copilot_metrics = {
            "active_users": 8,
            "inactive_count": 2,
            "avg_acceptance_rate": 42.5,
            "total_suggestions": 2500,
            "total_acceptances": 1063,
            "top_users": [
                {"name": "Alice", "suggestions": 500, "acceptances": 225},
                {"name": "Bob", "suggestions": 400, "acceptances": 180},
            ],
            "seat_data": {
                "total_seats": 10,
                "active_seats": 8,
                "inactive_seats": 2,
                "utilization_rate": Decimal("80.00"),
                "monthly_cost": Decimal("190.00"),
                "wasted_spend": Decimal("38.00"),
                "cost_per_active_user": Decimal("23.75"),
            },
            "delivery_impact": {
                "copilot_prs_count": 50,
                "non_copilot_prs_count": 25,
                "cycle_time_improvement_percent": 30,
                "review_time_improvement_percent": 20,
                "sample_sufficient": True,
            },
        }

        # Act
        result = self.template.render(copilot_metrics=copilot_metrics)

        # Assert - verify all sections are present
        self.assertIn("Copilot Usage Metrics", result)
        self.assertIn("Seat Utilization", result)
        self.assertIn("Delivery Impact", result)

        # Verify key data points from each section
        self.assertIn("8", result)  # active_users
        self.assertIn("Alice", result)  # top_users
        self.assertIn("80", result)  # utilization_rate
        self.assertIn("30%", result)  # cycle_time_improvement_percent
