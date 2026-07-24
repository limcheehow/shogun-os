#!/usr/bin/env python3
"""Log a Chatwoot conversation as a brain timeline entry on the contact's page."""

import argparse, json, os, sys, re, urllib.request, urllib.error
from datetime import datetime

def api_get(base, token, path):
    url = f"{base.rstrip('/')}/api/v1/{path.lstrip('/')}"
    req = urllib.request.Request(url, headers={"api_access_token": token})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

BRAIN_CONTACTS_DIR = os.path.expanduser("~/brain/people/contacts")

def main():
    parser = argparse.ArgumentParser(description="Log Chatwoot conversation to brain")
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--access-token", required=True)
    parser.add_argument("--conversation-id", required=True)
    args = parser.parse_args()

    # Fetch conversation details
    try:
        conv = api_get(args.api_url, args.access_token, f"conversations/{args.conversation_id}")
    except Exception as e:
        print(f"❌ Failed to fetch conversation: {e}")
        sys.exit(1)

    payload = conv.get("payload", conv)
    messages = payload.get("messages", []) or payload.get("data", {}).get("messages", [])

    if not messages:
        # Try meta
        meta = payload.get("meta", {})
        print(f"⚠️  No messages in conversation #{args.conversation_id}")
        print(f"   Status: {payload.get('status', '?')}")
        print(f"   Assignee: {payload.get('assignee', {}).get('name', 'none')}")
        return

    # Get contact info
    contact = payload.get("meta", {}).get("sender", payload.get("contact", {}))
    contact_name = contact.get("name", "Unknown")
    contact_id = contact.get("id")

    # Find the brain page for this contact
    if contact_id:
        brain_page = os.path.join(BRAIN_CONTACTS_DIR, f"chatwoot-{contact_id}.md")
        if not os.path.exists(brain_page):
            print(f"⚠️  Brain page not found for contact {contact_id}. Sync first.")
            return

        # Build timeline section
        first_msg = messages[0]
        last_msg = messages[-1]
        summary = first_msg.get("content", "(no text)")[:100]
        inbox_id = payload.get("inbox_id", "?")
        status = payload.get("status", "open")

        timeline_entry = f"""
**Chatwoot conversation #{args.conversation_id}**
- **Date:** {datetime.utcnow().strftime('%Y-%m-%d %H:%M UTC')}
- **Channel (inbox):** {inbox_id}
- **Status:** {status}
- **Summary:** {summary}
- **Messages:** {len(messages)}
"""

        # Append to the brain page
        with open(brain_page, "a") as f:
            f.write(f"\n## Conversation {args.conversation_id}\n{timeline_entry}\n")

        print(f"✅ Logged conversation #{args.conversation_id} → {brain_page}")
        print(f"   Contact: {contact_name}")
        print(f"   Messages: {len(messages)}, Status: {status}")
    else:
        print(f"⚠️  No contact ID found for conversation #{args.conversation_id}")

if __name__ == "__main__":
    main()
