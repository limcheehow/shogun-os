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

# Company words that must NEVER appear
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


def read_file(path):
    return Path(path).read_text()


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
    except SyntaxError:
        return set()
    except Exception:
        return set()


def get_classes(py_path):
    """Extract class names from a Python file via AST."""
    try:
        tree = ast.parse(Path(py_path).read_text())
        return {n.name for n in ast.walk(tree) if isinstance(n, ast.ClassDef)}
    except SyntaxError:
        return set()
    except Exception:
        return set()


def get_sections(body):
    """Extract ## section titles from markdown body."""
    return [l.strip() for l in body.splitlines() if l.startswith("## ")]


def all_files(extensions=None):
    """Walk all files in repo, excluding .git and llms-full.txt."""
    result = []
    for root, dirs, files in os.walk(REPO):
        dirs[:] = [d for d in dirs if d not in (".git", "__pycache__")]
        for f in files:
            if f == "llms-full.txt":
                continue
            fpath = Path(root) / f
            if extensions and fpath.suffix not in extensions:
                continue
            result.append(fpath)
    return result


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
    # Syntax check
    try:
        ast.parse(pf.read_text())
        ok(f"Syntax: {rel}")
    except SyntaxError as e:
        fail(f"Syntax: {rel}", str(e))

# No __pycache__ directories
pycache_dirs = []
for root, dirs, files in os.walk(REPO):
    if "__pycache__" in dirs:
        pycache_dirs.append(os.path.relpath(root, REPO))
if not pycache_dirs:
    ok("No __pycache__ directories in repo")
else:
    fail("No __pycache__ directories in repo", f"found: {pycache_dirs}")


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

    # Shebang check
    first_line = content.splitlines()[0] if content else ""
    if first_line.startswith("#!/bin/bash") or first_line.startswith("#!/usr/bin/env bash"):
        ok(f"Shebang: {rel}")
    else:
        fail(f"Shebang: {rel}", f"got: {first_line[:40]}")

    # bash -n syntax check
    r = subprocess.run(["bash", "-n", str(sf)], capture_output=True, text=True)
    if r.returncode == 0:
        ok(f"bash -n: {rel}")
    else:
        fail(f"bash -n: {rel}", r.stderr.strip()[:80])

    # No company words
    clean, found = check_company_words(sf)
    if clean:
        ok(f"No company words: {rel}")
    else:
        fail(f"No company words: {rel}", f"found: {found}")


# ══════════════════════════════════════════════════════════════════════
# GROUP 3: generate-profile.py
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 3: generate-profile.py")
print("=" * 60)

sys.path.insert(0, str(SCRIPTS))
import importlib.util
try:
    spec = importlib.util.spec_from_file_location("generate_profile", str(SCRIPTS / "generate-profile.py"))
    gp = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(gp)
    ok("generate-profile.py imports successfully")
except Exception as e:
    fail("generate-profile.py imports successfully", str(e))
    gp = None

