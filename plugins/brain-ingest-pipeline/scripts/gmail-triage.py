#!/usr/bin/env python3
"""
Gmail triage: label Primary inbox, mark promotions read, categorize remainder.
Uses SA-DWD — one service account, all 9 team members via domain-wide delegation.
Batch rotation: 3 accounts per run (state file tracks position) to avoid memory spike.

Usage:
  --dry-run         Preview only (for current batch)
  --summary         Priority summary for all accounts
  --alert           Check for urgent emails across all accounts
  --batch N         Override batch number (0, 1, 2)
  (no flags)        Full triage run — labels current batch
"""

import json, os, re, sys, time
from datetime import datetime, timedelta
from google.oauth2.service_account import Credentials
from googleapiclient.discovery import build

# ── CONFIG ────────────────────────────────────────────────────────
SCOPES = ["https://www.googleapis.com/auth/gmail.modify"]
SA_KEY = os.path.expanduser("~/.hermes/service-account-key.json")
STATE_FILE = os.path.expanduser("~/.hermes/cache/gmail-triage-state.json")

# Read batch config from JSON file
BATCH_CONFIG = os.path.expanduser("~/.hermes/config/gmail-batches.json")

def _load_batches():
    """Load batch definitions from config file."""
    if os.path.exists(BATCH_CONFIG):
        with open(BATCH_CONFIG) as f:
            cfg = json.load(f)
            return cfg.get("batches", [])
    # Fallback if config missing
    return [
        ["cheehow@gotapway.com", "hana@gotapway.com", "sarah@gotapway.com"],
        ["kunna@gotapway.com", "anwar@gotapway.com", "liyana@gotapway.com"],
        ["syazwan@gotapway.com", "fitri@gotapway.com", "iskandar@gotapway.com", "ashraf@gotapway.com"],
    ]

BATCHES = _load_batches()
NUM_BATCHES = len(BATCHES)
ALL_ACCOUNTS = [a for batch in BATCHES for a in batch]  # flat list

MAX_RESULTS = 500  # per account

# Yesterday's date boundary for Gmail queries (format: YYYY/MM/DD)
_yesterday = (datetime.now() - timedelta(days=1))
YESTERDAY_GMAIL_Q = f"after:{_yesterday.strftime('%Y/%m/%d')} before:{datetime.now().strftime('%Y/%m/%d')}"

# ── PRIORITY SCORING ──────────────────────────────────────────────

PRIORITY_HIGH_KEYWORDS = re.compile(
    r"(urgent|asap|critical|blocker|emergency|eod|deadline|"
    r"stop\s+ship|action\s+required|attention\s+needed|"
    r"payment\s+request|approval\s+needed|hour\s+of\s+need)",
    re.I,
)

PRIORITY_MEDIUM_KEYWORDS = re.compile(
    r"(project|update|follow.up|review|decision|"
    r"proposal|quotation|quote|contract|agreement|"
    r"meeting|schedule|timeline|milestone|delivery|"
    r"po|purchase\s+order|invoice|renewal|subscription|"
    r"demo|pilot|poc|proof\s+of\s+concept|"
    r"support|ticket|case|incident)",
    re.I,
)

PROMOTION_KEYWORDS = re.compile(
    r"(last\s+call|complimentary|exclusive\s+offer|free\s+accommodation|"
    r"discount|promo\s+code|limited\s+time|act\s+now|register\s+now|"
    r"sponsor|newsletter|e\.circular|e-circular|you're\s+invited\s+to\s+join|"
    r"weekly\s+e.bulletin|e-bulletin|incentive\s+statements)",
    re.I,
)


def short_name(email: str) -> str:
    """cheehow@gotapway.com → Chee How"""
    name = email.split("@")[0]
    name_map = {"cheehow": "Chee How", "syazwan": "Syazwan", "fitri": "Fitri",
                "ashraf": "Ashraf", "iskandar": "Iskandar", "liyana": "Liyana"}
    return name_map.get(name, name.capitalize())


