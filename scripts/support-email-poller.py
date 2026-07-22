#!/usr/bin/env python3
"""
Support Email Poller — polls a Gmail mailbox for support-labelled emails,
creates/updates support tickets in the brain, and notifies Slack.

Schedule: Mon–Fri, hourly 9am–6pm via Hermes cron
Gmail: Service account with domain-wide delegation

v2 — Customer Reply Detection
  Tracks individual message IDs, detects new messages in known threads,
  calls the customer-reply API endpoint for Slack notification + timeline.

Configure via env vars (see .env.example):
  GMAIL_USER              — Gmail mailbox to poll
  SERVICE_ACCOUNT_FILE    — path to Google service account key
  SUPPORT_LABEL_ID        — Gmail label ID for support emails
  DASHBOARD_BASE_URL      — base URL for customer-reply API
  SLACK_BOT_TOKEN         — Slack bot token for notifications
  SUPPORT_SLACK_CHANNEL   — Slack channel for alerts
  SUPPORT_ASSIGNEE_HANDLE — default assignee display name
  SUPPORT_ASSIGNEE_ID     — default assignee Slack ID
  INTERNAL_DOMAINS        — comma-separated list of internal email domains
  BRAIN_DIR               — brain root directory (default: ~/brain)
  TICKETS_DIR             — support tickets directory (default: BRAIN_DIR/projects/support_tickets/tickets)
  HERMES_SCRIPTS_DIR      — path to Hermes scripts directory
"""
import os
import re
import json
import base64
import logging
import datetime
import urllib.request
import urllib.parse
import urllib.error
from pathlib import Path
from email.utils import parseaddr, parsedate_to_datetime

from google.oauth2 import service_account
from googleapiclient.discovery import build

# ─── Config ──────────────────────────────────────────────────────────────

BRAIN_DIR = Path(os.environ.get("BRAIN_DIR", str(Path.home() / "brain")))
TICKETS_DIR = Path(os.environ.get(
    "TICKETS_DIR",
    str(BRAIN_DIR / "projects/support_tickets/tickets")
))
CUSTOMERS_DIR = Path(os.environ.get(
    "CUSTOMERS_DIR",
    str(BRAIN_DIR / "projects/support_tickets/customers")
))
INDEX_FILE = Path(os.environ.get(
    "TICKET_INDEX_FILE",
    str(BRAIN_DIR / "projects/support_tickets/INDEX.md")
))
CUST_INDEX = Path(os.environ.get(
    "CUSTOMER_INDEX_FILE",
    str(BRAIN_DIR / "projects/support_tickets/customers/INDEX.md")
))
STATE_FILE = Path(os.environ.get(
    "PROCESSED_STATE_FILE",
    str(BRAIN_DIR / "projects/support_tickets/.processed_emails.json")
))

SERVICE_ACCOUNT_FILE = os.environ.get(
    "SERVICE_ACCOUNT_FILE",
    os.path.expanduser("~/.hermes/service-account-key.json")
)
GMAIL_USER = os.environ.get("GMAIL_USER", "support@example.com")
GMAIL_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]
SUPPORT_LABEL = os.environ.get("SUPPORT_LABEL_ID", "")

DASHBOARD_BASE = os.environ.get("DASHBOARD_BASE_URL", "http://127.0.0.1:3001")

SLACK_TOKEN     = os.environ.get("SLACK_BOT_TOKEN", "")
SLACK_CHANNEL   = os.environ.get("SUPPORT_SLACK_CHANNEL", "")
ASSIGNEE_HANDLE = os.environ.get("SUPPORT_ASSIGNEE_HANDLE", "@support")
ASSIGNEE_ID     = os.environ.get("SUPPORT_ASSIGNEE_ID", "")

# Internal domains — replies from these addresses are NOT customer replies
_raw_internal = os.environ.get("INTERNAL_DOMAINS", "example.com")
INTERNAL_DOMAINS = set(d.strip() for d in _raw_internal.split(",") if d.strip())

MAX_STATE_ENTRIES = 500