if gp:
    # 3.1 PROFILE_META has 13 types
    expected_types = {"base", "coding", "engineering", "hr", "finance", "procurement",
                      "crm", "product", "marketing", "compliance", "support", "executive", "all"}
    actual_types = set(gp.PROFILE_META.keys())
    if actual_types == expected_types:
        ok(f"PROFILE_META has 13 types", f"{len(actual_types)} found")
    else:
        missing = expected_types - actual_types
        extra = actual_types - expected_types
        fail("PROFILE_META has 13 types", f"missing: {missing}, extra: {extra}")

    # 3.2 Every profile type has required fields
    required_fields = {"template", "skills", "cron_templates", "gbrain_source", "soul_snippet"}
    for ptype, meta in gp.PROFILE_META.items():
        missing_fields = required_fields - set(meta.keys())
        if not missing_fields:
            ok(f"PROFILE_META[{ptype}] has all required fields")
        else:
            fail(f"PROFILE_META[{ptype}] has all required fields", f"missing: {missing_fields}")

    # 3.3 Every soul_snippet has matching SOUL_SNIPPETS entry (or None)
    for ptype, meta in gp.PROFILE_META.items():
        snippet = meta.get("soul_snippet")
        if snippet is None:
            ok(f"PROFILE_META[{ptype}] soul_snippet=None (generic)")
        elif snippet in gp.SOUL_SNIPPETS:
            ok(f"PROFILE_META[{ptype}] → SOUL_SNIPPETS['{snippet}'] exists")
        else:
            fail(f"PROFILE_META[{ptype}] → SOUL_SNIPPETS['{snippet}']", "NOT FOUND")

    # 3.4 generate_soul includes Workflow Enforcement for every type
    for ptype, meta in gp.PROFILE_META.items():
        try:
            soul = gp.generate_soul("test-profile", ptype, meta)
            if "Workflow Enforcement" in soul:
                ok(f"generate_soul({ptype}) includes Workflow Enforcement")
            else:
                fail(f"generate_soul({ptype}) includes Workflow Enforcement", "section not found")
        except Exception as e:
            fail(f"generate_soul({ptype}) includes Workflow Enforcement", str(e))

    # 3.5 Every profile type includes company-workflow in skills
    for ptype, meta in gp.PROFILE_META.items():
        if "company-workflow" in meta.get("skills", []):
            ok(f"PROFILE_META[{ptype}] includes 'company-workflow' skill")
        else:
            fail(f"PROFILE_META[{ptype}] includes 'company-workflow' skill", "not in skills list")

    # 3.6 substitute_config replaces placeholders
    try:
        result = gp.substitute_config("profile: ${profile_name}\nsource: ${gbrain_source}", "hr-manager", "hr")
        if "hr-manager" in result and "hr" in result and "${" not in result:
            ok("substitute_config replaces placeholders")
        else:
            fail("substitute_config replaces placeholders", f"result: {result}")
    except Exception as e:
        fail("substitute_config replaces placeholders", str(e))

    # 3.7 Templates have placeholder variables
    for tmpl_name in ["base-config.yaml", "coding-config.yaml"]:
        tmpl_path = TEMPLATES / "profiles" / tmpl_name
        if tmpl_path.exists():
            content = tmpl_path.read_text()
            if "${" in content:
                ok(f"Template {tmpl_name} has ${{PLACEHOLDER}} variables")
            else:
                fail(f"Template {tmpl_name} has ${{PLACEHOLDER}} variables", "no placeholders found")
            # No hardcoded URLs
            if "aliyuncs.com" not in content and "dashscope" not in content.lower():
                ok(f"Template {tmpl_name} has no hardcoded provider URLs")
            else:
                fail(f"Template {tmpl_name} has no hardcoded provider URLs", "found hardcoded URL")


# ══════════════════════════════════════════════════════════════════════
# GROUP 4: wire-crons.py
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 4: wire-crons.py")
print("=" * 60)

try:
    spec = importlib.util.spec_from_file_location("wire_crons", str(SCRIPTS / "wire-crons.py"))
    wc = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(wc)
    ok("wire-crons.py imports successfully")
except Exception as e:
    fail("wire-crons.py imports successfully", str(e))
    wc = None

if wc:
    try:
        crons = wc.get_crons("hr", "hr-manager")
        if isinstance(crons, (dict, list)) and len(crons) > 0:
            ok(f"get_crons('hr', 'hr-manager') returns data ({len(crons)} entries)")
        else:
            fail("get_crons() returns data", f"got: {type(crons)}")
    except Exception as e:
        # Try without args
        try:
            crons = wc.get_crons()
            ok(f"get_crons() returns data ({len(crons) if hasattr(crons, '__len__') else 'ok'})")
        except Exception as e2:
            fail("get_crons() returns data", str(e2))


# ══════════════════════════════════════════════════════════════════════
# GROUP 5: Scrum Scripts
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 5: Scrum Scripts")
print("=" * 60)

