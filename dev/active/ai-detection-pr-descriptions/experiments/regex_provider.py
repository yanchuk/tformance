"""
Promptfoo custom provider for regex pattern detection.

This allows side-by-side comparison of regex vs LLM detection in promptfoo UI.

Usage in promptfoo.yaml:
  providers:
    - id: "python:regex_provider.py"
      label: "Regex Patterns v1.7.0"
"""

import json
import os
import sys
from pathlib import Path

# Add project root to path
PROJECT_ROOT = Path(__file__).resolve().parents[4]
sys.path.insert(0, str(PROJECT_ROOT))

# Setup Django
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "tformance.settings")
import django  # noqa: E402

django.setup()

from apps.metrics.services.ai_detector import detect_ai_in_text, get_patterns_version  # noqa: E402


def call_api(prompt: str, options: dict, context: dict) -> dict:
    """
    Promptfoo provider entry point.

    Args:
        prompt: The rendered prompt (system + user messages)
        options: Provider options from config
        context: Test context including vars

    Returns:
        dict with 'output' key containing JSON response
    """
    try:
        # Get user_prompt from context vars
        user_prompt = context.get("vars", {}).get("user_prompt", "")

        # Extract PR description from the prompt
        # The description is after "Description:" in the user prompt
        pr_body = ""
        if "Description:" in user_prompt:
            parts = user_prompt.split("Description:")
            if len(parts) > 1:
                # Get everything after "Description:" until next section or end
                desc_part = parts[1]
                # Find where description ends (next header or end)
                for marker in ["\n---", "\n##", "\n# "]:
                    if marker in desc_part:
                        desc_part = desc_part.split(marker)[0]
                        break
                pr_body = desc_part.strip()
        else:
            pr_body = user_prompt

        # Run regex detection
        result = detect_ai_in_text(pr_body)

        # Format as LLM-compatible response for comparison
        output = {
            "ai": {
                "is_assisted": result["is_ai_assisted"],
                "tools": result["ai_tools"],
                "confidence": 1.0 if result["is_ai_assisted"] else 0.0,
                "usage_type": "pattern_match" if result["is_ai_assisted"] else None,
            },
            "tech": {
                "languages": [],
                "categories": [],
                "frameworks": [],
            },
            "summary": {
                "title": "N/A (regex only)",
                "description": f"Regex pattern detection v{get_patterns_version()}",
                "type": "unknown",
            },
            "health": {
                "scope": "unknown",
                "risk_level": "unknown",
                "review_friction": "unknown",
                "insights": [f"Detected via regex patterns v{get_patterns_version()}"],
            },
            "_regex_details": {
                "version": get_patterns_version(),
                "tools_detected": result["ai_tools"],
                "body_length": len(pr_body),
            },
        }

        return {"output": json.dumps(output)}

    except Exception as e:
        return {"error": f"Regex detection failed: {str(e)}"}


# For direct testing
if __name__ == "__main__":
    test_prompt = """
    Description:
    This PR was generated with Claude Code.

    🤖 Generated with [Claude Code](https://claude.com/claude-code)
    """
    result = call_api(test_prompt, {}, {"vars": {"user_prompt": test_prompt}})
    print(json.dumps(json.loads(result["output"]), indent=2))
