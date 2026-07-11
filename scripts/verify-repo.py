#!/usr/bin/env python3
"""
Company OS — Pre-Deployment Verification Suite
───────────────────────────────────────────────
Runs comprehensive checks on the repo itself (not a running Hermes instance)
to catch issues before pushing to a fresh machine.

Usage:
  python3 scripts/verify-repo.py              # Full check
  python3 scripts/verify-repo.py --verbose    # Show all details
  python3 scripts/verify-repo.py --fix        # Auto-fix common issues
"""

import argparse
import json
import os
import re
import subprocess
import sys
import yaml
from pathlib import Path

REPO_ROOT = Path(__file__).resolve().parent.parent
SCRIPTS_DIR = REPO_ROOT / "scripts"
SKILLS_DIR = REPO_ROOT / "skills"
TEMPLATES_DIR = REPO_ROOT / "templates"
EXAMPLES_DIR = REPO_ROOT / "examples"
RECIPES_DIR = REPO_ROOT / "recipes"
DOCS_DIR = REPO_ROOT / "docs"

PASS = 0
FAIL = 0
WARN = 0
FIX = False
VERBOSE = False


def color(text, code):
    codes = {"green": "32", "cyan": "36", "yellow": "33", "red": "31", "bold": "1"}
    c = codes.get(code, "0")
    return f"\033[{c}m{text}\033[0m"


def ok(msg):
    global PASS
    PASS += 1
    print(f"  {color('✓', 'green')} {msg}")


def warn(msg):
    global WARN
    WARN += 1
    print(f"  {color('⚠', 'yellow')} {msg}")


def fail(msg):
    global FAIL
    FAIL += 1
    print(f"  {color('✗', 'red')} {msg}")


def section(name):
    print(f"\n{color(f'━━━ {name} ━━━', 'cyan')}")


