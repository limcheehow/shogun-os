# Bulk Import from Backup Zip

Use this when someone sends a `.zip` containing companies/ and persons/ .md files to be imported into the brain.

## Steps

1. **Inspect the archive:**
   ```bash
   unzip -l path/to/backup.zip | head -20
   unzip -l path/to/backup.zip | grep -c "companies/"
   unzip -l path/to/backup.zip | grep -c "persons/"
   ```

2. **Extract to a temp location:**
   ```bash
   mkdir -p /tmp/brain-update && cd /tmp/brain-update
   unzip -o ~/.hermes/cache/documents/<archive-name>.zip
   ```

3. **Copy files to brain directories** (use `-n`/`--update=none` to avoid overwriting existing):
   ```bash
   cp -n companies/*.md ~/brain/companies/
   cp -n persons/*.md ~/brain/people/
   ```

4. **Clean up temp files:**
   ```bash
   rm -rf /tmp/brain-update
   ```

5. **Run gbrain sync** (with OpenRouter key):
   ```bash
   cd ~/gbrain && \
     OPENROUTER_API_KEY=$(grep -m1 '^OPENROUTER_API_KEY=' ~/.hermes/.env | cut -d= -f2-) \
     OPENAI_API_KEY="" \
     bun run src/cli.ts sync
   ```

6. **Verify import:**
   ```bash
   cd ~/gbrain && bun run src/cli.ts doctor | grep "connection"
   # Expect: Connected, NNN pages (should be higher than before)
   ```

## Pitfalls

- Check the source `local_path` first — if it's null, sync does nothing (see main SKILL.md)
- Large archives (10K+ files) WILL timeout at 300s — run in background
- Stale locks accumulate on timeout — clear via `gbrain_cycle_locks` DELETE
- Don't run with only `OPENAI_API_KEY` — it's quota-exhausted, causing 429 errors on every embedding
