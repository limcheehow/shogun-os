"""Tests for msft_api.py — Microsoft 365 Graph API client.

TDD: These tests are written FIRST. They should fail when run against
the empty module, then pass after msft_api.py is implemented.
"""

import json
import os
import sys
import time
import unittest
from unittest.mock import MagicMock, patch

# Ensure the scripts directory is importable
_SCRIPTS_DIR = os.path.join(
    os.path.dirname(os.path.dirname(os.path.abspath(__file__))),
    "scripts",
)
if _SCRIPTS_DIR not in sys.path:
    sys.path.insert(0, _SCRIPTS_DIR)

import msft_api


class TestGraphClient(unittest.TestCase):
    """Tests for the GraphClient class."""

    def setUp(self):
        """Set up env vars and a fresh client before each test."""
        self.env_patcher = patch.dict(
            os.environ,
            {
                "MSFT_TENANT_ID": "test-tenant-123",
                "MSFT_CLIENT_ID": "test-client-456",
                "MSFT_CLIENT_SECRET": "test-secret-789",
            },
        )
        self.env_patcher.start()
        self.client = msft_api.GraphClient()

    def tearDown(self):
        self.env_patcher.stop()

    # ------------------------------------------------------------------ #
    # Test 1: Token refresh — verify token obtained on first call
    # ------------------------------------------------------------------ #
    @patch("msft_api.requests.post")
    def test_graph_client_token_refresh(self, mock_post):
        """Verify a fresh token is obtained when none exists."""
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {
            "access_token": "new-token-abc",
            "expires_in": 3600,
        }
        mock_post.return_value = mock_response

        token = self.client._ensure_token()

        self.assertEqual(token, "new-token-abc")
        self.assertEqual(self.client._token, "new-token-abc")
        mock_post.assert_called_once()
        # Verify the token URL was used
        call_args = mock_post.call_args[0][0]
        self.assertIn("test-tenant-123", call_args)
        self.assertIn("oauth2/v2.0/token", call_args)

    # ------------------------------------------------------------------ #
    # Test 2: Token cached — verify token reused if not expired
    # ------------------------------------------------------------------ #
    @patch("msft_api.requests.post")
    def test_graph_client_token_cached(self, mock_post):
        """Verify the cached token is reused when not expired."""
        # Set a token with a future expiry
        self.client._token = "cached-token-xyz"
        self.client._token_expiry = time.time() + 600  # 10 min from now

        token = self.client._ensure_token()

        self.assertEqual(token, "cached-token-xyz")
        # requests.post should NOT have been called
        mock_post.assert_not_called()

    # ------------------------------------------------------------------ #
    # Test 3: Mail search — verify path includes user email + messages
    # ------------------------------------------------------------------ #
    @patch("msft_api.requests.get")
    @patch("msft_api.GraphClient._ensure_token")
    def test_mail_search(self, mock_ensure_token, mock_get):
        """Verify mail search calls the correct endpoint."""
        mock_ensure_token.return_value = "fake-token"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": [{"id": "msg1"}]}
        mock_get.return_value = mock_response

        result = self.client.get(
            self.client._user_path("user@example.com", "/messages?$top=10&$search=\"meeting\"")
        )

        self.assertEqual(result, {"value": [{"id": "msg1"}]})
        # Verify the URL includes the user email and messages endpoint
        called_url = mock_get.call_args[0][0]
        self.assertIn("user@example.com", called_url)
        self.assertIn("messages", called_url)

    # ------------------------------------------------------------------ #
    # Test 4: Mail send — verify payload shape
    # ------------------------------------------------------------------ #
    @patch("msft_api.requests.post")
    @patch("msft_api.GraphClient._ensure_token")
    def test_mail_send(self, mock_ensure_token, mock_post):
        """Verify mail send constructs the correct payload."""
        mock_ensure_token.return_value = "fake-token"
        mock_response = MagicMock()
        mock_response.status_code = 202
        mock_response.json.return_value = {}
        mock_post.return_value = mock_response

        payload = {
            "message": {
                "subject": "Test Subject",
                "body": {"contentType": "Text", "content": "Hello World"},
                "toRecipients": [{"emailAddress": {"address": "recipient@example.com"}}],
            }
        }
        result = self.client.post(
            self.client._user_path("sender@example.com", "/sendMail"),
            payload,
        )

        # Verify the payload shape was passed to requests.post
        called_args = mock_post.call_args
        called_kwargs = called_args[1] if len(called_args) > 1 else called_args[0][1] if len(called_args[0]) > 1 else {}
        # Get the json body
        sent_json = called_kwargs.get("json", {})
        self.assertIn("message", sent_json)
        self.assertEqual(sent_json["message"]["subject"], "Test Subject")
        self.assertIn("toRecipients", sent_json["message"])
        self.assertEqual(
            sent_json["message"]["toRecipients"][0]["emailAddress"]["address"],
            "recipient@example.com",
        )

    # ------------------------------------------------------------------ #
    # Test 5: Calendar list — verify it calls get with correct args
    # ------------------------------------------------------------------ #
    @patch("msft_api.requests.get")
    @patch("msft_api.GraphClient._ensure_token")
    def test_calendar_list(self, mock_ensure_token, mock_get):
        """Verify calendar list calls the correct endpoint."""
        mock_ensure_token.return_value = "fake-token"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": [{"id": "event1"}]}
        mock_get.return_value = mock_response

        result = self.client.get(
            self.client._user_path("user@example.com", "/calendar/events?$top=50")
        )

        self.assertEqual(result, {"value": [{"id": "event1"}]})
        called_url = mock_get.call_args[0][0]
        self.assertIn("calendar", called_url)
        self.assertIn("events", called_url)

    # ------------------------------------------------------------------ #
    # Test 6: Drive list — verify it calls get
    # ------------------------------------------------------------------ #
    @patch("msft_api.requests.get")
    @patch("msft_api.GraphClient._ensure_token")
    def test_drive_list(self, mock_ensure_token, mock_get):
        """Verify drive list calls the correct endpoint."""
        mock_ensure_token.return_value = "fake-token"
        mock_response = MagicMock()
        mock_response.status_code = 200
        mock_response.json.return_value = {"value": [{"id": "file1", "name": "doc.txt"}]}
        mock_get.return_value = mock_response

        result = self.client.get(
            self.client._user_path("user@example.com", "/drive/root/children?$top=20")
        )

        self.assertEqual(result, {"value": [{"id": "file1", "name": "doc.txt"}]})
        called_url = mock_get.call_args[0][0]
        self.assertIn("drive", called_url)
        self.assertIn("root/children", called_url)

    # ------------------------------------------------------------------ #
    # Test 7: Connection fail — verify exception on failed connection
    # ------------------------------------------------------------------ #
    @patch("msft_api.requests.post")
    def test_connection_fail(self, mock_post):
        """Verify an exception is raised when the token endpoint fails."""
        mock_response = MagicMock()
        mock_response.status_code = 401
        mock_response.raise_for_status.side_effect = Exception("401 Unauthorized")
        mock_post.return_value = mock_response

        with self.assertRaises(Exception):
            self.client._ensure_token()


if __name__ == "__main__":
    unittest.main()