logging.basicConfig(
    level=logging.INFO,
    format="[%(asctime)s] %(levelname)s %(message)s",
    datefmt="%Y-%m-%d %H:%M:%S",
)
log = logging.getLogger(__name__)


# ─── Gmail Auth ──────────────────────────────────────────────────────────

def get_gmail_service():
    if not os.path.exists(SERVICE_ACCOUNT_FILE):
        raise FileNotFoundError(f"Service account key not found: {SERVICE_ACCOUNT_FILE}")
    creds = service_account.Credentials.from_service_account_file(
        SERVICE_ACCOUNT_FILE, scopes=GMAIL_SCOPES
    )
    delegated = creds.with_subject(GMAIL_USER)
    return build("gmail", "v1", credentials=delegated)


# ─── State ───────────────────────────────────────────────────────────────

def load_state() -> tuple[set, dict, bool]:
    if STATE_FILE.exists():
        data = json.loads(STATE_FILE.read_text(encoding="utf-8"))
        thread_ids = set(data.get("processed_thread_ids", []))
        msg_lookup = {}
        needs_migration = False
        raw_entries = data.get("processed_msg_ids")
        if raw_entries:
            for entry in raw_entries:
                if isinstance(entry, dict) and "thread_id" in entry and "msg_ids" in entry:
                    msg_lookup[entry["thread_id"]] = set(entry["msg_ids"])
        else:
            needs_migration = True if thread_ids else False
            log.info("Legacy state detected — %d threads need message ID migration", len(thread_ids))
        return thread_ids, msg_lookup, needs_migration
    return set(), {}, False


def save_state(processed_ids: set, msg_lookup: dict):
    tid_list = list(processed_ids)[-MAX_STATE_ENTRIES:]
    msg_entries = []
    for tid in tid_list:
        if tid in msg_lookup and msg_lookup[tid]:
            ids = list(msg_lookup[tid])[-MAX_STATE_ENTRIES:]
            msg_entries.append({"thread_id": tid, "msg_ids": ids})
    STATE_FILE.write_text(
        json.dumps({"processed_thread_ids": tid_list, "processed_msg_ids": msg_entries}, indent=2),
        encoding="utf-8"
    )


# ─── Email Parsing ───────────────────────────────────────────────────────

def get_header(headers: list, name: str) -> str:
    for h in headers:
        if h["name"].lower() == name.lower():
            return h["value"]
    return ""


def decode_body(payload: dict) -> str:
    if payload.get("mimeType") == "text/plain":
        data = payload.get("body", {}).get("data", "")
        return base64.urlsafe_b64decode(data + "==").decode("utf-8", errors="replace") if data else ""
    for part in payload.get("parts", []):
        text = decode_body(part)
        if text:
            return text
    return ""


def infer_customer(email_addr: str, sender_name: str) -> tuple[str, str]:
    domain = email_addr.split("@")[-1].split(".")[0]
    name = re.sub(r"[-_]", " ", domain).title()
    slug = re.sub(r"[^a-z0-9]+", "-", domain.lower()).strip("-")
    return name, slug


def classify_priority(subject: str, body: str) -> str:
    text = (subject + " " + body).lower()
    if any(k in text for k in ["system down", "all cameras offline", "complete outage", "data loss"]):
        return "P1 Critical"
    if any(k in text for k in ["urgent", "down", "offline", "not working", "critical", "production"]):
        return "P2 High"
    return "P3 Medium"


def classify_category(subject: str, body: str) -> str:
    text = (subject + " " + body).lower()
    if any(k in text for k in ["camera", "device", "hardware", "nvr", "dvr"]):
        return "Hardware"
    if any(k in text for k in ["software", "app", "dashboard", "login", "portal"]):
        return "Software"
    if any(k in text for k in ["network", "connection", "offline", "ping", "vpn"]):
        return "Network"
    if any(k in text for k in ["config", "configuration", "setting"]):
        return "Configuration"
    if any(k in text for k in ["slow", "performance", "lag"]):
        return "Performance"
    if any(k in text for k in ["access", "permission", "password"]):
        return "Access"
    return "Other"


