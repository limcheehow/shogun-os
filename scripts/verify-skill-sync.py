#!/usr/bin/env python3
"""
E2E test suite for Shogun OS v3.1.0 — skill sync verification.

Tests that the synced/merged skills from the live installation are:
1. Present and non-trivial (not empty/stub)
2. Free of company-specific words
3. Structurally valid (YAML frontmatter, required sections)
4. Functionally complete (key functions/sections exist)
5. Python scripts pass syntax check
6. Internal references resolve (no broken links)

Run: python3 scripts/verify-skill-sync.py
"""

import ast
import os
import re
import sys
import yaml
from pathlib import Path

REPO = Path(__file__).resolve().parent.parent
SKILLS = REPO / "skills"

PASSED = 0
FAILED = 0
ERRORS = []


def ok(name, detail=""):
    global PASSED
    PASSED += 1
    print(f"  ✅ {name}" + (f" — {detail}" if detail else ""))


def fail(name, detail=""):
    global FAILED
    FAILED += 1
    ERRORS.append((name, detail))
    print(f"  ❌ {name}" + (f" — {detail}" if detail else ""))


def read_skill(path):
    """Read a SKILL.md file and return (frontmatter_dict, body_str)."""
    full = Path(path).read_text()
    # Parse YAML frontmatter
    match = re.match(r"^---\n(.*?)\n---\n(.*)", full, re.DOTALL)
    if not match:
        return {}, full
    try:
        fm = yaml.safe_load(match.group(1)) or {}
    except yaml.YAMLError:
        return {}, full
    return fm, match.group(2)


def check_no_company_words(path):
    """Check a file for company-specific words."""
    company_words = [
        "Tapway", "tapway", "SamurAI", "samurai",
        "gotapway", "cheehow", "DashScope", "dashscope",
        "C0ABY3VT4U8", "C0308PA6Y", "C09SR9B5WJU",
        "D0B0LU0HP4L", "U060MSDBQMQ",
    ]
    try:
        content = Path(path).read_text()
    except Exception:
        return True, []  # Binary or unreadable — skip
    found = [w for w in company_words if w in content]
    return len(found) == 0, found


def get_sections(body):
    """Extract ## section titles from markdown body."""
    return [line.strip() for line in body.splitlines() if line.startswith("## ")]


def get_functions(py_path):
    """Extract function names from a Python file."""
    try:
        content = Path(py_path).read_text()
        tree = ast.parse(content)
        return {node.name for node in ast.walk(tree) if isinstance(node, ast.FunctionDef)}
    except SyntaxError:
        return set()
    except Exception:
        return set()


# ══════════════════════════════════════════════════════════════════════
# TEST GROUP 1: profile-enrichment
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("TEST GROUP 1: profile-enrichment")
print("=" * 60)

pe_path = SKILLS / "profile-enrichment" / "SKILL.md"

if not pe_path.exists():
    fail("profile-enrichment SKILL.md exists")
else:
    fm, body = read_skill(pe_path)
    size = len(body)

    # 1.1 Non-trivial (>5K chars — live is 48K, repo was 3K)
    if size > 5000:
        ok("profile-enrichment is non-trivial", f"{size} chars")
    else:
        fail("profile-enrichment is non-trivial", f"only {size} chars — expected >5000")

    # 1.2 No company-specific words
    clean, found = check_no_company_words(pe_path)
    if clean:
        ok("profile-enrichment has no company-specific words")
    else:
        fail("profile-enrichment has no company-specific words", f"found: {found}")

    # 1.3 Has key sections from live
    sections = get_sections(body)
    required_sections = ["Triggers", "Prerequisites"]
    for req in required_sections:
        if any(req.lower() in s.lower() for s in sections):
            ok(f"profile-enrichment has '{req}' section")
        else:
            fail(f"profile-enrichment has '{req}' section", f"not found in {sections}")

    # 1.4 Has reference files (live has business-card-ingestion, spreadsheet-contact-enrichment)
    refs_dir = SKILLS / "profile-enrichment" / "references"
    if refs_dir.is_dir():
        ref_files = [f.name for f in refs_dir.iterdir() if f.suffix == ".md"]
        ok("profile-enrichment has references dir", f"{len(ref_files)} files: {ref_files}")
    else:
        fail("profile-enrichment has references dir", "no references/ directory")

    # 1.5 YAML frontmatter is valid
    if fm.get("name"):
        ok("profile-enrichment YAML frontmatter valid", f"name={fm['name']}")
    else:
        fail("profile-enrichment YAML frontmatter valid", "no 'name' field")


