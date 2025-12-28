"""Tests for unified OAuth state management."""

import time
from unittest.mock import patch

from django.test import TestCase

from apps.auth.oauth_state import (
    FLOW_TYPE_INTEGRATION,
    FLOW_TYPE_ONBOARDING,
    OAUTH_STATE_MAX_AGE_SECONDS,
    OAuthStateError,
    create_oauth_state,
    verify_oauth_state,
)


class TestCreateOAuthState(TestCase):
    """Tests for create_oauth_state function."""

    def test_create_onboarding_state(self):
        """Test creating state for onboarding flow."""
        state = create_oauth_state(FLOW_TYPE_ONBOARDING)

        self.assertIsInstance(state, str)
        self.assertTrue(len(state) > 0)

        # Verify it can be decoded
        payload = verify_oauth_state(state)
        self.assertEqual(payload["type"], FLOW_TYPE_ONBOARDING)
        self.assertIn("iat", payload)
        self.assertNotIn("team_id", payload)

    def test_create_integration_state(self):
        """Test creating state for integration flow."""
        team_id = 123
        state = create_oauth_state(FLOW_TYPE_INTEGRATION, team_id=team_id)

        self.assertIsInstance(state, str)

        # Verify it can be decoded
        payload = verify_oauth_state(state)
        self.assertEqual(payload["type"], FLOW_TYPE_INTEGRATION)
        self.assertEqual(payload["team_id"], team_id)
        self.assertIn("iat", payload)

    def test_create_integration_state_requires_team_id(self):
        """Test that integration flow requires team_id."""
        with self.assertRaises(ValueError) as ctx:
            create_oauth_state(FLOW_TYPE_INTEGRATION)

        self.assertIn("team_id is required", str(ctx.exception))

    def test_create_onboarding_state_rejects_team_id(self):
        """Test that onboarding flow rejects team_id."""
        with self.assertRaises(ValueError) as ctx:
            create_oauth_state(FLOW_TYPE_ONBOARDING, team_id=123)

        self.assertIn("must be None", str(ctx.exception))

    def test_create_state_invalid_flow_type(self):
        """Test that invalid flow type is rejected."""
        with self.assertRaises(ValueError) as ctx:
            create_oauth_state("invalid_type")

        self.assertIn("Invalid flow_type", str(ctx.exception))


class TestVerifyOAuthState(TestCase):
    """Tests for verify_oauth_state function."""

    def test_verify_valid_onboarding_state(self):
        """Test verifying a valid onboarding state."""
        state = create_oauth_state(FLOW_TYPE_ONBOARDING)
        payload = verify_oauth_state(state)

        self.assertEqual(payload["type"], FLOW_TYPE_ONBOARDING)
        self.assertIn("iat", payload)

    def test_verify_valid_integration_state(self):
        """Test verifying a valid integration state."""
        team_id = 456
        state = create_oauth_state(FLOW_TYPE_INTEGRATION, team_id=team_id)
        payload = verify_oauth_state(state)

        self.assertEqual(payload["type"], FLOW_TYPE_INTEGRATION)
        self.assertEqual(payload["team_id"], team_id)

    def test_verify_empty_state(self):
        """Test that empty state is rejected."""
        with self.assertRaises(OAuthStateError) as ctx:
            verify_oauth_state("")

        self.assertIn("Missing", str(ctx.exception))

    def test_verify_none_state(self):
        """Test that None state is rejected."""
        with self.assertRaises(OAuthStateError) as ctx:
            verify_oauth_state(None)

        self.assertIn("Missing", str(ctx.exception))

    def test_verify_tampered_state(self):
        """Test that tampered state is rejected."""
        state = create_oauth_state(FLOW_TYPE_ONBOARDING)
        # Tamper with the signature
        tampered = state[:-5] + "XXXXX"

        with self.assertRaises(OAuthStateError) as ctx:
            verify_oauth_state(tampered)

        self.assertIn("signature", str(ctx.exception).lower())

    def test_verify_expired_state(self):
        """Test that expired state is rejected."""
        # Create state with mocked time in the past
        expired_time = int(time.time()) - OAUTH_STATE_MAX_AGE_SECONDS - 100

        with patch("apps.auth.oauth_state.time") as mock_time:
            mock_time.time.return_value = expired_time
            state = create_oauth_state(FLOW_TYPE_ONBOARDING)

        # Now verify with current time
        with self.assertRaises(OAuthStateError) as ctx:
            verify_oauth_state(state)

        self.assertIn("expired", str(ctx.exception).lower())

    def test_verify_future_state(self):
        """Test that state with future timestamp is rejected."""
        # Create state with mocked time in the future
        future_time = int(time.time()) + 3600  # 1 hour in future

        with patch("apps.auth.oauth_state.time") as mock_time:
            mock_time.time.return_value = future_time
            state = create_oauth_state(FLOW_TYPE_ONBOARDING)

        # Now verify with current time
        with self.assertRaises(OAuthStateError) as ctx:
            verify_oauth_state(state)

        self.assertIn("future", str(ctx.exception).lower())

    def test_verify_malformed_base64(self):
        """Test that malformed base64 is rejected."""
        from django.core.signing import Signer

        signer = Signer()
        # Sign invalid base64
        state = signer.sign("not-valid-base64!!!")

        with self.assertRaises(OAuthStateError) as ctx:
            verify_oauth_state(state)

        self.assertIn("Malformed", str(ctx.exception))

    def test_verify_malformed_json(self):
        """Test that malformed JSON is rejected."""
        import base64

        from django.core.signing import Signer

        signer = Signer()
        # Sign valid base64 but invalid JSON
        encoded = base64.b64encode(b"not-json").decode()
        state = signer.sign(encoded)

        with self.assertRaises(OAuthStateError) as ctx:
            verify_oauth_state(state)

        self.assertIn("Malformed", str(ctx.exception))

    def test_verify_integration_state_without_team_id(self):
        """Test that integration state without team_id is rejected."""
        import base64
        import json

        from django.core.signing import Signer

        # Manually create state without team_id
        payload = {"type": FLOW_TYPE_INTEGRATION, "iat": int(time.time())}
        encoded = base64.b64encode(json.dumps(payload).encode()).decode()
        signer = Signer()
        state = signer.sign(encoded)

        with self.assertRaises(OAuthStateError) as ctx:
            verify_oauth_state(state)

        self.assertIn("team_id", str(ctx.exception))
