"""Compare different prompt versions for insight generation."""

import json
import os

from groq import Groq

from apps.metrics.prompts.experiments.prompt_a_baseline import PROMPT_A
from apps.metrics.prompts.experiments.prompt_b_bullets_with_actions import PROMPT_B
from apps.metrics.prompts.experiments.prompt_c_compact_actionable import PROMPT_C
from apps.metrics.prompts.experiments.prompt_d_refined import PROMPT_D
from apps.metrics.prompts.experiments.prompt_e_structured import PROMPT_E

# Common JSON schema for all prompts
INSIGHT_SCHEMA = {
    "type": "object",
    "properties": {
        "headline": {"type": "string"},
        "detail": {"type": "string"},
        "possible_causes": {
            "type": "array",
            "items": {"type": "string"},
        },
        "recommendation": {"type": "string"},
        "metric_cards": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "label": {"type": "string"},
                    "value": {"type": "string"},
                    "trend": {"type": "string"},
                },
                "required": ["label", "value", "trend"],
                "additionalProperties": False,
            },
        },
        "actions": {
            "type": "array",
            "items": {
                "type": "object",
                "properties": {
                    "action_type": {"type": "string"},
                    "label": {"type": "string"},
                },
                "required": ["action_type", "label"],
                "additionalProperties": False,
            },
        },
    },
    "required": ["headline", "detail", "recommendation", "metric_cards", "actions"],
    "additionalProperties": False,
}


def run_prompt(client, prompt: str, user_data: str, name: str) -> dict:
    """Run a single prompt and return the result."""
    try:
        response = client.chat.completions.create(
            model="llama-3.3-70b-versatile",  # More reliable for testing
            messages=[
                {"role": "system", "content": prompt},
                {"role": "user", "content": user_data},
            ],
            temperature=0.3,
            max_tokens=1500,
            response_format={"type": "json_object"},
        )
        content = response.choices[0].message.content
        return {"name": name, "result": json.loads(content), "error": None}
    except Exception as e:
        return {"name": name, "result": None, "error": str(e)}


def compare_prompts(team_slug: str = "activepieces-demo", days: int = 30):
    """Compare all prompt versions with the same team data."""
    from datetime import date, timedelta

    from apps.metrics.services.insight_llm import build_insight_prompt, gather_insight_data
    from apps.teams.models import Team

    # Get team and data
    team = Team.objects.get(slug=team_slug)
    end_date = date.today()
    start_date = end_date - timedelta(days=days)

    data = gather_insight_data(team, start_date, end_date)
    user_prompt = build_insight_prompt(data)

    # Initialize client
    client = Groq(api_key=os.environ.get("GROQ_API_KEY"))

    # Run all prompts
    prompts = [
        (PROMPT_A, "Version A: Baseline"),
        (PROMPT_B, "Version B: Bullets+Actions"),
        (PROMPT_C, "Version C: Compact"),
        (PROMPT_D, "Version D: Refined"),
        (PROMPT_E, "Version E: Structured"),
    ]

    results = []
    for prompt, name in prompts:
        print(f"\n{'=' * 60}")
        print(f"Running {name}...")
        result = run_prompt(client, prompt, user_prompt, name)
        results.append(result)

        if result["error"]:
            print(f"ERROR: {result['error']}")
        else:
            r = result["result"]
            print(f"\nHEADLINE: {r.get('headline', 'N/A')}")
            print(f"\nDETAIL:\n{r.get('detail', 'N/A')}")
            if r.get("possible_causes"):
                print("\nCAUSES:")
                for cause in r.get("possible_causes", []):
                    print(f"  • {cause}")
            print(f"\nRECOMMENDATION: {r.get('recommendation', 'N/A')}")
            print("\nACTIONS:")
            for action in r.get("actions", []):
                if isinstance(action, dict):
                    print(f"  [{action.get('action_type')}] {action.get('label')}")
                else:
                    print(f"  {action}")

    return results


if __name__ == "__main__":
    compare_prompts()
