#!/usr/bin/env python3
"""Brain Compliance Helper — ensures every new brain page is compliant and non-orphan.

This module provides a single entry point for all brain-writing scripts and agent
workflows. It enforces:

1. Proper YAML frontmatter (title, type, tags)
2. A # H1 heading matching the frontmatter title
3. Slug conventions (lowercase, hyphens, no underscores/uppercase)
4. At least one inbound graph link (orphan prevention)
5. Post-write validation via the brain-compliance validator
6. Entity cross-linking (person↔company, deal↔company, meeting↔attendees)

Usage in scripts:
    from brain_compliance_helper import write_brain_page, link_to_index, validate_page

    # Write a compliant page + auto-link to index (prevents orphan)
    write_brain_page(
        slug="deals/acme-foo",
        title="Acme Foo Deal",
        page_type="deal",
        content="...",
        category="deal",          # triggers auto-link to deals-index/all
        entity_links=[            # cross-link to related entities
            ("companies/acme-corp", "customer"),
        ],
    )

Usage in shell:
    gbrain link deals-index/all deals/acme-foo --link-type mentions --link-source script-auto

Usage in agent skills (MCP):
    mcp_gbrain_put_page(slug, content)
    mcp_gbrain_add_link(from="deals-index/all", to="deals/acme-foo",
                         link_type="mentions", link_source="script-auto")

Design principles (from gbrain skills):
- gbrain-capture: "Cross-link — use mcp_gbrain_add_link from every mentioned entity TO this page"
- gbrain-ingest: "Cross-link — mcp_gbrain_add_link from entities TO the new page (back-links)"
- brain-compliance: "Every brain-writing script MUST ensure new pages have at least one inbound wikilink"
- brain-link-campaign: "Index hub pages — markdown pages that mass-link to orphan pages with [[slug]] wikilinks"
- gbrain link CLI: --link-source must be kebab-case, cannot be 'markdown/frontmatter/mentions/wikilink-resolved'
"""

import os
import re
import sys
import subprocess
from pathlib import Path
from datetime import datetime, timezone
from typing import Optional, List, Tuple

# ─── Constants ──────────────────────────────────────────────────────────────

BRAIN_DIR = Path(os.environ.get("BRAIN_DIR", os.path.expanduser("~/brain")))
GBRAIN_BIN = os.environ.get("GBRAIN_BIN", os.path.expanduser("~/.local/bin/gbrain"))
VALIDATOR = os.environ.get(
    "BRAIN_VALIDATOR",
    os.path.expanduser("~/.hermes/skills/brain-compliance/scripts/validate-brain-page.py"),
)

# Index page mapping — each category has a hub page that provides inbound links
def _build_index_map():
    """Build index map with dynamic monthly/batch slugs."""
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")
    day = now.day
    half = "w1" if day <= 15 else "w2"
    return {
        "email": f"email-index/{month}-{half}",
        "deal": "deals-index/all",
        "meeting": "meetings-index/all",
        "scrum": "scrum-index/all",
        "person": "people-index/batch-04",
        "company": "companies-index/batch-03",
        "staff": "staff-index/all-staff",
        "hr": "hr-index/all-hr",
        "ticket": "projects/support_tickets/all-tickets",
        "calendar": f"cal-index/{month}",
        "project": "projects/active_projects/all-pages",
        "note": "notes-index/all",
        "concept": "concepts-index/all",
        "reference": "references-index/all",
        "idea": "ideas-index/all",
    }

INDEX_MAP = _build_index_map()

# Canonical page types (from brain-compliance skill)
CANONICAL_TYPES = {
    "company", "person", "project", "project-scrum", "deal", "meeting",
    "product-scrum", "note", "email", "concept", "calendar-event",
    "hr", "ticket", "status-report", "reference", "idea",
}

# Reserved link_source values that gbrain rejects (reconciliation-managed)
RESERVED_LINK_SOURCES = {"markdown", "frontmatter", "mentions", "wikilink-resolved"}


# ─── Slug Validation ────────────────────────────────────────────────────────

