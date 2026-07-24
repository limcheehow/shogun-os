#!/usr/bin/env python3
"""Create Chatwoot inboxes for each channel via Chatwoot API."""

import argparse, json, os, sys, time
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

CHANNEL_TYPES = {
    "web":  "Website",
    "wa":   "WhatsApp",
    "fb":   "Facebook",
    "ig":   "Instagram",
    "email": "Email",
    "line": "Line",
}

def main():
    parser = argparse.ArgumentParser(description="Create Chatwoot inboxes")
    parser.add_argument("--api-url", required=True)
    parser.add_argument("--access-token", required=True)
    parser.add_argument("--channels", default="web,wa,fb,ig",
                        help="Comma-separated channel list (default: web,wa,fb,ig)")
    args = parser.parse_args()

    channels = [c.strip() for c in args.channels.split(",") if c.strip()]
    results = []

    for ch in channels:
        ch_type = CHANNEL_TYPES.get(ch, ch)
        name = f"Kizuna - {ch_type}"
        print(f"→ Creating inbox '{name}' ({ch_type})...", end=" ", flush=True)

        status, data = api_call(args.api_url, args.access_token, "POST",
                                f"inboxes",
                                {"name": name, "channel": {"type": ch_type}})

        if status in (200, 201):
            inbox_id = data.get("id", "?")
            print(f"✅ ID {inbox_id}")
            results.append({"channel": ch, "type": ch_type, "id": inbox_id, "name": name})
        else:
            print(f"❌ {data.get('error', data)}")
            results.append({"channel": ch, "type": ch_type, "error": data.get("error", str(data))})

    print("\n=== Summary ===")
    for r in results:
        status = f"✅ inbox #{r['id']}" if "id" in r else f"❌ {r.get('error','failed')}"
        print(f"  {r['channel']:6s} ({r['type']:12s}): {status}")

    # Output JSON for piping into config writing
    print(f"\n--- Config Block ---")
    print(json.dumps({"inboxes": [r for r in results if "id" in r]}, indent=2))

if __name__ == "__main__":
    main()
