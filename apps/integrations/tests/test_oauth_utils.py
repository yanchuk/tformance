"""Tests for OAuth utility functions.

Tests for the create_oauth_state and verify_oauth_state functions
that handle secure state parameter encoding/decoding for OAuth flows.
"""

from django.test import TestCase

from apps.integrations.services.oauth_utils import create_oauth_state, verify_oauth_state


class TestCreateOAuthState(TestCase):
    """Tests for create_oauth_state function."""

    def test_create_oauth_state_returns_string(self):
        """Test that create_oauth_state returns a string."""
        result = create_oauth_state(team_id=123)

        self.assertIsInstance(result, str)

    def test_create_oauth_state_contains_signature(self):
        """Test that create_oauth_state returns a signed string (contains colon)."""
        result = create_oauth_state(team_id=123)

        # Django Signer adds a colon-separated signature
        self.assertIn(":", result)

    def test_create_oauth_state_different_teams_different_states(self):
        """Test that different team IDs produce different states."""
        state1 = create_oauth_state(team_id=1)
        state2 = create_oauth_state(team_id=2)

        self.assertNotEqual(state1, state2)

    def test_create_oauth_state_same_team_same_state(self):
        """Test that same team ID produces consistent output."""
        state1 = create_oauth_state(team_id=123)
        state2 = create_oauth_state(team_id=123)

        # The signed states should be equal since they encode the same data
        self.assertEqual(state1, state2)

    def test_create_oauth_state_handles_large_team_id(self):
        """Test that create_oauth_state handles large team IDs."""
        result = create_oauth_state(team_id=999999999)

        self.assertIsInstance(result, str)
        self.assertIn(":", result)


class TestVerifyOAuthState(TestCase):
    """Tests for verify_oauth_state function."""

    def test_verify_oauth_state_returns_dict(self):
        """Test that verify_oauth_state returns a dictionary."""
        state = create_oauth_state(team_id=123)

        result = verify_oauth_state(state)

        self.assertIsInstance(result, dict)

    def test_verify_oauth_state_returns_team_id(self):
        """Test that verify_oauth_state returns the correct team_id."""
        original_team_id = 456
        state = create_oauth_state(team_id=original_team_id)

        result = verify_oauth_state(state)

        self.assertEqual(result["team_id"], original_team_id)

    def test_verify_oauth_state_roundtrip(self):
        """Test that create and verify work together correctly."""
        team_id = 789
        state = create_oauth_state(team_id=team_id)
        result = verify_oauth_state(state)

        self.assertEqual(result["team_id"], team_id)

    def test_verify_oauth_state_invalid_state_raises_value_error(self):
        """Test that verify_oauth_state raises ValueError for invalid state."""
        with self.assertRaises(ValueError) as context:
            verify_oauth_state("invalid-state-string")

        self.assertIn("Invalid OAuth state", str(context.exception))

    def test_verify_oauth_state_tampered_signature_raises_value_error(self):
        """Test that verify_oauth_state detects tampered signatures."""
        state = create_oauth_state(team_id=123)
        # Tamper with the signature
        tampered_state = state + "tampered"

        with self.assertRaises(ValueError) as context:
            verify_oauth_state(tampered_state)

        self.assertIn("Invalid OAuth state", str(context.exception))

    def test_verify_oauth_state_empty_string_raises_value_error(self):
        """Test that verify_oauth_state raises ValueError for empty string."""
        with self.assertRaises(ValueError) as context:
            verify_oauth_state("")

        self.assertIn("Invalid OAuth state", str(context.exception))

    def test_verify_oauth_state_modified_payload_raises_value_error(self):
        """Test that verify_oauth_state detects modified payloads."""
        state = create_oauth_state(team_id=123)
        # Split at the signature separator and modify the payload
        parts = state.split(":")
        if len(parts) == 2:
            # Modify the base64 payload portion
            modified_payload = parts[0][:-1] + "X"  # Change last character
            modified_state = f"{modified_payload}:{parts[1]}"

            with self.assertRaises(ValueError) as context:
                verify_oauth_state(modified_state)

            self.assertIn("Invalid OAuth state", str(context.exception))


class TestOAuthStateIntegration(TestCase):
    """Integration tests for OAuth state handling."""

    def test_multiple_team_ids_roundtrip(self):
        """Test that multiple team IDs can be encoded and decoded correctly."""
        team_ids = [1, 100, 1000, 99999]

        for team_id in team_ids:
            state = create_oauth_state(team_id=team_id)
            result = verify_oauth_state(state)
            self.assertEqual(
                result["team_id"],
                team_id,
                f"Failed roundtrip for team_id={team_id}",
            )

    def test_state_is_url_safe(self):
        """Test that generated state is reasonably URL-safe."""
        state = create_oauth_state(team_id=123)

        # Should not contain characters that break URLs
        # Note: base64 can contain + and /, Django's signer uses : for separator
        # These are typically URL-encoded but the state itself should be usable
        self.assertNotIn(" ", state)
        self.assertNotIn("\n", state)
        self.assertNotIn("\t", state)

    def test_state_not_easily_guessable(self):
        """Test that state is not a simple encoding of team_id."""
        state = create_oauth_state(team_id=123)

        # The state should be longer than just "123"
        self.assertGreater(len(state), 10)

        # Should not be a simple string representation
        self.assertNotEqual(state, "123")
        self.assertNotEqual(state, "team_id=123")