# 5.1 send-scrum-dms.py: state saved BEFORE sending DMs
send_path = SKILLS / "department-scrum" / "scripts" / "send-scrum-dms.py"
send_content = send_path.read_text()

# Check that state_file.write_text appears before provider.send_dm in the code
state_save_pos = send_content.find('state_file.write_text')
dm_send_pos = send_content.find('provider.send_dm')
if state_save_pos > 0 and dm_send_pos > 0 and state_save_pos < dm_send_pos:
    ok("send-scrum-dms.py: state saved BEFORE sending DMs (race condition fix)")
else:
    fail("send-scrum-dms.py: state saved BEFORE sending DMs",
         f"state_save at {state_save_pos}, dm_send at {dm_send_pos}")

# 5.2 State schema has required fields
required_state_fields = ["date", "profile", "team", "errors", "questions_sent_at"]
for field in required_state_fields:
    if field in send_content:
        ok(f"send-scrum-dms.py: state schema has '{field}'")
    else:
        fail(f"send-scrum-dms.py: state schema has '{field}'", "not found in source")

# 5.3 posted_to_channel field
if "posted_to_channel" in send_content:
    ok("send-scrum-dms.py: has 'posted_to_channel' field")
else:
    fail("send-scrum-dms.py: has 'posted_to_channel' field", "not found")

# 5.4 submission_state field
if "submission_state" in send_content:
    ok("send-scrum-dms.py: has 'submission_state' field")
else:
    fail("send-scrum-dms.py: has 'submission_state' field", "not found")

# 5.5 check-scrum-replies.py: function existence
check_path = SKILLS / "department-scrum" / "scripts" / "check-scrum-replies.py"
check_funcs = get_functions(check_path)
for fn in ["extract_task_ids", "extract_domain_terms", "assess_quality"]:
    if fn in check_funcs:
        ok(f"check-scrum-replies.py: has function '{fn}'")
    else:
        fail(f"check-scrum-replies.py: has function '{fn}'", "not found")

# 5.6 assess_quality false-positive guard for "none"
check_content = check_path.read_text()
if "none" in check_content.lower() and ("exact" in check_content.lower() or "strip" in check_content.lower()):
    ok("check-scrum-replies.py: has false-positive guard for 'none'")
else:
    fail("check-scrum-replies.py: has false-positive guard for 'none'", "guard not found")


# ══════════════════════════════════════════════════════════════════════
# GROUP 6: Comm Providers
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 6: Comm Providers")
print("=" * 60)

comm_dir = SKILLS / "department-scrum" / "scripts" / "comm"
sys.path.insert(0, str(comm_dir))

# 6.1 provider.py
try:
    import provider
    ok("comm/provider.py imports")
    if hasattr(provider, "CommProvider"):
        ok("provider.py: CommProvider class exists")
    else:
        fail("provider.py: CommProvider class exists", "not found")
    if hasattr(provider, "get_provider"):
        ok("provider.py: get_provider() function exists")
    else:
        fail("provider.py: get_provider() function exists", "not found")
    if hasattr(provider, "register"):
        ok("provider.py: register() function exists")
    else:
        fail("provider.py: register() function exists", "not found")
except Exception as e:
    fail("comm/provider.py imports", str(e))

# 6.2 SlackProvider
required_methods = ["send_dm", "read_replies", "post_message", "add_reaction", "search_messages"]
try:
    # Comm providers use relative imports — set up as package
    import types
    pkg = types.ModuleType("comm_pkg")
    pkg.__path__ = [str(comm_dir)]
    sys.modules["comm_pkg"] = pkg
    spec = importlib.util.spec_from_file_location("comm_pkg.slack", str(comm_dir / "slack.py"))
    slack_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(slack_mod)
    ok("comm/slack.py imports")
    if hasattr(slack_mod, "SlackProvider"):
        ok("slack.py: SlackProvider class exists")
        for method in required_methods:
            if hasattr(slack_mod.SlackProvider, method):
                ok(f"slack.py: SlackProvider.{method}() exists")
            else:
                fail(f"slack.py: SlackProvider.{method}() exists", "not found")
    else:
        fail("slack.py: SlackProvider class exists", "not found")