def validate_slug(slug: str) -> Tuple[bool, str]:
    """Check slug follows conventions: lowercase, hyphens, no underscores/uppercase.

    Returns (is_valid, message).
    """
    if not slug:
        return False, "slug is empty"

    if slug != slug.lower():
        return False, f"slug contains uppercase: '{slug}' — use lowercase only"

    if "_" in slug:
        return False, f"slug contains underscores: '{slug}' — use hyphens instead"

    if " " in slug:
        return False, f"slug contains spaces: '{slug}' — use hyphens instead"

    if slug.startswith("-") or slug.endswith("-"):
        return False, f"slug starts/ends with hyphen: '{slug}'"

    return True, "valid"


# ─── Frontmatter Builder ────────────────────────────────────────────────────

def build_frontmatter(
    title: str,
    page_type: str = "note",
    tags: Optional[List[str]] = None,
    extra_fields: Optional[dict] = None,
) -> str:
    """Build compliant YAML frontmatter.

    Ensures:
    - title: is present and quoted (handles titles with colons/special chars)
    - type: is a canonical type
    - tags: is a list (if provided)
    - extra_fields: merged in (source, date, company, etc.)
    """
    if page_type not in CANONICAL_TYPES:
        print(f"⚠️  Warning: type '{page_type}' not in canonical types", file=sys.stderr)

    lines = ["---"]
    lines.append(f'title: "{title}"')
    lines.append(f"type: {page_type}")

    if tags:
        if isinstance(tags, str):
            tags = [tags]
        if page_type not in tags:
            tags = list(tags) + [page_type]
        lines.append(f"tags: [{', '.join(tags)}]")
    else:
        lines.append(f"tags: [{page_type}]")

    if extra_fields:
        for key, value in sorted(extra_fields.items()):
            if isinstance(value, str):
                lines.append(f'{key}: "{value}"')
            elif isinstance(value, bool):
                lines.append(f"{key}: {str(value).lower()}")
            elif isinstance(value, (int, float)):
                lines.append(f"{key}: {value}")
            else:
                lines.append(f'{key}: "{value}"')

    lines.append("---")
    return "\n".join(lines)


# ─── Page Builder ───────────────────────────────────────────────────────────

def build_page(
    title: str,
    page_type: str = "note",
    body: str = "",
    tags: Optional[List[str]] = None,
    extra_fields: Optional[dict] = None,
    wikilinks: Optional[List[str]] = None,
) -> str:
    """Build a complete compliant brain page.

    Ensures:
    1. YAML frontmatter with title + type
    2. # H1 heading matching frontmatter title
    3. Optional [[wikilinks]] in body
    4. Body content
    """
    fm = build_frontmatter(title, page_type, tags, extra_fields)
    heading = f"# {title}"
    parts = [fm, "", heading, ""]

    if wikilinks:
        parts.append("## Cross-links")
        parts.append("")
        for wl in wikilinks:
            parts.append(f"- [[{wl}]]")
        parts.append("")

    if body:
        parts.append(body)

    return "\n".join(parts)


# ─── Graph Link Creation ────────────────────────────────────────────────────

def create_graph_link(
    from_slug: str,
    to_slug: str,
    link_type: str = "mentions",
    link_source: str = "script-auto",
    context: str = "",
) -> bool:
    """Create a gbrain graph link between two pages.

    Uses: gbrain link <from> <to> --link-type T --link-source S --context C

    Rules (from gbrain CLI):
    - link_source must be kebab-case
    - link_source cannot be one of the reserved reconciliation-managed values
    - link_type examples: mentions, works_at, invested_in, founded, customer_of
    """
    if link_source in RESERVED_LINK_SOURCES:
        print(f"⚠️  link_source '{link_source}' is reserved — using 'script-auto' instead", file=sys.stderr)
        link_source = "script-auto"

    cmd = [GBRAIN_BIN, "link", from_slug, to_slug,
           "--link-type", link_type,
           "--link-source", link_source]

    if context:
        cmd.extend(["--context", context])

    try:
        result = subprocess.run(cmd, capture_output=True, text=True, timeout=15)
        if result.returncode == 0:
            return True
        else:
            print(f"⚠️  gbrain link failed: {result.stderr.strip()}", file=sys.stderr)
            return False
    except subprocess.TimeoutExpired:
        print(f"⚠️  gbrain link timed out (15s)", file=sys.stderr)
        return False
    except FileNotFoundError:
        print(f"⚠️  gbrain not found at {GBRAIN_BIN}", file=sys.stderr)
        return False


