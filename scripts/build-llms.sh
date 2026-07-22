#!/usr/bin/env bash
# Generate llms-full.txt — inlines core docs for single-fetch LLM ingestion.
# Run this after updating any of the core docs listed below.
#
# Usage:
#   ./scripts/build-llms.sh
#
# See: https://github.com/garrytan/gbrain#llms-full-txt

set -euo pipefail

REPO_ROOT="$(cd "$(dirname "$0")/.." && pwd)"
OUTPUT="$REPO_ROOT/llms-full.txt"
REPO_BASE="${LLMS_REPO_BASE:-https://raw.githubusercontent.com/limcheehow/company-os/main}"

# ── Files to inline (in order) ──
CORE_DOCS=(
  "AGENTS.md"
  "INSTALL_FOR_AGENTS.md"
  "ARCHITECTURE.md"
  "SETUP.md"
  "PROFILE_CATALOG.md"
  "CRON_INVENTORY.md"
  "SECURITY.md"
)

cat > "$OUTPUT" << HEADER
# Shogun OS — Full Context

> Shogun OS is a reference architecture for running an entire organization through
> Hermes Agent. Each department gets a dedicated AI operator with role-specific
> tools, memory, and autonomy. Built on Hermes Agent + GBrain.

This file concatenates core Shogun OS documentation for single-fetch ingestion.
For the link-only index, see \`llms.txt\`. Source of truth: https://github.com/limcheehow/company-os.

HEADER

for doc in "${CORE_DOCS[@]}"; do
  src="$REPO_ROOT/$doc"
  if [ -f "$src" ]; then
    echo "" >> "$OUTPUT"
    echo "---" >> "$OUTPUT"
    echo "# $doc" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
    echo "Source: $REPO_BASE/$doc" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
    cat "$src" >> "$OUTPUT"
    echo "" >> "$OUTPUT"
    echo "✓ Inlined: $doc"
  else
    echo "⚠ Skipped (not found): $doc"
  fi
done

echo ""
echo "✅ Generated: $OUTPUT"
wc -l "$OUTPUT"