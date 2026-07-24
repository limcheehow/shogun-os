#!/usr/bin/env python3
"""Create brain channel pages from CC config."""

import argparse, json, os, sys, yaml

def main():
    parser = argparse.ArgumentParser(description="Create brain pages for channels")
    parser.add_argument("--config", required=True, help="Path to Kizuna config.yaml")
    args = parser.parse_args()

    if not os.path.exists(args.config):
        print(f"❌ Config not found: {args.config}")
        sys.exit(1)

    with open(args.config) as f:
        # Parse YAML (first extract the customer_communication section)
        # For simplicity, we accept a standalone JSON/yaml file too
        content = f.read()
        config = yaml.safe_load(content)

    cc = config.get("customer_communication", {})
    if not cc.get("enabled"):
        print("⚠️  Customer communication not enabled. Skipping.")
        return

    platform = cc.get("platform", "unknown")
    channels = cc.get("channels", [])
    assignment = cc.get("assignment_model", "hermes-first")

    brain_dir = os.path.expanduser("~/brain/channels")
    os.makedirs(brain_dir, exist_ok=True)

    channel_names = {
        "ig": "Instagram DM",
        "fb": "Facebook Messenger",
        "wa": "WhatsApp Business",
        "web": "Website Chat Widget",
        "line": "LINE",
        "email": "Email",
        "tg": "Telegram",
    }

    for ch in channels:
        ch_name = channel_names.get(ch, ch.upper())
        slug = ch
        platform_label = {"respondio": "Respond.io", "chatwoot": "Chatwoot"}.get(platform, "Unknown")

        content = f"""---
type: channel
platform: {platform}
channel_id: {slug}
name: {ch_name}
tags: [customer-communication, {slug}]
---

# {ch_name}

**Platform:** {platform_label}
**Status:** Active
**Assigned to:** Kizuna (CRM)

## Routing

- **Assignment model:** {assignment}
- **Role:** Customer inquiries, support, lead qualification
- **Escalation:** When Hermes can't resolve or customer asks for human

## Connected Since

{platform_label} onboarding via Shogun OS Kizuna wizard.

## Usage Notes

- All inbound messages come through {platform_label} and are forwarded to Kizuna (Hermes CRM agent).
- Replies go back through {platform_label} to the customer.
- Conversation history is mirrored to brain.
"""
        fpath = os.path.join(brain_dir, f"{slug}.md")
        with open(fpath, "w") as f:
            f.write(content.lstrip("\n"))
        print(f"✅ Created brain page: {fpath}")

    # Create inbox summary page
    inbox_content = f"""---
type: inbox
platform: {platform}
tags: [customer-communication, kizuna]
---

# Kizuna Inbox — {platform_label}

## Active Channels

"""
    for ch in channels:
        ch_name = channel_names.get(ch, ch.upper())
        inbox_content += f"- **{ch_name}** → `channels/{ch}.md`\n"

    inbox_content += f"""
## Agent Assignment

- **Model:** {assignment}
- **Human agents:** See `people/` directory (tagged `kizuna`)

## SLA Targets

- First response: < 5 min (auto), < 30 min (human)
- Resolution: < 4 hours (standard), < 24 hours (complex)

## Configuration

- Platform config: `~/.hermes/profiles/kizuna/config.yaml`
- Bridge skill: `~/.hermes/profiles/kizuna/skills/cc-bridge`
"""

    inbox_path = os.path.join(brain_dir, "inbox.md")
    with open(inbox_path, "w") as f:
        f.write(inbox_content.lstrip("\n"))
    print(f"✅ Created inbox summary: {inbox_path}")

    print(f"\n=== Channel Pages Created ===")
    print(f"  Total channels: {len(channels)}")
    print(f"  Location: {brain_dir}/")

if __name__ == "__main__":
    main()
