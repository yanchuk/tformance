"""
Question answering service using Gemini with function calling.

Handles natural language questions about team metrics by using Gemini's
function calling capabilities to query the dashboard service.
"""

import logging

from django.conf import settings

from apps.insights.services.function_defs import get_function_declarations
from apps.insights.services.function_executor import execute_function

logger = logging.getLogger(__name__)

# Maximum function calls per query to prevent runaway loops
MAX_FUNCTION_CALLS = 3

QA_SYSTEM_INSTRUCTION = """You are an analytics assistant for engineering managers.
You help answer questions about team metrics using the available functions.

When answering questions:
1. Call the appropriate function(s) to get the data you need
2. Interpret the results in a helpful, concise way
3. Highlight key insights and any concerning patterns
4. Be direct and avoid generic filler language

If you don't have enough information to answer, say so clearly.
Keep responses to 2-4 sentences unless more detail is specifically requested."""


def answer_question(
    team,
    question: str,
    user_id: str | None = None,
) -> str:
    """Answer a natural language question about team metrics.

    Uses Gemini with function calling to query the dashboard service
    and generate a natural language response.

    Args:
        team: The team to query data for.
        question: The natural language question from the user.
        user_id: Optional user ID for PostHog tracking.

    Returns:
        A natural language answer string.
    """
    api_key = getattr(settings, "GOOGLE_AI_API_KEY", "")
    if not api_key:
        logger.warning("GOOGLE_AI_API_KEY not configured")
        return (
            "I'm unable to answer questions right now because the AI service "
            "is not configured. Please contact your administrator."
        )

    try:
        from google import genai
        from google.genai import types

        client = genai.Client(api_key=api_key)

        # Build tools from function declarations
        tools = [
            types.Tool(
                function_declarations=[
                    types.FunctionDeclaration(
                        name=decl["name"],
                        description=decl["description"],
                        parameters=decl["parameters"],
                    )
                    for decl in get_function_declarations()
                ]
            )
        ]

        # Start conversation
        contents = [types.Content(role="user", parts=[types.Part(text=question)])]

        function_call_count = 0
        while function_call_count < MAX_FUNCTION_CALLS:
            # Call Gemini
            response = client.models.generate_content(
                model="gemini-2.0-flash-exp",
                contents=contents,
                config=types.GenerateContentConfig(
                    system_instruction=QA_SYSTEM_INSTRUCTION,
                    tools=tools,
                ),
            )

            # Check if Gemini wants to call a function
            if not response.candidates:
                return "I wasn't able to generate a response. Please try rephrasing your question."

            candidate = response.candidates[0]
            if not candidate.content or not candidate.content.parts:
                return "I wasn't able to generate a response. Please try rephrasing your question."

            # Check for function calls
            function_calls = [part for part in candidate.content.parts if part.function_call]

            if not function_calls:
                # No function calls - return the text response
                text_parts = [part.text for part in candidate.content.parts if part.text]
                if text_parts:
                    return " ".join(text_parts)
                return "I wasn't able to answer that question with the available data."

            # Execute function calls and add results to conversation
            contents.append(candidate.content)

            function_responses = []
            for part in function_calls:
                fc = part.function_call
                function_call_count += 1

                try:
                    # Extract arguments from the function call
                    args = dict(fc.args) if fc.args else {}
                    result = execute_function(fc.name, args, team)
                    function_responses.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=fc.name,
                                response={"result": result},
                            )
                        )
                    )
                except Exception as e:
                    logger.error(f"Function execution error: {e}")
                    function_responses.append(
                        types.Part(
                            function_response=types.FunctionResponse(
                                name=fc.name,
                                response={"error": str(e)},
                            )
                        )
                    )

            contents.append(types.Content(role="user", parts=function_responses))

        # If we hit the limit, return what we have
        return "I've gathered some data but need to simplify my answer. Please try asking a more specific question."

    except ImportError:
        logger.error("google-genai package not installed")
        return "The AI service is not properly configured."
    except Exception as e:
        logger.error(f"QA error: {e}")
        return f"I encountered an error while processing your question: {e}"


def get_suggested_questions() -> list[str]:
    """Return a list of suggested questions users can ask.

    Returns:
        List of example question strings.
    """
    return [
        "How is the team doing this month?",
        "Who has the fastest cycle time?",
        "What's our AI adoption trend?",
        "Are AI-assisted PRs higher quality than regular PRs?",
        "Who reviews the most pull requests?",
        "Show me recent PRs from this week.",
    ]
