"""
Communication Provider Interface
─────────────────────────────────
Abstract interface that all comm providers must implement.
Used by send-scrum-dms.py and check-scrum-replies.py for no_agent cron jobs.
"""

import importlib
import os
from pathlib import Path
from typing import Optional


class CommProvider:
    """Interface for communication providers."""

    def send_dm(self, user_id: str, text: str) -> dict:
        """Send a DM to a user.

        Returns:
            dict with keys: thread_id, conversation_id
        """
        raise NotImplementedError

    def read_replies(self, user_id: str, thread_id: str) -> list:
        """Read replies in a thread.

        Returns:
            list of dicts with keys: sender, text, ts
        """
        raise NotImplementedError

    def post_message(self, channel_id: str, text: str) -> dict:
        """Post a message to a channel.

        Returns:
            dict with keys: message_id
        """
        raise NotImplementedError

    def add_reaction(self, channel_id: str, message_id: str, reaction: str):
        """Add a reaction to a message."""
        raise NotImplementedError

    def search_messages(self, channel_id: str, query: str, limit: int = 10) -> list:
        """Search messages in a channel.

        Returns:
            list of dicts with keys: sender, text, ts, thread_id
        """
        raise NotImplementedError


# ── Provider registry ───────────────────────────────────────────────────

REGISTRY = {}

def register(name: str, cls: type):
    REGISTRY[name] = cls


def get_provider(name: str, env: dict = None) -> CommProvider:
    """Load a comm provider by name.

    Args:
        name: Provider name (e.g. 'slack', 'telegram')
        env: Optional env dict (defaults to os.environ)

    Returns:
        CommProvider instance

    Raises:
        ValueError: If provider not found or missing required env vars
    """
    if not REGISTRY:
        _discover_providers()

    if name not in REGISTRY:
        available = ", ".join(sorted(REGISTRY.keys()))
        raise ValueError(
            f"Unknown comm provider: '{name}'. "
            f"Available: {available}"
        )

    cls = REGISTRY[name]
    return cls(env or os.environ)


def _discover_providers():
    """Auto-discover provider modules in the comm/ directory."""
    provider_dir = Path(__file__).parent
    for f in sorted(provider_dir.glob("*.py")):
        if f.name == "__init__.py" or f.name == "provider.py":
            continue
        mod_name = f"comm.{f.stem}"
        try:
            importlib.import_module(mod_name)
        except ImportError as e:
            # Silently skip providers with missing dependencies
            pass