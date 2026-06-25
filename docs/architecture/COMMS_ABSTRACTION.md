# Communication Provider Abstraction

> **Standard interface for sending DMs, reading replies, and posting messages.**
> Any provider (Slack, Telegram, Discord, etc.) that implements this interface
> can be used by the scrum scripts and cron delivery system.

## The Interface

All communication scripts import from `comm/provider.py`, which loads the configured provider:

```python
from comm.provider import send_dm, read_replies, post_message
```

The provider is determined by the `comm_provider` field in `scrum.yaml`.

## Standard Tool Names (MCP)

For agent-facing cron jobs (11am, 5pm), the agent uses these MCP tool names:

| Tool | Purpose | Required Fields |
|------|---------|-----------------|
| `comm_send_dm` | Send a direct message | `userId`, `text` |
| `comm_read_replies` | Read replies in a thread | `userId`, `threadId` |
| `comm_post_message` | Post to a channel | `channelId`, `text` |
| `comm_add_reaction` | React to a message | `channelId`, `messageId`, `reaction` |

## Provider Interface (Python)

For `no_agent` cron scripts, each provider implements:

```python
class CommProvider:
    """Interface that every comm provider must implement."""

    def send_dm(self, user_id: str, text: str) -> dict:
        """Send a DM to a user. Returns {thread_id, conversation_id}."""
        ...

    def read_replies(self, user_id: str, thread_id: str) -> list:
        """Read replies in a thread. Returns list of {sender, text, ts}."""
        ...

    def post_message(self, channel_id: str, text: str) -> dict:
        """Post a message to a channel. Returns {message_id}."""
        ...

    def add_reaction(self, channel_id: str, message_id: str, reaction: str):
        """Add a reaction/emoji to a message."""
        ...
```

## Scrum Config Schema

The `scrum.yaml` now includes a `comm_provider` field:

```yaml
profile: hr-manager
app_name: Jinzai
comm_provider: slack              # ← provider name (slack, telegram, etc.)

team:
  - name: "Alice"
    user_id: "U0XXXXXXX"         # ← provider-specific user ID (was slack_id)
    role: "HR Manager"
```

When `comm_provider` is set, the state file stores provider-agnostic identifiers:

```json
{
  "profile": "hr-manager",
  "date": "2026-06-26",
  "comm_provider": "slack",
  "team": [
    {
      "name": "Alice",
      "user_id": "U0XXXXXXX",
      "thread_id": "1734567890.123456",
      "conversation_id": "D0XXXXXXX"
    }
  ]
}
```

## Provider Implementations

### Slack Provider

Location: `skills/department-scrum/scripts/comm/slack.py`

Uses `slack_sdk.WebClient` with `SLACK_BOT_TOKEN` from env.

| Abstract Field | Slack Mapping |
|---------------|--------------|
| `user_id` | Slack user ID (e.g. `U0XXXXXXX`) |
| `thread_id` | Slack message timestamp (e.g. `1734567890.123456`) |
| `conversation_id` | Slack channel/DM ID (e.g. `D0XXXXXXX`, `C0XXXXXXX`) |

### Telegram Provider

Location: `skills/department-scrum/scripts/comm/telegram.py`

Uses `python-telegram-bot` with `TELEGRAM_BOT_TOKEN` from env.

| Abstract Field | Telegram Mapping |
|---------------|-----------------|
| `user_id` | Telegram chat ID (e.g. `1101916530`) |
| `thread_id` | Telegram message ID (e.g. `12345`) |
| `conversation_id` | Telegram chat ID (same as user_id for DMs) |

## Adding a New Provider

Create `skills/department-scrum/scripts/comm/<name>.py`:

```python
from .provider import CommProvider

class MyProvider(CommProvider):
    def send_dm(self, user_id, text):
        # ... implement
        return {"thread_id": "...", "conversation_id": "..."}
    def read_replies(self, user_id, thread_id):
        # ... implement
        return [{"sender": "...", "text": "...", "ts": "..."}]
    def post_message(self, channel_id, text):
        # ... implement
        return {"message_id": "..."}
    def add_reaction(self, channel_id, message_id, reaction):
        # ... implement
        pass
```

Then set `comm_provider: myprovider` in `scrum.yaml`.

## Environment Variables

| Provider | Required Env Var | Where to Set |
|----------|-----------------|-------------|
| Slack | `SLACK_BOT_TOKEN` | Profile `.env` |
| Telegram | `TELEGRAM_BOT_TOKEN` | Profile `.env` |