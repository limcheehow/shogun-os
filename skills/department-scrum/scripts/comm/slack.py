"""
Slack Communication Provider
─────────────────────────────
Implements CommProvider interface using slack_sdk WebClient.

Requires:
  - pip install slack_sdk
  - SLACK_BOT_TOKEN env var (from Slack App -> OAuth & Permissions)
"""

import json
import os
import time
from typing import Optional

from .provider import CommProvider, register


class SlackProvider(CommProvider):
    def __init__(self, env: dict):
        self.env = env
        token = self._get_token()
        from slack_sdk import WebClient
        self.client = WebClient(token=token)

    def _get_token(self) -> str:
        """Resolve SLACK_BOT_TOKEN from env, profile .env, or global .env."""
        token = self.env.get("SLACK_BOT_TOKEN")
        if token:
            return token
        # Check profile .env
        profile_dir = self.env.get("HERMES_HOME", os.path.expanduser("~/.hermes"))
        profile = self.env.get("HERMES_PROFILE", "")
        if profile:
            env_path = os.path.join(profile_dir, "profiles", profile, ".env")
            if os.path.exists(env_path):
                token = self._parse_env_file(env_path)
                if token:
                    return token
        # Check global .env
        env_path = os.path.join(profile_dir, ".env")
        if os.path.exists(env_path):
            token = self._parse_env_file(env_path)
            if token:
                return token
        raise ValueError(
            "SLACK_BOT_TOKEN not found. Set in profile .env or global .env"
        )

    def _parse_env_file(self, path: str) -> Optional[str]:
        with open(path) as f:
            for line in f:
                line = line.strip()
                if line.startswith("SLACK_BOT_TOKEN=") and not line.startswith("#"):
                    return line.split("=", 1)[1].strip().strip('"').strip("'")
        return None

    def send_dm(self, user_id: str, text: str) -> dict:
        dm = self.client.conversations_open(users=[user_id])
        dm_channel = dm["channel"]["id"]
        msg = self.client.chat_postMessage(channel=dm_channel, text=text)
        return {
            "thread_id": msg["ts"],
            "conversation_id": dm_channel,
        }

    def read_replies(self, user_id: str, thread_id: str) -> list:
        """Read replies. user_id is ignored for Slack — we use conversation_id instead."""
        # This method needs conversation_id — read from state file
        # For direct use, use the overload with channel parameter
        raise NotImplementedError(
            "Use read_replies_in_thread(channel_id, thread_id) for Slack"
        )

    def read_replies_in_thread(self, channel_id: str, thread_id: str) -> list:
        import datetime
        result = self.client.conversations_history(
            channel=channel_id,
            oldest=str(float(thread_id)),
            inclusive=False,
            limit=100,
        )
        replies = []
        for msg in result.get("messages", []):
            if msg.get("thread_ts") == thread_id or msg.get("ts") == thread_id:
                continue  # skip parent message
            replies.append({
                "sender": msg.get("user", msg.get("bot_id", "unknown")),
                "text": msg.get("text", ""),
                "ts": msg.get("ts", ""),
            })
        return replies

    def post_message(self, channel_id: str, text: str) -> dict:
        msg = self.client.chat_postMessage(channel=channel_id, text=text)
        return {"message_id": msg["ts"]}

    def add_reaction(self, channel_id: str, message_id: str, reaction: str):
        self.client.reactions_add(
            channel=channel_id,
            name=reaction,
            timestamp=message_id,
        )

    def search_messages(self, channel_id: str, query: str, limit: int = 10) -> list:
        result = self.client.search_messages(
            query=query,
            sort="timestamp",
            count=limit,
        )
        matches = []
        for msg in result.get("messages", {}).get("matches", []):
            matches.append({
                "sender": msg.get("user", "unknown"),
                "text": msg.get("text", ""),
                "ts": msg.get("ts", ""),
                "thread_id": msg.get("thread_ts", msg.get("ts")),
                "channel": msg.get("channel", {}).get("id", channel_id),
            })
        return matches


register("slack", SlackProvider)