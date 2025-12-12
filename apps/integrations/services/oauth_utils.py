"""Shared OAuth utilities for all integrations."""

import base64
import json
from typing import Any

from django.core.signing import BadSignature, Signer


def create_oauth_state(team_id: int) -> str:
    """Create a signed OAuth state parameter containing team_id.

    Args:
        team_id: The ID of the team to encode in the state

    Returns:
        Signed state string containing the team_id
    """
    # Create JSON payload
    payload = json.dumps({"team_id": team_id})

    # Base64 encode
    encoded = base64.b64encode(payload.encode()).decode()

    # Sign with Django's Signer
    signer = Signer()
    signed_state = signer.sign(encoded)

    return signed_state


def verify_oauth_state(state: str) -> dict[str, Any]:
    """Verify and decode OAuth state parameter.

    Args:
        state: The signed state string to verify

    Returns:
        Dictionary containing team_id

    Raises:
        ValueError: If state is invalid or tampered with
    """
    try:
        # Unsign the state
        signer = Signer()
        unsigned = signer.unsign(state)

        # Base64 decode
        decoded = base64.b64decode(unsigned).decode()

        # Parse JSON
        payload = json.loads(decoded)

        return payload
    except (BadSignature, ValueError, KeyError) as e:
        raise ValueError(f"Invalid OAuth state: {str(e)}") from e
