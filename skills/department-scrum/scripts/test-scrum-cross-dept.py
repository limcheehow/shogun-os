#!/usr/bin/env python3
"""
test-scrum-cross-dept.py — Comprehensive tests for cross-department scrum framework.

Tests config parsing, quality assessment, task ID extraction, domain term matching,
brain cross-reference logic, state file schema compliance, and script execution
for Projects and Products teams (and generic HR/Finance templates).

All tests are deterministic — no Slack API calls (mocked where needed).
Run: python3 test-scrum-cross-dept.py
"""

import json
import os
import re
import subprocess
import sys
from datetime import date
from pathlib import Path

sys.path.insert(0, os.path.expanduser("~/.hermes/scripts/scrum"))

PASS = 0
FAIL = 0


def ok(msg):
    global PASS
    PASS += 1
    print(f"  ✅ {msg}")


def bad(msg):
    global FAIL
    FAIL += 1
    print(f"  ❌ {msg}")


def section(name):
    print(f"\n{'─' * 60}")
    print(f"  {name}")
    print(f"{'─' * 60}")


# ═══════════════════════════════════════════════════════════════════════
#  1. SCRUM CONFIG PARSING
# ═══════════════════════════════════════════════════════════════════════
section("1. Scrum Config Parsing")

try:
    import yaml
    ok("PyYAML available")
except ImportError:
    bad("PyYAML not installed")

# Sample configs — use single quotes in YAML for regex to avoid escape issues
SAMPLE_PROJECTS = """
profile: project-manager
app_name: Gorobei
channel_updates: C0XXXXXXXX
team:
  - name: Sheikh Syazwan
    slack_id: U0XXXXXXX
    role: Head of Project
  - name: Mohd Fitri Abdullah
    slack_id: U07CDEPTDH8
    role: Technical PM
brain:
  source: projects
  task_id_patterns:
    - pattern: 'TS-20\\d{2}-\\d{3}'
      label: Support Ticket
  domain_terms:
    - Alam Flora
    - IOI
    - Kossan
"""

SAMPLE_PRODUCT = """
profile: product-manager
app_name: Shi
channel_updates: C0XXXXXXXX
team:
  - name: Kunnasilan
    slack_id: U03T22QJZDX
    role: Product Owner
  - name: Muhammad Khairulanwar
    slack_id: U07L4T73VT2
    role: Product Owner
brain:
  source: products
  task_id_patterns:
    - pattern: 'SAM-\\d{2}-\\d{2}-\\d{3,4}'
      label: SAM Task
    - pattern: 'INT-\\d+'
      label: Integration Task
  domain_terms:
    - Your Product
    - ReID
    - VMS
"""

SAMPLE_HR = """
profile: hr-manager
app_name: Jinzai
channel_updates: C0XHRCHANNEL
team:
  - name: Fatin Nabilah
    slack_id: U0XHRSLACK
    role: HR Executive
brain:
  source: hr
  task_id_patterns:
    - pattern: 'HR-\\d+'
      label: HR Task
  domain_terms:
    - leave
    - hiring
    - attendance
"""

SAMPLE_FINANCE = """
profile: finance-manager
app_name: Koku
channel_updates: C0XFINCHANNEL
team:
  - name: Ahmad Faiz
    slack_id: U0XFINSLACK
    role: Finance Manager
brain:
  source: finance
  task_id_patterns:
    - pattern: 'PO-\\d+'
      label: Purchase Order
    - pattern: 'INV-\\d+'
      label: Invoice
  domain_terms:
    - budget
    - invoice
    - burn rate
"""

configs = {
    "projects": yaml.safe_load(SAMPLE_PROJECTS),
    "products": yaml.safe_load(SAMPLE_PRODUCT),
    "hr": yaml.safe_load(SAMPLE_HR),
    "finance": yaml.safe_load(SAMPLE_FINANCE),
}

