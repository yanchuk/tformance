"""Error sanitization utilities.

This module provides functions to convert internal exceptions into
user-safe error messages that don't leak sensitive implementation details.
"""

import json
import logging

import requests

logger = logging.getLogger(__name__)


def sanitize_error(exc: Exception) -> str:
    """Convert an exception to a user-safe error message.

    This function maps known exception types to generic, helpful error messages
    that don't expose internal implementation details like API endpoints, hostnames,
    tokens, or stack traces.

    The original exception should be logged separately for debugging purposes.

    Args:
        exc: The exception to sanitize.

    Returns:
        A user-friendly error message string.
    """
    # Log the full exception for debugging (internal use only)
    logger.debug("Sanitizing exception: %s: %s", type(exc).__name__, exc)

    # Handle requests library exceptions
    if isinstance(exc, requests.exceptions.Timeout):
        return "Request timed out. Please try again later."

    if isinstance(exc, requests.exceptions.ConnectionError):
        return "Connection failed. Please try again later."

    if isinstance(exc, requests.exceptions.SSLError):
        return "Connection failed. Please try again later."

    if isinstance(exc, requests.exceptions.HTTPError):
        return _sanitize_http_error(exc)

    if isinstance(exc, requests.exceptions.RequestException):
        return "Connection failed. Please try again later."

    # Handle JSON decode errors
    if isinstance(exc, json.JSONDecodeError):
        return "Invalid response received. Please try again later."

    # Default fallback for unknown exceptions
    return "An error occurred. Please try again or contact support."


def _sanitize_http_error(exc: requests.exceptions.HTTPError) -> str:
    """Sanitize HTTP errors based on status code.

    Args:
        exc: The HTTPError exception.

    Returns:
        A user-friendly error message based on the HTTP status code.
    """
    response = exc.response
    if response is None:
        return "Connection failed. Please try again later."

    status_code = response.status_code

    if status_code == 401:
        return "Authentication failed. Please reconnect your integration."

    if status_code == 403:
        return "Permission denied. Check your integration permissions."

    if status_code == 404:
        return "Resource not found. It may have been deleted."

    if status_code == 429:
        return "Rate limit exceeded. Please wait and try again."

    if 500 <= status_code < 600:
        return "External service error. Please try again later."

    # Generic HTTP error
    return "An error occurred. Please try again or contact support."
