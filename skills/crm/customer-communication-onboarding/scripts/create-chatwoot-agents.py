#!/usr/bin/env python3
"""Create Chatwoot agent accounts from brain people pages."""

import argparse, json, os, sys, re
import urllib.request, urllib.error

def api_call(base, token, method, path, data=None):
    url = f"{base.rstrip('/')}/api/v1/{path.lstrip('/')}"
    headers = {
        "api_access_token": token,
        "Content-Type": "application/json",
    }
    body = json.dumps(data).encode() if data else None
    req = urllib.request.Request(url, data=body, headers=headers, method=method)
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.status, json.loads(resp.read())
    except urllib.error.HTTPError as e:
        return e.code, json.loads(e.read()) if e.read() else {"error": str(e)}

BRAIN_PEOPLE_DIR = os.path.expanduser("~/brain/people")

def parse_brain_person(filepath):
    """Extract name, email, and tags from a brain people page."""
    slug = os.path.splitext(os.path.basename(filepath))[0]
    name = slug.replace("-", " ").title()
    email = ""
    tags = []
    with open(filepath) as f:
        for line in f:
            m = re.match(r"^\s*email:\s*(.+)$", line, re.I)
            if m: email = m.group(1).strip()
            m = re.match(r"^\s*-\s*(.+)$", line)
            if m: tags.append(m.group(1).strip())
            # Frontmatter tags
            m = re.match(r"^tags:\s*\[?(.+?)\]?\s*$", line)
            if m:
                raw = m.group(1)
                tags.extend([t.strip().strip("'\"") for t in raw.split(",")])
    return {"slug": slug, "name": name, "email": email, "tags": tags}

def main():
    parser = argparse.ArgumentParser(description="Sync brain people → Chatwoot agents")
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--access-token", required=True)
    parser.add_argument("--agents-file", default=BRAIN_PEOPLE_DIR,
                        help=f"Directory of brain people pages (default: {BRAIN_PEOPLE_DIR})")
    args = parser.parse_args()

    if not os.path.isdir(args.agents_file):
        print(f"❌ Directory not found: {args.agents_file}")
        sys.exit(1)

    people = []
    for fname in sorted(os.listdir(args.agents_file)):
        fpath = os.path.join(args.agents_file, fname)
        if fname.endswith(".md"):
            person = parse_brain_person(fpath)
            if "kizuna" in person["tags"] or "crm" in person["tags"] or "sales" in person["tags"]:
                people.append(person)

    if not people:
        print("⚠️  No brain people tagged 'kizuna', 'crm', or 'sales' found.")
        print("   Creating agents from all brain people instead...")
        for fname in sorted(os.listdir(args.agents_file)):
            fpath = os.path.join(args.agents_file, fname)
            if fname.endswith(".md"):
                people.append(parse_brain_person(fpath))

    results = []
    for p in people:
        if not p["email"]:
            print(f"⚠️  Skipping {p['name']}: no email in brain page")
            results.append({**p, "status": "skipped", "reason": "no email"})
            continue

        print(f"→ Creating agent {p['name']} ({p['email']})...", end=" ", flush=True)
        status, data = api_call(args.api_url, args.access_token, "POST",
                                "platform_accounts/create_agent",
                                {"name": p["name"], "email": p["email"], "role": "agent"})

        if status in (200, 201):
            print(f"✅ ID {data.get('id', '?')}")
            results.append({**p, "status": "created", "chatwoot_id": data.get("id")})
        else:
            print(f"❌ {data.get('error', data)}")
            results.append({**p, "status": "failed", "error": data.get("error")})

    print(f"\n=== Summary ===")
    created = [r for r in results if r.get("status") == "created"]
    skipped = [r for r in results if r.get("status") == "skipped"]
    failed  = [r for r in results if r.get("status") == "failed"]
    print(f"  Created: {len(created)}")
    print(f"  Skipped: {len(skipped)}")
    print(f"  Failed:  {len(failed)}")

if __name__ == "__main__":
    main()
