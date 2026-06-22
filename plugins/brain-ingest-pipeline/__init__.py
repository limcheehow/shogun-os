"""
brain-ingest-pipeline — unified brain ingestion plugin.

Registers the brain-ingest-pipeline skill that defines the standard
COLLECT → ROUTE → BRIDGE → ENRICH → VALIDATE flow for all ingest sources.
"""

from pathlib import Path


def register(ctx):
    plugin_dir = Path(__file__).parent
    skills_dir = plugin_dir / "skills"

    skill_mappings = [
        ("brain-ingest-pipeline", skills_dir / "brain-ingest-pipeline" / "SKILL.md"),
    ]

    for name, path in skill_mappings:
        if path.exists():
            ctx.register_skill(name=name, path=path)