def sla_deadline(priority: str, opened: datetime.datetime) -> str:
    if "P1" in priority:
        delta = datetime.timedelta(hours=4)
    elif "P2" in priority:
        delta = datetime.timedelta(hours=8)
    elif "P3" in priority:
        delta = datetime.timedelta(days=2)
    else:
        delta = datetime.timedelta(days=5)
    return (opened + delta).strftime("%Y-%m-%d %H:%M")


# ─── Ticket ID ───────────────────────────────────────────────────────────

def next_ticket_id() -> str:
    year = datetime.datetime.now().year
    max_n = 0
    if INDEX_FILE.exists():
        for match in re.finditer(r"TS-(\d{4})-(\d{3})", INDEX_FILE.read_text(encoding="utf-8")):
            yr = int(match.group(1))
            n = int(match.group(2))
            max_n = max(max_n, n)
    return f"TS-{year}-{max_n + 1:03d}"


# ─── Duplicate Detection ─────────────────────────────────────────────────

def find_existing_ticket(customer_slug: str, subject: str) -> str | None:
    if not INDEX_FILE.exists():
        return None
    keywords = set(re.findall(r"\b\w{4,}\b", subject.lower()))
    for f in TICKETS_DIR.glob("TS-*.md"):
        content = f.read_text(encoding="utf-8")
        if f"customer_slug:  {customer_slug}" not in content and customer_slug not in content:
            continue
        if "status:         Open" not in content and "status: Open" not in content:
            continue
        title_match = re.search(r"title:\s+(.+?)[\r\n]", content)
        if title_match:
            title_words = set(re.findall(r"\b\w{4,}\b", title_match.group(1).lower()))
            if len(keywords & title_words) >= 2:
                tid = re.search(r"TS-\d{4}-\d{3}", f.name)
                return tid.group() if tid else None
    return None


# ─── Ticket File Ops ─────────────────────────────────────────────────────

def append_to_ticket(ticket_id: str, sender_name: str, sender_email: str,
                     subject: str, body_summary: str, received: str):
    fpath = TICKETS_DIR / f"{ticket_id}.md"
    if not fpath.exists():
        return
    entry = (f"| {received} | New email from {sender_name} <{sender_email}>: "
             f"\"{subject}\" — {body_summary[:200]} | auto |")
    content = fpath.read_text(encoding="utf-8")
    content = re.sub(r"(last_updated:\s+)\S+", f"\\g<1>{datetime.date.today()}", content)
    content += f"\n{entry}\n"
    fpath.write_text(content, encoding="utf-8")
    log.info("Grouped email into %s", ticket_id)


def create_ticket(ticket_id: str, customer_name: str, customer_slug: str,
                  sender_name: str, sender_email: str, subject: str,
                  body_summary: str, received: str, priority: str,
                  category: str, target_resolve: str, gmail_thread_id: str = ""):
    TICKETS_DIR.mkdir(parents=True, exist_ok=True)
    support_email = os.environ.get("SUPPORT_EMAIL", "support@example.com")
    content = f"""# Support Ticket: {ticket_id}
title:          {subject}
customer:       {customer_name}
customer_slug:  {customer_slug}
linked_project: None
reporter:       {sender_name} <{sender_email}>
opened:         {received}
target_resolve: {target_resolve}
priority:       {priority}
category:       {category}
tier:           L1
assigned_to:    {ASSIGNEE_HANDLE}
status:         Open
last_updated:   {datetime.date.today()}
source:         email
gmail_thread_id: {gmail_thread_id}

---

## Description
{body_summary}

---

## Steps to Reproduce / Context
Received via email to {support_email} on {received}.

---

## Timeline
| Date & Time | Action | By |
|-------------|--------|----|
| {received} | Ticket opened from inbound email. Assigned to {ASSIGNEE_HANDLE} (L1). | auto |

---

## Resolution Notes


---

## Closure
resolved_by:
resolved_date:
root_cause:
preventive:
status:        Open
"""
    (TICKETS_DIR / f"{ticket_id}.md").write_text(content, encoding="utf-8")
    log.info("Created ticket %s with gmail_thread_id=%s", ticket_id, gmail_thread_id)