# ─── Orphan Prevention ──────────────────────────────────────────────────────

def link_to_index(slug: str, category: str, context: str = "") -> bool:
    """Link a new page to its category index hub page.

    This is the primary orphan prevention mechanism. Every new page should
    call this immediately after creation.

    Args:
        slug: The new page's slug (e.g., "deals/acme-foo")
        category: One of INDEX_MAP keys (e.g., "deal", "email", "person")
        context: Optional context string for the link

    Returns:
        True if link was created (or already existed), False on failure
    """
    index_slug = INDEX_MAP.get(category)
    if not index_slug:
        print(f"⚠️  No index page for category '{category}' — page may be orphaned", file=sys.stderr)
        return False

    return create_graph_link(
        from_slug=index_slug,
        to_slug=slug,
        link_type="mentions",
        link_source="script-auto",
        context=context or f"Auto-linked from {index_slug}",
    )


# ─── Entity Cross-Linking ───────────────────────────────────────────────────

def link_entities(
    page_slug: str,
    entity_links: List[Tuple[str, str]],
) -> int:
    """Create bidirectional graph links between a new page and related entities.

    Args:
        page_slug: The new page's slug
        entity_links: List of (entity_slug, link_type) tuples
                      e.g., [("companies/acme", "customer_of"), ("people/john", "attended")]

    Returns:
        Number of links successfully created
    """
    count = 0
    for entity_slug, link_type in entity_links:
        if create_graph_link(entity_slug, page_slug, link_type, "script-auto"):
            count += 1
        create_graph_link(page_slug, entity_slug, link_type, "script-auto")
    return count


# ─── Page Validation ────────────────────────────────────────────────────────

def validate_page(filepath: str) -> Tuple[bool, str]:
    """Run the brain-compliance validator on a file."""
    if not os.path.exists(VALIDATOR):
        print(f"⚠️  Validator not found at {VALIDATOR}", file=sys.stderr)
        return True, "validator not found — skipping"

    try:
        result = subprocess.run(
            ["python3", VALIDATOR, filepath],
            capture_output=True, text=True, timeout=30
        )
        output = result.stdout + result.stderr
        is_valid = result.returncode == 0
        return is_valid, output
    except subprocess.TimeoutExpired:
        return False, "validator timed out"
    except Exception as e:
        return False, str(e)


# ─── Write + Link + Validate (Full Pipeline) ───────────────────────────────

