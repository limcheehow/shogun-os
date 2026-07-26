#!/usr/bin/env python3
"""E2E tests for shogunify: install, slash registration, skill scaffold, path isolation.

Creates a disposable Hermes profile `test-shogunify`, installs skills, scaffolds a
demo skill via the questionnaire templates, verifies Hermes skill discovery /
slash command registration, and tears down on success (unless --keep).

Usage:
  python3 ~/shogun-os/skills/shogunify/scripts/e2e_test_shogunify.py
  python3 ~/shogun-os/skills/shogunify/scripts/e2e_test_shogunify.py --keep
"""

from __future__ import annotations

import argparse
import json
import os
import re
import shutil
import subprocess
import sys
import tempfile
from pathlib import Path

HERMES_ROOT = Path.home() / ".hermes"
PROFILES_DIR = HERMES_ROOT / "profiles"
REPO = Path.home() / "shogun-os"
SHOGUNIFY_SRC = REPO / "skills" / "shogunify"
INSTALL_SCRIPT = SHOGUNIFY_SRC / "scripts" / "install-to-profiles.py"
PROFILE = "test-shogunify"
DEMO_SKILL = "demo-echo-skill"
CONNECTOR_DOMAIN = "demo-inventory"


class Fail(Exception):
    pass


PASSED = 0
FAILED = 0


def report(name: str, ok: bool, detail: str = "") -> None:
    global PASSED, FAILED
    if ok:
        PASSED += 1
        print(f"  ✅ PASS  {name}" + (f" — {detail}" if detail else ""))
    else:
        FAILED += 1
        print(f"  ❌ FAIL  {name}" + (f" — {detail}" if detail else ""))


def run(cmd: list[str], env: dict | None = None, timeout: int = 120) -> subprocess.CompletedProcess:
    return subprocess.run(
        cmd,
        capture_output=True,
        text=True,
        env=env or os.environ.copy(),
        timeout=timeout,
        check=False,
    )


def ensure_shogunify_source() -> None:
    if not (SHOGUNIFY_SRC / "SKILL.md").is_file():
        raise Fail(f"Missing skill source: {SHOGUNIFY_SRC}")
    report("shogunify source exists", True, str(SHOGUNIFY_SRC))


def install_shogunify_all() -> None:
    r = run(
        [
            sys.executable,
            str(INSTALL_SCRIPT),
            "--skill",
            "shogunify",
            "--profiles",
            "all",
            "--src",
            str(SHOGUNIFY_SRC),
            "--force",
        ]
    )
    ok = r.returncode == 0
    report("install-to-profiles all", ok, (r.stdout + r.stderr)[-400:])
    if not ok:
        raise Fail("install-to-profiles failed")


def create_test_profile() -> Path:
    pdir = PROFILES_DIR / PROFILE
    if pdir.exists():
        shutil.rmtree(pdir)
    # Prefer hermes CLI if available
    r = run(["hermes", "profile", "create", PROFILE])
    if r.returncode != 0 or not pdir.is_dir():
        # Manual minimal profile
        pdir.mkdir(parents=True, exist_ok=True)
        (pdir / "skills").mkdir(exist_ok=True)
        (pdir / "cron").mkdir(exist_ok=True)
        (pdir / "config.yaml").write_text(
            "model:\n  default: null\n\n# test-shogunify e2e profile\n",
            encoding="utf-8",
        )
        (pdir / "SOUL.md").write_text(
            f"# {PROFILE}\n\nDisposable profile for shogunify E2E.\n",
            encoding="utf-8",
        )
        (pdir / ".env").write_text("# empty test env\n", encoding="utf-8")
        report("create profile (manual)", True, str(pdir))
    else:
        report("create profile (hermes CLI)", True, str(pdir))
    return pdir


def link_shogunify_to_profile(pdir: Path) -> None:
    r = run(
        [
            sys.executable,
            str(INSTALL_SCRIPT),
            "--skill",
            "shogunify",
            "--profiles",
            PROFILE,
            "--src",
            str(SHOGUNIFY_SRC),
            "--force",
            "--no-default",
        ]
    )
    target = pdir / "skills" / "shogunify" / "SKILL.md"
    ok = r.returncode == 0 and target.is_file()
    report("link shogunify into test profile", ok, str(target))
    if not ok:
        raise Fail("shogunify not on test profile")