def get_service_for(email: str):
    creds = Credentials.from_service_account_file(SA_KEY, scopes=SCOPES)
    return build("gmail", "v1", credentials=creds.with_subject(email), cache_discovery=False)


def build_label_map(service):
    raw = service.users().labels().list(userId="me").execute()
    labels = raw.get("labels", [])
    name_to_id = {l["name"]: l["id"] for l in labels}
    id_to_name = {l["id"]: l["name"] for l in labels}
    return name_to_id, id_to_name


def extract_sender_domain(from_header: str) -> str:
    m = re.search(r"@([\w.-]+)", from_header or "")
    return m.group(1).lower() if m else ""


def extract_subject(headers: dict) -> str:
    return headers.get("Subject", headers.get("subject", ""))


def extract_sender_name(from_header: str) -> str:
    m = re.match(r"^([^<]+)", from_header or "")
    return m.group(1).strip().strip('"') if m else from_header[:40]


def is_promotion(subject: str, from_header: str) -> bool:
    if PROMOTION_KEYWORDS.search(subject):
        return True
    domain = extract_sender_domain(from_header)
    lower_from = from_header.lower()
    for kw in ["substack", "mail.notion", "notify@", "newsletter", "marketing@",
               "promo@", "e-circular", "e.circular"]:
        if kw in domain or kw in lower_from:
            return True
    return False


def get_priority_score(subject: str, body_preview: str = "") -> str:
    combined = subject + " " + body_preview
    if PRIORITY_HIGH_KEYWORDS.search(combined):
        return "high"
    if PRIORITY_MEDIUM_KEYWORDS.search(combined):
        return "medium"
    return "low"


