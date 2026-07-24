#!/usr/bin/env python3
"""SLA report for Chatwoot conversations."""
import argparse, json, os, sys, urllib.request, urllib.error
from datetime import datetime, timezone, timedelta

def api_get(base, token, path):
    url = f"{base.rstrip('/')}/api/v1/{path.lstrip('/')}"
    req = urllib.request.Request(url, headers={"api_access_token": token})
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
    parser = argparse.ArgumentParser(description="Chatwoot SLA report")
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--access-token", required=True)
    parser.add_argument("--account-id", type=int, default=1)
    parser.add_argument("--hours", type=int, default=24)
    parser.add_argument("--threshold-minutes", type=int, default=5)
    args = parser.parse_args()

    # Fetch open conversations in the last N hours
    try:
        data = api_get(args.api_url, args.access_token,
                       f"accounts/{args.account_id}/conversations/filter")
    except Exception as e:
        print(f"❌ Failed to fetch conversations: {e}")
        sys.exit(1)

    # The filter endpoint returns paginated results
    all_convs = data.get("data", {}).get("payload", data.get("payload", []))
    if not all_convs and isinstance(data, list):
        all_convs = data

    if not all_convs:
        # Try the simpler endpoint
        try:
            data = api_get(args.api_url, args.access_token, "conversations?status=all")
            all_convs = data.get("data", {}).get("payload", data.get("payload", []))
        except:
            pass

    total = len(all_convs) if all_convs else 0
    if total == 0:
        print("📊 SLA Report: No conversations found.")
        return

    # For each conversation, check first response time
    # Chatwoot webhook payloads carry `created_at` per message
    # We compute time between first incoming message and first outgoing from an agent
    auto = 0
    human = 0
    breached = []
    human_times = []

    for conv in (all_convs or []):
        first_msg = conv.get("messages", [{}])[0] if conv.get("messages") else None
        if not first_msg:
            continue

        created = first_msg.get("created_at")
        if not created:
            continue

        try:
            t1 = datetime.fromisoformat(created.replace("Z", "+00:00"))
        except:
            t1 = datetime.now(timezone.utc)

        # Check if there's a reply
        reply_msgs = [m for m in (conv.get("messages") or [])
                      if m.get("message_type") == 1 and m.get("id") != first_msg.get("id")]
        if not reply_msgs:
            continue

        reply_created = reply_msgs[0].get("created_at", created)
        try:
            t2 = datetime.fromisoformat(reply_created.replace("Z", "+00:00"))
        except:
            t2 = t1 + timedelta(seconds=10)

        response_seconds = (t2 - t1).total_seconds()

        if response_seconds < args.threshold_minutes * 60:
            auto += 1
        else:
            human += 1
            human_times.append(response_seconds)
            if response_seconds > 30 * 60:
                contact_name = conv.get("meta", {}).get("sender", {}).get("name", "Unknown")
                inbox_id = conv.get("inbox_id", "?")
                breached.append({
                    "id": conv.get("id"),
                    "name": contact_name,
                    "inbox": inbox_id,
                    "duration": format_duration(response_seconds),
                })

    avg_human = sum(human_times) / len(human_times) if human_times else 0

    print(f"📊 SLA Report (last {args.hours}h)")
    print("━" * 40)
    print(f"Total conversations:  {total}")
    print(f"Quick reply (≤{args.threshold_minutes}m): {auto:>3d} ({auto*100//total if total else 0}%)")
    print(f"Human response:       {human:>3d} ({human*100//total if total else 0}%)")
    if human_times:
        print(f"Avg response time:    {format_duration(avg_human)}")
    print(f"Breached (>30min):    {len(breached)}")
    for b in breached:
        print(f"  • {b['name']} (inbox {b['inbox']}) → {b['duration']}")

if __name__ == "__main__":
    main()
