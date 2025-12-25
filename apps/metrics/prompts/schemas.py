"""JSON Schema definitions for LLM response validation.

This module defines the expected structure of LLM responses,
enabling programmatic validation and better error messages.

Usage:
    from apps.metrics.prompts.schemas import validate_llm_response

    response = {"ai": {"is_assisted": True, ...}, ...}
    is_valid, errors = validate_llm_response(response)
    if not is_valid:
        print(f"Validation errors: {errors}")
"""

from __future__ import annotations

from typing import Any

from jsonschema import Draft202012Validator

# Schema version - increment when schema changes
SCHEMA_VERSION = "6.0.0"

# JSON Schema for the AI detection portion of the response
AI_SCHEMA = {
    "type": "object",
    "required": ["is_assisted", "tools", "confidence"],
    "properties": {
        "is_assisted": {
            "type": "boolean",
            "description": "Whether AI was used to write this code",
        },
        "tools": {
            "type": "array",
            "items": {"type": "string"},
            "description": "List of AI tools detected (lowercase)",
        },
        "usage_type": {
            "type": ["string", "null"],
            "enum": ["authored", "assisted", "reviewed", "brainstorm", None],
            "description": "How AI was used",
        },
        "confidence": {
            "type": "number",
            "minimum": 0.0,
            "maximum": 1.0,
            "description": "Confidence in AI detection (0.0-1.0)",
        },
    },
    "additionalProperties": False,
}

# JSON Schema for the technology detection portion
TECH_SCHEMA = {
    "type": "object",
    "required": ["languages", "frameworks", "categories"],
    "properties": {
        "languages": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Programming languages detected (lowercase)",
        },
        "frameworks": {
            "type": "array",
            "items": {"type": "string"},
            "description": "Frameworks/libraries detected (lowercase)",
        },
        "categories": {
            "type": "array",
            "items": {
                "type": "string",
                "enum": ["backend", "frontend", "devops", "mobile", "data"],
            },
            "description": "Technology categories",
        },
    },
    "additionalProperties": False,
}

# JSON Schema for the summary portion
SUMMARY_SCHEMA = {
    "type": "object",
    "required": ["title", "description", "type"],
    "properties": {
        "title": {
            "type": "string",
            "minLength": 1,
            "maxLength": 100,
            "description": "Brief 5-10 word title",
        },
        "description": {
            "type": "string",
            "minLength": 1,
            "maxLength": 500,
            "description": "1-2 sentence CTO-friendly summary",
        },
        "type": {
            "type": "string",
            "enum": ["feature", "bugfix", "refactor", "docs", "test", "chore", "ci"],
            "description": "PR type classification",
        },
    },
    "additionalProperties": False,
}

# JSON Schema for the health assessment portion
HEALTH_SCHEMA = {
    "type": "object",
    "required": ["review_friction", "scope", "risk_level", "insights"],
    "properties": {
        "review_friction": {
            "type": "string",
            "enum": ["low", "medium", "high"],
            "description": "Level of review friction",
        },
        "scope": {
            "type": "string",
            "enum": ["small", "medium", "large", "xlarge"],
            "description": "PR scope/size category",
        },
        "risk_level": {
            "type": "string",
            "enum": ["low", "medium", "high"],
            "description": "Risk level of the changes",
        },
        "insights": {
            "type": "array",
            "items": {"type": "string"},
            "description": "1-2 sentence observations about PR process",
        },
    },
    "additionalProperties": False,
}

# Complete response schema (v6.0.0+)
PR_ANALYSIS_RESPONSE_SCHEMA = {
    "$schema": "https://json-schema.org/draft/2020-12/schema",
    "title": "PR Analysis Response",
    "description": "LLM response schema for PR analysis (v6.0.0+)",
    "type": "object",
    "required": ["ai", "tech", "summary", "health"],
    "properties": {
        "ai": AI_SCHEMA,
        "tech": TECH_SCHEMA,
        "summary": SUMMARY_SCHEMA,
        "health": HEALTH_SCHEMA,
    },
    "additionalProperties": False,
}

# Validator instance (reusable for performance)
_validator = Draft202012Validator(PR_ANALYSIS_RESPONSE_SCHEMA)


def validate_llm_response(response: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate an LLM response against the schema.

    Args:
        response: The parsed JSON response from the LLM

    Returns:
        Tuple of (is_valid, errors) where:
        - is_valid: True if response matches schema
        - errors: List of error messages (empty if valid)

    Example:
        >>> response = {"ai": {"is_assisted": True, "tools": ["cursor"], "confidence": 0.9}, ...}
        >>> is_valid, errors = validate_llm_response(response)
        >>> if not is_valid:
        ...     print(f"Errors: {errors}")
    """
    errors = []

    for error in _validator.iter_errors(response):
        # Build a readable error message
        path = " -> ".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
        errors.append(f"{path}: {error.message}")

    return len(errors) == 0, errors


def validate_ai_response(ai_data: dict[str, Any]) -> tuple[bool, list[str]]:
    """Validate just the 'ai' portion of the response.

    Useful for testing AI detection in isolation.

    Args:
        ai_data: The 'ai' object from the response

    Returns:
        Tuple of (is_valid, errors)
    """
    validator = Draft202012Validator(AI_SCHEMA)
    errors = []

    for error in validator.iter_errors(ai_data):
        path = " -> ".join(str(p) for p in error.absolute_path) if error.absolute_path else "root"
        errors.append(f"{path}: {error.message}")

    return len(errors) == 0, errors


def get_schema_as_json() -> dict[str, Any]:
    """Get the full schema as a dictionary.

    Useful for exporting to promptfoo or other tools.

    Returns:
        The PR_ANALYSIS_RESPONSE_SCHEMA dictionary
    """
    return PR_ANALYSIS_RESPONSE_SCHEMA


# Example valid response for testing
EXAMPLE_VALID_RESPONSE = {
    "ai": {
        "is_assisted": True,
        "tools": ["cursor", "claude"],
        "usage_type": "authored",
        "confidence": 0.95,
    },
    "tech": {
        "languages": ["python", "typescript"],
        "frameworks": ["django", "react"],
        "categories": ["backend", "frontend"],
    },
    "summary": {
        "title": "Add dark mode toggle to settings",
        "description": "Implements user preference for dark/light theme with persistence.",
        "type": "feature",
    },
    "health": {
        "review_friction": "low",
        "scope": "medium",
        "risk_level": "low",
        "insights": ["Fast review turnaround indicates clear PR scope"],
    },
}

# Example minimal valid response (all required fields, minimal data)
EXAMPLE_MINIMAL_RESPONSE = {
    "ai": {
        "is_assisted": False,
        "tools": [],
        "usage_type": None,
        "confidence": 0.0,
    },
    "tech": {
        "languages": [],
        "frameworks": [],
        "categories": [],
    },
    "summary": {
        "title": "Fix typo",
        "description": "Corrects typo in readme.",
        "type": "docs",
    },
    "health": {
        "review_friction": "low",
        "scope": "small",
        "risk_level": "low",
        "insights": [],
    },
}