def label_for_email(subject: str, from_header: str, name_to_id: dict):
    """Return (label_id, label_name) or (None, None) to skip."""
    domain = extract_sender_domain(from_header)
    subj_lower = subject.lower()

    # ── 0. Promotion detection ──
    if is_promotion(subject, from_header):
        return "__mark_read__", "Promotion"

    # ── 1. Subject prefix rules (match prefix substring, not exact)
    # Uses startswith so "[sales" catches "[Sales]", "[Sales Enquiry]", "[Sales Request]", etc.
    prefix_map = [
        ("[sales", "Sales"),
        ("[project", "Projects"), ("[proj", "Projects"),
        ("[hr", "HR"), ("[hiring", "HR"), ("[careers", "HR"),
        ("[admin", "HR"),
        ("[finance", "Finance & Accounting"),
        ("[payment", "Finance & Accounting"),
        ("[invoice", "Finance & Accounting"),
        ("[leave", "HR"),
    ]
    for prefix, label in prefix_map:
        if subj_lower.startswith(prefix) and label in name_to_id:
            return name_to_id[label], label

    # ── 2. Support ticket detection ──
    if re.search(r"\[sr_|ticket\s+#|case\s+#|incident\s+#", subj_lower):
        if "tapway-support/new" in name_to_id:
            return name_to_id["tapway-support/new"], "tapway-support/new"

    # ── 2b. Skip internal audit/compliance (not marketing) ──
    if re.search(r"iso\s+\d+|audit\s+finding|audit\s+-+\s+closing|certification", subj_lower):
        if domain in ("gotapway.com", "itmax.com.my"):
            return None, None

    # ── 3. Event / Meeting / Marketing ──
    event_kw = r"(invitation|webinar|workshop|seminar|summit|conference|expo|"
    event_kw += r"exhibition|ai\s+day|meet|forum|training\s+session|"
    event_kw += r"sizing\s+training|collaboration\s+discussion|"
    event_kw += r"lunch\s+meeting|tech\s+update\s+session|"
    event_kw += r"accepted:|appointment\s+booked:|"
    event_kw += r"canceled:|cancelled\s+event:|"
    event_kw += r"rescheduled:|meeting\s+reschedule)"
    if re.search(event_kw, subj_lower):
        if "Marketing/Events" in name_to_id:
            return name_to_id["Marketing/Events"], "Marketing/Events"
        if "Marketing" in name_to_id:
            return name_to_id["Marketing"], "Marketing"

    # ── 4. HR / Hiring / Universities (expanded for internal HR) ──
    hr_kw = r"(hiring|career|internship|intern|job|recruit|talent|"
    hr_kw += r"university|college|academy|scholarship|"
    hr_kw += r"replacement\s+hire|immediately\s+available|"
    hr_kw += r"headhunt|recruitment\s+agency|"
    hr_kw += r"salary\s+increment|leave\s+application|new\s+leave|"
    hr_kw += r"grant\s+rules|hrd\s+corp|salary\s+survey|"
    hr_kw += r"internship\s+application|work\s+permit)"
    hr_recruiters = r"(hays|michael\s+page|robert\s+walters|randstad|kelly\s+services|"
    hr_recruiters += r"adecco|manpower|recruit\s+first|jobsdb|linkedin)"
    if (re.search(hr_kw, subj_lower) or re.search(hr_recruiters, subj_lower)
            or re.search(r"\.edu(\b|\.)", domain)):
        if "HR" in name_to_id:
            return name_to_id["HR"], "HR"

    # ── 5. Partner sub-label detection ──
    partner_map = {
        "nvidia.com": "Partners/NVIDIA",
        "microsoft.com": "Partners/Microsoft",
        "intel.com": "Partners/Intel",
    }
    if re.search(r"canon", domain) and "Partners/Canon" in name_to_id:
        return name_to_id["Partners/Canon"], "Partners/Canon"
    if re.search(r"alibaba", domain) and "Partners/Alibaba" in name_to_id:
        return name_to_id["Partners/Alibaba"], "Partners/Alibaba"
    if (re.search(r"aws.*amazon\.com|amazonaws\.com", domain)
            and "Partners/AWS" in name_to_id):
        return name_to_id["Partners/AWS"], "Partners/AWS"
    for dom_key, label in partner_map.items():
        if dom_key in domain and label in name_to_id:
            return name_to_id[label], label

    if re.search(r"milestone", domain) and "Partners" in name_to_id:
        return name_to_id["Partners"], "Partners"
    if re.search(r"fujifilm", domain) and "Partners" in name_to_id:
        return name_to_id["Partners"], "Partners"

    partner_kw = r"(partner|partnership|alliance|ecosystem\s+partner|"
    partner_kw += r"solution\s+partner|collaboration\s+discussion)"
    if re.search(partner_kw, subj_lower) and "Partners" in name_to_id:
        return name_to_id["Partners"], "Partners"

    # ── 6. Business Development ──
    bd_kw = r"(business\s+development|bd\s+|collaboration|"
    bd_kw += r"partnership\s+discussion|strategic|"
    bd_kw += r"presence\s+and\s+priority|expansion|"
    bd_kw += r"market\s+entry|scale.up\s+grant|grant\s+application)"
    if re.search(bd_kw, subj_lower):
        if "Business Development" in name_to_id:
            return name_to_id["Business Development"], "Business Development"

    # ── 7. Project-related (expanded for proposals, claims, milestones) ──
    proj_kw = r"(project|poc|proof\s+of\s+concept|pilot|demo|"
    proj_kw += r"delivery\s+timeline|floor\s+finishes|"
    proj_kw += r"handheld\s+enhancement|outstanding\s+works|"
    proj_kw += r"subscription\s+renewal|"
    proj_kw += r"camera\s+mapping|queue\s+length|"
    proj_kw += r"phase|phases\s+overview|deep\s+dive|"
    proj_kw += r"progressive\s+claim|milestone\s+\d+\s+quarter|"
    proj_kw += r"device\s+requirement|rfp\s+|technical\s+proposal|"
    proj_kw += r"milestone\s+\d+\s+submission|perkeso)"
    if re.search(proj_kw, subj_lower):
        if "Projects" in name_to_id:
            return name_to_id["Projects"], "Projects"

    # ── 8. Finance & Accounting (expanded for renewals) ──
    fin_kw = r"(invoice|payment|subscription\s+renewal|"
    fin_kw += r"credit\s+application|payment\s+request|"
    fin_kw += r"outstanding\s+payment|overdue|"
    fin_kw += r"submit\s+invoice|renewal\s+for\s+subscription|"
    fin_kw += r"peopletrack\s+renewal|renewal\s+-\s+\d+\s+year|"
    fin_kw += r"progressive\s+claim\s+no)"
    if re.search(fin_kw, subj_lower):
        if "Finance & Accounting" in name_to_id:
            return name_to_id["Finance & Accounting"], "Finance & Accounting"

    # ── 8b. Sales fallback (catch deal-related replies without [Sales] prefix) ──
    sales_fb = r"(deal\s+registration|tapway\s+pipeline|"
    sales_fb += r"service\s+agreement|golden\s+screen|habib\s+suria|"
    sales_fb += r"vision\s+ai\s+for|samurai\s+for)"
    if re.search(sales_fb, subj_lower):
        if "Sales" in name_to_id:
            return name_to_id["Sales"], "Sales"

    # ── 9. Vendor detection ──
    vendor_kw = r"(thinkstation|pgx|hardware\s+supplier|"
    vendor_kw += r"shipment|delivery\s+confirmation|"
    vendor_kw += r"software\s+subscription\s+renewal|"
    vendor_kw += r"vendor|supplier|procurement|"
    vendor_kw += r"quotation|quote|rfq|purchase\s+order)"
    if re.search(vendor_kw, subj_lower):
        if "Vendors" in name_to_id:
            return name_to_id["Vendors"], "Vendors"

    # ── 10. Meeting Minutes (also catches "Notes:" prefix)
    mm_kw = r"(minutes\s+of\s+meeting|mom\s*|meeting\s+minutes|"
    mm_kw += r"meeting\s+notes|recap|summary\s+of\s+meeting)"
    if re.search(mm_kw, subj_lower) or subj_lower.startswith("notes:"):
        if "Meeting Minutes" in name_to_id:
            return name_to_id["Meeting Minutes"], "Meeting Minutes"

    # ── 11. Technical ──
    tech_kw = r"(sdk|api\s+doc|changelog|release\s+notes|"
    tech_kw += r"deployment|config|integration\s+spec|"
    tech_kw += r"camera\s+mapping|queue\s+length\s+assessment)"
    if re.search(tech_kw, subj_lower):
        if re.search(r"(sdk|api|library|npm|pip)", subj_lower) and "Developer" in name_to_id:
            return name_to_id["Developer"], "Developer"
        if "Technical" in name_to_id:
            return name_to_id["Technical"], "Technical"

    # ── 12. Cold outreach ──
    cold_kw = r"(introduction|reach\s+out|let\s+us\s+show|"
    cold_kw += r"schedule\s+a\s+call|book\s+a\s+demo|"
    cold_kw += r"partnership\s+opportunity|exclusive\s+access)"
    salesy_domains = r"(\.io\b|\.ventures\b|\.ai\b|consulting)"
    if (re.search(cold_kw, subj_lower) or re.search(salesy_domains, domain)):
        if not re.search(r"(gotapway|itmax|partner|project)", subj_lower):
            if "Cold outreach" in name_to_id:
                return name_to_id["Cold outreach"], "Cold outreach"

    return None, None


