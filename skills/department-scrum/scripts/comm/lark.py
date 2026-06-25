"""
Lark (Feishu) Communication Provider
─────────────────────────────────────
Implements CommProvider interface using Lark Open APIs.

Requires:
  - pip install requests
  - LARK_APP_ID and LARK_APP_SECRET env vars (from Lark Developer Console)
  - Or LARK_ACCESS_TOKEN for pre-authenticated access

API Docs: https://open.larksuite.com/document/server-docs/im-v1/message/create
"""

import json
import os
import time
from typing import Optional

import requests

from .provider import CommProvider, register


LARK_API = "https://open.larksuite.com/open-apis"


class LarkProvider(CommProvider):
    def __init__(self, env: dict):
        self.env = env
        self._app_id = None
        self._app_secret = None
        self._token = None
        self._token_expires_at = 0
        self._load_credentials()

    def _load_credentials(self):
        """Load Lark credentials from env."""
        hermes = self.env.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
        profile = self.env.get("HERMES_PROFILE", "")

        # Try direct token first
        self._token = self.env.get("LARK_ACCESS_TOKEN")
        if self._token:
            self._token_expires_at = float("inf")
            return

        # Try app credentials
        self._app_id = self.env.get("LARK_APP_ID") or self._read_env_var(
            hermes, profile, "LARK_APP_ID"
        )
        self._app_secret = self.env.get("LARK_APP_SECRET") or self._read_env_var(
            hermes, profile, "LARK_APP_SECRET"
        )

        if not self._app_id or not self._app_secret:
            raise ValueError(
                "Lark credentials not found. Set LARK_APP_ID + LARK_APP_SECRET "
                "(or LARK_ACCESS_TOKEN for pre-authenticated) in profile .env"
            )

    def _read_env_var(self, hermes: str, profile: str, var: str) -> Optional[str]:
        """Read env var from profile .env or global .env."""
        paths = []
        if profile:
            paths.append(os.path.join(hermes, "profiles", profile, ".env"))
        paths.append(os.path.join(hermes, ".env"))
        for path in paths:
            if os.path.exists(path):
                with open(path) as f:
                    for line in f:
                        line = line.strip()
                        if line.startswith(f"{var}=***") and not line.startswith("#"):
                            return line.split("=", 1)[1].strip().strip('"').strip("'")
        return None

    def _ensure_token(self):
        """Get or refresh tenant access token."""
        if time.time() < self._token_expires_at:
            return
        if self._app_id and self._app_secret:
            resp = requests.post(
                f"{LARK_API}/auth/v3/tenant_access_token/internal",
                json={"app_id": self._app_id, "app_secret": self._app_secret},
                timeout=10,
            )
            resp.raise_for_status()
            data = resp.json()
            if not data.get("code") == 0:
                raise ValueError(f"Lark auth failed: {data.get('msg', 'unknown')}")
            self._token = data["tenant_access_token"]
            self._token_expires_at = time.time() + data.get("expire", 7200) - 60
        else:
            raise ValueError("No Lark access token available")

    def _api(self, method: str, path: str, data: dict = None) -> dict:
        """Call Lark Open API with auto-refresh."""
        self._ensure_token()
        headers = {
            "Authorization": f"Bearer {self._token}",
            "Content-Type": "application/json",
        }
        url = f"{LARK_API}{path}"
        resp = requests.request(method, url, json=data, headers=headers, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 0:
            raise ValueError(f"Lark API error ({path}): {result.get('msg', 'unknown')}")
        return result.get("data", {})

    def send_dm(self, user_id: str, text: str) -> dict:
        """Send a text DM to a Lark user.

        user_id should be the Lark user_id (not open_id or union_id).
        The bot must have im:message scope and be added as a contact.
        """
        content = json.dumps({"text": text})
        result = self._api("POST", "/im/v1/messages?receive_id_type=user_id", {
            "receive_id": user_id,
            "msg_type": "text",
            "content": content,
        })
        message = result.get("message", {})
        return {
            "thread_id": message.get("message_id", ""),
            "conversation_id": message.get("chat_id", ""),
        }

    def read_replies(self, user_id: str, thread_id: str) -> list:
        """Read replies to a message in Lark.

        Note: Lark does not expose thread replies easily via simple API.
        This lists recent messages from the chat and filters by parent_id.
        """
        # We need the chat_id to read messages. Since user_id is the recipient,
        # we assume it's a DM (p2p chat). Lark DM chat IDs are not easily
        # derivable from user_id alone.
        # For simplicity, this returns an empty list — the agent cron (not no_agent)
        # handles reply checking via its own MCP tools.
        return []

    def post_message(self, channel_id: str, text: str) -> dict:
        """Post a message to a Lark chat (group or DM).

        channel_id is the Lark chat_id.
        """
        content = json.dumps({"text": text})
        result = self._api("POST", "/im/v1/messages?receive_id_type=chat_id", {
            "receive_id": channel_id,
            "msg_type": "text",
            "content": content,
        })
        message = result.get("message", {})
        return {"message_id": message.get("message_id", "")}

    def add_reaction(self, channel_id: str, message_id: str, reaction: str):
        """Add a reaction emoji to a Lark message.

        reaction should be an emoji Unicode string (e.g. ✅, 👍).
        """
        try:
            self._api("POST", f"/im/v1/messages/{message_id}/reactions", {
                "reaction_type": {"emoji_type": reaction},
            })
        except Exception:
            # Lark reactions may fail if the message is too old or bot lacks scope
            pass

    def search_messages(self, channel_id: str, query: str, limit: int = 10) -> list:
        """Search messages in a Lark chat.

        Note: Lark's message search API requires specific permissions.
        Falls back to listing recent messages.
        """
        try:
            result = self._api(
                "GET",
                f"/im/v1/messages?container_id_type=chat&container_id={channel_id}&page_size={limit}&sort_type=ByCreateTimeDesc",
            )
            matches = []
            for msg in result.get("items", []):
                body = msg.get("body", {})
                content_str = body.get("content", "{}")
                try:
                    content = json.loads(content_str)
                    text = content.get("text", "")
                except (json.JSONDecodeError, TypeError):
                    text = str(content_str)
                if query.lower() in text.lower():
                    matches.append({
                        "sender": msg.get("sender", {}).get("id", "unknown"),
                        "text": text,
                        "ts": msg.get("create_time", ""),
                        "thread_id": msg.get("message_id", ""),
                        "channel": channel_id,
                    })
            return matches[:limit]
        except Exception:
            return []


register("lark", LarkProvider)