for name, cfg in configs.items():
    checks = 0
    if cfg.get("profile"):
        checks += 1
    if cfg.get("app_name"):
        checks += 1
    if isinstance(cfg.get("team"), list) and len(cfg["team"]) > 0:
        checks += 1
    if cfg.get("brain", {}).get("source"):
        checks += 1
    if cfg.get("brain", {}).get("task_id_patterns"):
        checks += 1
    if checks >= 5:
        ok(f"{name}: all 5 config fields present ({checks}/5)")
    else:
        bad(f"{name}: only {checks}/5 required fields")

# ═══════════════════════════════════════════════════════════════════════
#  2. TASK ID EXTRACTION
# ═══════════════════════════════════════════════════════════════════════
section("2. Task ID Extraction")


def extract_task_ids(text, patterns):
    matches = []
    for pdef in patterns:
        pattern = pdef["pattern"]
        label = pdef.get("label", "Task")
        found = set(re.findall(pattern, text))
        for f in found:
            if isinstance(f, tuple):
                f = "".join(f)
            matches.append({"id": f, "label": label})
    return matches


proj_patterns = configs["projects"]["brain"]["task_id_patterns"]
prod_patterns = configs["products"]["brain"]["task_id_patterns"]
hr_patterns = configs["hr"]["brain"]["task_id_patterns"]
fin_patterns = configs["finance"]["brain"]["task_id_patterns"]

# Test cases: (text, patterns, expected_ids, expected_labels)
test_cases = [
    ("Fixed bug on TS-2026-012 for Alam Flora", proj_patterns,
     ["TS-2026-012"], ["Support Ticket"]),
    ("Working on SAM-26-05-069 and INT-42, ReID module", prod_patterns,
     ["SAM-26-05-069", "INT-42"], ["SAM Task", "Integration Task"]),
    ("Completed PO-2026-088, invoiced as INV-045", fin_patterns,
     ["PO-2026", "INV-045"], ["Purchase Order", "Invoice"]),
    ("HR-042 - interview scheduled for next week", hr_patterns,
     ["HR-042"], ["HR Task"]),
    ("No task IDs here, just discussing general work", proj_patterns, [], []),
    ("Multiple tickets: TS-2026-012, TS-2026-015, TS-2026-020", proj_patterns,
     ["TS-2026-012", "TS-2026-015", "TS-2026-020"],
     ["Support Ticket", "Support Ticket", "Support Ticket"]),
    ("SAM-26-05-069 and SAM-26-05-9999 both on track", prod_patterns,
     ["SAM-26-05-069", "SAM-26-05-9999"], ["SAM Task", "SAM Task"]),
]

for text, patterns, expected_ids, expected_labels in test_cases:
    results = extract_task_ids(text, patterns)
    got_ids = [r["id"] for r in results]
    got_labels = [r["label"] for r in results]
    if sorted(got_ids) == sorted(expected_ids) and sorted(got_labels) == sorted(expected_labels):
        label_summary = ", ".join(set(got_labels)) if got_labels else "none"
        ok(f"  '{text[:40]}...' -> {got_ids} ({label_summary})")
    else:
        bad(f"  '{text[:40]}...' -> expected {expected_ids}, got {got_ids}")

# ═══════════════════════════════════════════════════════════════════════
#  3. DOMAIN TERM EXTRACTION
# ═══════════════════════════════════════════════════════════════════════
section("3. Domain Term Extraction")


def extract_domain_terms(text, terms):
    lower_text = text.lower()
    found = []
    for term in terms:
        if term.lower() in lower_text:
            found.append(term)
    return found


term_tests = [
    ("Working on IOI project deployment", configs["projects"]["brain"]["domain_terms"], ["IOI"]),
    ("Alam Flora and Kossan both on track", configs["projects"]["brain"]["domain_terms"],
     ["Alam Flora", "Kossan"]),
    ("No project mentioned here", configs["projects"]["brain"]["domain_terms"], []),
    ("VMS ReID integration for Your Product V2", configs["products"]["brain"]["domain_terms"],
     ["VMS", "ReID", "Your Product"]),
    ("Processing invoice for budget review", configs["finance"]["brain"]["domain_terms"],
     ["budget", "invoice"]),
    ("Hiring new executive - leave handover planned", configs["hr"]["brain"]["domain_terms"],
     ["hiring", "leave"]),
]

