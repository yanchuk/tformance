"""Tests for experiment runner."""

import json
import os
import tempfile
from unittest.mock import MagicMock, patch

from django.test import TestCase

from apps.metrics.experiments.runner import (
    AIDetectionResult,
    ExperimentConfig,
    ExperimentResult,
    ExperimentRunner,
    create_batch_request,
    detect_ai_with_litellm,
    load_prompt_from_file,
    parse_llm_response,
)
from apps.metrics.factories import PullRequestFactory, TeamFactory


class TestAIDetectionResult(TestCase):
    """Tests for AIDetectionResult dataclass."""

    def test_create_from_dict(self):
        """Test creating result from LLM response dict."""
        data = {
            "is_ai_assisted": True,
            "tools": ["cursor", "claude"],
            "usage_category": "assisted",
            "confidence": 0.95,
            "reasoning": "Cursor IDE mentioned in AI Disclosure section",
        }
        result = AIDetectionResult.from_dict(data)

        self.assertTrue(result.is_ai_assisted)
        self.assertEqual(result.tools, ["cursor", "claude"])
        self.assertEqual(result.usage_category, "assisted")
        self.assertEqual(result.confidence, 0.95)
        self.assertEqual(result.reasoning, "Cursor IDE mentioned in AI Disclosure section")

    def test_create_from_dict_missing_optional_fields(self):
        """Test creating result with only required fields."""
        data = {
            "is_ai_assisted": False,
            "tools": [],
            "confidence": 0.9,
        }
        result = AIDetectionResult.from_dict(data)

        self.assertFalse(result.is_ai_assisted)
        self.assertEqual(result.tools, [])
        self.assertIsNone(result.usage_category)
        self.assertEqual(result.confidence, 0.9)
        self.assertIsNone(result.reasoning)

    def test_to_dict(self):
        """Test converting result to dict."""
        result = AIDetectionResult(
            is_ai_assisted=True,
            tools=["copilot"],
            usage_category="authored",
            confidence=0.85,
            reasoning="Copilot signature found",
        )
        data = result.to_dict()

        self.assertEqual(data["is_ai_assisted"], True)
        self.assertEqual(data["tools"], ["copilot"])
        self.assertEqual(data["usage_category"], "authored")
        self.assertEqual(data["confidence"], 0.85)
        self.assertEqual(data["reasoning"], "Copilot signature found")


class TestLoadPromptFromFile(TestCase):
    """Tests for loading prompts from markdown files."""

    def test_load_prompt_file(self):
        """Test loading a prompt from a markdown file."""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".md", delete=False) as f:
            f.write("# Test Prompt\n\n## System Prompt\n\nYou are a test assistant.\n")
            f.flush()

            content = load_prompt_from_file(f.name)
            self.assertIn("You are a test assistant", content)

        os.unlink(f.name)

    def test_load_prompt_file_not_found(self):
        """Test loading a nonexistent prompt file raises error."""
        with self.assertRaises(FileNotFoundError):
            load_prompt_from_file("/nonexistent/prompt.md")


class TestParseLLMResponse(TestCase):
    """Tests for parsing LLM responses."""

    def test_parse_valid_json(self):
        """Test parsing valid JSON response."""
        response = '{"is_ai_assisted": true, "tools": ["cursor"], "confidence": 0.9}'
        result = parse_llm_response(response)

        self.assertTrue(result.is_ai_assisted)
        self.assertEqual(result.tools, ["cursor"])
        self.assertEqual(result.confidence, 0.9)

    def test_parse_json_in_markdown_block(self):
        """Test parsing JSON wrapped in markdown code block."""
        response = """Here is the analysis:

```json
{"is_ai_assisted": true, "tools": ["claude"], "confidence": 0.85}
```

The PR shows clear signs of AI usage."""
        result = parse_llm_response(response)

        self.assertTrue(result.is_ai_assisted)
        self.assertEqual(result.tools, ["claude"])

    def test_parse_invalid_json_returns_default(self):
        """Test parsing invalid JSON returns conservative default."""
        response = "This is not JSON at all"
        result = parse_llm_response(response)

        self.assertFalse(result.is_ai_assisted)
        self.assertEqual(result.tools, [])
        self.assertEqual(result.confidence, 0.0)


class TestCreateBatchRequest(TestCase):
    """Tests for batch request creation."""

    def test_create_batch_request(self):
        """Test creating a batch request for Groq API."""
        request = create_batch_request(
            pr_id=123,
            pr_body="Test PR body",
            system_prompt="You are a detector.",
            model="llama-3.3-70b-versatile",
        )

        self.assertEqual(request["custom_id"], "pr-123")
        self.assertEqual(request["method"], "POST")
        self.assertEqual(request["url"], "/v1/chat/completions")
        self.assertEqual(request["body"]["model"], "llama-3.3-70b-versatile")
        self.assertEqual(len(request["body"]["messages"]), 2)
        self.assertEqual(request["body"]["messages"][0]["role"], "system")
        self.assertEqual(request["body"]["messages"][1]["role"], "user")
        self.assertIn("Test PR body", request["body"]["messages"][1]["content"])