# ── BATCH ROTATION ────────────────────────────────────────────────

def read_state():
    """Read batch state or initialize."""
    if os.path.exists(STATE_FILE):
        try:
            with open(STATE_FILE) as f:
                return json.load(f)
        except (json.JSONDecodeError, KeyError):
            pass
    return {"batch": 0, "last_run": None}


def write_state(state: dict):
    os.makedirs(os.path.dirname(STATE_FILE), exist_ok=True)
    with open(STATE_FILE, "w") as f:
        json.dump(state, f)


def get_current_batch(override: int = None) -> tuple:
    """Return (batch_index, accounts_slice) for this run."""
    if override is not None:
        batch = override % NUM_BATCHES
    else:
        state = read_state()
        batch = state.get("batch", 0)
        # Advance for next run
        state["batch"] = (batch + 1) % NUM_BATCHES
        state["last_run"] = datetime.now().isoformat()
        write_state(state)

    return batch, BATCHES[batch]


def get_just_processed_batch() -> list:
    """Return accounts from the batch that was most recently triaged.
    
    After a triage run, get_current_batch() advances the state to the NEXT batch.
    This reads the state and backtracks to return the batch that was just labeled.
    If no state exists (standalone summary/alert), returns batch 2 (last batch of the rotation).
    """
    state = read_state()
    if state.get("last_run") is None:
        # No prior triage — default to last batch
        prev_batch = NUM_BATCHES - 1  # last batch
    else:
        current = state.get("batch", 0)
        prev_batch = (current - 1) % NUM_BATCHES
    return BATCHES[prev_batch]


