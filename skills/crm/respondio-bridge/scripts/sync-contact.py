#!/usr/bin/env python3
"""Sync a Respond.io contact to brain people page."""

import argparse, json, os, sys, re, urllib.request, urllib.error
from datetime import datetime

def api_get(api_key, path):
    url = f"https://api.respond.io/v2/{path.lstrip('/')}"
    req = urllib.request.Request(url, headers={"X-API-Key": api_key})
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

BRAIN_CONTACTS_DIR = os.path.expanduser("~/brain/people/contacts")

def slugify(name):
    s = name.lower().replace(" ", "-").replace(".", "-")
    return re.sub(r"[^a-z0-9-]", "", s)

def main():
    parser = argparse.ArgumentParser(description="Sync Respond.io contact to brain")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--contact-id", required=True)
    parser.add_argument("--channel", default="unknown")
    args = parser.parse_args()

    # Fetch contact from Respond.io
    try:
        contact = api_get(args.api_key, f"contacts/{args.contact_id}")
    except Exception as e:
        print(f"❌ Failed to fetch contact: {e}")
        sys.exit(1)

    contact_data = contact.get("data", contact)
    name = contact_data.get("name") or contact_data.get("firstName", "") + " " + contact_data.get("lastName", "")
    name = name.strip() or f"Contact {args.contact_id[:8]}"
    phone = contact_data.get("phone", "")
    email = contact_data.get("email", "")
    country = contact_data.get("country", "")
    custom_fields = contact_data.get("customFields", {})
    tags = contact_data.get("tags", [])

    # Create brain page
    slug = f"cnt-{args.channel}-{slugify(name)}"
    os.makedirs(BRAIN_CONTACTS_DIR, exist_ok=True)

    tag_lines = "\n".join(f"  - {t}" for t in(["customer", f"channel:{args.channel}", "respondio"] + tags))

    content = f"""---
type: person
source: respondio
channel: {args.channel}
respondio_id: {args.contact_id}
tags:
{tag_lines}
---

# {name}

## Contact
- **Phone:** {phone}
- **Email:** {email}
- **Country:** {country}
- **Source:** Respond.io ({args.channel})
- **First seen:** {datetime.utcnow().isoformat()}Z
- **Custom fields:** {json.dumps(custom_fields)}
"""

    filepath = os.path.join(BRAIN_CONTACTS_DIR, f"{slug}.md")
    with open(filepath, "w") as f:
        f.write(content.lstrip("\n"))

    print(f"✅ Synced {name} → {filepath}")
    print(f"   Phone: {phone}, Channel: {args.channel}")

if __name__ == "__main__":
    main()
