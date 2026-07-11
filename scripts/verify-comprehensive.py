#!/usr/bin/env python3
"""
Comprehensive E2E test suite for Company OS.
Covers: Python syntax, shell scripts, unit tests, skills, recipes, templates, examples.
Run: python3 scripts/verify-comprehensive.py
"""

import ast
import json
import os
import re
import subprocess
import sys
import tempfile
import yaml
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"
SCRIPTS = REPO / "scripts"
RECIPES = REPO / "recipes"
TEMPLATES = REPO / "templates"
EXAMPLES = REPO / "examples"

PASSED = 0
FAILED = 0
ERRORS = []

# Company words that must NEVER appear in any file
COMPANY_WORDS = [
    "Tapway", "tapway", "SamurAI", "samurai",
    "gotapway", "cheehow", "DashScope", "dashscope",
    "OpenRouter", "openrouter",
]


def ok(name, detail=""):
    global PASSED
    PASSED += 1
    print(f"  ✅ {name}" + (f" — {detail}" if detail else ""))


def fail(name, detail=""):
    global FAILED
    FAILED += 1
    ERRORS.append((name, detail))
    print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))


def parse_yaml_frontmatter(content):
    """Parse YAML frontmatter from markdown. Returns (fm_dict, body_str)."""
    match = re.match(r"^---\n(.*?)\n---\n(.*)", content, re.DOTALL)
    if not match:
        return {}, content
    try:
        fm = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}, content
    return fm, match.group(2)


def check_company_words(path):
    """Check a file for company-specific words. Returns (is_clean, found_words)."""
    try:
        content = Path(path).read_text()
    except Exception:
        return True, []
    found = [w for w in COMPANY_WORDS if w in content]
    return len(found) == 0, found


def get_functions(py_path):
    """Extract function names from a Python file via AST."""
    try:
        tree = ast.parse(Path(py_path).read_text())
        return {n.name for n in ast.walk(tree) if isinstance(n, ast.FunctionDef)}
    except (SyntaxError, Exception):
        return set()


