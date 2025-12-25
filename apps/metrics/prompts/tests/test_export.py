"""Tests for prompt export functionality."""

import tempfile
from pathlib import Path

import yaml
from django.test import TestCase

from apps.metrics.prompts.export import (
    export_promptfoo_config,
    get_promptfoo_config,
)
from apps.metrics.services.llm_prompts import (
    PR_ANALYSIS_SYSTEM_PROMPT,
    PROMPT_VERSION,
)


class TestGetPromptfooConfig(TestCase):
    """Tests for get_promptfoo_config function."""

    def test_returns_dict(self):
        """Config should be a dictionary."""
        config = get_promptfoo_config("v1.0.0-system.txt")
        self.assertIsInstance(config, dict)

    def test_includes_description_with_version(self):
        """Description should include prompt version."""
        config = get_promptfoo_config("v1.0.0-system.txt")
        self.assertIn(PROMPT_VERSION, config["description"])

    def test_includes_groq_providers(self):
        """Should configure Groq providers (Llama and GPT-OSS)."""
        config = get_promptfoo_config("v1.0.0-system.txt")
        self.assertEqual(len(config["providers"]), 2)
        # Both providers should be Groq-based
        for provider in config["providers"]:
            self.assertIn("groq", provider["id"])

    def test_includes_prompt_with_version(self):
        """Prompt ID should match version."""
        config = get_promptfoo_config("v1.0.0-system.txt")
        self.assertEqual(config["prompts"][0]["id"], f"v{PROMPT_VERSION}")

    def test_default_test_references_prompt_file(self):
        """Default test should reference the prompt file."""
        config = get_promptfoo_config("v1.0.0-system.txt")
        self.assertIn("v1.0.0-system.txt", config["defaultTest"]["vars"]["system_prompt"])

    def test_includes_test_cases(self):
        """Should include basic test cases."""
        config = get_promptfoo_config("v1.0.0-system.txt")
        self.assertGreater(len(config["tests"]), 0)

    def test_test_cases_have_assertions(self):
        """Each test case should have assertions."""
        config = get_promptfoo_config("v1.0.0-system.txt")
        for test in config["tests"]:
            self.assertIn("assert", test)
            self.assertGreater(len(test["assert"]), 0)

    def test_config_is_valid_yaml(self):
        """Config should serialize to valid YAML."""
        config = get_promptfoo_config("v1.0.0-system.txt")
        yaml_str = yaml.dump(config)
        parsed = yaml.safe_load(yaml_str)
        self.assertEqual(parsed["description"], config["description"])


class TestExportPromptfooConfig(TestCase):
    """Tests for export_promptfoo_config function."""

    def test_creates_prompt_file(self):
        """Should create versioned prompt file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = export_promptfoo_config(Path(tmpdir))
            self.assertTrue(result["prompt"].exists())
            self.assertIn(PROMPT_VERSION, result["prompt"].name)

    def test_creates_config_file(self):
        """Should create promptfoo.yaml."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = export_promptfoo_config(Path(tmpdir))
            self.assertTrue(result["config"].exists())
            self.assertEqual(result["config"].name, "promptfoo.yaml")

    def test_prompt_file_contains_system_prompt(self):
        """Prompt file should contain the system prompt."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = export_promptfoo_config(Path(tmpdir))
            content = result["prompt"].read_text()
            # Check key sections are present
            self.assertIn("AI Detection", content)
            self.assertIn("Technology Detection", content)
            self.assertIn("Response Format", content)

    def test_prompt_file_matches_source(self):
        """Prompt file should exactly match source of truth."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = export_promptfoo_config(Path(tmpdir))
            content = result["prompt"].read_text()
            self.assertEqual(content, PR_ANALYSIS_SYSTEM_PROMPT)

    def test_config_file_is_valid_yaml(self):
        """Config file should be valid YAML."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = export_promptfoo_config(Path(tmpdir))
            content = result["config"].read_text()
            config = yaml.safe_load(content)
            self.assertIn("description", config)
            self.assertIn("providers", config)
            self.assertIn("tests", config)

    def test_config_references_correct_prompt_file(self):
        """Config should reference the generated prompt file."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = export_promptfoo_config(Path(tmpdir))
            content = result["config"].read_text()
            config = yaml.safe_load(content)
            prompt_ref = config["defaultTest"]["vars"]["system_prompt"]
            self.assertIn(f"v{PROMPT_VERSION}", prompt_ref)

    def test_creates_prompts_subdirectory(self):
        """Should create prompts/ subdirectory."""
        with tempfile.TemporaryDirectory() as tmpdir:
            export_promptfoo_config(Path(tmpdir))
            prompts_dir = Path(tmpdir) / "prompts"
            self.assertTrue(prompts_dir.exists())
            self.assertTrue(prompts_dir.is_dir())

    def test_config_includes_header_comment(self):
        """Config file should include header comment."""
        with tempfile.TemporaryDirectory() as tmpdir:
            result = export_promptfoo_config(Path(tmpdir))
            content = result["config"].read_text()
            self.assertIn("Auto-generated", content)
            self.assertIn("DO NOT EDIT", content)