# ══════════════════════════════════════════════════════════════════════
# TEST GROUP 2: slack-formatting
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("TEST GROUP 2: slack-formatting")
print("=" * 60)

sf_path = SKILLS / "slack-formatting" / "SKILL.md"

if not sf_path.exists():
    fail("slack-formatting SKILL.md exists")
else:
    fm, body = read_skill(sf_path)
    size = len(body)
    sections = get_sections(body)

    # 2.1 Non-trivial (>15K chars — live is 21K)
    if size > 15000:
        ok("slack-formatting is non-trivial", f"{size} chars")
    else:
        fail("slack-formatting is non-trivial", f"only {size} chars — expected >15000")

    # 2.2 No company-specific words
    clean, found = check_no_company_words(sf_path)
    if clean:
        ok("slack-formatting has no company-specific words")
    else:
        fail("slack-formatting has no company-specific words", f"found: {found}")

    # 2.3 Has long-content handling section (Part 6 — critical for truncation prevention)
    if any("long-content" in s.lower() or "truncat" in s.lower() for s in sections):
        ok("slack-formatting has long-content/truncation section")
    else:
        fail("slack-formatting has long-content/truncation section", f"not found in {sections}")

    # 2.4 Has file uploads section (Part 7)
    if any("file upload" in s.lower() for s in sections):
        ok("slack-formatting has file uploads section")
    else:
        fail("slack-formatting has file uploads section", f"not found in {sections}")

    # 2.5 Has gateway pass-through section (Part 4b)
    if any("pass-through" in s.lower() or "passthrough" in s.lower() or "gateway" in s.lower() for s in sections):
        ok("slack-formatting has gateway pass-through section")
    else:
        fail("slack-formatting has gateway pass-through section", f"not found in {sections}")

    # 2.6 Has pipe table warning
    if "pipe table" in body.lower() or "garbage" in body.lower():
        ok("slack-formatting has pipe table warning")
    else:
        fail("slack-formatting has pipe table warning", "not found in body")


# ══════════════════════════════════════════════════════════════════════
# TEST GROUP 3: google_api.py
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("TEST GROUP 3: google-workspace/scripts/google_api.py")
print("=" * 60)

ga_path = SKILLS / "google-workspace" / "scripts" / "google_api.py"

if not ga_path.exists():
    fail("google_api.py exists")
else:
    funcs = get_functions(ga_path)
    size = ga_path.stat().st_size

    # 3.1 Non-trivial (>35K — live is 45K)
    if size > 35000:
        ok("google_api.py is non-trivial", f"{size} bytes")
    else:
        fail("google_api.py is non-trivial", f"only {size} bytes — expected >35000")

    # 3.2 Python syntax check
    try:
        ast.parse(ga_path.read_text())
        ok("google_api.py passes syntax check")
    except SyntaxError as e:
        fail("google_api.py passes syntax check", str(e))

    # 3.3 Has the 10 new functions from live
    required_funcs = [
        "docs_create", "docs_append", "drive_create_folder",
        "drive_download", "drive_upload", "drive_share",
        "drive_get", "drive_delete", "sheets_create",
    ]
    for fn in required_funcs:
        if fn in funcs:
            ok(f"google_api.py has function '{fn}'")
        else:
            fail(f"google_api.py has function '{fn}'", "not found")

    # 3.4 No company-specific words
    clean, found = check_no_company_words(ga_path)
    if clean:
        ok("google_api.py has no company-specific words")
    else:
        fail("google_api.py has no company-specific words", f"found: {found}")


# ══════════════════════════════════════════════════════════════════════
# TEST GROUP 4: gbrain-operations (merged — CLI ref + operational)
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("TEST GROUP 4: gbrain-operations")
print("=" * 60)

go_path = SKILLS / "gbrain-operations" / "SKILL.md"

if not go_path.exists():
    fail("gbrain-operations SKILL.md exists")