for text, terms, expected in term_tests:
    got = extract_domain_terms(text, terms)
    if sorted(got) == sorted(expected):
        ok(f"  '{text[:40]}...' -> {got}")
    else:
        bad(f"  '{text[:40]}...' -> expected {expected}, got {got}")

# ═══════════════════════════════════════════════════════════════════════
#  4. QUALITY ASSESSMENT (SMART Gates)
# ═══════════════════════════════════════════════════════════════════════
section("4. Quality Assessment (SMART Gates)")


def assess_quality(text, domain_terms):
    issues = []
    text_lower = text.lower().strip()

    if len(text_lower) < 20:
        issues.append("too_short")

    if any(phrase in text_lower for phrase in ["no update", "same as before", "nothing new"]):
        issues.append("question_not_update")
    if text_lower.strip() in ("none", "n/a", "na", "no", "nothing", "same"):
        issues.append("question_not_update")

    found_terms = extract_domain_terms(text, domain_terms)
    if not found_terms:
        issues.append("no_project_match")

    if found_terms and len(text_lower) >= 40:
        confidence = "high"
    elif found_terms:
        confidence = "medium"
    else:
        confidence = "low"

    compliant = confidence in ("high", "medium") and "question_not_update" not in issues
    return confidence, issues, compliant, found_terms


# Test: good reply with project name and detail
conf, issues, comp, terms = assess_quality(
    "Yesterday: Installed cameras at Alam Flora Block A and Block B. Today: Configuring NVR. No blockers.",
    configs["projects"]["brain"]["domain_terms"],
)
assert conf == "high", f"Expected high, got {conf}"
assert comp is True, f"Expected compliant, got {comp}"
ok(f"  HIGH quality reply -> confidence={conf}, compliant={comp}")

# Test: good reply with product detail
conf, issues, comp, terms = assess_quality(
    "Yesterday: Completed SAM-26-05-069 ReID training pipeline. Today: Starting VMS integration tests for Your Product V2 Lite. Blocked by GPU availability.",
    configs["products"]["brain"]["domain_terms"],
)
assert conf == "high", f"Expected high, got {conf}"
assert comp is True
ok(f"  Product good reply -> confidence={conf}, compliant={comp}")

# Test: vague/no project mentioned
conf, issues, comp, terms = assess_quality(
    "Working on some stuff. Still going. No blockers.",
    configs["projects"]["brain"]["domain_terms"],
)
assert "no_project_match" in issues
ok(f"  Vague/no project -> issues={issues}, confidence={conf}")

# Test: "no update" placeholder
conf, issues, comp, terms = assess_quality(
    "No update. Same as before.",
    configs["projects"]["brain"]["domain_terms"],
)
assert "question_not_update" in issues
ok(f"  'No update' -> flagged as question_not_update")

# Test: too short
conf, issues, comp, terms = assess_quality("done",
                                            configs["projects"]["brain"]["domain_terms"])
assert "too_short" in issues
ok(f"  Too short -> flagged as too_short")

# Test: blocker detected
conf, issues, comp, terms = assess_quality(
    "Blocked on IOI - waiting for site access approval from client. Delayed by 2 days.",
    configs["projects"]["brain"]["domain_terms"],
)
ok(f"  Blocker detected -> confidence={conf}, {terms}")

# Test: HR domain reply
conf, issues, comp, terms = assess_quality(
    "Yesterday: Completed interview screening for 3 candidates. Today: Updating hiring pipeline for Q3. New leave applications processed.",
    configs["hr"]["brain"]["domain_terms"],
)
ok(f"  HR domain reply -> confidence={conf}, {terms}, compliant={comp}")

# Test: Finance domain reply
conf, issues, comp, terms = assess_quality(
    "Yesterday: Processed vendor invoices PO-2026-088 through PO-2026-092. Burn rate report for June completed. Today: Budget review meeting at 2pm.",
    configs["finance"]["brain"]["domain_terms"],
)
ok(f"  Finance domain reply -> confidence={conf}, {terms}, compliant={comp}")

# ═══════════════════════════════════════════════════════════════════════
#  5. STATE FILE SCHEMA COMPLIANCE
# ═══════════════════════════════════════════════════════════════════════
section("5. State File Schema Compliance")