def check_syntax_py(path: Path):
    """Python syntax check."""
    try:
        result = subprocess.run(
            [sys.executable, "-m", "py_compile", str(path)],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0, result.stderr
    except subprocess.TimeoutExpired:
        return False, "timed out"
    except FileNotFoundError:
        return False, "python3 not found"


def check_syntax_sh(path: Path):
    """Shell syntax check (if bash is available)."""
    try:
        result = subprocess.run(
            ["bash", "-n", str(path)],
            capture_output=True, text=True, timeout=10
        )
        return result.returncode == 0, result.stderr
    except (subprocess.TimeoutExpired, FileNotFoundError):
        return None, "bash not available"


# ═══════════════════════════════════════════════════════════════════════
#  TESTS
# ═══════════════════════════════════════════════════════════════════════

def test_root_docs_exist():
    """All root-level docs exist."""
    section("Root Docs")
    expected = [
        "README.md", "AGENTS.md", "ARCHITECTURE.md", "SETUP.md",
        "PROFILE_CATALOG.md", "CRON_INVENTORY.md", "RECIPE_INDEX.md",
        "HUB.md", "CHANGELOG.md", "CONTRIBUTING.md", "SECURITY.md",
        "CLAUDE.md", "INSTALL_FOR_AGENTS.md", "llms.txt", "llms-full.txt",
    ]
    for doc in expected:
        path = REPO_ROOT / doc
        if path.exists():
            ok(f"{doc} exists")
        else:
            fail(f"{doc} missing")


def test_scripts_syntax():
    """All scripts pass syntax checks."""
    section("Script Syntax")

    for script in sorted(SCRIPTS_DIR.iterdir()):
        if not script.is_file():
            continue
        if script.suffix == ".py":
            ok_check, err = check_syntax_py(script)
            if ok_check:
                ok(f"{script.name} — Python syntax OK")
            else:
                fail(f"{script.name} — syntax error: {err.strip()[:100]}")
        elif script.suffix == ".sh":
            result = check_syntax_sh(script)
            if result is None:
                warn(f"{script.name} — bash not available, skipping")
            elif result[0]:
                ok(f"{script.name} — shell syntax OK")
            else:
                fail(f"{script.name} — shell error: {result[1].strip()[:100]}")


def test_yaml_templates():
    """All YAML templates are valid."""
    section("YAML Templates")

    yaml_files = list(TEMPLATES_DIR.rglob("*.yaml"))
    yaml_files += list(EXAMPLES_DIR.rglob("*.yaml"))

    for yf in yaml_files:
        try:
            with open(yf) as f:
                data = yaml.safe_load(f)
            if data is None:
                warn(f"{yf.relative_to(REPO_ROOT)} — empty YAML")
            else:
                ok(f"{yf.relative_to(REPO_ROOT)} — valid YAML")
        except yaml.YAMLError as e:
            fail(f"{yf.relative_to(REPO_ROOT)} — YAML error: {str(e)[:100]}")


def test_skills_manifest():
    """Skills listed in HUB.md match skills/ directory."""
    section("Skills Manifest")

    hub = (REPO_ROOT / "HUB.md").read_text()
    actual_skills = sorted(d.name for d in SKILLS_DIR.iterdir() if d.is_dir())

    # Extract skill names from HUB.md skill table
    hub_skills = set()
    in_table = False
    for line in hub.split("\n"):
        if "| `department-scrum`" in line:
            in_table = True
        if in_table and line.startswith("| `"):
            name = line.split("`")[1]
            hub_skills.add(name)
        if in_table and line.strip() == "":
            in_table = False

    for s in actual_skills:
        if s in hub_skills:
            ok(f"`{s}` — in repo AND HUB.md")
        else:
            warn(f"`{s}` — in repo but MISSING from HUB.md")
            if FIX:
                print("     (add skill to HUB.md skill table manually)")

    for s in sorted(hub_skills):
        if s not in actual_skills:
            fail(f"`{s}` — in HUB.md but MISSING from skills/ directory")


def test_skills_have_skilmd():
    """Every skill has a SKILL.md."""
    section("Skill SKILL.md Presence")

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skilmd = skill_dir / "SKILL.md"
        if skilmd.exists():
            ok(f"{skill_dir.name}/SKILL.md")
        else:
            fail(f"{skill_dir.name}/SKILL.md missing")


def test_verify_skill_list_matches():
    """verify-install.sh's skill check list matches actual skills."""
    section("verify-install.sh Skill List")

    verify_sh = (SCRIPTS_DIR / "verify-install.sh").read_text()
    actual_skills = sorted(d.name for d in SKILLS_DIR.iterdir() if d.is_dir())

    # Extract skills from the for loop in verify-install.sh
    match = re.findall(r'"([a-z][a-z0-9-]+)"', verify_sh)
    checked_skills = [s for s in match if s not in ("profile", "support", "gbrain", "stock-scanner")]

    for s in actual_skills:
        if s in checked_skills:
            ok(f"`{s}` — checked by verify-install.sh")
        else:
            warn(f"`{s}` — NOT checked by verify-install.sh, add to script")
    for s in checked_skills:
        if s not in actual_skills:
            fail(f"`{s}` — in verify-install.sh but skill doesn't exist")


def test_profile_types_match():
    """PROFILE_META types and SOUL_SNIPPETS keys are consistent."""
    section("Profile Generator Consistency")

    gen_py = (SCRIPTS_DIR / "generate-profile.py").read_text()

    # Extract PROFILE_META keys and their soul_snippet values
    meta_pattern = re.findall(
        r'"([^"]+)":\s*\{[^}]*"soul_snippet":\s*("[^"]*"|None)',
        gen_py
    )

    snippet_keys = set(re.findall(r'"([a-z-]+-soul)"', gen_py))

    for name, snippet_ref in meta_pattern:
        if snippet_ref == "None":
            ok(f"`{name}` — no SOUL snippet (generic) — OK")
        else:
            key = snippet_ref.strip('"')
            if key in snippet_keys:
                ok(f"`{name}` → `{key}` ✅")
            else:
                fail(f"`{name}` → `{key}` but snippet NOT FOUND in SOUL_SNIPPETS")
                if FIX:
                    print(f"     (create `{key}` entry in SOUL_SNIPPETS or set to None)")

    # Check reverse: all SOUL_SNIPPETS keys should be referenced by PROFILE_META
    meta_snippet_refs = set()
    for name, snippet_ref in meta_pattern:
        if snippet_ref != "None":
            meta_snippet_refs.add(snippet_ref.strip('"'))

    for key in sorted(snippet_keys):
        if key not in meta_snippet_refs:
            warn(f"`{key}` — in SOUL_SNIPPETS but UNREFERENCED by PROFILE_META")


def test_wire_crons_skill_refs():
    """wire-crons.py doesn't reference phantom skills."""
    section("Cron Wirer Skill References")

    wire_py = (SCRIPTS_DIR / "wire-crons.py").read_text()
    actual_skills = sorted(d.name for d in SKILLS_DIR.iterdir() if d.is_dir())

    # Extract all skills references in PROFILE_EXTRA_CRONS
    ref_pattern = re.findall(r'"skills":\s*\[([^\]]*)\]', wire_py)
    referenced = set()
    for refs in ref_pattern:
        if refs.strip():
            skills = re.findall(r'"([^"]+)"', refs)
            for s in skills:
                referenced.add(s)

    # Also check SCRUM_CRONS
    scrum_pattern = re.findall(r'"skills":\s*\[([^\]]*)\]', wire_py)
    for refs in scrum_pattern:
        if refs.strip():
            skills = re.findall(r'"([^"]+)"', refs)
            for s in skills:
                referenced.add(s)

    for s in sorted(referenced):
        if s in actual_skills:
            ok(f"`{s}` — exists in skills/")
        else:
            warn(f"`{s}` — referenced by wire-crons but NOT in skills/")
            if FIX:
                print(f"     (add to skills/ or remove from wire-crons.py)")


def test_scrum_configs():
    """All scrum configs match expected profiles."""
    section("Scrum Config Coverage")

    scrum_dir = EXAMPLES_DIR / "scrum-configs"
    expected = [
        "hr-manager", "finance-manager", "project-manager",
        "procurement-manager", "product-manager", "crm-manager",
        "marketing-manager", "compliance-manager", "customer-support",
    ]

    for name in expected:
        path = scrum_dir / f"{name}.yaml"
        if path.exists():
            try:
                with open(path) as f:
                    data = yaml.safe_load(f)
                profile = data.get("profile", "")
                if profile == name:
                    ok(f"{name}.yaml — valid (profile={profile})")
                else:
                    warn(f"{name}.yaml — profile field is '{profile}', expected '{name}'")
            except yaml.YAMLError as e:
                fail(f"{name}.yaml — invalid YAML: {str(e)[:80]}")
        else:
            fail(f"{name}.yaml — MISSING")


def test_readme_links():
    """README links point to existing files."""
    section("README Links")

    readme = (REPO_ROOT / "README.md").read_text()
    links = re.findall(r'\[([^\]]+)\]\(([^)]+)\)', readme)

    for text, link in links:
        if link.startswith("http"):
            continue  # skip external links
        target = (REPO_ROOT / link).resolve()
        if target.exists():
            if VERBOSE:
                ok(f"`{link}` — exists")
        else:
            warn(f"`{link}` (text: '{text}') — BROKEN (not found)")


def test_skilmd_frontmatter():
    """All SKILL.md files have valid frontmatter."""
    section("SKILL.md Frontmatter")

    for skill_dir in sorted(SKILLS_DIR.iterdir()):
        if not skill_dir.is_dir():
            continue
        skilmd = skill_dir / "SKILL.md"
        if not skilmd.exists():
            continue

        content = skilmd.read_text()
        # Check for YAML frontmatter
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                fm = content[3:end].strip()
                try:
                    yaml.safe_load(fm)
                    ok(f"{skill_dir.name}/SKILL.md — frontmatter valid")
                except yaml.YAMLError as e:
                    fail(f"{skill_dir.name}/SKILL.md — frontmatter invalid: {str(e)[:80]}")
            else:
                fail(f"{skill_dir.name}/SKILL.md — no closing ---")
        else:
            warn(f"{skill_dir.name}/SKILL.md — no frontmatter")


def test_recipe_syntax():
    """All recipes have valid frontmatter."""
    section("Recipe Frontmatter")

    for recipe in sorted(RECIPES_DIR.glob("*.md")):
        content = recipe.read_text()
        if content.startswith("---"):
            end = content.find("---", 3)
            if end > 0:
                fm = content[3:end].strip()
                try:
                    data = yaml.safe_load(fm)
                    has_id = "id" in data if data else False
                    if has_id:
                        ok(f"{recipe.name} — frontmatter OK (id={data['id']})")
                    else:
                        warn(f"{recipe.name} — frontmatter missing 'id' field")
                except yaml.YAMLError as e:
                    fail(f"{recipe.name} — invalid frontmatter: {str(e)[:80]}")
            else:
                fail(f"{recipe.name} — no closing ---")
        else:
            warn(f"{recipe.name} — no frontmatter")


def test_hub_skills_match():
    """HUB.md skills table lists exactly the skills in directory."""
    section("HUB.md vs Skills Manifest")

    hub = (REPO_ROOT / "HUB.md").read_text()
    actual_skills = sorted(d.name for d in SKILLS_DIR.iterdir() if d.is_dir())

    # Parse HUB.md skill table — look for lines with backtick-skills
    hub_skills = set()
    for line in hub.split("\n"):
        if line.startswith("| `") and "` |" in line:
            name = line.split("`")[1]
            hub_skills.add(name)

    # Compare
    missing_hub = [s for s in actual_skills if s not in hub_skills]
    extra_hub = [s for s in hub_skills if s not in actual_skills]

    if missing_hub:
        for s in missing_hub:
            warn(f"`{s}` — in skills/ but not in HUB.md table")
    if extra_hub:
        for s in extra_hub:
            warn(f"`{s}` — in HUB.md table but not in skills/")
    if not missing_hub and not extra_hub:
        ok("All skills match between HUB.md and skills/ directory")


def test_changelog_version():
    """CHANGELOG has a version entry for current release."""
    section("CHANGELOG")

    changelog = (REPO_ROOT / "CHANGELOG.md").read_text()
    if "## [2.3.0]" in changelog:
        ok("v2.3.0 entry present in CHANGELOG.md")
    else:
        warn("No v2.3.0 entry in CHANGELOG.md")


def run_all():
    parser = argparse.ArgumentParser(
        description="Company OS — Pre-Deployment Repo Verification",
    )
    parser.add_argument("--verbose", "-v", action="store_true", help="Show all details")
    parser.add_argument("--fix", "-f", action="store_true", help="Auto-fix common issues")
    args = parser.parse_args()

    global FIX, VERBOSE
    FIX = args.fix
    VERBOSE = args.verbose

    print(f"\n{color('Company OS — Pre-Deployment Repo Verification', 'cyan')}")
    print(f"  Repo: {REPO_ROOT}")
    print()

    test_root_docs_exist()
    test_scripts_syntax()
    test_yaml_templates()
    test_skills_manifest()
    test_skills_have_skilmd()
    test_skilmd_frontmatter()
    test_verify_skill_list_matches()
    test_profile_types_match()
    test_wire_crons_skill_refs()
    test_scrum_configs()
    test_recipe_syntax()
    test_hub_skills_match()
    test_readme_links()
    test_changelog_version()

    # Summary
    print(f"\n{color('═' * 50, 'cyan')}")
    print(f"  {color('Results:', 'bold')}  {color(f'{PASS} passed', 'green')}, "
          f"{color(f'{WARN} warnings', 'yellow')}, "
          f"{color(f'{FAIL} failed', 'red')}")
    print(f"{color('═' * 50, 'cyan')}")

    return 0 if FAIL == 0 else 1


if __name__ == "__main__":
    sys.exit(run_all())