else:
    fm, body = read_skill(go_path)
    size = len(body)
    sections = get_sections(body)

    # 4.1 Has CLI reference sections (from repo — should be preserved)
    cli_sections = ["CLI Reference", "Quick Reference", "sync", "embed", "doctor"]
    has_cli = any(any(kw.lower() in s.lower() for kw in cli_sections) for s in sections)
    if has_cli:
        ok("gbrain-operations has CLI reference sections")
    else:
        fail("gbrain-operations has CLI reference sections", f"not found in {sections}")

    # 4.2 Has operational sections (from live — should be merged in)
    ops_sections = ["Core Loop", "Read", "Enrich", "Write", "Health", "PGLite", "git-synced"]
    has_ops = any(any(kw.lower() in s.lower() for kw in ops_sections) for s in sections)
    if has_ops:
        ok("gbrain-operations has operational sections (merged from live)")
    else:
        fail("gbrain-operations has operational sections", f"not found in {sections}")

    # 4.3 No company-specific words
    clean, found = check_no_company_words(go_path)
    if clean:
        ok("gbrain-operations has no company-specific words")
    else:
        fail("gbrain-operations has no company-specific words", f"found: {found}")

    # 4.4 Non-trivial (>12K — merged should be larger than either alone)
    if size > 12000:
        ok("gbrain-operations is non-trivial (merged)", f"{size} chars")
    else:
        fail("gbrain-operations is non-trivial (merged)", f"only {size} chars — expected >12000 after merge")


# ══════════════════════════════════════════════════════════════════════
# TEST GROUP 5: brain-compliance (merged — entity types + enforcement)
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("TEST GROUP 5: brain-compliance")
print("=" * 60)

bc_path = SKILLS / "brain-compliance" / "SKILL.md"

if not bc_path.exists():
    fail("brain-compliance SKILL.md exists")
else:
    fm, body = read_skill(bc_path)
    size = len(body)
    sections = get_sections(body)

    # 5.1 Has entity type standards (from repo)
    has_entity = any("entity" in s.lower() or "frontmatter" in s.lower() or "per-entity" in s.lower() for s in sections)
    if has_entity:
        ok("brain-compliance has entity type standards")
    else:
        fail("brain-compliance has entity type standards", f"not found in {sections}")

    # 5.2 Has enforcement architecture (from live)
    has_enforcement = any("enforce" in s.lower() or "pre-commit" in s.lower() or "audit" in s.lower() or "orphan" in s.lower() or "compliance baseline" in s.lower() or "conventions" in s.lower() for s in sections)
    if has_enforcement:
        ok("brain-compliance has enforcement architecture (merged from live)")
    else:
        fail("brain-compliance has enforcement architecture", f"not found in {sections}")

    # 5.3 No company-specific words
    clean, found = check_no_company_words(bc_path)
    if clean:
        ok("brain-compliance has no company-specific words")
    else:
        fail("brain-compliance has no company-specific words", f"found: {found}")

    # 5.4 Non-trivial
    if size > 5000:
        ok("brain-compliance is non-trivial", f"{size} chars")
    else:
        fail("brain-compliance is non-trivial", f"only {size} chars")


# ══════════════════════════════════════════════════════════════════════
# TEST GROUP 6: google-workspace (new references + rclone_configure.py)
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("TEST GROUP 6: google-workspace (new references + scripts)")
print("=" * 60)

gw_refs_dir = SKILLS / "google-workspace" / "references"
gw_scripts_dir = SKILLS / "google-workspace" / "scripts"

# 6.1 Has the 6 new reference files from live
new_refs = [
    "manual-oauth-callback.md",
    "rclone-sync-cron.md",
    "sa-dwd-usage-examples.md",
    "service-account-dwd-setup.md",
    "shared-drives.md",
    "web-application-oauth.md",
]
for ref in new_refs:
    ref_path = gw_refs_dir / ref
    if ref_path.exists():
        ok(f"google-workspace has reference '{ref}'")
    else:
        fail(f"google-workspace has reference '{ref}'", "file not found")

# 6.2 Has rclone_configure.py
rclone_path = gw_scripts_dir / "rclone_configure.py"
if rclone_path.exists():
    ok("google-workspace has rclone_configure.py")
    # Syntax check
    try:
        ast.parse(rclone_path.read_text())
        ok("rclone_configure.py passes syntax check")
    except SyntaxError as e:
        fail("rclone_configure.py passes syntax check", str(e))