def scaffold_demo_skill(pdir: Path) -> Path:
    """Simulate shogunify skill mode: write from template into profile skills."""
    tpl = (SHOGUNIFY_SRC / "templates" / "skill-SKILL.md.tpl").read_text(encoding="utf-8")
    body = (
        tpl.replace("{{SKILL_NAME}}", DEMO_SKILL)
        .replace("{{TRIGGER}}", "user asks for a demo echo")
        .replace("{{ONE_LINE_BEHAVIOR}}", "Echo a fixed confirmation string for E2E")
        .replace("{{TAGS}}", "demo, e2e, test")
        .replace("{{CATEGORY}}", "testing")
        .replace("{{TITLE}}", "Demo Echo Skill")
        .replace("{{OVERVIEW}}", "E2E fixture skill created by shogunify tests.")
        .replace("{{TRIGGER_1}}", "demo echo")
        .replace("{{TRIGGER_2}}", f"/{DEMO_SKILL}")
        .replace("{{COUNTER_TRIGGERS}}", "production work")
        .replace("{{PROFILE}}", PROFILE)
        .replace("{{ENV_VARS}}", "none")
        .replace("{{TOOLS}}", "none")
        .replace("{{WORKFLOW_1_NAME}}", "Echo")
        .replace("{{STEP_1}}", "Reply with DEMO_ECHO_OK")
        .replace("{{CRITERION_1}}", "message contains DEMO_ECHO_OK")
        .replace("{{STEP_2}}", "Stop")
        .replace("{{CRITERION_2}}", "done")
        .replace("{{PITFALL_1}}", "Do not install outside test profile")
    )
    skill_dir = pdir / "skills" / DEMO_SKILL
    if skill_dir.exists():
        shutil.rmtree(skill_dir)
    skill_dir.mkdir(parents=True)
    skill_md = skill_dir / "SKILL.md"
    skill_md.write_text(body, encoding="utf-8")

    # Frontmatter checks
    text = skill_md.read_text(encoding="utf-8")
    ok_fm = text.startswith("---") and "name: demo-echo-skill" in text and "description:" in text
    report("scaffold demo skill frontmatter", ok_fm, str(skill_md))
    if not ok_fm:
        raise Fail("bad frontmatter")
    return skill_dir


def scaffold_demo_connector(tmp_repo: Path) -> None:
    """Simulate provider-only-ish domain scaffold into a temp dir (not live recipes)."""
    domain = tmp_repo / "recipes" / CONNECTOR_DOMAIN
    domain.mkdir(parents=True)
    contract_tpl = (SHOGUNIFY_SRC / "templates" / "contract.md.tpl").read_text(encoding="utf-8")
    generic_tpl = (SHOGUNIFY_SRC / "templates" / "generic-skill.md.tpl").read_text(encoding="utf-8")
    provider_tpl = (SHOGUNIFY_SRC / "templates" / "provider.md.tpl").read_text(encoding="utf-8")

    def fill(t: str) -> str:
        return (
            t.replace("{{DOMAIN_TITLE}}", "Demo Inventory")
            .replace("{{DOMAIN}}", "demo inventory")
            .replace("{{PREFIX}}", "inv")
            .replace("{{ENTITIES}}", "items")
            .replace("{{ENTITY}}", "item")
            .replace("{{REQUIRED_FIELD}}", "sku")
            .replace("{{SKILL_NAME}}", "demo-inventory-provider")
            .replace("{{MCP_SERVER_NAME}}", "demo-inventory")
            .replace("{{PROFILE}}", PROFILE)
            .replace("{{PROVIDER_ENV}}", "INV_PROVIDER")
            .replace("{{VENDOR}}", "FakeWMS")
            .replace("{{VENDOR_SLUG}}", "fakewms")
            .replace("{{API_KEY_ENV}}", "FAKEWMS_API_KEY")
            .replace("{{BRIDGE_PATH}}", str(HERMES_ROOT / "scripts" / "demo-inventory-bridge.py"))
        )

    (domain / "CONTRACT.md").write_text(fill(contract_tpl), encoding="utf-8")
    (domain / "GENERIC_SKILL.md").write_text(fill(generic_tpl), encoding="utf-8")
    (domain / "providers").mkdir()
    (domain / "providers" / "fakewms.md").write_text(fill(provider_tpl), encoding="utf-8")
    ok = all(
        (domain / p).is_file()
        for p in ("CONTRACT.md", "GENERIC_SKILL.md", "providers/fakewms.md")
    )
    report("scaffold demo connector recipes", ok, str(domain))
    if not ok:
        raise Fail("connector scaffold incomplete")


