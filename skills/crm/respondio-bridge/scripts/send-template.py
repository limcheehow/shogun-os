#!/usr/bin/env python3
"""Send a template reply from brain to a Respond.io conversation."""

import argparse, json, os, sys, re
import urllib.request, urllib.error
import yaml

RESPONDIO_API = "https://api.respond.io/v2"
TEMPLATES_DIR = os.path.expanduser("~/brain/templates")

def api_post(api_key, path, data):
    url = f"{RESPONDIO_API}/{path.lstrip('/')}"
    body = json.dumps(data).encode()
    req = urllib.request.Request(url, data=body,
        headers={"X-API-Key": api_key, "Content-Type": "application/json"},
        method="POST")
    with urllib.request.urlopen(req, timeout=15) as resp:
        return json.loads(resp.read())

def find_template(name):
    """Find template by name in brain templates directory."""
    if not os.path.isdir(TEMPLATES_DIR):
        return None

    for fname in os.listdir(TEMPLATES_DIR):
        if not fname.endswith(".md"):
            continue
        fpath = os.path.join(TEMPLATES_DIR, fname)
        with open(fpath) as f:
            content = f.read()

        # Parse frontmatter
        m = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
        if not m:
            continue
        try:
            frontmatter = yaml.safe_load(m.group(1))
        except:
            continue

        if frontmatter.get("name") == name:
            # Extract body (everything after frontmatter, skipping the title line)
            body = m.group(2)
            # Strip title if present
            body = re.sub(r"^# .+\n", "", body)
            return frontmatter, body.strip()

    return None

def render_template(template_body, variables):
    """Replace {{variables}} in template body."""
    result = template_body
    for key, val in variables.items():
        result = result.replace("{{" + key + "}}", val)
    return result

def main():
    parser = argparse.ArgumentParser(description="Send template reply via Respond.io")
    parser.add_argument("--api-key", required=True)
    parser.add_argument("--name", required=True, help="Template name")
    parser.add_argument("--conversation", required=True, help="Conversation ID")
    parser.add_argument("--contact-name", default="there", help="Customer name")
    args = parser.parse_args()

    # Find the template
    template = find_template(args.name)
    if not template:
        print(f"❌ Template '{args.name}' not found in {TEMPLATES_DIR}")
        sys.exit(1)

    frontmatter, body = template
    print(f"✓ Found template: {args.name}")

    # Render variables
    variables = {
        "contact_name": args.contact_name,
        "contact_name:upper": args.contact_name.upper(),
        "company": os.environ.get("COMPANY_NAME", "our company"),
    }
    rendered = render_template(body, variables)
    print(f"✓ Rendered ({len(rendered)} chars): {rendered[:100]}...")

    # Send via API
    try:
        result = api_post(args.api_key, "messages", {
            "conversation_id": args.conversation,
            "type": "text",
            "text": rendered,
        })
        print(f"✅ Sent! Message ID: {result.get('data', {}).get('id', '?')}")
    except Exception as e:
        print(f"❌ Failed to send: {e}")
        sys.exit(1)

if __name__ == "__main__":
    main()
