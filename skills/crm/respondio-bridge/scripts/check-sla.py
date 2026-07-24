#!/usr/bin/env python3
"""SLA report: first response times from Respond.io conversations."""
import argparse, json, os, sys, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

def api_get(api_key, path, params=None):
    url = f"https://api.respond.io/v2/{path.lstrip('/')}"
    if params:
        url += "?" + "&".join(f"{k}={v}" for k, v in params.items())
    req = urllib.request.Request(url, headers={"X-API-Key": api_key})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

def format_duration(seconds):
    if seconds < 60:
        return f"{int(seconds)}s"
    mins = seconds / 60
    if mins < 60:
        return f"{int(mins)}m{int(seconds % 60)}s"
    hours = mins / 60
    return f"{int(hours)}h{int(mins % 60)}m"

def main():
    parser = argparse.ArgumentParser(description="Check response SLA")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--threshold-minutes", type=int, default=5,
                        help="Auto-respond threshold in minutes")
    args = parser.parse_args()

    since = (datetime.now(timezone.utc) - timedelta(hours=args.hours)).isoformat()

    try:
        data = api_get(args.api_key, "conversations", {
            "since": since,
            "limit": 100,
        })
    except Exception as e:
        print(f"❌ Failed to fetch conversations: {e}")
        sys.exit(1)

    conversations = data.get("data", [])
    total = len(conversations)
    if total == 0:
        print("📊 SLA Report: No conversations in the last 24 hours.")
        return

    auto = 0
    human = 0
    breached = []
    human_times = []

    for conv in conversations:
        msgs = conv.get("messages", [])
        if not msgs:
            continue

        first_msg = msgs[0]
        first_reply = next((m for m in msgs[1:] if m.get("direction") == "outbound"), None)

        if not first_reply:
            continue

        t1 = datetime.fromisoformat(first_msg["timestamp"].replace("Z", "+00:00"))
        t2 = datetime.fromisoformat(first_reply["timestamp"].replace("Z", "+00:00"))
        response_seconds = (t2 - t1).total_seconds()

        if response_seconds < args.threshold_minutes * 60:
            auto += 1
        else:
            human += 1
            human_times.append(response_seconds)
            if response_seconds > 30 * 60:  # > 30 min
                contact_name = conv.get("contact", {}).get("name", "Unknown")
                channel = conv.get("channel", "?")
                breached.append({
                    "id": conv.get("id", "?"),
                    "name": contact_name,
                    "channel": channel,
                    "time": response_seconds,
                    "duration": format_duration(response_seconds),
                })

    avg_human = sum(human_times) / len(human_times) if human_times else 0

    print(f"📊 SLA Report (last {args.hours}h)")
    print("━" * 40)
    print(f"Total conversations:  {total}")
    print(f"Auto-responded (≤{args.threshold_minutes}m): {auto:>3d} ({auto*100//total}%)")
    print(f"Human response:       {human:>3d} ({human*100//total}%)")
    if human_times:
        print(f"Avg human response:   {format_duration(avg_human)}")
    print(f"Breached (>30min):    {len(breached)}")
    for b in breached:
        print(f"  • {b['name']} ({b['channel']}) → {b['duration']}")

if __name__ == "__main__":
    main()
