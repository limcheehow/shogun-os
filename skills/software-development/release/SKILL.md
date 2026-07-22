---
name: release
description: Bump semver, generate changelog, create git tag. Triggers include "release", "bump version", "ship release", "tag release", "publish v".
category: software-development
---

# Release — Version Bumping & Changelog

**Route to:** coding-agent profile

Replicate of the `/release` slash command from -superpowers.

## Protocol

```bash
#!/bin/bash
set -e

BUMP="$1"
if [[ "$BUMP" != "patch" && "$BUMP" != "minor" && "$BUMP" != "major" ]]; then
  echo "ERROR: arg must be one of: patch, minor, major" >&2
  exit 1
fi

# Read current version
if [[ ! -f VERSION ]]; then
  echo "0.1.0" > VERSION
fi
CURRENT=$(cat VERSION)

# Parse
IFS='.' read -r MAJOR MINOR PATCH <<< "$CURRENT"

# Bump
case "$BUMP" in
  major) MAJOR=$((MAJOR + 1)); MINOR=0; PATCH=0 ;;
  minor) MINOR=$((MINOR + 1)); PATCH=0 ;;
  patch) PATCH=$((PATCH + 1)) ;;
esac

NEW_VERSION="${MAJOR}.${MINOR}.${PATCH}"
TODAY=$(date +%Y-%m-%d)

echo "Bumping $CURRENT → $NEW_VERSION"

# Prepare changelog
if [[ -f CHANGELOG.unreleased.md ]]; then
  UNRELEASED=$(sed '1,2d' CHANGELOG.unreleased.md)
else
  UNRELEASED=""
fi

if [[ ! -f CHANGELOG.md ]]; then
  echo "# Changelog" > CHANGELOG.md
  echo "" >> CHANGELOG.md
fi

# Prepend new version to CHANGELOG.md
{
  echo "# Changelog"
  echo ""
  echo "## v${NEW_VERSION} (${TODAY})"
  echo ""
  if [[ -n "$UNRELEASED" ]]; then
    echo "$UNRELEASED"
  else
    echo "- No changes recorded"
  fi
  echo ""
  tail -n +3 CHANGELOG.md 2>/dev/null
} > CHANGELOG.tmp && mv CHANGELOG.tmp CHANGELOG.md

# Reset unreleased changelog
echo "## Unreleased" > CHANGELOG.unreleased.md
echo "" >> CHANGELOG.unreleased.md

# Write new version
echo "$NEW_VERSION" > VERSION

# Git operations
git add VERSION CHANGELOG.md CHANGELOG.unreleased.md
git commit -m "chore: bump version to ${NEW_VERSION}"
git tag "v${NEW_VERSION}"

echo "Released v${NEW_VERSION}"
echo "Run 'git push && git push --tags' to push to remote"
```

## Usage

```
/release patch    # 0.1.0 → 0.1.1
/release minor    # 0.1.0 → 0.2.0  
/release major    # 0.1.0 → 1.0.0
```

## What it does
1. Reads current version from `VERSION` file (creates `0.1.0` if missing)
2. Bumps the version
3. Reads `CHANGELOG.unreleased.md` entries
4. Prepends them to `CHANGELOG.md` under a `## vX.Y.Z (YYYY-MM-DD)` header
5. Clears `CHANGELOG.unreleased.md`
6. Writes new version to `VERSION`
7. Git commits and tags

## Guardrails

- Must be on a clean branch (no uncommitted changes)
- CHANGELOG.unreleased.md should have actual entries
- Tag should be pushed with the commit