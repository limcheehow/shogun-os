# Brain Markdown → Google Doc Sync Pattern

Use this when you need to keep a Google Doc in sync with a local `.md` file (e.g. a trip itinerary in `~/brain/trips/`). The pattern: read the markdown, convert to clean Google Doc text, replace all content via `batchUpdate`, then apply heading/bold styles by re-reading the doc.

## When to Use

- User has a Google Doc they want updated whenever a corresponding brain file changes
- The Doc content is a derivative of the `.md` (not a full 1:1 — tables become structured text, wiki links are dropped, markdown artifacts stripped)
- You need scheduled sync (cron) to keep them aligned daily

## The Sync Script Structure

### 1. Read & Clean

```python
def clean_markdown(text):
    """Strip **bold**, [text](url) links, __ underlines."""
    text = re.sub(r'\*\*(.+?)\*\*', r'\1', text)
    text = re.sub(r'\[([^\]]+)\]\([^)]+\)', r'\1', text)
    return text
```

Key conversion decisions:
- **Tables** (`| cell | cell |`) → collapse to pipe-delimited text lines, skip separator rows (`|---|---|`)
- **Bullets** (`- item`) → prefix with `• `, clean markdown inside
- **Headings** (`## Title`) → strip the `#` markers; they become plain text that gets styled later via API
- **Wiki links** (`[[page]]`) → skip entirely
- **Empties** → collapse runs of blank lines to one

### 2. Delete + Insert (full replace)

```python
# Get current doc extent
doc = api_get()
last_idx = max(e["endIndex"] for e in doc["body"]["content"] if "endIndex" in e)

# Delete everything from index 1 to last_idx-1
requests = [{"deleteContentRange": {"range": {"startIndex": 1, "endIndex": last_idx - 1}}}]

# Insert new text at index 1
requests.append({"insertText": {"location": {"index": 1}, "text": clean_text + "\n"}})

api_batch(requests)
```

**Pitfall:** Always delete with `endIndex = last_idx - 1` (not `last_idx`) — the exclusive upper bound. If `last_idx` is 2 (empty doc), skip the delete to avoid an empty body error.

**Pitfall:** Terminate `insertText` with `"\n"` so Google Docs creates at least one paragraph element. Without it, the first style update hits index-out-of-range.

### 3. Re-read → Classify → Style

Do NOT pre-compute paragraph indices from your source text. Google Docs paragraph indices include invisible structural elements. Always re-fetch after insertion and classify by **text content**:

```python
doc = api_get()
style_reqs = []
for elem in doc["body"]["content"]:
    if "paragraph" not in elem:
        continue
    para_text = "".join(run["textRun"]["content"]
                        for run in elem["paragraph"]["elements"]
                        if "textRun" in run)
    stripped = para_text.strip()
    if not stripped:
        continue

    start_idx = elem["paragraph"]["elements"][0]["startIndex"]
    end_idx = elem["paragraph"]["elements"][-1]["endIndex"]

    # Classify
    heading = None
    if stripped.upper() in ["FLIGHTS", "HOTELS", "DAILY ITINERARY", ...]:
        heading = "HEADING_1"
    elif re.match(r'^DAY \d', stripped, re.IGNORECASE):
        heading = "HEADING_2"
    elif re.match(r'^(Step \d|Option [A-Z]|Route [A-Z])', stripped):
        heading = "HEADING_3"

    if heading:
        style_reqs.append({
            "updateParagraphStyle": {
                "range": {"startIndex": start_idx, "endIndex": end_idx},
                "paragraphStyle": {"namedStyleType": heading},
                "fields": "namedStyleType"
            }
        })

    # Also apply bold to label prefixes like "Booking Ref:", "Lunch:", etc.
```

Apply in batches of 50 (API limit per call).

## Cron Setup (no_agent = True)

Since syncing is purely mechanical (no LLM reasoning needed), use a `no_agent=true` cron job:

```bash
cp ~/brain/trips/my-sync-script.py ~/.hermes/scripts/my-sync-script.py
```

```python
cronjob(action="create",
        name="my-brain-to-doc-daily-sync",
        schedule="0 6 * * *",   # Daily at 6AM
        script="my-sync-script.py",
        no_agent=True,
        deliver="origin")
```

**Why no_agent:** The script reads the file, calls the Docs API, and prints output. No LLM tokens consumed. The stdout is delivered to the origin channel. If the script fails, the user gets an error alert.

**Why not no_agent:** If you need variable handling (e.g. compare brain file modification time vs doc revision, or decide whether to sync based on content diff), use a regular cron job with a prompt and let the agent decide.

## Token Handling for cron Scripts

The OAuth token lives at `~/.hermes/google_token.json` and auto-refreshes. The sync script reads it directly:

```python
with open(os.path.expanduser("~/.hermes/google_token.json")) as f:
    tok_data = json.load(f)
TOKEN = tok_data.get("token", tok_data.get("access_token", ""))
if not TOKEN:
    TOKEN = tok_data.get("credentials", {}).get("token", "")
```

The token format varies (sometimes `{"token": "...", ...}`, sometimes `Credentials` object). Handle both.

## Verification Checks

After syncing, verify key content anchors:

```python
checks = [
    ("Day 4 — Tsutsumidori", "Tsutsumidori" in body),
    ("Day 3 — Toshima Kids Park", "Toshima Kids Park" in body),
    ("Haruka schedule", "Haruka" in body),
]
```

This catches truncation, bad deletion ranges, or style application failures silently.

## Pitfalls

| Issue | Fix |
|-------|-----|
| **Script path must be in `~/.hermes/scripts/` for cron** | `cronjob(..., script="name.py")` resolves relative to `~/.hermes/scripts/`. Absolute paths are rejected. |
| **Token format varies** | Check both `"token"` and `"access_token"` keys; also `["credentials"]["token"]` for google-auth format. |
| **Empty body after delete** | Always check `last_idx` before deleting. A fresh doc has body content ending at index 2. |
| **Style requests fail if doc has no paragraphs** | Ensure insert text ends with `\n` so the parser creates paragraph elements. |
| **batchUpdate index shift** | After every write operation, all subsequent indices change. Always re-read the doc after insert before building style requests. |
| **Merged paragraphs** | If you delete mid-paragraph, Google Docs may merge adjacent paragraphs. Use `\n` between logical sections. |
| **batchUpdate 50-request limit** | Batch by slicing `style_reqs[i:i+50]` — larger batches get rejected silently. |