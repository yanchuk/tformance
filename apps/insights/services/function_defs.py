"""
Gemini function declarations for metrics queries.

Defines the function calling interface that Gemini can use to query team metrics.
These declarations are passed to Gemini so it can decide which functions to call
based on user questions.
"""

# Function declarations for Gemini
# Each declaration describes a function that can be called with its parameters
FUNCTION_DECLARATIONS = [
    {
        "name": "get_team_metrics",
        "description": (
            "Get key metrics overview for the team including PR count, merge rate, "
            "cycle time, review time, and AI adoption percentage."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (default 30, max 90)",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_ai_adoption_trend",
        "description": ("Get AI adoption trend over time showing percentage of AI-assisted PRs by week or month."),
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (default 30, max 90)",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_developer_stats",
        "description": (
            "Get per-developer breakdown including PR count, average cycle time, "
            "AI adoption rate, and lines changed for each team member."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (default 30, max 90)",
                },
                "developer_name": {
                    "type": "string",
                    "description": "Filter to a specific developer by name (optional)",
                },
            },
            "required": [],
        },
    },
    {
        "name": "get_ai_quality_comparison",
        "description": (
            "Compare quality metrics between AI-assisted and non-AI PRs including "
            "revert rates, hotfix rates, and cycle times."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (default 30, max 90)",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_reviewer_workload",
        "description": (
            "Get reviewer workload statistics showing reviews per person, average review time, and approval rates."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (default 30, max 90)",
                }
            },
            "required": [],
        },
    },
    {
        "name": "get_recent_prs",
        "description": (
            "Get a list of recent pull requests with their status, author, "
            "cycle time, and whether they were AI-assisted."
        ),
        "parameters": {
            "type": "object",
            "properties": {
                "days": {
                    "type": "integer",
                    "description": "Number of days to look back (default 7, max 30)",
                },
                "limit": {
                    "type": "integer",
                    "description": "Maximum number of PRs to return (default 10, max 20)",
                },
            },
            "required": [],
        },
    },
]


def get_function_declarations() -> list[dict]:
    """Return the function declarations for Gemini.

    Returns:
        List of function declaration dictionaries.
    """
    return FUNCTION_DECLARATIONS