def update_index(ticket_id: str, customer_name: str, subject: str,
                 priority: str, received: str):
    if not INDEX_FILE.exists():
        return
    content = INDEX_FILE.read_text(encoding="utf-8")
    content = re.sub(
        r"(open_count:\s*)(\d+)",
        lambda m: m.group(1) + str(int(m.group(2)) + 1),
        content
    )
    content = re.sub(
        r"(total_count:\s*)(\d+)",
        lambda m: m.group(1) + str(int(m.group(2)) + 1),
        content
    )
    content = re.sub(r"(last_updated:\s*)\S+", f"\\g<1>{datetime.date.today()}", content)
    new_row = f"| {ticket_id} | {customer_name} | {subject} | {priority} | {ASSIGNEE_HANDLE} | Open | {received} |"
    content += f"\n{new_row}\n"
    INDEX_FILE.write_text(content, encoding="utf-8")


def update_customer(customer_name: str, customer_slug: str,
                    sender_name: str, sender_email: str,
                    ticket_id: str, subject: str, priority: str, received: str):
    CUSTOMERS_DIR.mkdir(parents=True, exist_ok=True)
    cfile = CUSTOMERS_DIR / f"{customer_slug}.md"
    new_row = f"| {ticket_id} | {subject} | {priority} | {ASSIGNEE_HANDLE} | Open | {received} |"
    if cfile.exists():
        content = cfile.read_text(encoding="utf-8")
        content = re.sub(r"(last_updated:\s*)\S+", f"\\g<1>{datetime.date.today()}", content)
        content += f"\n{new_row}\n"
        cfile.write_text(content, encoding="utf-8")
    else:
        pm_handle = os.environ.get("SUPPORT_PM_HANDLE", "@pm")
        content = f"""# Customer: {customer_name}
slug:           {customer_slug}
linked_project: None
primary_contact: {sender_name}, {sender_email}
pm:             {pm_handle}
support_owner:  {ASSIGNEE_HANDLE}
created:        {datetime.date.today()}
last_updated:   {datetime.date.today()}

---

## Customer Summary
Customer identified from inbound support email. Details to be confirmed.

---

## Open Tickets

| Ticket ID | Title | Priority | Assigned | Status | Opened |
|-----------|-------|----------|----------|--------|--------|
{new_row}

---

## Resolved Tickets

| Ticket ID | Title | Priority | Resolved By | Closed Date |
|-----------|-------|----------|-------------|-------------|

---

## Notes
"""
        cfile.write_text(content, encoding="utf-8")


# ─── Slack ───────────────────────────────────────────────────────────────

def notify_slack(message: str):
    if not SLACK_TOKEN:
        log.warning("No SLACK_BOT_TOKEN set — skipping Slack notification")
        return
    import subprocess
    try:
        subprocess.run([
            "curl", "-s", "-X", "POST", "https://slack.com/api/chat.postMessage",
            "-H", f"Authorization: Bearer {SLACK_TOKEN}",
            "-H", "Content-Type: application/json",
            "-d", json.dumps({"channel": SLACK_CHANNEL, "text": message, "mrkdwn": True})
        ], timeout=10, capture_output=True)
    except Exception as e:
        log.error("Slack notification failed: %s", e)


# ─── Customer Reply Detection ────────────────────────────────────────────

def is_internal_sender(sender_email: str) -> bool:
    domain = sender_email.split("@")[-1].lower() if "@" in sender_email else ""
    return domain in INTERNAL_DOMAINS