# ── GOOGLE API BATCH HELPER ──────────────────────────────────────

# Labels that MUST exist for triage to work (auto-created if missing)
REQUIRED_LABELS = [
    "Sales", "Projects", "HR", "Finance & Accounting",
    "Marketing", "Marketing/Events", "Partners", "Vendors",
    "Business Development", "Meeting Minutes", "Technical",
    "Developer", "Cold outreach", "tapway-support/new",
    "tapway-support/done",
]

def ensure_labels(service, email: str, dry_run: bool = False):
    """Create any missing required labels for an account."""
    name_to_id, _ = build_label_map(service)
    created = []
    for label_name in REQUIRED_LABELS:
        if label_name not in name_to_id:
            if not dry_run:
                try:
                    created_label = service.users().labels().create(
                        userId=email,
                        body={"name": label_name,
                              "labelListVisibility": "labelShow",
                              "messageListVisibility": "show"}
                    ).execute()
                    name_to_id[label_name] = created_label["id"]
                except Exception:
                    pass
            created.append(label_name)
    if created:
        sys.stderr.write(f"  Created {len(created)} labels for {email}: {', '.join(created[:5])}"
                         f"{'...' if len(created) > 5 else ''}\n")
    return name_to_id

def batch_get_messages(service, email: str, msg_ids: list, headers_needed: list = None) -> dict:
    """Fetch multiple messages in ONE HTTP call using Gmail batch API.
    Returns {msg_id: message_resource, ...}"""
    if headers_needed is None:
        headers_needed = ["From", "Subject"]

    message_data = {}
    errors = []

    def handle_msg(request_id, response, exception):
        if exception:
            errors.append((request_id, str(exception)))
            return
        message_data[request_id] = response

    # Process in chunks of 100 (Gmail batch limit)
    for i in range(0, len(msg_ids), 100):
        batch = service.new_batch_http_request()
        chunk = msg_ids[i:i + 100]
        for mid in chunk:
            batch.add(
                service.users().messages().get(
                    userId=email, id=mid,
                    format="metadata",
                    metadataHeaders=headers_needed
                ),
                callback=handle_msg,
                request_id=mid
            )
        batch.execute()

    return message_data


def batch_modify_messages(service, email: str, operations: list, dry_run: bool = False):
    """Apply label modifications in ONE HTTP call.
    operations: [{"msg_id": "...", "add": [...], "remove": [...]}, ...]"""
    if dry_run:
        return

    def handle_mod(request_id, response, exception):
        pass  # fire-and-forget; errors logged at summary level

    for i in range(0, len(operations), 100):
        batch = service.new_batch_http_request()
        chunk = operations[i:i + 100]
        for op in chunk:
            body = {}
            if op.get("add"):
                body["addLabelIds"] = op["add"]
            if op.get("remove"):
                body["removeLabelIds"] = op["remove"]
            batch.add(
                service.users().messages().modify(
                    userId=email, id=op["msg_id"],
                    body=body
                ),
                callback=handle_mod
            )
        batch.execute()


