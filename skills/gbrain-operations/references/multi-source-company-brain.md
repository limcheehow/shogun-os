# Multi-Source Company Brain Setup

Setting up gbrain as a multi-source company brain for department-level agent isolation.

## Architecture

Each department gets its own gbrain source, and each Hermes profile connects to its corresponding source via `GBRAIN_SOURCE` env var:

```
gbrain sources list
  hr/         → ~/brain/hr/         → Hermes HR profile
  projects/   → ~/brain/projects/   → Hermes Projects profile
  finance/    → ~/brain/finance/    → Hermes Finance profile
  procurement/ → ~/brain/procurement/ → Hermes Procurement profile
```

## Setup

```bash
# Create sources per department
gbrain sources add hr --path ~/brain/hr
gbrain sources add projects --path ~/brain/projects
gbrain sources add finance --path ~/brain/finance
gbrain sources add procurement --path ~/brain/procurement

# Verify
gbrain sources status --json
```

## Per-Profile config.yaml

Each Hermes profile configures gbrain MCP scoped to its source:

```yaml
mcp_servers:
  gbrain:
    command: "gbrain"
    args: ["mcp"]
    env:
      GBRAIN_SOURCE: "hr"     # change per profile
```

## Scoping Behavior

| Action | With GBRAIN_SOURCE=hr | Without GBRAIN_SOURCE |
|---|---|---|
| `search` | Only hr/ source | All sources |
| `put_page` | Writes to hr/ source | Default source |
| `think` | Only hr/ source | All sources |
| `list_pages` | Only hr/ source | All sources |

## Cross-Source Operations

When a profile needs to access another department's data:

```bash
# CLI — explicit source
gbrain search "query" --source projects

# Via MCP — not possible with source-scoped connection.
# Use CLI or create a separate MCP connection for cross-source.
```

## Schema Packs Per Source

Each source can have its own schema pack defining entity types:

```bash
# HR schema
gbrain schema add-type employee --primitive person --prefix hr/employees/
gbrain schema add-type candidate --primitive person --prefix hr/candidates/

# Projects schema
gbrain schema add-type task --primitive note --prefix projects/tasks/
gbrain schema add-type milestone --primitive note --prefix projects/milestones/
```

See the main gbrain-operations skill for full MCP tools reference and refactoring patterns.