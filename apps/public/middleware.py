"""Middleware for public analytics pages."""

import logging

logger = logging.getLogger(__name__)

# Known AI crawler User-Agent substrings
AI_BOT_SIGNATURES = [
    "ClaudeBot",
    "Claude-SearchBot",
    "GPTBot",
    "ChatGPT-User",
    "OAI-SearchBot",
    "PerplexityBot",
    "Google-Extended",
    "Amazonbot",
    "DuckAssistBot",
]


class AIBotLoggingMiddleware:
    """Log AI crawler visits to public pages.

    Only logs requests to /open-source/ paths to keep noise down.
    Uses INFO level so it shows up in production logs.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        if request.path.startswith("/open-source/") and response.status_code == 200:
            user_agent = request.META.get("HTTP_USER_AGENT", "")
            for bot in AI_BOT_SIGNATURES:
                if bot in user_agent:
                    logger.info(
                        "AI bot visit: %s on %s (status=%d)",
                        bot,
                        request.path,
                        response.status_code,
                    )
                    break

        return response
