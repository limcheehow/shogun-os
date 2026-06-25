"""
Lark (Feishu) Communication Provider
─────────────────────────────────────
Implements CommProvider interface using Lark Open APIs.

Requires:
  - pip install requests
  - LARK_APP_ID and LARK_APP_SECRET env vars
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
        hermes = self.env.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
        profile = self.env.get("HERMES_PROFILE", "")
        self._token = self.env.get("LARK_ACCESS_TOKEN")
        if self._token:
            self._token_expires_at = float("inf")
            return
        self._app_id = self.env.get("LARK_APP_ID") or self._read_env_var(hermes, profile, "LARK_APP_ID")
        self._app_secret = self.env.get("LARK_APP_SECRET") or self._read_env_var(hermes, profile, "LARK_APP_SECRET")
        if not self._app_id or not self._app_secret:
            raise ValueError("Lark credentials not found. Set LARK_APP_ID + LARK_APP_SECRET in profile .env")

    def _read_env_var(self, hermes: str, profile: str, var: str) -> Optional[str]:
        paths = [os.path.join(hermes, "profiles", profile, ".env")] if profile else []
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
        if time.time() < self._token_expires_at:
            return
        if self._app_id and self._app_secret:
            resp = requests.post(f"{LARK_API}/auth/v3/tenant_access_token/internal",
                                 json={"app_id": self._app_id, "app_secret": self._app_secret}, timeout=10)
            resp.raise_for_status()
            data = resp.json()
            if data.get("code") != 0:
                raise ValueError(f"Lark auth failed: {data.get('msg', 'unknown')}")
            self._token = data["tenant_access_token"]
            self._token_expires_at = time.time() + data.get("expire", 7200) - 60
        else:
            raise ValueError("No Lark access token available")

    def _api(self, method: str, path: str, data: dict = None) -> dict:
        self._ensure_token()
        headers = {"Authorization": f"Bearer {self._token}", "Content-Type": "application/json"}
        url = f"{LARK_API}{path}"
        resp = requests.request(method, url, json=data, headers=headers, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if result.get("code") != 0:
            raise ValueError(f"Lark API error ({path}): {result.get('msg', 'unknown')}")
        return result.get("data", {})

    # ── CommProvider interface ────────────────────────────────────────

    def send_dm(self, user_id: str, text: str) -> dict:
        content = json.dumps({"text": text})
        result = self._api("POST", "/im/v1/messages?receive_id_type=user_id", {
            "receive_id": user_id, "msg_type": "text", "content": content,
        })
        msg = result.get("message", {})
        return {"thread_id": msg.get("message_id", ""), "conversation_id": msg.get("chat_id", "")}

    def read_replies(self, user_id: str, thread_id: str) -> list:
        try:
            chat_id = self._resolve_conversation_id(user_id)
            if not chat_id:
                return []
            result = self._api("GET",
                f"/im/v1/messages?container_id_type=chat&container_id={chat_id}&page_size=50&sort_type=ByCreateTimeDesc")
            replies = []
            for msg in result.get("items", []):
                body = msg.get("body", {})
                content_str = body.get("content", "{}")
                try:
                    content = json.loads(content_str)
                    text = content.get("text", "")
                except (json.JSONDecodeError, TypeError):
                    text = str(content_str)
                if msg.get("root_id") == thread_id or msg.get("parent_id") == thread_id:
                    replies.append({"sender": msg.get("sender", {}).get("id", "unknown"), "text": text, "ts": msg.get("create_time", "")})
            return replies
        except Exception:
            return []

    def post_message(self, channel_id: str, text: str) -> dict:
        content = json.dumps({"text": text})
        result = self._api("POST", "/im/v1/messages?receive_id_type=chat_id", {
            "receive_id": channel_id, "msg_type": "text", "content": content,
        })
        return {"message_id": result.get("message", {}).get("message_id", "")}

    def add_reaction(self, channel_id: str, message_id: str, reaction: str):
        try:
            self._api("POST", f"/im/v1/messages/{message_id}/reactions",
                      {"reaction_type": {"emoji_type": reaction}})
        except Exception:
            pass

    def search_messages(self, channel_id: str, query: str, limit: int = 10) -> list:
        try:
            result = self._api("GET",
                f"/im/v1/messages?container_id_type=chat&container_id={channel_id}&page_size={limit}&sort_type=ByCreateTimeDesc")
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
                        "sender": msg.get("sender", {}).get("id", "unknown"), "text": text,
                        "ts": msg.get("create_time", ""), "thread_id": msg.get("message_id", ""), "channel": channel_id,
                    })
            return matches[:limit]
        except Exception:
            return []

    # ── Lark-specific methods ─────────────────────────────────────────

    def send_card(self, channel_id: str, card: dict) -> dict:
        result = self._api("POST", "/im/v1/messages?receive_id_type=chat_id", {
            "receive_id": channel_id, "msg_type": "interactive", "content": json.dumps(card),
        })
        return {"message_id": result.get("message", {}).get("message_id", "")}

    def get_chat_info(self, chat_id: str) -> dict:
        return self._api("GET", f"/im/v1/chats/{chat_id}")

    def list_chats(self, page_size: int = 50) -> list:
        result = self._api("GET", f"/im/v1/chats?page_size={page_size}")
        return result.get("items", [])

    def verify_webhook(self, body: dict) -> bool:
        """Verify a Lark webhook event by responding to the challenge."""
        if body.get("type") == "url_verification":
            return body.get("challenge", "")
        return True

    def parse_webhook_event(self, body: dict) -> Optional[dict]:
        """Parse a Lark webhook event into a standard format.

        Returns: {type, sender, text, chat_id, message_id} or None
        """
        event = body.get("event", {})
        msg = event.get("message", {})
        chat_type = msg.get("chat_type", "")
        sender = msg.get("sender", {}).get("sender_id", {}).get("user_id", "unknown")
        content_str = msg.get("content", "{}")
        try:
            content = json.loads(content_str)
            text = content.get("text", content_str)
        except (json.JSONDecodeError, TypeError):
            text = content_str
        return {
            "type": event.get("event_type", ""),
            "sender": sender,
            "text": text,
            "chat_id": msg.get("chat_id", ""),
            "chat_type": "dm" if chat_type == "p2p" else "group",
            "message_id": msg.get("message_id", ""),
            "mention": bool(event.get("mention", {}).get("key")),
        }

    def _resolve_conversation_id(self, user_id: str) -> Optional[str]:
        if user_id.startswith("oc_"):
            return user_id
        return user_id


register("lark", LarkProvider)