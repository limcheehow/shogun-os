# Slack Posting from Cron Jobs

How to post messages to Slack from a Hermes cron job using Python, extracting the bot token from the active profile's `.env` file.

## Why Use Python Instead of `curl | jq`

- `jq` may not be installed on the system
- Python's `urllib.request` is stdlib — no pip install needed
- Conditional logic (find channel ID, handle errors) is easier in Python
- Works on both agent-mode and no_agent cron jobs

## Token Extraction

The Slack bot token lives in the profile's `.env` file at `~/.hermes/profiles/<profile>/.env`. The shoutout app's `start.sh` established the canonical extraction pattern using `grep`:

```python
import urllib.request, json

def get_slack_token():
    with open('/home/tapway/.hermes/profiles/hr-manager/.env') as f:
        for line in f:
            if line.startswith('SLACK_BOT_TOKEN='):
                return line.split('=', 1)[1].strip()
    raise Exception('SLACK_BOT_TOKEN not found in profile .env')

TOKEN = get_slack_token()
```

> **Security note:** The `.env` file stores the `xoxb-...` bot token as a raw value. The `grep` command `grep '^SLACK_BOT_TOKEN=' .env | head -1 | cut -d= -f2-` extracts it. This is the same approach the shoutout app's `start.sh` launcher uses.

## Finding the Channel ID

To post to a named channel (e.g., `#team-happiness`), resolve its Slack channel ID via `conversations.list`:

```python
req = urllib.request.Request(
    "https://slack.com/api/conversations.list?types=public_channel,private_channel&limit=200",
    headers={"Authorization": f"Bearer {TOKEN}"}
)
resp = json.loads(urllib.request.urlopen(req).read().decode())

if not resp.get("ok"):
    raise Exception(f"Slack API error: {resp.get('error')}")

channel = None
for ch in resp.get("channels", []):
    if ch["name"] == "team-happiness":
        channel = ch
        break

if not channel:
    raise Exception("Channel not found")
```

Known channel IDs (discovered from production runs):
- `#team-happiness` = `C02V7GKJP`

> You can hardcode the channel ID for a known channel, but resolving via API is more robust across workspace migrations.

## Posting a Message

Use `chat.postMessage` with the bot token:

```python
message = "<!channel> 🎂 *Happy Birthday!* 🎉\nToday we celebrate *Finny*!\nWishing you an amazing day filled with joy, cake, and zero production incidents. 🍰\n— Jinzai (HR bot)"

post_data = json.dumps({
    "channel": channel["id"],
    "text": message,
}).encode()

post_req = urllib.request.Request(
    "https://slack.com/api/chat.postMessage",
    data=post_data,
    headers={
        "Authorization": f"Bearer {TOKEN}",
        "Content-Type": "application/json; charset=utf-8",
    }
)
post_resp = json.loads(urllib.request.urlopen(post_req).read().decode())

if post_resp.get("ok"):
    print(f"✅ Posted! Timestamp: {post_resp.get('ts')}")
else:
    print(f"❌ Failed: {post_resp.get('error')}")
```

### Rich Block Messages

If you need a richer layout (buttons, dividers, context blocks), pass a `blocks` array alongside `text`. Blocks render in the Slack client; `text` serves as fallback for notifications:

```python
blocks = [
    {
        "type": "section",
        "text": {
            "type": "mrkdwn",
            "text": "<!channel> 🎂 *Happy Birthday!* 🎉\nToday we celebrate *Finny*!"
        }
    }
]

post_data = json.dumps({
    "channel": channel["id"],
    "text": "<!channel> Happy Birthday Finny!",  # notification fallback
    "blocks": blocks,
}).encode()
```

## Complete Cron Job Pattern (Birthday Post)

This is the pattern used by Jinzai's daily birthday check cron job on the hr-manager profile:

```python
import urllib.request, json, os, sys

# 1. Extract token
with open('/home/tapway/.hermes/profiles/hr-manager/.env') as f:
    for line in f:
        if line.startswith('SLACK_BOT_TOKEN='):
            TOKEN = line.split('=', 1)[1].strip()
            break

# 2. Post message
channel_id = "C02V7GKJP"  # #team-happiness
message = "<!channel> 🎂 *Happy Birthday!* 🎉\nToday we celebrate *Finny*!"

post_data = json.dumps({"channel": channel_id, "text": message}).encode()
req = urllib.request.Request(
    "https://slack.com/api/chat.postMessage",
    data=post_data,
    headers={"Authorization": f"Bearer {TOKEN}", "Content-Type": "application/json; charset=utf-8"}
)
resp = json.loads(urllib.request.urlopen(req).read().decode())

if not resp.get("ok"):
    print(f"❌ Failed: {resp.get('error')}")
    sys.exit(1)

print(f"✅ Posted at {resp.get('ts')}")
```

## Pitfalls

- **Token hidden by shell redaction:** The `.env` file content appears as `***` in some tool output (grep, cat) because the terminal redacts secrets. Use Python's open()+readline() or the specific grep command from `start.sh` to get the raw value.
- **Rate limits:** Slack allows ~1 request per second per token for `conversations.list`. Cache the channel ID if calling frequently.
- **Bot must be in the channel:** `chat.postMessage` fails with `not_in_channel` if the bot hasn't been invited. Either invite it manually (`/invite @BotName`) or use `conversations.join` for public channels first.
- **`<!channel>` only works in public channels** — it notifies all members. Use `<!here>` for smaller groups or `<!everyone>` sparingly.
- **Block messages without `text`** won't appear in push notifications. Always include a plain `text` fallback.
- **Token per profile:** Each Hermes profile (hr-manager, marketing-manager, etc.) has its own `.env` with its own Slack bot token. Always read from the correct profile path.