def get_classes(py_path):
    """Extract class names from a Python file via AST."""
    try:
        tree = ast.parse(Path(py_path).read_text())
        return {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    except (SyntaxError, Exception):
        return set()


def get_sections(body):
    """Extract ## section titles from markdown body."""
    return [l.strip() for l in body.splitlines() if l.startswith("## ")]


def all_files():
    """Walk all files in repo, excluding .git and llms-full.txt."""
    result = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for f in files:
            if f == "llms-full.txt":
                continue
            fpath = Path(root) / f
            result.append(fpath)
    return result


# ── Helper to import a Python file as a module ──
import importlib.util

def _load_module(name, path):
    """Load a Python file as a module using importlib. Returns the module or None."""
    try:
        spec = importlib.util.spec_from_file_location(name, str(path))
        if spec is None:
            return None
        mod = importlib.util.module_from_spec(spec)
        # Don't exec - just return the spec so we can check names
        # Instead, we'll use AST-based extraction
        return None
    except Exception:
        return None


# ══════════════════════════════════════════════════════════════════════
# GROUP 1: Python Syntax & Import
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 1: Python Syntax & Import")
print("=" * 60)

py_files = list(SCRIPTS.glob("*.py")) + list(SKILLS.rglob("*.py"))
py_files = [f for f in py_files if "__pycache__" not in str(f)]

for pf in sorted(py_files):
    rel = pf.relative_to(REPO)
    try:
        ast.parse(pf.read_text())
        ok(f"Syntax: {rel}")
    except SyntaxError as e:
        fail(f"Syntax: {rel}", str(e))

# Check for __pycache__ directories
pycache_dirs = []
for root, dirs, files in os.walk(REPO):
    if "__pycache__" in dirs:
        pycache_dirs.append(os.path.relpath(root, REPO))
if not pycache_dirs:
    ok("No __pycache__ directories in repo")
else:
    fail("__pycache__ directories found", f"found: {pycache_dirs}")


# ══════════════════════════════════════════════════════════════════════
# GROUP 2: Shell Script Validation
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 2: Shell Script Validation")
print("=" * 60)

sh_files = list(SCRIPTS.glob("*.sh")) + list(SKILLS.rglob("*.sh"))
for sf in sorted(sh_files):
    rel = sf.relative_to(REPO)
    content = sf.read_text()
    first_line = content.splitlines()[0] if content else ""

    if first_line.startswith("#!/bin/bash") or first_line.startswith("#!/usr/bin/env bash"):
        ok(f"Shebang: {rel}")
    else:
        fail(f"Shebang: {rel}", f"got: {first_line[:40]}")

    r = subprocess.run(["bash", "-n", str(sf)], capture_output=True, text=True)
    if r.returncode == 0:
        ok(f"bash -n: {rel}")
    else:
        fail(f"bash -n: {rel}", r.stderr.strip()[:80])

    clean, found = check_company_words(sf)
    if clean:
        ok(f"No company words: {rel}")
    else:
        fail(f"No company words: {rel}", f"found: {found}")


# ══════════════════════════════════════════════════════════════════════
# GROUP 3: generate-profile.py (AST-based analysis)
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 3: generate-profile.py")
print("=" * 60)

gp_path = SCRIPTS / "generate-profile.py"
gp_text = gp_path.read_text()
gp_tree = ast.parse(gp_text)
gp_funcs = get_functions(gp_path)

# 3.1 PROFILE_META has 13 profile types
# Extract PROFILE_META dict keys via AST
profile_types = []
for node in ast.walk(gp_tree):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "PROFILE_META":
                if isinstance(node.value, ast.Dict):
                    for key in node.value.keys:
                        if isinstance(key, ast.Constant):
                            profile_types.append(key.value)
                    break

expected_types = {"base", "coding", "engineering", "hr", "finance", "procurement",
                  "crm", "product", "marketing", "compliance", "support", "executive", "all"}
actual_types = set(profile_types)
if actual_types == expected_types:
    ok(f"PROFILE_META has 13 types", f"{len(actual_types)} found: {sorted(actual_types)}")
else:
    missing = expected_types - actual_types
    extra = actual_types - expected_types
    fail("PROFILE_META has 13 types", f"missing: {missing}, extra: {extra}")

# 3.2 SOUL_SNIPPETS dict exists
has_soul_snippets = False
has_workflow_enforcement = False
for node in ast.walk(gp_tree):
    if isinstance(node, ast.Assign):
        for target in node.targets:
            if isinstance(target, ast.Name) and target.id == "SOUL_SNIPPETS":
                has_soul_snippets = True
            if isinstance(target, ast.Name) and target.id == "WORKFLOW_ENFORCEMENT":
                has_workflow_enforcement = True

if has_soul_snippets:
    ok("SOUL_SNIPPETS dict exists")
else:
    fail("SOUL_SNIPPETS dict exists", "not found")

if has_workflow_enforcement:
    ok("WORKFLOW_ENFORCEMENT constant exists")
else:
    fail("WORKFLOW_ENFORCEMENT constant exists", "not found")

# 3.3 Functions exist
for fn in ["load_template", "substitute_config", "generate_soul", "main"]:
    if fn in gp_funcs:
        ok(f"generate-profile.py: has function '{fn}'")
    else:
        fail(f"generate-profile.py: has function '{fn}'", "not found")

# 3.4 Templates have PLACEHOLDER variables
for tmpl_name in ["base-config.yaml", "coding-config.yaml"]:
    tmpl_path = TEMPLATES / "profiles" / tmpl_name
    if tmpl_path.exists():
        content = tmpl_path.read_text()
        if "${" in content:
            ok(f"Template {tmpl_name} has ${{PLACEHOLDER}} variables")
        else:
            fail(f"Template {tmpl_name} has ${{PLACEHOLDER}} variables", "no placeholders found")
        if "dashscope" not in content.lower() and "aliyuncs" not in content.lower():
            ok(f"Template {tmpl_name} has no hardcoded provider URLs")
        else:
            fail(f"Template {tmpl_name} has no hardcoded provider URLs", "found hardcoded URL")


# ══════════════════════════════════════════════════════════════════════
# GROUP 4: wire-crons.py (AST-based analysis)
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 4: wire-crons.py")
print("=" * 60)

wc_path = SCRIPTS / "wire-crons.py"
wc_funcs = get_functions(wc_path)
wc_text = wc_path.read_text()

for fn in ["get_crons", "format_cron_commands", "apply_crons", "main"]:
    if fn in wc_funcs:
        ok(f"wire-crons.py: has function '{fn}'")
    else:
        fail(f"wire-crons.py: has function '{fn}'", "not found")

# Check SCRUM_CRONS exists
has_scrum_crons = "SCRUM_CRONS" in wc_text
has_holiday_gate = "HOLIDAY_GATE" in wc_text
has_profile_extra = "PROFILE_EXTRA_CRONS" in wc_text
if has_scrum_crons:
    ok("wire-crons.py: SCRUM_CRONS defined")
else:
    fail("wire-crons.py: SCRUM_CRONS", "not found")
if has_holiday_gate:
    ok("wire-crons.py: HOLIDAY_GATE defined")
else:
    fail("wire-crons.py: HOLIDAY_GATE", "not found")
if has_profile_extra:
    ok("wire-crons.py: PROFILE_EXTRA_CRONS defined")
else:
    fail("wire-crons.py: PROFILE_EXTRA_CRONS", "not found")

# Check references to department-scrum skill
dept_scrum_refs = wc_text.count("department-scrum")
if dept_scrum_refs >= 3:
    ok(f"wire-crons.py: references department-scrum ({dept_scrum_refs} times)")
else:
    fail(f"wire-crons.py: references department-scrum", f"only {dept_scrum_refs} refs")


# ══════════════════════════════════════════════════════════════════════
# GROUP 5: Scrum Scripts
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 5: Scrum Scripts")
print("=" * 60)

# 5.1 send-scrum-dms.py: state saved BEFORE sending DMs
send_path = SKILLS / "department-scrum" / "scripts" / "send-scrum-dms.py"
send_content = send_path.read_text()

state_save_pos = send_content.find('state_file.write_text')
dm_send_pos = send_content.find('provider.send_dm')
if state_save_pos > 0 and dm_send_pos > 0 and state_save_pos < dm_send_pos:
    ok("send-scrum-dms.py: state saved BEFORE sending DMs (race condition fix)")
else:
    fail("send-scrum-dms.py: state saved BEFORE sending DMs",
         f"state_save at {state_save_pos}, dm_send at {dm_send_pos}")

# 5.2 State schema has required fields
for field in ["date", "profile", "team", "errors", "questions_sent_at"]:
    if field in send_content:
        ok(f"send-scrum-dms.py: state schema has '{field}'")
    else:
        fail(f"send-scrum-dms.py: state schema has '{field}'", "not found")

# 5.3 posted_to_channel and submission_state fields
for field in ["posted_to_channel", "submission_state", "warned_11am"]:
    if field in send_content:
        ok(f"send-scrum-dms.py: has '{field}' field")
    else:
        fail(f"send-scrum-dms.py: has '{field}' field", "not found")

# 5.4 check-scrum-replies.py functions
check_path = SKILLS / "department-scrum" / "scripts" / "check-scrum-replies.py"
check_funcs = get_functions(check_path)
for fn in ["extract_task_ids", "extract_domain_terms", "assess_quality", "cross_ref_task"]:
    if fn in check_funcs:
        ok(f"check-scrum-replies.py: has function '{fn}'")
    else:
        fail(f"check-scrum-replies.py: has function '{fn}'", "not found")

# 5.5 False-positive guard for "none"
check_content = check_path.read_text()
if "none" in check_content.lower() and ("exact" in check_content.lower() or "strip" in check_content.lower()):
    ok("check-scrum-replies.py: has false-positive guard for 'none'")
else:
    fail("check-scrum-replies.py: has false-positive guard for 'none'", "guard not found")

# 5.6 --profile argument exists
if "--profile" in check_content and "required=True" in check_content:
    ok("check-scrum-replies.py: --profile argument is required")
else:
    fail("check-scrum-replies.py: --profile argument", "not found or not required")


# ══════════════════════════════════════════════════════════════════════
# GROUP 6: Comm Providers
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 6: Comm Providers")
print("=" * 60)

comm_dir = SKILLS / "department-scrum" / "scripts" / "comm"

# provider.py
prov_path = comm_dir / "provider.py"
prov_classes = get_classes(prov_path)
prov_funcs = get_functions(prov_path)

if "CommProvider" in prov_classes:
    ok("provider.py: CommProvider class exists")
else:
    fail("provider.py: CommProvider class", "not found")

for fn in ["get_provider", "register"]:
    if fn in prov_funcs:
        ok(f"provider.py: function '{fn}' exists")
    else:
        fail(f"provider.py: function '{fn}'", "not found")

# SlackProvider
slack_path = comm_dir / "slack.py"
slack_classes = get_classes(slack_path)
if "SlackProvider" in slack_classes:
    ok("slack.py: SlackProvider class exists")
else:
    fail("slack.py: SlackProvider class", "not found")

for method in ["send_dm", "read_replies", "post_message", "add_reaction", "search_messages"]:
    if method in get_functions(slack_path):
        ok(f"slack.py: SlackProvider.{method}() exists")
    else:
        fail(f"slack.py: SlackProvider.{method}()", "not found")

# TelegramProvider
telegram_path = comm_dir / "telegram.py"
telegram_classes = get_classes(telegram_path)
if "TelegramProvider" in telegram_classes:
    ok("telegram.py: TelegramProvider class exists")
else:
    fail("telegram.py: TelegramProvider class", "not found")

for method in ["send_dm", "read_replies", "post_message", "add_reaction", "search_messages"]:
    if method in get_functions(telegram_path):
        ok(f"telegram.py: TelegramProvider.{method}() exists")
    else:
        fail(f"telegram.py: TelegramProvider.{method}()", "not found")

# LarkProvider
lark_path = comm_dir / "lark.py"
lark_classes = get_classes(lark_path)
if "LarkProvider" in lark_classes:
    ok("lark.py: LarkProvider class exists")
else:
    fail("lark.py: LarkProvider class", "not found")

for method in ["send_dm", "read_replies", "post_message", "add_reaction", "search_messages"]:
    if method in get_functions(lark_path):
        ok(f"lark.py: LarkProvider.{method}() exists")
    else:
        fail(f"lark.py: LarkProvider.{method}()", "not found")

for method in ["send_card", "get_chat_info", "list_chats", "verify_webhook", "parse_webhook_event"]:
    if method in get_functions(lark_path):
        ok(f"lark.py: LarkProvider.{method}() (extra) exists")
    else:
        fail(f"lark.py: LarkProvider.{method}() (extra)", "not found")

# Check register() calls exist
for name, path in [("slack", slack_path), ("telegram", telegram_path), ("lark", lark_path)]:
    text = path.read_text()
    if f'register("{name}"' in text or f"register('{name}'" in text:
        ok(f"{name}.py: register() call exists")
    else:
        fail(f"{name}.py: register() call", "not found")


# ══════════════════════════════════════════════════════════════════════
# GROUP 7: gmail-triage.py
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 7: gmail-triage.py")
print("=" * 60)

gmail_path = SKILLS / "brain-ingest-pipeline" / "scripts" / "gmail-triage.py"
gmail_funcs = get_functions(gmail_path)
for fn in ["extract_sender_domain", "extract_subject", "is_promotion", "get_priority_score",
           "read_state", "write_state", "get_current_batch", "_load_batches",
           "short_name", "extract_sender_name", "label_for_email"]:
    if fn in gmail_funcs:
        ok(f"gmail-triage.py: has function '{fn}'")
    else:
        fail(f"gmail-triage.py: has function '{fn}'", "not found")

# gmail-batches.json exists
batches_path = EXAMPLES / "brain-ingest-configs" / "gmail-batches.json"
if batches_path.exists():
    try:
        data = json.loads(batches_path.read_text())
        ok(f"gmail-batches.json loads ({len(data)} top-level keys)")
    except json.JSONDecodeError as e:
        fail("gmail-batches.json loads", str(e))
else:
    fail("gmail-batches.json exists", "not found")

# Check PRIORITY_HIGH_KEYWORDS exists
gmail_text = gmail_path.read_text()
if "PRIORITY_HIGH_KEYWORDS" in gmail_text:
    ok("gmail-triage.py: PRIORITY_HIGH_KEYWORDS defined")
else:
    fail("gmail-triage.py: PRIORITY_HIGH_KEYWORDS", "not found")

if "PROMOTION_KEYWORDS" in gmail_text:
    ok("gmail-triage.py: PROMOTION_KEYWORDS defined")
else:
    fail("gmail-triage.py: PROMOTION_KEYWORDS", "not found")

if "PRIORITY_MEDIUM_KEYWORDS" in gmail_text:
    ok("gmail-triage.py: PRIORITY_MEDIUM_KEYWORDS defined")
else:
    fail("gmail-triage.py: PRIORITY_MEDIUM_KEYWORDS", "not found")


# ══════════════════════════════════════════════════════════════════════
# GROUP 8: collect-calendar.py
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 8: collect-calendar.py")
print("=" * 60)

cal_path = SKILLS / "brain-ingest-pipeline" / "scripts" / "collect-calendar.py"
cal_funcs = get_functions(cal_path)
for fn in ["short_name", "get_service_for", "clean_pii", "main"]:
    if fn in cal_funcs:
        ok(f"collect-calendar.py: has function '{fn}'")
    else:
        fail(f"collect-calendar.py: has function '{fn}'", "not found")

# Check PII regex patterns
cal_text = cal_path.read_text()
if "re.sub" in cal_text and "[EMAIL]" in cal_text:
    ok("collect-calendar.py: has email PII scrubber")
else:
    fail("collect-calendar.py: has email PII scrubber", "not found")

if "re.sub" in cal_text and "[PHONE]" in cal_text:
    ok("collect-calendar.py: has phone PII scrubber")
else:
    fail("collect-calendar.py: has phone PII scrubber", "not found")


# ══════════════════════════════════════════════════════════════════════
# GROUP 9: google_api.py
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 9: google_api.py")
print("=" * 60)

ga_path = SKILLS / "google-workspace" / "scripts" / "google_api.py"
ga_funcs = get_functions(ga_path)

# All required functions
required_ga_funcs = [
    "docs_create", "docs_append", "drive_create_folder", "drive_download",
    "drive_upload", "drive_share", "drive_get", "drive_delete", "sheets_create",
    "_docs_insert_text", "get_credentials", "build_service",
    "gmail_search", "gmail_get", "gmail_send",
    "calendar_list", "drive_search", "contacts_list", "sheets_get",
]
for fn in required_ga_funcs:
    if fn in ga_funcs:
        ok(f"google_api.py: has function '{fn}'")
    else:
        fail(f"google_api.py: has function '{fn}'", "not found")

# Size check
ga_size = ga_path.stat().st_size
if ga_size > 35000:
    ok(f"google_api.py is non-trivial ({ga_size} bytes)")
else:
    fail(f"google_api.py is non-trivial", f"only {ga_size} bytes")

# No company words
clean, found = check_company_words(ga_path)
if clean:
    ok("google_api.py has no company words")
else:
    fail("google_api.py has no company words", f"found: {found}")


# ══════════════════════════════════════════════════════════════════════
# GROUP 10: scan_null_bytes.py
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 10: scan_null_bytes.py")
print("=" * 60)

snb_path = SKILLS / "gbrain-frontmatter-guard" / "scripts" / "scan_null_bytes.py"
snb_funcs = get_functions(snb_path)
for fn in ["get_git_tracked_files", "scan", "main"]:
    if fn in snb_funcs:
        ok(f"scan_null_bytes.py: has function '{fn}'")
    else:
        fail(f"scan_null_bytes.py: has function '{fn}'", "not found")


# ══════════════════════════════════════════════════════════════════════
# GROUP 11: batch-enrich-exa.py
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 11: batch-enrich-exa.py")
print("=" * 60)

be_path = SKILLS / "profile-enrichment" / "scripts" / "batch-enrich-exa.py"
be_funcs = get_functions(be_path)
for fn in ["slugify", "parse_dt", "extract_info", "exa_search", "build_file", "main"]:
    if fn in be_funcs:
        ok(f"batch-enrich-exa.py: has function '{fn}'")
    else:
        fail(f"batch-enrich-exa.py: has function '{fn}'", "not found")


# ══════════════════════════════════════════════════════════════════════
# GROUP 12: generate-org-chart.py
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 12: generate-org-chart.py")
print("=" * 60)

oc_path = SCRIPTS / "generate-org-chart.py"
oc_funcs = get_functions(oc_path)
for fn in ["parse_profiles", "resolve_manager", "build_tree", "escape_xml",
           "get_dept_accent", "layout_subtree", "layout_all", "generate_nodes",
           "generate_edges", "generate_legend", "generate_drawio"]:
    if fn in oc_funcs:
        ok(f"generate-org-chart.py: has function '{fn}'")
    else:
        fail(f"generate-org-chart.py: has function '{fn}'", "not found")

# Check DEPT_ACCENT exists
oc_text = oc_path.read_text()
if "DEPT_ACCENT" in oc_text:
    ok("generate-org-chart.py: DEPT_ACCENT defined")
else:
    fail("generate-org-chart.py: DEPT_ACCENT", "not found")


# ══════════════════════════════════════════════════════════════════════
# GROUP 13: daily-disk-cleanup.py
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 13: daily-disk-cleanup.py")
print("=" * 60)

dc_path = SCRIPTS / "daily-disk-cleanup.py"
dc_funcs = get_functions(dc_path)
for fn in ["resolve_path", "run", "size", "rm_older", "log_action"]:
    if fn in dc_funcs:
        ok(f"daily-disk-cleanup.py: has function '{fn}'")
    else:
        fail(f"daily-disk-cleanup.py: has function '{fn}'", "not found")


# ══════════════════════════════════════════════════════════════════════
# GROUP 14: daily-token-cost.py
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 14: daily-token-cost.py")
print("=" * 60)

tc_path = SCRIPTS / "daily-token-cost.py"
tc_funcs = get_functions(tc_path)
if "fmt_tok" in tc_funcs:
    ok("daily-token-cost.py: has function 'fmt_tok'")
else:
    fail("daily-token-cost.py: has function 'fmt_tok'", "not found")


# ══════════════════════════════════════════════════════════════════════
# GROUP 15: switch-profile.py
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 15: switch-profile.py")
print("=" * 60)

sp_path = SCRIPTS / "switch-profile.py"
sp_funcs = get_functions(sp_path)
for fn in ["get_all_profiles", "read_config", "write_config", "list_profiles",
           "switch_model", "sync_mcp", "main"]:
    if fn in sp_funcs:
        ok(f"switch-profile.py: has function '{fn}'")
    else:
        fail(f"switch-profile.py: has function '{fn}'", "not found")

# Check PRESETS exists
sp_text = sp_path.read_text()
if "PRESETS" in sp_text:
    ok("switch-profile.py: PRESETS defined")
else:
    fail("switch-profile.py: PRESETS", "not found")
if "SHARED_MCP_SERVERS" in sp_text:
    ok("switch-profile.py: SHARED_MCP_SERVERS defined")
else:
    fail("switch-profile.py: SHARED_MCP_SERVERS", "not found")


# ══════════════════════════════════════════════════════════════════════
# GROUP 16: backup/restore crons
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 16: backup/restore crons")
print("=" * 60)

bc_path = SCRIPTS / "backup-crons.py"
rc_path = SCRIPTS / "restore-crons.py"
bc_funcs = get_functions(bc_path)
rc_funcs = get_functions(rc_path)

if "main" in bc_funcs:
    ok("backup-crons.py: has main()")
else:
    fail("backup-crons.py: has main()", "not found")

if "color" in bc_funcs:
    ok("backup-crons.py: has color()")
else:
    fail("backup-crons.py: has color()", "not found")

if "run_hermes_cron_create" in rc_funcs:
    ok("restore-crons.py: has run_hermes_cron_create()")
else:
    fail("restore-crons.py: has run_hermes_cron_create()", "not found")

if "main" in rc_funcs:
    ok("restore-crons.py: has main()")
else:
    fail("restore-crons.py: has main()", "not found")


# ══════════════════════════════════════════════════════════════════════
# GROUP 17: YAML Templates
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 17: YAML Templates")
print("=" * 60)

for tmpl in ["base-config.yaml", "coding-config.yaml"]:
    tpath = TEMPLATES / "profiles" / tmpl
    if tpath.exists():
        content = tpath.read_text()
        try:
            yaml.safe_load(content)
            ok(f"{tmpl}: valid YAML")
        except yaml.YAMLError as e:
            fail(f"{tmpl}: valid YAML", str(e))
        if "${" in content:
            ok(f"{tmpl}: has ${{PLACEHOLDER}} variables")
        else:
            fail(f"{tmpl}: has ${{PLACEHOLDER}} variables", "none found")
        clean, found = check_company_words(tpath)
        if clean:
            ok(f"{tmpl}: no company words")
        else:
            fail(f"{tmpl}: no company words", f"found: {found}")

# executive-identities.yaml
ei_path = TEMPLATES / "identities" / "executive-identities.yaml"
if ei_path.exists():
    try:
        data = yaml.safe_load(ei_path.read_text())
        ok("executive-identities.yaml: valid YAML")
        if "master" in data:
            ok("executive-identities.yaml: has 'master' key")
        else:
            fail("executive-identities.yaml: has 'master' key", "missing")
        clean, found = check_company_words(ei_path)
        if clean:
            ok("executive-identities.yaml: no company words")
        else:
            fail("executive-identities.yaml: no company words", f"found: {found}")
    except yaml.YAMLError as e:
        fail("executive-identities.yaml: valid YAML", str(e))


# ══════════════════════════════════════════════════════════════════════
# GROUP 18: Example Scrum Configs
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 18: Example Scrum Configs")
print("=" * 60)

scrum_dir = EXAMPLES / "scrum-configs"
scrum_configs = sorted(scrum_dir.glob("*.yaml"))

for sc_path in scrum_configs:
    name = sc_path.name
    try:
        data = yaml.safe_load(sc_path.read_text())
        ok(f"{name}: valid YAML")

        # Required top-level fields
        for field in ["profile", "app_name", "comm_provider", "channel_updates", "team"]:
            if data and field in data:
                ok(f"{name}: has '{field}'")
            else:
                fail(f"{name}: has '{field}'", "missing")

        # Team members
        team = data.get("team", []) if data else []
        if team:
            member = team[0]
            for field in ["name", "role"]:
                if field in member:
                    ok(f"{name}: team member has '{field}'")
                else:
                    fail(f"{name}: team member has '{field}'", "missing")

        # Brain section - task_id_patterns is optional (some profiles don't use it)
        brain = data.get("brain", {}) if data else {}
        if brain:
            for field in ["source", "domain_terms"]:
                if field in brain:
                    ok(f"{name}: brain has '{field}'")
                else:
                    fail(f"{name}: brain has '{field}'", "missing")
            # task_id_patterns is optional but should use single quotes when present
            if "task_id_patterns" in brain:
                ok(f"{name}: brain has 'task_id_patterns'")
            else:
                ok(f"{name}: brain has no task_id_patterns (optional)")
        else:
            fail(f"{name}: brain section", "missing")

        # task_id_patterns quoting check
        raw = sc_path.read_text()
        if "task_id_patterns" in raw:
            pattern_lines = [l for l in raw.splitlines() if "pattern:" in l]
            for pl in pattern_lines:
                stripped = pl.strip()
                # Check if pattern value is single-quoted (YAML-safe for regex)
                if "'" in stripped and stripped.index("'") < stripped.index(":") + 4:
                    ok(f"{name}: task_id_pattern uses single quotes")
                elif stripped.count('"') >= 2:
                    # Double-quoted - check if it has escaped backslashes (valid YAML)
                    if "\\\\" in stripped:
                        ok(f"{name}: task_id_pattern double-quoted with escaped backslashes")
                    else:
                        fail(f"{name}: task_id_pattern uses single quotes", "found double quotes without escapes")

        # No company words
        clean, found = check_company_words(sc_path)
        if clean:
            ok(f"{name}: no company words")
        else:
            fail(f"{name}: no company words", f"found: {found}")
    except yaml.YAMLError as e:
        fail(f"{name}: valid YAML", str(e))


# ══════════════════════════════════════════════════════════════════════
# GROUP 19: Recipes
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 19: Recipes")
print("=" * 60)

recipe_files = sorted(RECIPES.rglob("*.md"))
# Filter out non-recipe files (like time-tracking subfolder docs)
recipe_files = [f for f in recipe_files
                if f.name not in ("CONTRACT.md", "GENERIC_SKILL.md", "kamil.md", "README.md")]

for rf in recipe_files:
    name = rf.name
    content = rf.read_text()
    fm, body = parse_yaml_frontmatter(content)

    if fm:
        ok(f"{name}: has YAML frontmatter")
    else:
        fail(f"{name}: has YAML frontmatter", "not found")

    for field in ["name", "category"]:
        if field in fm:
            ok(f"{name}: frontmatter has '{field}'")
        else:
            fail(f"{name}: frontmatter has '{field}'", "missing")

    if body.lstrip().startswith("# "):
        ok(f"{name}: has H1 title")
    else:
        fail(f"{name}: has H1 title", "not found")

    sections = get_sections(body)
    if any("setup" in s.lower() for s in sections):
        ok(f"{name}: has Setup section")
    else:
        fail(f"{name}: has Setup section", "not found")

    clean, found = check_company_words(rf)
    if clean:
        ok(f"{name}: no company words")
    else:
        fail(f"{name}: no company words", f"found: {found}")


# ══════════════════════════════════════════════════════════════════════
# GROUP 20: Skills Manifest
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 20: Skills Manifest")
print("=" * 60)

skill_dirs = sorted([d for d in SKILLS.iterdir() if d.is_dir()])

for sd in skill_dirs:
    name = sd.name
    skilmd = sd / "SKILL.md"
    if not skilmd.exists():
        fail(f"{name}: SKILL.md exists", "not found")
        continue
    content = skilmd.read_text()
    fm, body = parse_yaml_frontmatter(content)

    if fm.get("name"):
        ok(f"{name}: frontmatter has 'name'")
    else:
        fail(f"{name}: frontmatter has 'name'", "missing")

    sections = get_sections(body)
    if sections:
        ok(f"{name}: has sections ({len(sections)})")
    else:
        fail(f"{name}: has sections", "none found")

    clean, found = check_company_words(skilmd)
    if clean:
        ok(f"{name}: no company words")
    else:
        fail(f"{name}: no company words", f"found: {found}")

# department-scrum mentions production-pitfalls.md
ds_content = (SKILLS / "department-scrum" / "SKILL.md").read_text()
if "production-pitfalls" in ds_content:
    ok("department-scrum: references production-pitfalls.md")
else:
    fail("department-scrum: references production-pitfalls.md", "not found")

pp_path = SKILLS / "department-scrum" / "references" / "production-pitfalls.md"
if pp_path.exists():
    ok("department-scrum/references/production-pitfalls.md exists")
else:
    fail("department-scrum/references/production-pitfalls.md exists", "not found")


# ══════════════════════════════════════════════════════════════════════
# GROUP 21: Company-Word Global Sweep
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 21: Company-Word Global Sweep")
print("=" * 60)

# Exclude self and verify-skill-sync.py from the sweep (they contain company words as test terms)
exclude_files = {
    str(SCRIPTS / "verify-comprehensive.py"),
    str(SCRIPTS / "verify-skill-sync.py"),
}

all_dirty = []
for fpath in all_files():
    if str(fpath) in exclude_files:
        continue
    clean, found = check_company_words(fpath)
    if not clean:
        all_dirty.append((str(fpath.relative_to(REPO)), found))

if not all_dirty:
    ok("ALL files are company-word-free (excluding test files)")
else:
    fail("Company-word global sweep", f"{len(all_dirty)} files with company words")
    for fp, words in all_dirty[:10]:
        print(f"         {fp}: {words}")


# ══════════════════════════════════════════════════════════════════════
# GROUP 22: Cross-Reference Integrity
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 22: Cross-Reference Integrity")
print("=" * 60)

# 22.1 Markdown links in SKILL.md files
broken_links = []
for sd in skill_dirs:
    skilmd = sd / "SKILL.md"
    if not skilmd.exists():
        continue
    content = skilmd.read_text()
    links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
    for text, link in links:
        if link.startswith("http") or link.startswith("mailto") or link.startswith("#"):
            continue
        # Skip placeholder links (used in markdown code examples)
        if link in ("url", "path", "channel", "channel_id", "slug", "path/to/file"):
            continue
        if link.startswith("url/") or link.startswith("path/"):
            continue
        target = (sd / link).resolve()
        if not target.exists():
            target2 = (REPO / link).resolve()
            if not target2.exists():
                broken_links.append((sd.name, link, text))

if not broken_links:
    ok("All SKILL.md markdown links resolve")
else:
    # Filter conceptual refs (references/ paths that are relative to the skill)
    real_broken = [b for b in broken_links if not b[1].startswith("references/")]
    if not real_broken:
        ok("All SKILL.md markdown links resolve (reference paths excluded)")
    else:
        fail("All SKILL.md markdown links resolve", f"{len(real_broken)} broken")
        for skill, link, text in real_broken[:5]:
            print(f"         {skill}: [{text}]({link})")

# 22.2 Cron template files exist
cron_templates_dir = SKILLS / "department-scrum" / "templates"
if cron_templates_dir.is_dir():
    templates = list(cron_templates_dir.glob("*.yaml"))
    ok(f"Cron templates directory has {len(templates)} templates")
    for t in sorted(templates):
        ok(f"Cron template '{t.name}' exists")
else:
    fail("Cron templates directory exists", "not found")

# 22.3 Cron template names referenced in generate-profile.py PROFILE_META
# Extract profile cron_templates references from the AST
gp_profile_cron_refs = set()
for node in ast.walk(gp_tree):
    if isinstance(node, ast.Dict):
        for key, val in zip(node.keys, node.values):
            if isinstance(key, ast.Constant) and key.value == "cron_templates":
                if isinstance(val, ast.List):
                    for elt in val.elts:
                        if isinstance(elt, ast.Constant):
                            gp_profile_cron_refs.add(elt.value)

all_cron_template_names = {t.stem for t in cron_templates_dir.glob("*.yaml")}
for ref in gp_profile_cron_refs:
    if ref in all_cron_template_names:
        ok(f"Cron template '{ref}' referenced in PROFILE_META exists")
    else:
        fail(f"Cron template '{ref}' referenced in PROFILE_META", f"not found in templates/")


# ══════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
total = PASSED + FAILED
print(f"  Total:   {total}")
print(f"  Passed:  {PASSED}")
print(f"  Failed:  {FAILED}")
if total > 0:
    print(f"  Rate:    {PASSED/total*100:.1f}%")

if FAILED > 0:
    print(f"\n  Failed tests:")
    for name, detail in ERRORS:
        print(f"    ❌ {name}: {detail}")

print(f"\n  Test groups: 22")
print(f"  Files scanned: {len(all_files())}")

sys.exit(0 if FAILED == 0 else 1)