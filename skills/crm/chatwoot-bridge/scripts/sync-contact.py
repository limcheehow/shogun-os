#!/usr/bin/env python3
"""Sync a Chatwoot contact to a brain people page."""

import argparse, json, os, sys, re, urllib.request, urllib.error
from datetime import datetime

def api_get(base, token, path):
    url = f"{base.rstrip('/')}/api/v1/{path.lstrip('/')}"
    req = urllib.request.Request(url, headers={"api_access_token": token})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

BRAIN_CONTACTS_DIR = os.path.expanduser("~/brain/people/contacts")

def slugify(name):
    s = name.lower().replace(" ", "-").replace(".", "-")
    return re.sub(r"[^a-z0-9-]", "", s)

def main():
    parser = argparse.ArgumentParser(description="Sync Chatwoot contact to brain")
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--access-token", required=True)
    parser.add_argument("--contact-id", required=True)
    args = parser.parse_args()

    try:
        contact = api_get(args.api_url, args.access_token, f"contacts/{args.contact_id}")
    except Exception as e:
        print(f"❌ Failed to fetch contact: {e}")
        sys.exit(1)

    payload = contact.get("payload", contact)
    name = payload.get("name", f"Contact {args.contact_id}")
    email = payload.get("email", "")
    phone = payload.get("phone_number", "")
    additional = payload.get("additional_attributes", {})

    slug = f"chatwoot-{slugify(name)}"
    os.makedirs(BRAIN_CONTACTS_DIR, exist_ok=True)

    content = f"""---
type: person
source: chatwoot
chatwoot_id: {args.contact_id}
tags:
  - customer
  - chatwoot
  - kizuna
---

# {name}

## Contact
- **Phone:** {phone}
- **Email:** {email}
- **Source:** Chatwoot
- **First synced:** {datetime.utcnow().isoformat()}Z
- **Additional attributes:** {json.dumps(additional)}
"""

    filepath = os.path.join(BRAIN_CONTACTS_DIR, f"{slug}.md")
    with open(filepath, "w") as f:
        f.write(content.lstrip("\n"))

    print(f"✅ Synced {name} → {filepath}")
    print(f"   Phone: {phone}, Email: {email}")

if __name__ == "__main__":
    main()