else:
    fail("google-workspace has rclone_configure.py", "file not found")

# 6.3 No company-specific words in new references
for ref in new_refs:
    ref_path = gw_refs_dir / ref
    if ref_path.exists():
        clean, found = check_no_company_words(ref_path)
        if clean:
            ok(f"'{ref}' has no company-specific words")
        else:
            fail(f"'{ref}' has no company-specific words", f"found: {found}")


# ══════════════════════════════════════════════════════════════════════
# TEST GROUP 7: Global — no company words in ANY skill
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("TEST GROUP 7: Global — no company words in ALL skills")
print("=" * 60)

company_words = [
    "Tapway", "tapway", "SamurAI", "samurai",
    "gotapway", "cheehow", "DashScope", "dashscope",
]

all_clean = True
dirty_files = []
for root, dirs, files in os.walk(SKILLS):
    # Skip __pycache__
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for fname in files:
        fpath = Path(root) / fname
        clean, found = check_no_company_words(fpath)
        if not clean:
            all_clean = False
            dirty_files.append((str(fpath.relative_to(SKILLS)), found))

if all_clean:
    ok("ALL skills are company-word-free")
else:
    fail("ALL skills are company-word-free", f"{len(dirty_files)} files with company words")
    for fpath, words in dirty_files[:10]:
        print(f"         {fpath}: {words}")


# ══════════════════════════════════════════════════════════════════════
# TEST GROUP 8: All Python scripts pass syntax check
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("TEST GROUP 8: All Python scripts pass syntax check")
print("=" * 60)

all_syntax_ok = True
syntax_errors = []
for root, dirs, files in os.walk(SKILLS):
    dirs[:] = [d for d in dirs if d != "__pycache__"]
    for fname in files:
        if fname.endswith(".py"):
            fpath = Path(root) / fname
            try:
                ast.parse(fpath.read_text())
            except SyntaxError as e:
                all_syntax_ok = False
                syntax_errors.append((str(fpath.relative_to(SKILLS)), str(e)))

if all_syntax_ok:
    ok("ALL Python scripts pass syntax check")
else:
    fail("ALL Python scripts pass syntax check", f"{len(syntax_errors)} errors")
    for fpath, err in syntax_errors:
        print(f"         {fpath}: {err}")


# ══════════════════════════════════════════════════════════════════════
# TEST GROUP 9: YAML frontmatter valid for all SKILL.md files
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("TEST GROUP 9: YAML frontmatter valid for all SKILL.md files")
print("=" * 60)

all_yaml_ok = True
yaml_errors = []
for root, dirs, files in os.walk(SKILLS):
    for fname in files:
        if fname == "SKILL.md":
            fpath = Path(root) / fname
            full = fpath.read_text()
            match = re.match(r"^---\n(.*?)\n---\n", full, re.DOTALL)
            if not match:
                all_yaml_ok = False
                yaml_errors.append((str(fpath.relative_to(SKILLS)), "no frontmatter"))
                continue
            try:
                fm = yaml.safe_load(match.group(1))
                if not fm or not fm.get("name"):
                    all_yaml_ok = False
                    yaml_errors.append((str(fpath.relative_to(SKILLS)), "missing 'name' field"))
            except yaml.YAMLError as e:
                all_yaml_ok = False
                yaml_errors.append((str(fpath.relative_to(SKILLS)), str(e)))

if all_yaml_ok:
    ok("ALL SKILL.md files have valid YAML frontmatter with 'name' field")
else:
    fail("ALL SKILL.md files have valid YAML frontmatter", f"{len(yaml_errors)} errors")
    for fpath, err in yaml_errors:
        print(f"         {fpath}: {err}")


# ══════════════════════════════════════════════════════════════════════
# SUMMARY
# ══════════════════════════════════════════════════════════════════════
print("\n" + "=" * 60)
print("SUMMARY")
print("=" * 60)
total = PASSED + FAILED
print(f"  Total: {total} tests")
print(f"  Passed: {PASSED}")
print(f"  Failed: {FAILED}")
print(f"  Pass rate: {PASSED/total*100:.1f}%" if total > 0 else "  No tests run")

if FAILED > 0:
    print(f"\n  Failed tests:")
    for name, detail in ERRORS:
        print(f"    ❌ {name}: {detail}")

sys.exit(0 if FAILED == 0 else 1)
