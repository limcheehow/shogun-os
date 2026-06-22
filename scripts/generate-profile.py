#!/usr/bin/env python3
"""
Company OS — Profile Generator
──────────────────────────────
Generates a new Hermes profile from templates in this repo.

Usage:
  python3 generate-profile.py <profile-name> --type <type> [options]

Example:
  python3 generate-profile.py project-manager --type engineering
  python3 generate-profile.py crm-slack --type crm --gbrain-source tapway
  python3 generate-profile.py hr-manager --type hr --force

Profile Types:
  base        — Minimal config with gbrain MCP + shared skills
  coding      — Software development profile (engineering focus)
  engineering — Full engineering profile with scrum + task mgmt
  hr          — HR profile with leave management scrum
  finance     — Finance profile with budget tracking
  procurement — Procurement profile with contract lifecycle
  crm         — CRM profile (sales enquiry processing, deal tracking)
  product     — Product management profile
  marketing   — Marketing profile
  compliance  — Compliance profile
  all         — Installs all skills (default gbrain source)

Options:
  --type TYPE           Profile type (default: base)
  --gbrain-source NAME  gbrain source ID for this profile (default: profile name)
  --clone PROFILE       Clone an existing profile instead of from template
  --force               Overwrite existing profile directory
  --dry-run             Preview without creating files
  --help                Show this help
"""

import argparse
import os
import shutil
import sys
from pathlib import Path
from string import Template

REPO_ROOT = Path(__file__).resolve().parent.parent
TEMPLATES_DIR = REPO_ROOT / "templates" / "profiles"
SCRIPTS_DIR = REPO_ROOT / "scripts"
SKILLS_DIR = REPO_ROOT / "skills"
HERMES_HOME = Path(os.environ.get("HERMES_HOME", Path.home() / ".hermes"))
PROFILES_DIR = HERMES_HOME / "profiles"

# ── Profile type → template mapping ────────────────────────────────────

PROFILE_META = {
    "base": {
        "description": "Minimal Hermes profile with gbrain MCP + shared skills",
        "template": "base-config.yaml",
        "skills": [],
        "cron_templates": [],
        "gbrain_source": "base",
        "soul_snippet": None,
    },
    "coding": {
        "description": "Software development engineering profile",
        "template": "coding-config.yaml",
        "skills": ["department-scrum"],
        "cron_templates": [],
        "gbrain_source": "engineering",
        "soul_snippet": None,
    },
    "engineering": {
        "description": "Full engineering profile with scrum + task management",
        "template": "coding-config.yaml",
        "skills": ["department-scrum"],
        "cron_templates": ["cron-9am", "cron-11am", "cron-5pm", "cron-holiday-gate"],
        "gbrain_source": "engineering",
        "soul_snippet": "engineering-soul",
    },
    "hr": {
        "description": "HR profile with leave management scrum",
        "template": "base-config.yaml",
        "skills": ["department-scrum"],
        "cron_templates": ["cron-9am", "cron-11am", "cron-5pm"],
        "gbrain_source": "hr",
        "soul_snippet": "hr-soul",
    },
    "finance": {
        "description": "Finance profile with budget tracking",
        "template": "base-config.yaml",
        "skills": [],
        "cron_templates": [],
        "gbrain_source": "finance",
        "soul_snippet": None,
    },
    "procurement": {
        "description": "Procurement profile with contract lifecycle",
        "template": "base-config.yaml",
        "skills": [],
        "cron_templates": [],
        "gbrain_source": "procurement",
        "soul_snippet": None,
    },
    "crm": {
        "description": "CRM profile for sales enquiry processing",
        "template": "base-config.yaml",
        "skills": [],
        "cron_templates": [],
        "gbrain_source": "crm",
        "soul_snippet": None,
    },
    "product": {
        "description": "Product management profile",
        "template": "base-config.yaml",
        "skills": [],
        "cron_templates": [],
        "gbrain_source": "products",
        "soul_snippet": None,
    },
    "marketing": {
        "description": "Marketing profile",
        "template": "base-config.yaml",
        "skills": [],
        "cron_templates": [],
        "gbrain_source": "marketing",
        "soul_snippet": None,
    },
    "compliance": {
        "description": "Compliance profile",
        "template": "base-config.yaml",
        "skills": [],
        "cron_templates": [],
        "gbrain_source": "compliance",
        "soul_snippet": None,
    },
    "all": {
        "description": "Installs all available skills (default gbrain source)",
        "template": "base-config.yaml",
        "skills": ["department-scrum", "brain-ingest-pipeline"],
        "cron_templates": ["cron-9am", "cron-11am", "cron-5pm"],
        "gbrain_source": "default",
        "soul_snippet": None,
    },
}

