#!/usr/bin/env python3
"""Install a skill into one or more Hermes profile skill directories.

Hermes named profiles only see skills under:
  ~/.hermes/profiles/<profile>/skills/

Default profile sees:
  ~/.hermes/skills/

This script copies (or symlinks) a skill from a source into the default
HERMES home and/or named profiles so slash commands like /shogunify work.

Usage:
  python3 install-to-profiles.py --skill shogunify --profiles all
  python3 install-to-profiles.py --skill shogunify --profiles hr-manager,finance-manager
  python3 install-to-profiles.py --skill my-skill --profiles test-shogunify \\
      --src ~/shogun-os/skills/my-skill --mode copy
"""

from __future__ import annotations

import argparse
import os
import shutil
import sys
from pathlib import Path

HERMES_HOME = Path(os.environ.get("HERMES_HOME_ROOT", Path.home() / ".hermes"))
# When HERMES_HOME points at a profile, still use the root for multi-profile install
if (HERMES_HOME / "profiles").is_dir():
    HERMES_ROOT = HERMES_HOME
else:
    # e.g. HERMES_HOME=~/.hermes/profiles/foo → root is ~/.hermes
    if HERMES_HOME.parent.name == "profiles":
        HERMES_ROOT = HERMES_HOME.parent.parent
    else:
        HERMES_ROOT = Path.home() / ".hermes"

PROFILES_DIR = HERMES_ROOT / "profiles"
DEFAULT_SKILLS = HERMES_ROOT / "skills"

# Shogun department profiles that should always get shared meta-skills
SHOGUN_CORE_PROFILES = [
    "hr-manager",
    "finance-manager",
    "procurement-manager",
    "crm-manager",
    "marketing-manager",
    "compliance-manager",
    "customer-support",
    "coding-agent",
    "project-manager",
    "product-manager",
    "executive-assistant",
]


def ok(msg: str) -> None:
    print(f"  ✅ {msg}")


def warn(msg: str) -> None:
    print(f"  ⚠️  {msg}")


def err(msg: str) -> None:
    print(f"  ❌ {msg}", file=sys.stderr)


def resolve_src(skill: str, src: str | None) -> Path:
    if src:
        p = Path(src).expanduser().resolve()
        if not (p / "SKILL.md").is_file():
            raise SystemExit(f"Source missing SKILL.md: {p}")
        return p

    candidates = [
        Path(__file__).resolve().parent.parent,  # skills/shogunify when script lives there
        DEFAULT_SKILLS / skill,
        HERMES_ROOT.parent / "shogun-os" / "skills" / skill,
        Path.home() / "shogun-os" / "skills" / skill,
    ]
    # If script is inside skills/<skill>/scripts/, parent.parent is the skill dir
    script_skill = Path(__file__).resolve().parent.parent
    if script_skill.name == skill and (script_skill / "SKILL.md").is_file():
        return script_skill

    for c in candidates:
        if c.is_dir() and (c / "SKILL.md").is_file() and c.name == skill:
            return c
        if c.is_dir() and (c / "SKILL.md").is_file() and skill == c.name:
            return c

    # Last: any path ending with skill name under shogun-os
    shogun = Path.home() / "shogun-os" / "skills"
    if shogun.is_dir():
        direct = shogun / skill
        if (direct / "SKILL.md").is_file():
            return direct
        for p in shogun.rglob("SKILL.md"):
            if p.parent.name == skill:
                return p.parent

    raise SystemExit(f"Could not find skill source for '{skill}'. Pass --src.")


def ensure_link_or_copy(src: Path, dst: Path, mode: str, force: bool) -> str:
    dst.parent.mkdir(parents=True, exist_ok=True)
    if dst.exists() or dst.is_symlink():
        if not force:
            return "exists"
        if dst.is_symlink() or dst.is_file():
            dst.unlink()
        else:
            shutil.rmtree(dst)

    if mode == "symlink":
        try:
            os.symlink(str(src.resolve()), str(dst))
            return "symlink"
        except OSError:
            shutil.copytree(src, dst)
            return "copy-fallback"
    shutil.copytree(src, dst)
    return "copy"


def expand_profiles(spec: str) -> list[str]:
    spec = spec.strip().lower()
    if spec in ("all", "*"):
        names = []
        if PROFILES_DIR.is_dir():
            names = sorted(p.name for p in PROFILES_DIR.iterdir() if p.is_dir())
        return names
    if spec in ("all-shogun", "shogun"):
        names = []
        for n in SHOGUN_CORE_PROFILES:
            if (PROFILES_DIR / n).is_dir():
                names.append(n)
        return names
    return [p.strip() for p in spec.split(",") if p.strip()]


def main() -> int:
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--skill", required=True, help="Skill directory name")
    ap.add_argument(
        "--profiles",
        default="all-shogun",
        help="Comma list, 'all', or 'all-shogun' (default). Use 'default' for ~/.hermes/skills only.",
    )
    ap.add_argument("--src", default=None, help="Source skill directory (contains SKILL.md)")
    ap.add_argument("--mode", choices=["symlink", "copy"], default="symlink")
    ap.add_argument("--force", action="store_true", help="Replace existing skill dir/link")
    ap.add_argument("--also-default", action="store_true", default=True, help="Also install to ~/.hermes/skills (default true)")
    ap.add_argument("--no-default", action="store_true", help="Skip default ~/.hermes/skills install")
    ap.add_argument("--dry-run", action="store_true")
    args = ap.parse_args()

    src = resolve_src(args.skill, args.src)
    print(f"Source: {src}")
    print(f"Hermes root: {HERMES_ROOT}")

    targets: list[Path] = []
    install_default = args.also_default and not args.no_default
    profile_spec = args.profiles

    if profile_spec.strip().lower() == "default":
        install_default = True
        profiles: list[str] = []
    else:
        profiles = expand_profiles(profile_spec)

    if install_default:
        targets.append(DEFAULT_SKILLS / args.skill)

    for name in profiles:
        pdir = PROFILES_DIR / name
        if not pdir.is_dir():
            warn(f"Profile missing, skip: {name}")
            continue
        targets.append(pdir / "skills" / args.skill)

    if not targets:
        err("No install targets")
        return 1

    for dst in targets:
        if args.dry_run:
            ok(f"[DRY-RUN] {args.mode} → {dst}")
            continue
        action = ensure_link_or_copy(src, dst, args.mode, args.force)
        if action == "exists":
            warn(f"Already exists (use --force): {dst}")
        else:
            ok(f"{action} → {dst}")

    print()
    ok(f"Done. Skill '{args.skill}' → slash /{args.skill} on installed profiles (new session).")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