# ── TRIAGE ENGINE (streaming — 50 msgs at a time) ────────────────

STREAM_CHUNK = 50  # process in sub-batches to cap memory

def run_triage_for_account(email: str, dry_run: bool = False):
    """Label inbox for one account. Streaming: fetch 50, process, apply, discard."""
    try:
        service = get_service_for(email)
        name_to_id = ensure_labels(service, email, dry_run=dry_run)
    except Exception as e:
        return {"email": email, "name": short_name(email), "error": str(e),
                "total": 0, "labeled": 0, "marked_read": 0,
                "already_labeled": 0, "skipped": 0, "log": []}

    # Step 1: Get message ID list (1 API call — IDs only, tiny)
    try:
        results = service.users().messages().list(
            userId=email, q=f"in:inbox -in:chats -category:promotions -category:social {YESTERDAY_GMAIL_Q}",
            maxResults=MAX_RESULTS, fields="messages/id,nextPageToken"
        ).execute()
    except Exception as e:
        return {"email": email, "name": short_name(email), "error": str(e),
                "total": 0, "labeled": 0, "marked_read": 0,
                "already_labeled": 0, "skipped": 0, "log": []}

    msgs = results.get("messages", [])
    if not msgs:
        return {"email": email, "name": short_name(email), "total": 0,
                "labeled": 0, "marked_read": 0, "already_labeled": 0,
                "skipped": 0, "log": []}

    labeled = 0
    marked_read = 0
    already_labeled = 0
    skipped = 0
    log = []

    # Step 2: Stream-process in chunks of 50
    total = len(msgs)
    for i in range(0, total, STREAM_CHUNK):
        chunk = msgs[i:i + STREAM_CHUNK]
        chunk_ids = [m["id"] for m in chunk]

        # Fetch this chunk's messages (1 batch HTTP call)
        message_data = batch_get_messages(service, email, chunk_ids)

        # Classify and collect modify ops for this chunk
        chunk_ops = []
        for m in chunk:
            msg = message_data.get(m["id"])
            if not msg:
                continue

            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            current_labels = msg.get("labelIds", [])

            user_label_ids = [l for l in current_labels if l.startswith("Label_")]
            if user_label_ids:
                already_labeled += 1
                continue

            subject = extract_subject(headers)
            from_header = headers.get("From", "")

            label_id, label_name = label_for_email(subject, from_header, name_to_id)

            if label_id == "__mark_read__":
                chunk_ops.append({"msg_id": m["id"], "remove": ["UNREAD"]})
                marked_read += 1
                log.append(f"  READ         [{label_name:20s}] {subject[:55]}")
            elif label_id:
                chunk_ops.append({"msg_id": m["id"], "add": [label_id]})
                labeled += 1
                log.append(f"  LABELED      [{label_name:20s}] {subject[:55]}")
            else:
                skipped += 1
                log.append(f"  SKIP                          {subject[:55]}")

        # Apply this chunk's labels (1 batch modify call), then discard
        if chunk_ops:
            batch_modify_messages(service, email, chunk_ops, dry_run=dry_run)

        # Free memory — chunk dict + ops dropped at end of loop iteration
        sys.stderr.write(f"  Chunk {i//STREAM_CHUNK + 1}/{(total + STREAM_CHUNK - 1)//STREAM_CHUNK} "
                         f"({min(i+STREAM_CHUNK, total)}/{total}) done\n")
        sys.stderr.flush()

    return {
        "email": email,
        "name": short_name(email),
        "total": len(msgs),
        "labeled": labeled,
        "marked_read": marked_read,
        "already_labeled": already_labeled,
        "skipped": skipped,
        "log": log,
    }


