"""Custom middleware for security and utility functions."""

import logging

from django.conf import settings

logger = logging.getLogger(__name__)


class SecurityHeadersMiddleware:
    """Middleware to add security headers to all responses.

    Adds the following headers:
    - X-Content-Type-Options: nosniff - Prevents MIME type sniffing
    - X-Frame-Options: DENY - Prevents clickjacking (Django also has this)
    - Referrer-Policy: strict-origin-when-cross-origin - Controls referrer information
    - Permissions-Policy: Restricts browser features
    - Content-Security-Policy: XSS protection (basic policy)
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # X-Content-Type-Options: Prevents browsers from MIME-sniffing
        response["X-Content-Type-Options"] = "nosniff"

        # Referrer-Policy: Controls how much referrer info is sent
        response["Referrer-Policy"] = "strict-origin-when-cross-origin"

        # Permissions-Policy: Disable unnecessary browser features
        response["Permissions-Policy"] = (
            "accelerometer=(), "
            "camera=(), "
            "geolocation=(), "
            "gyroscope=(), "
            "magnetometer=(), "
            "microphone=(), "
            "payment=(), "
            "usb=()"
        )

        # Content-Security-Policy: Basic XSS protection
        # This is a permissive policy suitable for HTMX/Alpine.js
        # Tighten these directives based on your actual requirements
        # Note: 'unsafe-inline' is needed for HTMX and Alpine.js to work
        # In production, consider using nonces for stricter CSP

        # In DEBUG mode, allow Vite dev server (localhost:5173)
        vite_src = "http://localhost:5173" if settings.DEBUG else ""
        ws_src = "ws://localhost:5173" if settings.DEBUG else ""

        script_src = (
            f"script-src 'self' 'unsafe-inline' 'unsafe-eval' "
            f"https://cdn.jsdelivr.net https://unpkg.com https://cdn.tailwindcss.com "
            f"https://*.posthog.com https://*.i.posthog.com "
            f"https://www.googletagmanager.com https://www.google-analytics.com {vite_src}"
        )
        style_src = (
            f"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com "
            f"https://cdn.jsdelivr.net https://cdnjs.cloudflare.com https://*.posthog.com {vite_src}"
        )
        connect_src = (
            f"connect-src 'self' https://api.github.com https://api.atlassian.com "
            f"https://slack.com https://*.posthog.com https://*.i.posthog.com "
            f"https://*.google-analytics.com https://*.analytics.google.com "
            f"https://*.googletagmanager.com wss: {vite_src} {ws_src}"
        )

        csp_directives = [
            "default-src 'self'",
            script_src.strip(),
            style_src.strip(),
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com",
            "img-src 'self' data: https: blob:",
            connect_src.strip(),
            "frame-ancestors 'none'",
            "form-action 'self' https://github.com https://accounts.google.com",
            "base-uri 'self'",
        ]
        response["Content-Security-Policy"] = "; ".join(csp_directives)

        return response


class ErrorTrackingMiddleware:
    """Middleware to track server errors in PostHog.

    Tracks 500 errors (server errors) in PostHog for monitoring and analytics.
    This complements Sentry's exception tracking by providing error data
    within PostHog for correlation with other user behavior.

    Only tracks 500 errors, not 4xx client errors which are expected behavior.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        response = self.get_response(request)

        # Only track 500 errors (server errors)
        if response.status_code >= 500:
            self._track_error(request, response)

        return response

    def _track_error(self, request, response):
        """Track the error in PostHog."""
        from apps.utils.analytics import track_error

        # Get user if authenticated
        user = request.user if hasattr(request, "user") and request.user.is_authenticated else None

        # Get view name from resolver match
        view_name = None
        if hasattr(request, "resolver_match") and request.resolver_match:
            view_name = request.resolver_match.view_name

        # Build properties (avoid PII)
        properties = {
            "path": request.path,
            "method": request.method,
            "status_code": response.status_code,
        }
        if view_name:
            properties["view_name"] = view_name

        # Track the error
        try:
            track_error(user, "server_error", properties)
        except Exception:
            # Don't let error tracking cause more errors
            logger.exception("Failed to track error in PostHog")
