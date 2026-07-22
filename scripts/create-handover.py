#!/usr/bin/env python3
"""
create-handover.py — Create a handover page from a won deal.

Creates a structured handover page in ~/brain/handovers/pending/ and
outputs a notification message for the project manager.

Usage:
    python3 create-handover.py \\
      --deal "deals/acme-foo" \\
      --customer "Acme Corp" \\
      --scope "Implementation of widget system" \\
      --po-number "PO-12345" \\
      --amount 15000 \\
      --currency USD \\
      --contact "John Doe <john@acme.com>"

Configure via env vars:
  BRAIN_DIR — brain root directory (default: ~/brain)
  HANDOVER_SALES_ROLE — who creates handovers (default: "CRM Manager")
  HANDOVER_PROJECT_ROLE — who processes handovers (default: "Project Manager")
  HANDOVER_NOTIFY_CHANNEL — where to notify (default: empty)
"""
import os, sys, json, argparse
from pathlib import Path
from datetime import datetime, timezone

BRAIN_DIR = Path(os.environ.get("BRAIN_DIR", str(Path.home() / "brain")))
HANDOVERS_DIR = BRAIN_DIR / "handovers"
PENDING_DIR = HANDOVERS_DIR / "pending"
COMPLETED_DIR = HANDOVERS_DIR / "completed"
SALES_ROLE = os.environ.get("HANDOVER_SALES_ROLE", "CRM Manager")
PROJECT_ROLE = os.environ.get("HANDOVER_PROJECT_ROLE", "Project Manager")
NOTIFY_CHANNEL = os.environ.get("HANDOVER_NOTIFY_CHANNEL", "")


def build_handover_page(
    deal_slug: str,
    customer: str,
    scope: str,
    po_number: str = "",
    amount: float = 0.0,
    currency: str = "USD",
    contact: str = "",
    end_client: str = "",
    owner: str = "",
    quote_ref: str = "",
    deal_stage: str = "Won",
    close_date: str = "",
) -> str:
    """Build a complete handover page markdown."""
    today = datetime.now(timezone.utc).strftime("%Y-%m-%d")
    close_date = close_date or today

    contact_name = contact
    contact_email = ""
    if "<" in contact:
        parts = contact.split("<")
        contact_name = parts[0].strip()
        contact_email = parts[1].rstrip(">").strip()

    return f"""---
title: "{customer} — {scope[:60]}"
type: handover
status: pending
source_deal: "{deal_slug}"
source: "{SALES_ROLE} — {owner or 'CRM'}"
created: {today}
handover_target: {PROJECT_ROLE}
gate: 0
gate_status: gated
---

# Project Handover: {customer} — {scope[:60]}

> **Handed over by:** {owner or SALES_ROLE} (via {SALES_ROLE})
> **Pick up by:** {PROJECT_ROLE}
> **Target:** {scope[:100]}

---

## Customer Information

| Field | Value |
|-------|-------|
| **Customer** | {customer} |
| **End Client** | {end_client or 'TBC'} |
| **Contact Person** | {contact_name} |
| **Contact Email** | {contact_email} |
| **Contact Phone** | TBC |

## Deal & PO Details

| Field | Value |
|-------|-------|
| **PO Number** | {po_number or 'TBC'} |
| **PO Amount** | {currency} {amount:,.2f} |
| **Currency** | {currency} |
| **Deal Stage** | {deal_stage} ✅ |
| **Close Date** | {close_date} |
| **Quote Reference** | {quote_ref or 'N/A'} |

## Scope of Work

{scope}

## Deliverables

- [ ] Deliverable 1 — TBC
- [ ] Deliverable 2 — TBC

## References

| Item | Path |
|------|------|
| Deal Page | `~/brain/{deal_slug}.md` |

## Next Steps for {PROJECT_ROLE}

- [ ] Acknowledge receipt of handover
- [ ] Review scope and contact customer
- [ ] Create project in `~/brain/projects/active_projects/`
- [ ] Progress gates (G0→G1→G2→G3)
- [ ] Move to `~/brain/handovers/completed/` when done
"""


def main():
    parser = argparse.ArgumentParser(description="Create a handover page from a won deal")
    parser.add_argument("--deal", required=True, help="Deal slug (e.g., 'deals/acme-foo')")
    parser.add_argument("--customer", required=True, help="Customer name")
    parser.add_argument("--scope", required=True, help="Scope of work description")
    parser.add_argument("--po-number", default="", help="Purchase order number")
    parser.add_argument("--amount", type=float, default=0.0, help="Deal amount")
    parser.add_argument("--currency", default="USD", help="Currency code")
    parser.add_argument("--contact", default="", help="Contact person and email")
    parser.add_argument("--end-client", default="", help="End client name")
    parser.add_argument("--owner", default="", help="Deal owner name")
    parser.add_argument("--quote-ref", default="", help="Quote reference")
    parser.add_argument("--dry-run", action="store_true", help="Print handover page to stdout without writing")

    args = parser.parse_args()

    # Extract slug from deal path
    deal_slug = args.deal.replace(".md", "").strip("/")
    # Create handover filename from deal slug
    filename = deal_slug.replace("deals/", "") + "-handover.md"
    filepath = PENDING_DIR / filename

    content = build_handover_page(
        deal_slug=deal_slug,
        customer=args.customer,
        scope=args.scope,
        po_number=args.po_number,
        amount=args.amount,
        currency=args.currency,
        contact=args.contact,
        end_client=args.end_client,
        owner=args.owner,
        quote_ref=args.quote_ref,
    )

    if args.dry_run:
        print(content)
        return

    # Write handover page
    PENDING_DIR.mkdir(parents=True, exist_ok=True)
    filepath.write_text(content, encoding="utf-8")
    os.chmod(filepath, 0o664)

    # Output notification
    notification = {
        "action": "handover_created",
        "handover_file": str(filepath),
        "deal": deal_slug,
        "customer": args.customer,
        "scope": args.scope[:80],
        "notify_channel": NOTIFY_CHANNEL,
        "message": (
            f"📋 *New handover ready for {PROJECT_ROLE}*\n"
            f"*Customer:* {args.customer}\n"
            f"*Deal:* {deal_slug}\n"
            f"*Scope:* {args.scope[:80]}...\n"
            f"*PO:* {args.po_number or 'TBC'} — {args.currency} {args.amount:,.2f}\n"
            f"\\n"
            f"Run `process-handover.py --review {deal_slug}` to review."
        ),
    }

    print(json.dumps(notification, indent=2))
    print(f"\n✅ Handover created: {filepath}", file=sys.stderr)
    print(f"📋 Handover ready for {PROJECT_ROLE} to process.", file=sys.stderr)


if __name__ == "__main__":
    main()