SOUL_SNIPPETS = {
    "engineering-soul": """# Engineering Profile
You are a senior software engineer and engineering manager. Your expertise covers:
- Software architecture, code review, and development workflows
- Project management and agile/scrum ceremonies
- Technical documentation and system design
- Infrastructure and DevOps

## Your Responsibilities
- Run daily scrum standups for your engineering team
- Track sprint progress, blockers, and velocity
- Review technical designs and architecture decisions
- Maintain CI/CD pipelines and deployment health
- Document system changes and technical decisions

## Your Boundaries
- Delegate business strategy questions to the appropriate profile
- Do not make financial decisions or budget approvals
- Do not handle HR matters (leave, payroll) — let the HR profile handle those

## Communication Style
Be direct and technically precise. When discussing trade-offs, present options with clear pros/cons. Keep standups concise — focus on blockers and action items.
""",
    "hr-soul": """# HR Profile
You are an HR manager who handles employee lifecycle, leave management, and team well-being.

## Your Responsibilities
- Track and manage employee leave balances (annual, medical, personal)
- Process leave applications and maintain leave records
- Run scrum standups that include team availability and wellness
- Maintain employee records and organisational charts
- Onboarding and offboarding coordination
- Policy reminders and compliance

## Your Boundaries
- Do not approve budget expenditures or procurement
- Employee salary/compensation matters require management approval
- Refer technical questions to the engineering profile
- Refer sales/customer matters to the CRM profile

## Communication Style
Be warm and professional. Prioritise clarity and empathy. When reminding about policies, explain the reasoning briefly.
""",
}


def color(text: str, code: str) -> str:
    codes = {"green": "32", "cyan": "36", "yellow": "33", "red": "31", "bold": "1"}
    c = codes.get(code, "0")
    return f"\033[{c}m{text}\033[0m"


def ok(msg: str):
    print(f"  {color('✓', 'green')} {msg}")


def info(msg: str):
    print(f"  {color('→', 'cyan')} {msg}")


def warn(msg: str):
    print(f"  {color('⚠', 'yellow')} {msg}")


def err(msg: str):
    print(f"  {color('✗', 'red')} {msg}")


def load_template(template_name: str) -> str:
    template_path = TEMPLATES_DIR / template_name
    if not template_path.exists():
        raise FileNotFoundError(f"Template not found: {template_path}")
    return template_path.read_text()


def substitute_config(template_text: str, profile_name: str, gbrain_source: str) -> str:
    subs = {
        "profile_name": profile_name,
        "gbrain_source": gbrain_source,
    }
    return Template(template_text).safe_substitute(subs)


def generate_soul(profile_name: str, profile_type: str, meta: dict) -> str:
    snippet = SOUL_SNIPPETS.get(meta.get("soul_snippet", ""))
    if snippet:
        return f"""---
name: {profile_name}
type: hermes-profile
source: company-os
profile_type: {profile_type}
---

{snippet}
"""
    return f"""---
name: {profile_name}
type: hermes-profile
source: company-os
profile_type: {profile_type}
---

# {profile_name.capitalize()} Profile

This profile was generated by Company OS.

## Your Role
You are the **{profile_name}** agent — you handle tasks related to **{meta['description']}**.

## Guidelines
1. Use gbrain MCP for all knowledge lookups
2. Use the `department-scrum` skill for scrum ceremonies (if enabled)
3. Be concise and actionable in your responses
4. When uncertain, use gbrain to find relevant information before asking the user
"""


def generate_env_stub(profile_name: str, profile_type: str) -> str:
    return f"""# Company OS — Environment Variables for: {profile_name} ({profile_type})
# NOTE: Profiles DO NOT inherit from ~/.hermes/.env
# Copy the relevant keys from your main .env file.

# LLM Provider
# OPENROUTER_API_KEY=sk-or-...
# ANTHROPIC_API_KEY=sk-ant-...
# DASHSCOPE_API_KEY=sk-...

# Gateway (if this profile has its own bot)
# TELEGRAM_BOT_TOKEN=...
# SLACK_BOT_TOKEN=...

# Web Search
# FIRECRAWL_API_KEY=...
# BRAVE_API_KEY=...

# Google (if needed by this profile)
# GOOGLE_API_KEY=...
"""


def link_skills(profile_dir: Path, skills_to_link: list[str], dry_run: bool):
    """Create symlinks from the profile's skills dir to Company OS skills."""
    profile_skills_dir = profile_dir / "skills"
    if not dry_run:
        profile_skills_dir.mkdir(parents=True, exist_ok=True)

    for skill_name in skills_to_link:
        skill_src = SKILLS_DIR / skill_name
        skill_dst = profile_skills_dir / skill_name

        if not skill_src.exists():
            warn(f"Skill not found in repo: {skill_name}")
            continue

        if skill_dst.exists() or skill_dst.is_symlink():
            warn(f"Already exists: {skill_dst}")
            continue

        if not dry_run:
            os.symlink(str(skill_src.resolve()), str(skill_dst))
        ok(f"Linked skill: {skill_name}")