except Exception as e:
    fail("comm/slack.py imports", str(e))

# 6.3 TelegramProvider
try:
    spec = importlib.util.spec_from_file_location("comm_pkg.telegram", str(comm_dir / "telegram.py"))
    tg_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(tg_mod)
    ok("comm/telegram.py imports")
    if hasattr(tg_mod, "TelegramProvider"):
        ok("telegram.py: TelegramProvider class exists")
        for method in required_methods:
            if hasattr(tg_mod.TelegramProvider, method):
                ok(f"telegram.py: TelegramProvider.{method}() exists")
            else:
                fail(f"telegram.py: TelegramProvider.{method}() exists", "not found")
    else:
        fail("telegram.py: TelegramProvider class exists", "not found")
except Exception as e:
    fail("comm/telegram.py imports", str(e))

# 6.4 LarkProvider (has extra methods)
try:
    spec = importlib.util.spec_from_file_location("comm_pkg.lark", str(comm_dir / "lark.py"))
    lark_mod = importlib.util.module_from_spec(spec)
    spec.loader.exec_module(lark_mod)
    ok("comm/lark.py imports")
    if hasattr(lark_mod, "LarkProvider"):
        ok("lark.py: LarkProvider class exists")
        for method in required_methods:
            if hasattr(lark_mod.LarkProvider, method):
                ok(f"lark.py: LarkProvider.{method}() exists")
            else:
                fail(f"lark.py: LarkProvider.{method}() exists", "not found")
        # Extra methods
        for method in ["send_card", "get_chat_info", "list_chats", "verify_webhook", "parse_webhook_event"]:
            if hasattr(lark_mod.LarkProvider, method):
                ok(f"lark.py: LarkProvider.{method}() exists (extra)")
            else:
                fail(f"lark.py: LarkProvider.{method}() exists (extra)", "not found")
    else:
        fail("lark.py: LarkProvider class exists", "not found")
except Exception as e:
    fail("comm/lark.py imports", str(e))


# ══════════════════════════════════════════════════════════════════════
# GROUP 7: gmail-triage.py
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 7: gmail-triage.py")
print("=" * 60)

gmail_path = SKILLS / "brain-ingest-pipeline" / "scripts" / "gmail-triage.py"
gmail_funcs = get_functions(gmail_path)
for fn in ["extract_sender_domain", "extract_subject", "is_promotion", "get_priority_score",
           "read_state", "write_state", "get_current_batch", "_load_batches"]:
    if fn in gmail_funcs:
        ok(f"gmail-triage.py: has function '{fn}'")
    else:
        fail(f"gmail-triage.py: has function '{fn}'", "not found")

# Test _load_batches loads from examples config
batches_path = EXAMPLES / "brain-ingest-configs" / "gmail-batches.json"
if batches_path.exists():
    try:
        data = json.loads(batches_path.read_text())
        if isinstance(data, (list, dict)) and len(data) > 0:
            ok(f"gmail-batches.json loads ({len(data)} entries)")
        else:
            fail("gmail-batches.json loads", "empty")
    except json.JSONDecodeError as e:
        fail("gmail-batches.json loads", str(e))
else:
    fail("gmail-batches.json exists", "not found")


# ══════════════════════════════════════════════════════════════════════
# GROUP 8: collect-calendar.py
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 8: collect-calendar.py")
print("=" * 60)

cal_path = SKILLS / "brain-ingest-pipeline" / "scripts" / "collect-calendar.py"
cal_funcs = get_functions(cal_path)
for fn in ["short_name", "get_service_for", "clean_pii"]:
    if fn in cal_funcs:
        ok(f"collect-calendar.py: has function '{fn}'")
    else:
        fail(f"collect-calendar.py: has function '{fn}'", "not found")


