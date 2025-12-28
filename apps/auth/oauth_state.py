"""Unified OAuth state management for GitHub OAuth flows.

This module provides state creation and verification for both:
- Onboarding flow (new users without a team)
- Integration flow (existing teams adding GitHub)

The state parameter protects against CSRF and encodes flow context.
"""

import base64
import json
import time
from typing import Any

from django.core.signing import BadSignature, Signer

# OAuth state validity period in seconds (10 minutes)
OAUTH_STATE_MAX_AGE_SECONDS = 600

# Flow types
FLOW_TYPE_ONBOARDING = "onboarding"
FLOW_TYPE_INTEGRATION = "integration"


class OAuthStateError(Exception):
    """Exception raised for OAuth state errors."""

    pass


def create_oauth_state(flow_type: str, team_id: int | None = None) -> str:
    """Create a signed OAuth state parameter.

    Args:
        flow_type: Either "onboarding" or "integration"
        team_id: Required for integration flow, must be None for onboarding

    Returns:
        Signed state string for CSRF protection

    Raises:
        ValueError: If flow_type is invalid or team_id requirements not met
    """
    if flow_type not in (FLOW_TYPE_ONBOARDING, FLOW_TYPE_INTEGRATION):
        raise ValueError(f"Invalid flow_type: {flow_type}")

    if flow_type == FLOW_TYPE_INTEGRATION and team_id is None:
        raise ValueError("team_id is required for integration flow")

    if flow_type == FLOW_TYPE_ONBOARDING and team_id is not None:
        raise ValueError("team_id must be None for onboarding flow")

    # Build payload
    payload: dict[str, Any] = {
        "type": flow_type,
        "iat": int(time.time()),
    }

    if team_id is not None:
        payload["team_id"] = team_id

    # Encode and sign
    encoded = base64.b64encode(json.dumps(payload).encode()).decode()
    signer = Signer()
    return signer.sign(encoded)


def verify_oauth_state(state: str) -> dict[str, Any]:
    """Verify and decode OAuth state parameter.

    Validates:
    - Signature is valid (not tampered)
    - Timestamp is present and not expired (max 10 minutes)
    - Flow type is valid

    Args:
        state: The signed state string to verify

    Returns:
        Dictionary containing:
        - type: "onboarding" or "integration"
        - iat: issued-at timestamp
        - team_id: (only for integration flow)

    Raises:
        OAuthStateError: If state is invalid, tampered with, or expired
    """
    if not state:
        raise OAuthStateError("Missing OAuth state parameter")

    try:
        # Unsign the state
        signer = Signer()
        unsigned = signer.unsign(state)

        # Base64 decode
        decoded = base64.b64decode(unsigned).decode()

        # Parse JSON
        payload = json.loads(decoded)

        # Validate type
        flow_type = payload.get("type")
        if flow_type not in (FLOW_TYPE_ONBOARDING, FLOW_TYPE_INTEGRATION):
            raise OAuthStateError(f"Invalid flow type: {flow_type}")

        # Validate timestamp
        iat = payload.get("iat")
        if iat is None:
            raise OAuthStateError("Missing timestamp in OAuth state")

        age = int(time.time()) - iat
        if age > OAUTH_STATE_MAX_AGE_SECONDS:
            raise OAuthStateError(f"OAuth state expired (age: {age}s, max: {OAUTH_STATE_MAX_AGE_SECONDS}s)")
        if age < -60:  # Allow 60 seconds clock skew
            raise OAuthStateError("OAuth state has future timestamp")

        # Validate team_id for integration flow
        if flow_type == FLOW_TYPE_INTEGRATION:
            team_id = payload.get("team_id")
            if team_id is None:
                raise OAuthStateError("Missing team_id for integration flow")

        return payload

    except BadSignature as e:
        raise OAuthStateError("Invalid OAuth state signature") from e
    except (ValueError, json.JSONDecodeError) as e:
        raise OAuthStateError(f"Malformed OAuth state: {e}") from e