def run_triage_batch(dry_run: bool = False, batch_override: int = None):
    """Run triage for the current 3-account batch."""
    batch_idx, accounts = get_current_batch(batch_override)
    mode = "DRY RUN" if dry_run else "LIVE"

    print(f"{'='*60}")
    print(f"  GMAIL TRIAGE — {mode} — BATCH {batch_idx + 1}/3")
    print(f"  Accounts: {', '.join(short_name(a) for a in accounts)}")
    print(f"  Time: {datetime.now().strftime('%Y-%m-%d %H:%M:%S')}")
    print(f"{'='*60}")
    print()

    all_results = []
    for email in accounts:
        sys.stderr.write(f"Scanning {email}...\n")
        sys.stderr.flush()
        result = run_triage_for_account(email, dry_run=dry_run)
        all_results.append(result)

    # Per-account output
    for r in all_results:
        print(f"📧 {r['email']}")
        if "error" in r:
            print(f"  ❌ Error: {r['error'][:120]}")
        else:
            print(f"  Total: {r['total']}  Labeled: {r['labeled']}  "
                  f"Read: {r['marked_read']}  Already: {r['already_labeled']}  "
                  f"Skipped: {r['skipped']}")
            for line in r["log"]:
                print(line)
        print()

    # Summary
    total_msgs = sum(r.get("total", 0) for r in all_results)
    total_labeled = sum(r.get("labeled", 0) for r in all_results)
    total_read = sum(r.get("marked_read", 0) for r in all_results)
    total_already = sum(r.get("already_labeled", 0) for r in all_results)
    total_skipped = sum(r.get("skipped", 0) for r in all_results)
    errors = [r for r in all_results if "error" in r]

    print(f"{'='*60}")
    print(f"  BATCH {batch_idx + 1} SUMMARY")
    print(f"  {total_msgs} total · {total_labeled} labeled · "
          f"{total_read} marked read · {total_already} already · "
          f"{total_skipped} skipped")
    if errors:
        print(f"  ❌ {len(errors)} account(s) failed: "
              f"{', '.join(r['name'] for r in errors)}")
    print(f"{'='*60}")

    # Release WSL page cache after triage to prevent vmmem bloat
    _release_cache()


def _release_cache():
    """Drop Linux page cache to release memory back to Windows/WSL host.
    Safe — only drops clean caches, dirty pages are written first."""
    try:
        with open("/proc/sys/vm/drop_caches", "w") as f:
            f.write("1\n")
        sys.stderr.write("  💾 Page cache released\n")
    except (PermissionError, OSError):
        pass  # not root — skip silently


# ── SUMMARY & ALERT ───────────────────────────────────────────────