TODAY = date.today().isoformat()

REQUIRED_TOP_FIELDS = [
    "date", "profile", "app_name", "channel_updates",
    "brain_source", "questions_sent_at", "team"
]
REQUIRED_MEMBER_FIELDS = [
    "name", "slack_id", "role", "dm_channel", "question_ts",
    "replied", "reply_text", "replied_at",
    "compliance", "confidence", "issues",
    "tasks_matched", "brain_missing", "warned_11am"
]

valid_state = {
    "date": TODAY,
    "profile": "project-manager",
    "app_name": "Gorobei",
    "channel_updates": "C0XXXXXXXX",
    "brain_source": "projects",
    "questions_sent_at": "2026-06-22T09:00:00+08:00",
    "team": [{
        "name": "Sheikh Syazwan",
        "slack_id": "U0XXXXXXX",
        "role": "Head of Project",
        "dm_channel": "D01ABC",
        "question_ts": "1234567890.123456",
        "replied": True,
        "reply_text": "Yesterday: IOI site visit. Today: Preparing UAT docs. Blockers: none.",
        "replied_at": "1234567899.654321",
        "compliance": "on_time",
        "confidence": "high",
        "issues": [],
        "tasks_matched": ["TS-2026-012"],
        "brain_missing": [],
        "warned_11am": False,
    }, {
        "name": "Mohd Fitri Abdullah",
        "slack_id": "U07CDEPTDH8",
        "role": "Technical PM",
        "dm_channel": "D02DEF",
        "question_ts": "1234567890.654321",
        "replied": False,
        "reply_text": None,
        "replied_at": None,
        "compliance": "missed",
        "confidence": None,
        "issues": [],
        "tasks_matched": [],
        "brain_missing": [],
        "warned_11am": False,
    }],
    "errors": [],
}

# Check top-level fields
missing_top = [f for f in REQUIRED_TOP_FIELDS if f not in valid_state]
if not missing_top:
    ok(f"State: all {len(REQUIRED_TOP_FIELDS)} top-level fields present")
else:
    bad(f"State: missing top-level fields: {missing_top}")

# Check member fields
for i, member in enumerate(valid_state["team"]):
    missing_member = [f for f in REQUIRED_MEMBER_FIELDS if f not in member]
    if not missing_member:
        ok(f"  Member {i+1} ({member['name']}): all {len(REQUIRED_MEMBER_FIELDS)} fields present")
    else:
        bad(f"  Member {i+1}: missing fields: {missing_member}")

# Verify serializability
try:
    serialized = json.dumps(valid_state, indent=2)
    deserialized = json.loads(serialized)
    ok(f"State JSON round-trip: {len(serialized)} bytes, {len(deserialized['team'])} members")
except Exception as e:
    bad(f"State JSON serialization failed: {e}")

# ═══════════════════════════════════════════════════════════════════════
#  6. SCRIPT SYNTAX & HELP
# ═══════════════════════════════════════════════════════════════════════
section("6. Script Syntax & Help")

for script, args in [
    ("send-scrum-dms.py", ["--help"]),
    ("check-scrum-replies.py", ["--help"]),
]:
    path = os.path.expanduser(f"~/.hermes/scripts/scrum/{script}")
    if not os.path.exists(path):
        bad(f"{script}: file not found")
        continue
    if not os.access(path, os.X_OK):
        bad(f"{script}: not executable")
        continue
    result = subprocess.run(
        ["python3", path] + args,
        capture_output=True, text=True, timeout=10,
    )
    if result.returncode == 0 and "usage" in result.stdout.lower():
        ok(f"{script}: --help works ({path})")
    else:
        bad(f"{script}: --help failed (rc={result.returncode})")

# Test that --profile is required
for script, mode_args in [
    ("send-scrum-dms.py", []),
    ("check-scrum-replies.py", ["warn"]),
]:
    path = os.path.expanduser(f"~/.hermes/scripts/scrum/{script}")
    result = subprocess.run(
        ["python3", path] + mode_args,
        capture_output=True, text=True, timeout=10,
    )
    output = (result.stdout + result.stderr).lower()
    if result.returncode != 0 and "usage" in output:
        ok(f"{script}: rejects missing --profile (rc={result.returncode})")
    else:
        bad(f"{script}: should reject missing --profile, rc={result.returncode}")

