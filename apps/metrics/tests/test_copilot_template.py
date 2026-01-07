"""
Tests for Copilot metrics Jinja2 template rendering.
"""

from pathlib import Path

from django.test import TestCase
from jinja2 import Environment, FileSystemLoader


class TestCopilotMetricsTemplate(TestCase):
    """Tests for copilot_metrics.jinja2 template."""

    def setUp(self):
        """Set up Jinja2 environment."""
        template_dir = Path(__file__).parent.parent / "prompts" / "templates"
        self.env = Environment(
            loader=FileSystemLoader(str(template_dir)),
            trim_blocks=True,
            lstrip_blocks=True,
        )
        self.template = self.env.get_template("sections/copilot_metrics.jinja2")

    def test_renders_copilot_section_with_data(self):
        """Test that template renders Copilot section when data is present."""
        # Arrange
        copilot_metrics = {
            "active_users": 5,
            "inactive_count": 2,
            "avg_acceptance_rate": 45.5,
            "total_suggestions": 1000,
            "total_acceptances": 455,
            "top_users": [
                {"name": "Alice", "suggestions": 300, "acceptances": 150},
                {"name": "Bob", "suggestions": 200, "acceptances": 80},
            ],
        }

        # Act
        result = self.template.render(copilot_metrics=copilot_metrics)

        # Assert
        self.assertIn("Copilot Usage Metrics", result)
        self.assertIn("Active users (this period): 5", result)
        self.assertIn("Inactive licenses: 2", result)
        self.assertIn("45.5%", result)
        self.assertIn("Alice", result)
        self.assertIn("Bob", result)

    def test_hides_section_when_no_data(self):
        """Test that template handles empty copilot_metrics gracefully."""
        # Act
        result = self.template.render(copilot_metrics=None)

        # Assert
        self.assertIn("No Copilot usage data available", result)

    def test_shows_inactive_licenses_warning(self):
        """Test that inactive licenses are shown when present."""
        # Arrange
        copilot_metrics = {
            "active_users": 3,
            "inactive_count": 5,
            "avg_acceptance_rate": 30.0,
            "total_suggestions": 500,
            "total_acceptances": 150,
            "top_users": [],
        }

        # Act
        result = self.template.render(copilot_metrics=copilot_metrics)

        # Assert
        self.assertIn("Inactive licenses: 5", result)
        self.assertIn("zero usage", result)

    def test_hides_inactive_when_zero(self):
        """Test that inactive licenses line is hidden when count is 0."""
        # Arrange
        copilot_metrics = {
            "active_users": 5,
            "inactive_count": 0,
            "avg_acceptance_rate": 40.0,
            "total_suggestions": 1000,
            "total_acceptances": 400,
            "top_users": [],
        }

        # Act
        result = self.template.render(copilot_metrics=copilot_metrics)

        # Assert
        self.assertNotIn("Inactive licenses", result)

    def test_shows_low_adoption_warning(self):
        """Test that low adoption warning appears for low acceptance rates."""
        # Arrange
        copilot_metrics = {
            "active_users": 5,
            "inactive_count": 0,
            "avg_acceptance_rate": 15.0,  # Low rate
            "total_suggestions": 1000,
            "total_acceptances": 150,
            "top_users": [],
        }

        # Act
        result = self.template.render(copilot_metrics=copilot_metrics)

        # Assert
        self.assertIn("LOW", result)
        self.assertIn("training", result)

    def test_shows_good_adoption_indicator(self):
        """Test that good adoption indicator appears for high acceptance rates."""
        # Arrange
        copilot_metrics = {
            "active_users": 5,
            "inactive_count": 0,
            "avg_acceptance_rate": 50.0,  # High rate
            "total_suggestions": 1000,
            "total_acceptances": 500,
            "top_users": [],
        }

        # Act
        result = self.template.render(copilot_metrics=copilot_metrics)

        # Assert
        self.assertIn("GOOD", result)
        self.assertIn("healthy adoption", result)