def write_brain_page(
    slug: str,
    title: str,
    page_type: str = "note",
    body: str = "",
    tags: Optional[List[str]] = None,
    extra_fields: Optional[dict] = None,
    wikilinks: Optional[List[str]] = None,
    category: Optional[str] = None,
    entity_links: Optional[List[Tuple[str, str]]] = None,
    write_to_filesystem: bool = True,
    use_gbrain_put: bool = False,
) -> dict:
    """Full brain compliance pipeline: build → write → link → validate.

    This is the main entry point for all brain-writing scripts.

    Args:
        slug: Page slug (e.g., "deals/acme-foo")
        title: Page title (must match # H1 heading)
        page_type: Canonical type (deal, person, company, etc.)
        body: Markdown body content
        tags: Optional tags list
        extra_fields: Additional frontmatter fields
        wikilinks: Optional [[slug]] cross-links to include in body
        category: Category for index linking. If provided, creates a graph link
                  from the index hub to this page.
        entity_links: List of (entity_slug, link_type) for cross-linking
        write_to_filesystem: If True, writes .md file to BRAIN_DIR/<slug>.md
        use_gbrain_put: If True, also calls `gbrain put` to sync to DB

    Returns:
        dict with keys: slug, filepath, valid, links_created, warnings
    """
    warnings = []
    links_created = 0

    slug_valid, slug_msg = validate_slug(slug)
    if not slug_valid:
        warnings.append(f"Slug issue: {slug_msg}")

    content = build_page(
        title=title,
        page_type=page_type,
        body=body,
        tags=tags,
        extra_fields=extra_fields,
        wikilinks=wikilinks,
    )

    filepath = None
    if write_to_filesystem:
        filepath = str(BRAIN_DIR / f"{slug}.md")
        Path(filepath).parent.mkdir(parents=True, exist_ok=True)
        with open(filepath, "w") as f:
            f.write(content)
        os.chmod(filepath, 0o664)

    if use_gbrain_put:
        try:
            result = subprocess.run(
                [GBRAIN_BIN, "put", slug, "--content", content],
                capture_output=True, text=True, timeout=30
            )
            if result.returncode != 0:
                warnings.append(f"gbrain put failed: {result.stderr.strip()}")
        except Exception as e:
            warnings.append(f"gbrain put error: {e}")

    if category:
        if link_to_index(slug, category):
            links_created += 1
        else:
            warnings.append(f"Failed to link to {category} index — page may be orphaned")

    if entity_links:
        entity_count = link_entities(slug, entity_links)
        links_created += entity_count

    valid = True
    if filepath:
        valid, validation_msg = validate_page(filepath)
        if not valid:
            warnings.append(f"Validation issues: {validation_msg[:200]}")

    return {
        "slug": slug,
        "filepath": filepath,
        "valid": valid,
        "links_created": links_created,
        "warnings": warnings,
    }


# ─── Monthly Index Helper ───────────────────────────────────────────────────

def get_current_email_index_slug() -> str:
    """Return the current half-month email index slug."""
    now = datetime.now(timezone.utc)
    month = now.strftime("%Y-%m")
    day = now.day
    half = "w1" if day <= 15 else "w2"
    return f"email-index/{month}-{half}"


def get_current_cal_index_slug() -> str:
    """Return the current month's calendar index slug."""
    now = datetime.now(timezone.utc)
    return f"cal-index/{now.strftime('%Y-%m')}"


def update_index_map():
    """Update INDEX_MAP with current month/batch values.

    Call this at the top of scripts that run periodically to ensure
    they link to the correct current index page.
    """
    INDEX_MAP["email"] = get_current_email_index_slug()
    INDEX_MAP["calendar"] = get_current_cal_index_slug()


# ─── CLI Interface ──────────────────────────────────────────────────────────

def main():
    """CLI interface for quick orphan prevention from shell scripts.

    Usage:
        python3 brain_compliance_helper.py link deals/acme-foo deal
        python3 brain_compliance_helper.py link email-20260708-foo email
        python3 brain_compliance_helper.py validate ~/brain/deals/acme-foo.md
    """
    import argparse

    parser = argparse.ArgumentParser(description="Brain compliance helper")
    sub = parser.add_subparsers(dest="command")

    link_parser = sub.add_parser("link", help="Link a page to its index hub")
    link_parser.add_argument("slug", help="Page slug to link")
    link_parser.add_argument("category", help="Category (deal, email, person, etc.)")
    link_parser.add_argument("--context", default="", help="Link context")

    val_parser = sub.add_parser("validate", help="Validate a brain page")
    val_parser.add_argument("file", help="File path to validate")

    build_parser = sub.add_parser("build", help="Build a compliant page to stdout")
    build_parser.add_argument("slug", help="Page slug")
    build_parser.add_argument("--title", required=True, help="Page title")
    build_parser.add_argument("--type", default="note", help="Page type")
    build_parser.add_argument("--body", default="", help="Body content")

    args = parser.parse_args()

    if args.command == "link":
        update_index_map()
        success = link_to_index(args.slug, args.category, args.context)
        sys.exit(0 if success else 1)

    elif args.command == "validate":
        valid, msg = validate_page(args.file)
        print(msg)
        sys.exit(0 if valid else 1)

    elif args.command == "build":
        content = build_page(
            title=args.title,
            page_type=args.type,
            body=args.body,
        )
        print(content)
    else:
        parser.print_help()


if __name__ == "__main__":
    main()