def call_customer_reply_api(thread_id: str, sender_name: str, sender_email: str,
                            subject: str, body: str, message_id: str) -> bool:
    url = f"{DASHBOARD_BASE}/api/support/tickets/customer-reply"
    payload = json.dumps({
        "threadId": thread_id,
        "from": f"{sender_name} <{sender_email}>",
        "subject": subject,
        "body": body[:2000],
        "messageId": message_id,
    }).encode("utf-8")

    try:
        req = urllib.request.Request(url, data=payload,
            headers={"Content-Type": "application/json"},
            method="POST")
        with urllib.request.urlopen(req, timeout=15) as resp:
            result = json.loads(resp.read().decode("utf-8"))
            if result.get("success"):
                log.info("Customer reply notified for thread %s → ticket %s (reopened=%s)",
                         thread_id, result.get("ticketId"), result.get("reopened"))
                return True
            else:
                log.warning("Customer reply API returned error: %s", result.get("error"))
                return False
    except urllib.error.HTTPError as e:
        body_text = e.read().decode("utf-8", errors="replace")[:200]
        if e.code == 404:
            log.info("No ticket found for thread %s — skipping reply notification", thread_id)
        else:
            log.warning("Customer reply API HTTP %d: %s", e.code, body_text)
        return False
    except Exception as e:
        log.warning("Customer reply API call failed: %s", e)
        return False


# ─── Main ────────────────────────────────────────────────────────────────