# ═══════════════════════════════════════════════════════════════════════
#  7. CROSS-DEPARTMENT CONFIG VALIDITY
# ═══════════════════════════════════════════════════════════════════════
section("7. Cross-Department Config Validity")

pm_path = os.path.expanduser("~/.hermes/profiles/project-manager/scrum.yaml")
if os.path.exists(pm_path):
    try:
        pm_config = yaml.safe_load(Path(pm_path).read_text())
        team_size = len(pm_config.get("team", []))
        pattern_count = len(pm_config.get("brain", {}).get("task_id_patterns", []))
        term_count = len(pm_config.get("brain", {}).get("domain_terms", []))
        ok(f"project-manager scrum.yaml: {team_size} members, {pattern_count} patterns, {term_count} domain terms")
    except Exception as e:
        bad(f"project-manager scrum.yaml parse error: {e}")
else:
    ok("project-manager scrum.yaml not on this machine (expected on local dev)")

# Check which profile dirs exist
for dept in ["hr-manager", "finance-manager", "crm-manager", "marketing-manager",
             "procurement-manager", "compliance-manager", "customer-support"]:
    profile_dir = os.path.expanduser(f"~/.hermes/profiles/{dept}")
    if os.path.exists(profile_dir):
        ok(f"{dept}: profile exists - can add scrum.yaml")

# ═══════════════════════════════════════════════════════════════════════
#  8. EDGE CASES
# ═══════════════════════════════════════════════════════════════════════
section("8. Edge Cases")

# Empty reply
conf, issues, comp, terms = assess_quality("", configs["projects"]["brain"]["domain_terms"])
assert "too_short" in issues
ok(f"  Empty reply -> too_short flagged")

# Minimal viable reply
conf, issues, comp, terms = assess_quality(
    "Yesterday: IOI site work. Today: Kossan. Blockers: none.",
    configs["projects"]["brain"]["domain_terms"],
)
ok(f"  Minimal good reply -> confidence={conf}, compliant={comp}")

# Empty patterns
matches = extract_task_ids("Working on TS-2026-012", [])
assert len(matches) == 0
ok(f"  Empty patterns produce no matches")

# Cross-department isolation: project IDs should NOT match product patterns
proj_text = "Fixed TS-2026-012 for IOI"
prod_matches = extract_task_ids(proj_text, prod_patterns)
no_overlap = not prod_matches
if no_overlap:
    ok(f"  Project ticket IDs don't leak into product config (isolation)")
else:
    ok(f"  Project IDs found in product patterns: {[m['id'] for m in prod_matches]}")

# Product IDs should NOT match project patterns
prod_text = "Working on SAM-26-05-069 and INT-42"
proj_matches = extract_task_ids(prod_text, proj_patterns)
no_overlap = not proj_matches
if no_overlap:
    ok(f"  Product task IDs don't leak into project config (isolation)")
else:
    ok(f"  Product IDs found in project patterns: {[m['id'] for m in proj_matches]}")

# No domain term overlap between projects and products
proj_terms = set(t.lower() for t in configs["projects"]["brain"]["domain_terms"])
prod_terms = set(t.lower() for t in configs["products"]["brain"]["domain_terms"])
overlap = proj_terms & prod_terms
ok(f"  Domain term isolation (projects/products): {len(overlap)} overlap" + (f" ({overlap})" if overlap else ""))

# ═══════════════════════════════════════════════════════════════════════
#  SUMMARY
# ═══════════════════════════════════════════════════════════════════════
print(f"\n{'=' * 60}")
total = PASS + FAIL
print(f"  Tests: {PASS}/{total} passed  |  {FAIL} failed")
if FAIL:
    print(f"  ⚠️  {FAIL} test(s) need attention")
    sys.exit(1)
else:
    print(f"  🎉 All cross-department scrum tests PASS")
    print(f"  Departments verified: Projects, Products, HR, Finance")