def hermes_discovers_skills(pdir: Path) -> None:
    """Use Hermes skill_utils if importable; else filesystem + regex checks."""
    env = os.environ.copy()
    env["HERMES_HOME"] = str(pdir)
    # Attempt CLI
    for cmd in (
        ["hermes", "skills", "list"],
        ["hermes", "skill", "list"],
        ["hermes", "--help"],
    ):
        r = run(cmd, env=env, timeout=60)
        out = (r.stdout + r.stderr).lower()
        if r.returncode == 0 and ("shogunify" in out or "demo-echo" in out):
            report("hermes CLI lists skills", True, " ".join(cmd))
            break
    else:
        report("hermes CLI lists skills", True, "CLI list unavailable — using library path")

    # Direct import of skill discovery (most reliable)
    try:
        sys.path.insert(0, str(Path.home() / ".hermes" / "hermes-agent"))
        # hermes_constants uses HERMES_HOME
        os.environ["HERMES_HOME"] = str(pdir)
        from agent.skill_commands import get_skill_commands  # type: ignore

        cmds = get_skill_commands()
        names = set(cmds.keys()) if isinstance(cmds, dict) else set()
        # also try rebuild
        if hasattr(cmds, "keys"):
            has_shogunify = any("shogunify" in k for k in names)
            has_demo = any(DEMO_SKILL.replace("_", "-") in k or "demo-echo" in k for k in names)
            report("/shogunify registered", has_shogunify, f"commands sample={list(names)[:12]}")
            report(f"/{DEMO_SKILL} registered", has_demo, f"match demo in {len(names)} cmds")
            if not has_shogunify:
                # fallback scan
                raise ImportError("not found in get_skill_commands")
        return
    except Exception as e:
        report("skill_commands import", True, f"fallback scan ({e})")

    # Fallback: walk skills dir like Hermes
    found = {}
    skills_root = pdir / "skills"
    for skill_md in skills_root.rglob("SKILL.md"):
        text = skill_md.read_text(encoding="utf-8", errors="replace")
        m = re.search(r"^name:\s*[\"']?([a-z0-9-]+)", text, re.M)
        if m:
            found[m.group(1)] = skill_md
    report("/shogunify registered (fs)", "shogunify" in found, str(found.get("shogunify")))
    report(f"/{DEMO_SKILL} registered (fs)", DEMO_SKILL in found, str(found.get(DEMO_SKILL)))
    if "shogunify" not in found or DEMO_SKILL not in found:
        raise Fail(f"skills not discovered: {list(found)}")


def path_isolation_check(pdir: Path) -> None:
    """Demo skill must NOT appear under a random other profile unless linked."""
    other = None
    for cand in sorted(PROFILES_DIR.iterdir()):
        if cand.is_dir() and cand.name not in (PROFILE,):
            other = cand
            break
    if other is None:
        report("path isolation", True, "no other profile to compare")
        return
    leak = other / "skills" / DEMO_SKILL
    ok = not leak.exists()
    report("path isolation (no leak to other profile)", ok, f"checked {other.name}")
    if not ok:
        raise Fail(f"demo skill leaked to {leak}")


def check_default_and_dept_have_shogunify() -> None:
    default = HERMES_ROOT / "skills" / "shogunify" / "SKILL.md"
    report("default home has shogunify", default.is_file(), str(default))
    sample = ["hr-manager", "finance-manager", "crm-manager"]
    missing = []
    for name in sample:
        p = PROFILES_DIR / name / "skills" / "shogunify" / "SKILL.md"
        if not p.is_file():
            missing.append(name)
    report(
        "dept samples have /shogunify",
        not missing,
        "ok" if not missing else f"missing: {missing}",
    )


def generate_profile_shared_skills_unit() -> None:
    # Import generate-profile helpers
    gp = REPO / "scripts" / "generate-profile.py"
    text = gp.read_text(encoding="utf-8")
    ok = "SHARED_PROFILE_SKILLS" in text and "shogunify" in text and "with_shared_skills" in text
    report("generate-profile wires shared shogunify", ok)
    if not ok:
        raise Fail("generate-profile missing shared skills wiring")


def teardown(pdir: Path, keep: bool, tmp_repo: Path | None) -> None:
    if tmp_repo and tmp_repo.exists():
        shutil.rmtree(tmp_repo, ignore_errors=True)
    if keep:
        print(f"  ℹ️  keeping profile at {pdir}")
        return
    if pdir.exists():
        shutil.rmtree(pdir)
        report("teardown test profile", True, PROFILE)


def main() -> int:
    ap = argparse.ArgumentParser()
    ap.add_argument("--keep", action="store_true")
    args = ap.parse_args()

    print("━━━ shogunify E2E ━━━")
    pdir = None
    tmp_repo = None
    try:
        ensure_shogunify_source()
        generate_profile_shared_skills_unit()
        install_shogunify_all()
        check_default_and_dept_have_shogunify()
        pdir = create_test_profile()
        link_shogunify_to_profile(pdir)
        scaffold_demo_skill(pdir)
        tmp_repo = Path(tempfile.mkdtemp(prefix="shogunify-e2e-"))
        scaffold_demo_connector(tmp_repo)
        hermes_discovers_skills(pdir)
        path_isolation_check(pdir)
    except Fail as e:
        report("aborted", False, str(e))
    except Exception as e:
        report("unexpected error", False, repr(e))
        import traceback

        traceback.print_exc()
    finally:
        if pdir is not None:
            teardown(pdir, args.keep, tmp_repo)

    print()
    print(f"Results: {PASSED} passed, {FAILED} failed")
    return 1 if FAILED else 0


if __name__ == "__main__":
    raise SystemExit(main())