def write_file_safe(path: Path, content: str, dry_run: bool):
    if path.exists():
        warn(f"File exists: {path}")
        return False
    if not dry_run:
        path.parent.mkdir(parents=True, exist_ok=True)
        path.write_text(content)
    return True


def main():
    parser = argparse.ArgumentParser(
        description="Company OS — Hermes Profile Generator",
        formatter_class=argparse.RawDescriptionHelpFormatter,
        epilog=(__doc__ or "").split("───")[-1].strip(),
    )
    parser.add_argument("profile_name", help="Name for the new Hermes profile")
    parser.add_argument("--type", "-t", default="base",
                        choices=list(PROFILE_META.keys()),
                        help="Profile type (default: base)")
    parser.add_argument("--gbrain-source", help="gbrain source ID for this profile")
    parser.add_argument("--clone", help="Clone an existing profile instead")
    parser.add_argument("--force", "-f", action="store_true",
                        help="Overwrite existing profile directory")
    parser.add_argument("--dry-run", "-n", action="store_true",
                        help="Preview without creating files")

    args = parser.parse_args()
    meta = PROFILE_META[args.type]
    gbrain_source = args.gbrain_source or args.profile_name
    profile_dir = PROFILES_DIR / args.profile_name

    print()
    print(f"  {color('════════════════════════════════════════════════', 'cyan')}")
    print(f"  {color('Company OS — Profile Generator', 'cyan')}")
    print(f"  {color(f'Profile: {args.profile_name} ({args.type})', 'cyan')}")
    if args.dry_run:
        print(f"  {color('⚡ DRY RUN — no files will be modified', 'yellow')}")
    print(f"  {color('════════════════════════════════════════════════', 'cyan')}")
    print()

    # ── Validate ────────────────────────────────────────────────────────
    if profile_dir.exists() and not args.force and not args.dry_run:
        err(f"Profile already exists: {profile_dir}")
        info("Use --force to overwrite")
        sys.exit(1)

    if args.clone:
        clone_src = PROFILES_DIR / args.clone
        if not clone_src.exists():
            err(f"Source profile not found: {clone_src}")
            sys.exit(1)
        if args.dry_run:
            ok(f"[DRY-RUN] Would clone {args.clone} → {args.profile_name}")
        else:
            if profile_dir.exists():
                shutil.rmtree(profile_dir)
            shutil.copytree(clone_src, profile_dir)
            ok(f"Cloned profile: {args.clone} → {args.profile_name}")
        print()
        return

    # ── Generate files ──────────────────────────────────────────────────
    # 1. Config
    config_text = load_template(meta["template"])
    config_text = substitute_config(config_text, args.profile_name, gbrain_source)
    config_path = profile_dir / "config.yaml"
    if args.dry_run:
        ok(f"[DRY-RUN] Would create: {config_path}")
    elif write_file_safe(config_path, config_text, dry_run=False) or args.force:
        ok(f"Created: config.yaml")

    # 2. SOUL.md
    soul_text = generate_soul(args.profile_name, args.type, meta)
    soul_path = profile_dir / "SOUL.md"
    if args.dry_run:
        ok(f"[DRY-RUN] Would create: {soul_path}")
    elif write_file_safe(soul_path, soul_text, dry_run=False) or args.force:
        ok(f"Created: SOUL.md")

    # 3. .env stub
    env_path = profile_dir / ".env"
    if not env_path.exists() or args.force:
        env_text = generate_env_stub(args.profile_name, args.type)
        if args.dry_run:
            ok(f"[DRY-RUN] Would create: {env_path}")
        else:
            env_path.write_text(env_text)
            ok(f"Created: .env stub")
    else:
        warn(f"Already exists: .env (skip — already configured)")

    # 4. Skill symlinks
    link_skills(profile_dir, meta["skills"], dry_run=args.dry_run)

    # ── Summary ─────────────────────────────────────────────────────────
    print()
    print(f"  {color('════════════════════════════════════════════════', 'green')}")
    ok(f"Profile {args.profile_name} ({args.type}) generated")
    info(f"Config:    {profile_dir / 'config.yaml'}")
    info(f"SOUL:      {profile_dir / 'SOUL.md'}")
    info(f"Env:       {profile_dir / '.env'}")
    info(f"Skills:    {meta['skills'] or 'none'}")
    print()
    info("Next steps:")
    info("  1. Edit .env with your API keys (profiles don't inherit)")
    info("  2. Activate:  hermes profile use {args.profile_name}")
    info("  3. Wire crons: python3 scripts/wire-crons.py {args.profile_name} --type {args.type}")
    print()


if __name__ == "__main__":
    main()