def run_summary_all():
    """Priority summary for the batch that was just triaged."""
    accounts = get_just_processed_batch()
    print(f"📬 GMAIL INBOX SUMMARY — {datetime.now().strftime('%a %b %d %H:%M')} (batch of {len(accounts)})")
    print()

    for email in accounts:
        try:
            service = get_service_for(email)
        except Exception as e:
            print(f"📧 {short_name(email)} — ❌ auth error: {e}")
            continue

        try:
            results = service.users().messages().list(
                userId=email,
                q=f"in:inbox -in:chats -category:promotions -category:social {YESTERDAY_GMAIL_Q}",
                maxResults=300
            ).execute()
        except Exception as e:
            print(f"📧 {short_name(email)} — ❌ fetch error: {e}")
            continue

        msgs = results.get("messages", [])
        if not msgs:
            continue

        # Batch-fetch all messages
        msg_ids = [m["id"] for m in msgs]
        message_data = batch_get_messages(service, email, msg_ids,
                                          headers_needed=["From", "Subject", "Date"])

        high, medium, low = [], [], []

        for m in msgs:
            msg = message_data.get(m["id"])
            if not msg:
                continue

            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            subject = extract_subject(headers)
            from_header = headers.get("From", "")
            is_unread = "UNREAD" in msg.get("labelIds", [])
            is_important = "IMPORTANT" in msg.get("labelIds", [])

            if is_promotion(subject, from_header):
                continue

            score = get_priority_score(subject)
            if is_important and score != "high":
                score = "high"

            entry = {
                "subject": subject[:80],
                "from": extract_sender_name(from_header),
                "unread": is_unread,
            }

            if score == "high":
                high.append(entry)
            elif score == "medium":
                medium.append(entry)
            else:
                low.append(entry)

        if not (high or medium or low):
            continue

        print(f"📧 {short_name(email)} ({email}) — {len(msgs)} emails")
        print(f"   🔴 High:{len(high)}  🟡 Medium:{len(medium)}  ⚪ Low:{len(low)}")

        if high:
            for e in high[:5]:  # Top 5 high
                icon = "🔴" if e["unread"] else "  "
                print(f"   {icon} {e['subject'][:65]}")
                print(f"      └ {e['from']}")
        if medium:
            print(f"   🟡 {len(medium)} medium-priority emails"
                  f"{' (sample)' if len(medium) > 3 else ''}:")
            for e in medium[:3]:
                print(f"      · {e['subject'][:55]}")
        if low and len(low) <= 3:
            print(f"   ⚪ {len(low)} low-priority:")
            for e in low[:3]:
                print(f"      · {e['subject'][:50]}")
        elif low:
            print(f"   ⚪ {len(low)} low-priority emails (not shown)")
        print()

    _release_cache()


def run_alert_all():
    """Check urgent emails for the batch that was just triaged."""
    accounts = get_just_processed_batch()
    total_urgent = 0

    for email in accounts:
        try:
            service = get_service_for(email)
        except Exception:
            continue

        try:
            results = service.users().messages().list(
                userId=email,
                q="in:inbox -in:chats -category:promotions -category:social is:unread newer_than:2d",
                maxResults=50
            ).execute()
        except Exception:
            continue

        msgs = results.get("messages", [])
        if not msgs:
            continue

        # Batch-fetch all messages
        msg_ids = [m["id"] for m in msgs]
        message_data = batch_get_messages(service, email, msg_ids,
                                          headers_needed=["From", "Subject", "Date"])

        urgent = []

        for m in msgs:
            msg = message_data.get(m["id"])
            if not msg:
                continue

            headers = {h["name"]: h["value"] for h in msg["payload"]["headers"]}
            subject = extract_subject(headers)
            from_header = headers.get("From", "")
            is_important = "IMPORTANT" in msg.get("labelIds", [])

            score = get_priority_score(subject)

            if score == "high" or is_important:
                urgent.append({
                    "subject": subject,
                    "from": from_header,
                    "important": is_important,
                })

        if urgent:
            total_urgent += len(urgent)
            if total_urgent == len(urgent):  # First account with alerts
                print(f"🚨 URGENT ALERTS — {datetime.now().strftime('%a %b %d %H:%M')}")
                print()
            print(f"📧 {short_name(email)} — {len(urgent)} urgent")
            for e in urgent:
                badge = "🔴 IMPORTANT" if e["important"] else "🚨 URGENT"
                print(f"   {badge} {e['subject'][:65]}")
                print(f"   From: {extract_sender_name(e['from'])}")
            print()

    if total_urgent == 0:
        print("✅ No urgent emails in this batch.")

    _release_cache()


# ── CLI ENTRY ─────────────────────────────────────────────────────

if __name__ == "__main__":
    batch = None

    # Parse --batch N
    for i, arg in enumerate(sys.argv):
        if arg == "--batch" and i + 1 < len(sys.argv):
            try:
                batch = int(sys.argv[i + 1])
            except ValueError:
                pass

    if "--summary" in sys.argv:
        run_summary_all()

    elif "--alert" in sys.argv:
        run_alert_all()

    elif "--dry-run" in sys.argv or "-n" in sys.argv:
        run_triage_batch(dry_run=True, batch_override=batch)

    else:
        run_triage_batch(dry_run=False, batch_override=batch)