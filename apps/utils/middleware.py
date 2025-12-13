"""Custom middleware for security and utility functions."""

from django.conf import settings


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

        csp_directives = [
            "default-src 'self'",
            f"script-src 'self' 'unsafe-inline' 'unsafe-eval' https://cdn.jsdelivr.net https://unpkg.com {vite_src}".strip(),
            f"style-src 'self' 'unsafe-inline' https://fonts.googleapis.com https://cdn.jsdelivr.net https://cdnjs.cloudflare.com {vite_src}".strip(),
            "font-src 'self' https://fonts.gstatic.com https://cdnjs.cloudflare.com",
            "img-src 'self' data: https: blob:",
            f"connect-src 'self' https://api.github.com https://api.atlassian.com https://slack.com wss: {vite_src} {ws_src}".strip(),
            "frame-ancestors 'none'",
            "form-action 'self'",
            "base-uri 'self'",
        ]
        response["Content-Security-Policy"] = "; ".join(csp_directives)

        return response
