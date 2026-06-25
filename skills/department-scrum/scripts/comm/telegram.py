"""
Telegram Communication Provider
─────────────────────────────────
Implements CommProvider interface using direct Telegram Bot HTTP API.

Requires:
  - pip install requests
  - TELEGRAM_BOT_TOKEN env var (from BotFather)
"""

import json
import os
import time
from typing import Optional

import requests

from .provider import CommProvider, register


TELEGRAM_API = "https://api.telegram.org/bot"


class TelegramProvider(CommProvider):
    def __init__(self, env: dict):
        self.env = env
        self.token = self._get_token()
        self.api_url = f"{TELEGRAM_API}{self.token}"

    def _get_token(self) -> str:
        token = self.env.get("TELEGRAM_BOT_TOKEN")
        if token:
            return token
        hermes = self.env.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
        profile = self.env.get("HERMES_PROFILE", "")
        if profile:
            path = os.path.join(hermes, "profiles", profile, ".env")
            t = self._read_env(path)
            if t:
                return t
        path = os.path.join(hermes, ".env")
        t = self._read_env(path)
        if t:
            return t
        raise ValueError(
            "TELEGRAM_BOT_TOKEN not found. Set in profile .env or global .env"
        )

    def _read_env(self, path: str) -> Optional[str]:
        if not os.path.exists(path):
            return None
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("TELEGRAM_BOT_TOKEN=") and not line.startswith("#"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        return None

    def _api(self, method: str, data: dict = None) -> dict:
        """Call Telegram Bot API."""
        url = f"{self.api_url}/{method}"
        resp = requests.post(url, json=data or {}, timeout=10)
        resp.raise_for_status()
        result = resp.json()
        if not result.get("ok"):
            raise ValueError(f"Telegram API error: {result.get('description', 'unknown')}")
        return result.get("result", {})

    def _get_updates(self, offset: int = None, limit: int = 100) -> list:
        """Get updates (polling for replies)."""
        data = {"limit": limit, "timeout": 5}
        if offset:
            data["offset"] = offset
        return self._api("getUpdates", data)

    def send_dm(self, user_id: str, text: str) -> dict:
        msg = self._api("sendMessage", {
            "chat_id": int(user_id),
            "text": text,
        })
        return {
            "thread_id": str(msg["message_id"]),
            "conversation_id": str(msg["chat"]["id"]),
        }

    def read_replies(self, user_id: str, thread_id: str) -> list:
        """Read replies to a message. Polls for reply_to_message matching thread_id."""
        chat_id = int(user_id)
        offset: Optional[int] = None
        replies = []
        for _ in range(3):
            updates = self._get_updates(offset=offset, limit=100)
            for update in updates:
                current_offset = update.get("update_id", 0) + 1
                if offset is None or current_offset > offset:
                    offset = current_offset
                msg = update.get("message")
                if not msg:
                    continue
                if msg.get("chat", {}).get("id") != chat_id:
                    continue
                reply_to = msg.get("reply_to_message")
                if reply_to and str(reply_to.get("message_id")) == thread_id:
                    replies.append({
                        "sender": str(msg["from"]["id"]),
                        "text": msg.get("text", msg.get("caption", "")),
                        "ts": str(msg.get("date", 0)),
                    })
            time.sleep(1)
        return replies

    def post_message(self, channel_id: str, text: str) -> dict:
        msg = self._api("sendMessage", {
            "chat_id": int(channel_id),
            "text": text,
        })
        return {"message_id": str(msg["message_id"])}

    def add_reaction(self, channel_id: str, message_id: str, reaction: str):
        try:
            self._api("setMessageReaction", {
                "chat_id": int(channel_id),
                "message_id": int(message_id),
                "reaction": json.dumps([{"type": "emoji", "emoji": reaction}]),
            })
        except Exception:
            pass

    def search_messages(self, channel_id: str, query: str, limit: int = 10) -> list:
        chat_id = int(channel_id)
        offset: Optional[int] = None
        found = []
        for _ in range(5):
            updates = self._get_updates(offset=offset, limit=100)
            if not updates:
                break
            for update in updates:
                current_offset = update.get("update_id", 0) + 1
                if offset is None or current_offset > offset:
                    offset = current_offset
                msg = update.get("message")
                if not msg:
                    continue
                if msg.get("chat", {}).get("id") != chat_id:
                    continue
                text = msg.get("text", msg.get("caption", ""))
                if query.lower() in text.lower():
                    found.append({
                        "sender": str(msg["from"]["id"]),
                        "text": text,
                        "ts": str(msg.get("date", 0)),
                        "thread_id": str(msg["message_id"]),
                        "channel": str(msg["chat"]["id"]),
                    })
                    if len(found) >= limit:
                        return found
            time.sleep(1)
        return found[:limit]


register("telegram", TelegramProvider)