class TestExperimentConfig(TestCase):
    """Tests for experiment configuration."""

    def test_load_from_yaml(self):
        """Test loading config from YAML file."""
        yaml_content = """
experiment:
  name: "test-experiment"
  description: "Test description"

model:
  provider: "groq"
  name: "llama-3.3-70b-versatile"
  temperature: 0

prompt:
  file: "prompts/v1.md"
"""
        with tempfile.NamedTemporaryFile(mode="w", suffix=".yaml", delete=False) as f:
            f.write(yaml_content)
            f.flush()

            config = ExperimentConfig.from_yaml(f.name)

            self.assertEqual(config.experiment_name, "test-experiment")
            self.assertEqual(config.model_provider, "groq")
            self.assertEqual(config.model_name, "llama-3.3-70b-versatile")
            self.assertEqual(config.temperature, 0)

        os.unlink(f.name)

    def test_get_litellm_model_string(self):
        """Test getting LiteLLM model string."""
        config = ExperimentConfig(
            experiment_name="test",
            model_provider="groq",
            model_name="llama-3.3-70b-versatile",
        )
        self.assertEqual(config.litellm_model, "groq/llama-3.3-70b-versatile")


class TestDetectAIWithLiteLLM(TestCase):
    """Tests for LiteLLM-based detection."""

    @patch("apps.metrics.experiments.runner.litellm.completion")
    def test_detect_ai_positive(self, mock_completion):
        """Test detecting AI usage in a PR."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"is_ai_assisted": true, "tools": ["cursor"], '
                    '"confidence": 0.95, "reasoning": "Cursor mentioned"}'
                )
            )
        ]
        mock_completion.return_value = mock_response

        result = detect_ai_with_litellm(
            pr_body="Used Cursor for this PR",
            model="groq/llama-3.3-70b-versatile",
            system_prompt="You are a detector",
        )

        self.assertTrue(result.is_ai_assisted)
        self.assertIn("cursor", result.tools)
        self.assertEqual(result.confidence, 0.95)

    @patch("apps.metrics.experiments.runner.litellm.completion")
    def test_detect_ai_negative(self, mock_completion):
        """Test detecting no AI usage."""
        mock_response = MagicMock()
        mock_response.choices = [
            MagicMock(
                message=MagicMock(
                    content='{"is_ai_assisted": false, "tools": [], "confidence": 0.9, "reasoning": "No AI mentioned"}'
                )
            )
        ]
        mock_completion.return_value = mock_response

        result = detect_ai_with_litellm(
            pr_body="Regular PR without AI",
            model="groq/llama-3.3-70b-versatile",
            system_prompt="You are a detector",
        )

        self.assertFalse(result.is_ai_assisted)
        self.assertEqual(result.tools, [])


class TestExperimentRunner(TestCase):
    """Tests for the main ExperimentRunner class."""

    def setUp(self):
        """Set up test fixtures."""
        self.team = TeamFactory()
        self.pr_positive = PullRequestFactory(
            team=self.team,
            body="## AI Disclosure\nUsed Cursor for implementation",
        )
        self.pr_negative = PullRequestFactory(
            team=self.team,
            body="## AI Disclosure\nNo AI was used",
        )

    def test_runner_init_with_config_dict(self):
        """Test initializing runner with config dict."""
        config = {
            "experiment": {"name": "test"},
            "model": {
                "provider": "groq",
                "name": "llama-3.3-70b-versatile",
                "temperature": 0,
            },
            "prompt": {"system": "You are a detector"},
        }
        runner = ExperimentRunner(config=config)

        self.assertEqual(runner.config.experiment_name, "test")
        self.assertEqual(runner.config.model_provider, "groq")

    @patch("apps.metrics.experiments.runner.detect_ai_with_litellm")
    def test_run_on_prs(self, mock_detect):
        """Test running detection on a list of PRs."""
        mock_detect.return_value = AIDetectionResult(
            is_ai_assisted=True,
            tools=["cursor"],
            confidence=0.95,
        )

        runner = ExperimentRunner(
            config={
                "experiment": {"name": "test"},
                "model": {"provider": "groq", "name": "llama-3.3-70b-versatile"},
                "prompt": {"system": "You are a detector"},
            }
        )

        results = runner.run(pr_ids=[self.pr_positive.id])

        self.assertEqual(len(results.results), 1)
        self.assertTrue(results.results[self.pr_positive.id].llm_result.is_ai_assisted)

    @patch("apps.metrics.experiments.runner.detect_ai_with_litellm")
    def test_run_compares_with_regex(self, mock_detect):
        """Test that runner compares LLM results with regex baseline."""
        mock_detect.return_value = AIDetectionResult(
            is_ai_assisted=True,
            tools=["cursor"],
            confidence=0.95,
        )

        runner = ExperimentRunner(
            config={
                "experiment": {"name": "test"},
                "model": {"provider": "groq", "name": "llama-3.3-70b-versatile"},
                "prompt": {"system": "You are a detector"},
            }
        )

        results = runner.run(pr_ids=[self.pr_positive.id])
        pr_result = results.results[self.pr_positive.id]

        # Should have both LLM and regex results
        self.assertIsNotNone(pr_result.llm_result)
        self.assertIsNotNone(pr_result.regex_result)

    @patch("apps.metrics.experiments.runner.detect_ai_with_litellm")
    def test_run_on_team(self, mock_detect):
        """Test running detection on all PRs for a team."""
        mock_detect.return_value = AIDetectionResult(
            is_ai_assisted=False,
            tools=[],
            confidence=0.9,
        )

        runner = ExperimentRunner(
            config={
                "experiment": {"name": "test"},
                "model": {"provider": "groq", "name": "llama-3.3-70b-versatile"},
                "prompt": {"system": "You are a detector"},
            }
        )

        results = runner.run(team=self.team, limit=10)

        # Should have run on at least the PRs we created
        self.assertGreaterEqual(len(results.results), 2)

    @patch("apps.metrics.experiments.runner.detect_ai_with_litellm")
    def test_results_include_metadata(self, mock_detect):
        """Test that results include experiment metadata."""
        mock_detect.return_value = AIDetectionResult(
            is_ai_assisted=True,
            tools=["cursor"],
            confidence=0.95,
        )

        runner = ExperimentRunner(
            config={
                "experiment": {"name": "my-experiment", "description": "Test run"},
                "model": {"provider": "groq", "name": "llama-3.3-70b-versatile"},
                "prompt": {"system": "You are a detector"},
            }
        )

        results = runner.run(pr_ids=[self.pr_positive.id])

        self.assertEqual(results.experiment_name, "my-experiment")
        self.assertIsNotNone(results.started_at)
        self.assertIsNotNone(results.completed_at)


class TestExperimentResult(TestCase):
    """Tests for experiment result aggregation."""

    def test_calculate_metrics(self):
        """Test calculating aggregate metrics from results."""
        result = ExperimentResult(
            experiment_name="test",
            config={},
            started_at="2025-01-01T00:00:00",
            completed_at="2025-01-01T00:01:00",
            results={
                1: MagicMock(
                    llm_result=AIDetectionResult(is_ai_assisted=True, tools=["cursor"], confidence=0.9),
                    regex_result={"is_ai_assisted": True, "ai_tools": ["cursor"]},
                ),
                2: MagicMock(
                    llm_result=AIDetectionResult(is_ai_assisted=True, tools=["claude"], confidence=0.8),
                    regex_result={"is_ai_assisted": False, "ai_tools": []},
                ),
                3: MagicMock(
                    llm_result=AIDetectionResult(is_ai_assisted=False, tools=[], confidence=0.95),
                    regex_result={"is_ai_assisted": False, "ai_tools": []},
                ),
            },
        )

        metrics = result.calculate_metrics()

        self.assertEqual(metrics["total_prs"], 3)
        self.assertEqual(metrics["llm_detected"], 2)
        self.assertEqual(metrics["regex_detected"], 1)
        self.assertAlmostEqual(metrics["llm_detection_rate"], 2 / 3)
        self.assertAlmostEqual(metrics["regex_detection_rate"], 1 / 3)
        self.assertEqual(metrics["agreements"], 2)  # PR 1 and PR 3 agree
        self.assertEqual(metrics["disagreements"], 1)  # PR 2 disagrees

    def test_get_disagreements(self):
        """Test getting list of disagreements between LLM and regex."""
        result = ExperimentResult(
            experiment_name="test",
            config={},
            started_at="2025-01-01T00:00:00",
            completed_at="2025-01-01T00:01:00",
            results={
                1: MagicMock(
                    pr_id=1,
                    llm_result=AIDetectionResult(is_ai_assisted=True, tools=["claude"], confidence=0.8),
                    regex_result={"is_ai_assisted": False, "ai_tools": []},
                ),
            },
        )

        disagreements = result.get_disagreements()

        self.assertEqual(len(disagreements), 1)
        self.assertEqual(disagreements[0]["pr_id"], 1)
        self.assertTrue(disagreements[0]["llm_detected"])
        self.assertFalse(disagreements[0]["regex_detected"])

    def test_to_json(self):
        """Test exporting results to JSON."""
        result = ExperimentResult(
            experiment_name="test",
            config={"model": "test"},
            started_at="2025-01-01T00:00:00",
            completed_at="2025-01-01T00:01:00",
            results={},
        )

        json_str = result.to_json()
        data = json.loads(json_str)

        self.assertEqual(data["experiment_name"], "test")
        self.assertEqual(data["started_at"], "2025-01-01T00:00:00")