def main():
    log.info("Support email poller starting...")

    if not SUPPORT_LABEL:
        log.error("SUPPORT_LABEL_ID not set — cannot poll")
        return

    processed_threads, msg_lookup, needs_migration = load_state()
    log.info("%d thread IDs already processed.", len(processed_threads))

    service = get_gmail_service()

    result = service.users().messages().list(
        userId="me", labelIds=[SUPPORT_LABEL], maxResults=50
    ).execute()
    messages = result.get("messages", [])

    seen_threads = set()
    new_threads = []
    known_reply_threads = []

    for msg in messages:
        tid = msg["threadId"]
        mid = msg["id"]
        if tid not in seen_threads:
            seen_threads.add(tid)
            if tid not in processed_threads:
                new_threads.append(tid)
            else:
                known_ids = msg_lookup.get(tid, set())
                if mid not in known_ids:
                    known_reply_threads.append((tid, mid))

    if new_threads:
        log.info("%d new thread(s) to process.", len(new_threads))
    else:
        log.info("No new threads to process.")

    for thread_id in new_threads:
        try:
            thread = service.users().threads().get(
                userId="me", id=thread_id, format="full"
            ).execute()
            first_msg = thread["messages"][0]
            headers = first_msg["payload"]["headers"]

            from_raw = get_header(headers, "From")
            sender_name, sender_email = parseaddr(from_raw)
            subject = re.sub(r"^(Re:|Fwd?:)\s*", "", get_header(headers, "Subject"), flags=re.IGNORECASE).strip()
            date_raw = get_header(headers, "Date")

            try:
                received_dt = parsedate_to_datetime(date_raw)
                received_str = received_dt.strftime("%Y-%m-%d %H:%M")
            except Exception:
                received_str = datetime.datetime.now().strftime("%Y-%m-%d %H:%M")
                received_dt = datetime.datetime.now()

            body = decode_body(first_msg["payload"])
            body_summary = body[:600].replace("\n", " ").strip()

            customer_name, customer_slug = infer_customer(sender_email, sender_name)
            priority = classify_priority(subject, body)
            category = classify_category(subject, body)
            target = sla_deadline(priority, received_dt)

            existing = find_existing_ticket(customer_slug, subject)

            if existing:
                append_to_ticket(existing, sender_name, sender_email, subject, body_summary, received_str)
                notify_slack(
                    f"📧 *Email grouped into existing ticket*\n"
                    f"*Ticket:* {existing} — {subject}\n"
                    f"*From:* {sender_name} <{sender_email}>\n"
                    f"New email added to timeline. <@{ASSIGNEE_ID}> please review."
                )
            else:
                ticket_id = next_ticket_id()
                create_ticket(ticket_id, customer_name, customer_slug,
                              sender_name, sender_email, subject,
                              body_summary, received_str, priority, category, target,
                              gmail_thread_id=thread_id)
                update_index(ticket_id, customer_name, subject, priority, received_str)
                update_customer(customer_name, customer_slug, sender_name, sender_email,
                                ticket_id, subject, priority, received_str)
                notify_slack(
                    f"🎫 *New support ticket from email*\n"
                    f"*Ticket:* {ticket_id} — {subject}\n"
                    f"*Customer:* {customer_name}\n"
                    f"*From:* {sender_name} <{sender_email}>\n"
                    f"*Priority:* {priority} | *Category:* {category}\n"
                    f"*SLA deadline:* {target}\n"
                    f"Assigned to <@{ASSIGNEE_ID}>. Reply `/ticket update {ticket_id}` to add notes."
                )

            msg_ids = {m["id"] for m in thread["messages"]}
            msg_lookup[thread_id] = msg_ids
            processed_threads.add(thread_id)

        except Exception as e:
            log.error("Error processing thread %s: %s", thread_id, e)
            processed_threads.add(thread_id)

    if needs_migration:
        unpopulated = [tid for tid in processed_threads if tid not in msg_lookup or not msg_lookup[tid]]
        if unpopulated:
            log.info("Cold-start migration: fetching message IDs for %d known threads...", len(unpopulated))
            migrated_count = 0
            for thread_id in unpopulated:
                try:
                    thread = service.users().threads().get(
                        userId="me", id=thread_id, format="minimal"
                    ).execute()
                    msg_ids = {m["id"] for m in thread["messages"]}
                    msg_lookup[thread_id] = msg_ids
                    migrated_count += 1
                    if migrated_count % 10 == 0:
                        log.info("Migration progress: %d/%d threads", migrated_count, len(unpopulated))
                except Exception as e:
                    log.warning("Migration: could not fetch thread %s: %s", thread_id, e)
                    msg_lookup[thread_id] = set()
            log.info("Migration complete. %d threads processed.", migrated_count)
            save_state(processed_threads, msg_lookup)

    if known_reply_threads:
        log.info("%d known thread(s) with new message(s) to check for customer replies.", len(known_reply_threads))
    else:
        log.info("No new messages in known threads.")

    for thread_id, new_msg_id in known_reply_threads:
        try:
            thread = service.users().threads().get(
                userId="me", id=thread_id, format="full"
            ).execute()

            target_msg = None
            for m in thread["messages"]:
                if m["id"] == new_msg_id:
                    target_msg = m
                    break

            if not target_msg:
                log.warning("Could not find message %s in thread %s", new_msg_id, thread_id)
                msg_lookup.setdefault(thread_id, set()).add(new_msg_id)
                continue

            headers = target_msg["payload"]["headers"]
            from_raw = get_header(headers, "From")
            sender_name, sender_email = parseaddr(from_raw)

            if is_internal_sender(sender_email):
                log.info("Skipping internal sender %s on thread %s", sender_email, thread_id)
                msg_lookup.setdefault(thread_id, set()).add(new_msg_id)
                continue

            subject = get_header(headers, "Subject")
            body = decode_body(target_msg["payload"])

            log.info("Customer reply detected — thread %s from %s <%s>",
                     thread_id, sender_name, sender_email)

            success = call_customer_reply_api(
                thread_id=thread_id,
                sender_name=sender_name,
                sender_email=sender_email,
                subject=subject,
                body=body,
                message_id=new_msg_id,
            )

            msg_lookup.setdefault(thread_id, set()).add(new_msg_id)
            processed_threads.add(thread_id)

            if not success:
                body_preview = body[:200].replace("\n", " ").strip()
                notify_slack(
                    f"⚠️ *Customer reply detected (API unavailable)*\n"
                    f"*Thread:* {thread_id}\n"
                    f"*From:* {sender_name} <{sender_email}>\n"
                    f"*Reply:* \"{body_preview}\"\n"
                    f"Dashboard API was unreachable — check the ticket manually."
                )

        except Exception as e:
            log.error("Error processing reply on thread %s: %s", thread_id, e)
            msg_lookup.setdefault(thread_id, set()).add(new_msg_id)

    save_state(processed_threads, msg_lookup)
    total_new = len(new_threads) + len(known_reply_threads)
    log.info("Done. Processed %d new thread(s) + %d reply(ies).",
             len(new_threads), len(known_reply_threads))


if __name__ == "__main__":
    main()