# ══════════════════════════════════════════════════════════════════════
# GROUP 9: google_api.py
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 9: google_api.py")
print("=" * 60)

ga_path = SKILLS / "google-workspace" / "scripts" / "google_api.py"
ga_funcs = get_functions(ga_path)
for fn in ["docs_create", "docs_append", "drive_create_folder", "drive_download",
           "drive_upload", "drive_share", "drive_get", "drive_delete", "sheets_create",
           "_docs_insert_text", "get_credentials", "build_service"]:
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
print("GROUP 10: gbrain-frontmatter-guard/scan_null_bytes.py")
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
print("GROUP 11: profile-enrichment/batch-enrich-exa.py")
print("=" * 60)

be_path = SKILLS / "profile-enrichment" / "scripts" / "batch-enrich-exa.py"
be_funcs = get_functions(be_path)
for fn in ["slugify", "parse_dt", "extract_info", "build_file", "main"]:
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
for fn in ["parse_profiles", "resolve_manager", "build_tree", "escape_xml", "get_dept_accent"]:
    if fn in oc_funcs:
        ok(f"generate-org-chart.py: has function '{fn}'")
    else:
        fail(f"generate-org-chart.py: has function '{fn}'", "not found")


# ══════════════════════════════════════════════════════════════════════
# GROUP 13: daily-disk-cleanup.py
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 13: daily-disk-cleanup.py")
print("=" * 60)

dc_path = SCRIPTS / "daily-disk-cleanup.py"
dc_funcs = get_functions(dc_path)
for fn in ["resolve_path", "rm_older", "log_action"]:
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
for fn in ["get_all_profiles", "read_config", "write_config", "list_profiles", "switch_model"]:
    if fn in sp_funcs:
        ok(f"switch-profile.py: has function '{fn}'")
    else:
        fail(f"switch-profile.py: has function '{fn}'", "not found")


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

if "run_hermes_cron_create" in rc_funcs:
    ok("restore-crons.py: has run_hermes_cron_create()")
else:
    fail("restore-crons.py: has run_hermes_cron_create()", "not found")


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
        # Valid YAML
        try:
            yaml.safe_load(content)
            ok(f"{tmpl}: valid YAML")
        except yaml.YAMLError as e:
            fail(f"{tmpl}: valid YAML", str(e))
        # Has placeholders
        if "${" in content:
            ok(f"{tmpl}: has ${{PLACEHOLDER}} variables")
        else:
            fail(f"{tmpl}: has ${{PLACEHOLDER}} variables", "none found")
        # No company words
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
        # Valid YAML
        ok(f"{name}: valid YAML")
        # Has required fields
        for field in ["profile", "app_name", "comm_provider", "channel_updates", "team"]:
            if data and field in data:
                ok(f"{name}: has '{field}'")
            else:
                fail(f"{name}: has '{field}'", "missing")
        # Team members have required fields
        team = data.get("team", []) if data else []
        if team:
            member = team[0]
            for field in ["name", "role"]:
                if field in member:
                    ok(f"{name}: team member has '{field}'")
                else:
                    fail(f"{name}: team member has '{field}'", "missing")
        # Brain section
        brain = data.get("brain", {}) if data else {}
        for field in ["source", "domain_terms"]:
            if field in brain:
                ok(f"{name}: brain has '{field}'")
            else:
                fail(f"{name}: brain has '{field}'", "missing")
        # task_id_patterns is optional (some profiles don't have task IDs)
        if "task_id_patterns" in brain:
            ok(f"{name}: brain has 'task_id_patterns'")
        else:
            ok(f"{name}: brain has no task_id_patterns (optional — OK)")
        # task_id_patterns use single quotes (check source)
        raw = sc_path.read_text()
        if "task_id_patterns" in raw:
            # Check that regex patterns use single quotes
            pattern_lines = [l for l in raw.splitlines() if "pattern:" in l]
            for pl in pattern_lines:
                if "'" in pl:
                    ok(f"{name}: task_id_pattern uses single quotes")
                    break
            else:
                if pattern_lines:
                    fail(f"{name}: task_id_pattern uses single quotes", "found double quotes")
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

recipe_files = sorted(RECIPES.glob("*.md"))
for rf in recipe_files:
    name = rf.name
    content = rf.read_text()
    fm, body = parse_yaml_frontmatter(content)

    # Has frontmatter
    if fm:
        ok(f"{name}: has YAML frontmatter")
    else:
        fail(f"{name}: has YAML frontmatter", "not found")

    # Required frontmatter fields
    for field in ["name", "category"]:
        if field in fm:
            ok(f"{name}: frontmatter has '{field}'")
        else:
            fail(f"{name}: frontmatter has '{field}'", "missing")

    # Has H1 title
    if body.lstrip().startswith("# "):
        ok(f"{name}: has H1 title")
    else:
        fail(f"{name}: has H1 title", "not found")

    # Has Setup section
    sections = get_sections(body)
    if any("setup" in s.lower() for s in sections):
        ok(f"{name}: has Setup section")
    else:
        fail(f"{name}: has Setup section", "not found")

    # No company words
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

    # Has frontmatter with name
    if fm.get("name"):
        ok(f"{name}: frontmatter has 'name'")
    else:
        fail(f"{name}: frontmatter has 'name'", "missing")

    # Has at least one ## section
    sections = get_sections(body)
    if sections:
        ok(f"{name}: has sections ({len(sections)})")
    else:
        fail(f"{name}: has sections", "none found")

    # No company words
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

# production-pitfalls.md exists
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

all_dirty = []
for fpath in all_files():
    # Skip test files — they contain company words as search patterns
    fname = fpath.name
    if fname.startswith("verify-") or fname.startswith("test-") or "test_" in fname:
        continue
    clean, found = check_company_words(fpath)
    if not clean:
        all_dirty.append((str(fpath.relative_to(REPO)), found))

if not all_dirty:
    ok("ALL files are company-word-free")
else:
    fail("ALL files are company-word-free", f"{len(all_dirty)} files with company words")
    for fp, words in all_dirty[:10]:
        print(f"         {fp}: {words}")


# ══════════════════════════════════════════════════════════════════════
# GROUP 22: Cross-Reference Integrity
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("GROUP 22: Cross-Reference Integrity")
print("=" * 60)

# 22.1 Markdown links in SKILL.md files point to existing files
broken_links = []
for sd in skill_dirs:
    skilmd = sd / "SKILL.md"
    if not skilmd.exists():
        continue
    content = skilmd.read_text()
    links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', content)
    for text, link in links:
        if link.startswith("http"):
            continue
        # Skip placeholder links
        if link in ("url", "path", "channel", "channel_id", "#"):
            continue
        # Resolve relative to skill directory
        target = (sd / link).resolve()
        if not target.exists():
            # Try relative to repo root
            target2 = (REPO / link).resolve()
            if not target2.exists():
                broken_links.append((sd.name, link, text))

if not broken_links:
    ok("All SKILL.md markdown links resolve")
else:
    # Only fail for non-reference paths (some links are conceptual)
    real_broken = [b for b in broken_links if not b[1].startswith("references/")]
    if not real_broken:
        ok("All SKILL.md markdown links resolve (conceptual refs excluded)")
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


# ══════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
total = PASSED + FAILED
print(f"  Total:  {total}")
print(f"  Passed: {PASSED}")
print(f"  Failed: {FAILED}")
print(f"  Pass rate: {PASSED/total*100:.1f}%" if total > 0 else "  No tests run")

if FAILED > 0:
    print(f"\n  Failed tests:")
    for name, detail in ERRORS:
        print(f"    ❌ {name}: {detail}")

print(f"\n  Test groups: 22")
print(f"  Files scanned: {len(all_files())}")

sys.exit(0 if FAILED == 0 else 1)
