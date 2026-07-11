# Google Docs Content Update via batchUpdate

The `google_api.py` wrapper only supports `docs get` (read). To **write** to a Google Doc, use direct REST calls via Python's `requests` library against the batchUpdate endpoint.

## Prerequisites

The OAuth token needs **`https://www.googleapis.com/auth/documents`** write scope. Check: `cat ~/.hermes/google_token.json | python3 -c "import sys,json; scopes=json.load(sys.stdin)['scopes']; print('WRITE OK' if 'https://www.googleapis.com/auth/documents' in scopes else 'READONLY — need to re-auth')"`

If missing: patch `setup.py`'s SCOPES list (add `"https://www.googleapis.com/auth/documents"`), revoke with `$GSETUP --revoke`, then re-do the OAuth flow (Steps 3–5).

## Complete Script: Replace All Content in a Doc

Save as a standalone script (e.g. `docs_replace.py`). This reads the current doc structure, deletes all existing content, and inserts new text.

```python
import json, os, requests

DOC_ID = "1YNwymggnL9qtwr2n0iRy79JTe1FSt5PiQYL0SH6Cz84"
NEW_CONTENT = """Your new content here - plain text, \\n for newlines"""

def get_doc_structure(doc_id, token):
    """Get document to find the last index for full replacement."""
    headers = {"Authorization": f"Bearer {token}"}
    resp = requests.get(f"https://docs.googleapis.com/v1/documents/{doc_id}", headers=headers)
    resp.raise_for_status()
    doc = resp.json()
    # Find the end of the body content
    body_content = doc["body"]["content"]
    last_idx = body_content[-1]["endIndex"] if "endIndex" in body_content[-1] else body_content[-1].get("startIndex", 1)
    return last_idx, doc.get("revisionId")

def replace_all_content(doc_id, token, new_text):
    """Delete all body content and insert new text."""
    headers = {
        "Authorization": f"Bearer {token}",
        "Content-Type": "application/json"
    }
    
    last_idx, _ = get_doc_structure(doc_id, token)
    
    # Google Docs body always has at minimum 2 structural elements:
    # startIndex=1, endIndex=2 (the empty paragraph). We replace everything.
    requests_list = []
    
    # 1. Delete existing content (from index 1 to last_idx-1 or last_idx)
    # The document body starts at index 1
    end_idx = last_idx - 1 if last_idx > 2 else 2
    if end_idx > 1:
        requests_list.append({
            "deleteContentRange": {
                "range": {
                    "startIndex": 1,
                    "endIndex": end_idx
                }
            }
        })
    
    # 2. Insert new text at the start
    requests_list.append({
        "insertText": {
            "location": {"index": 1},
            "text": new_text
        }
    })

    body = {"requests": requests_list}
    resp = requests.post(
        f"https://docs.googleapis.com/v1/documents/{doc_id}:batchUpdate",
        headers=headers, json=body
    )
    resp.raise_for_status()
    return resp.json()

if __name__ == "__main__":
    with open(os.path.expanduser("~/.hermes/google_token.json")) as f:
        tok = json.load(f)
    
    result = replace_all_content(DOC_ID, tok["token"], NEW_CONTENT)
    print(f"Updated. Revision: {result.get('replies', [{}])[-1].get('revisionId', 'unknown')}")
```

## Append Content to an Existing Doc

When the doc already has content and you want to **add** text at the end (not replace everything):

```python
import json, os, requests

DOC_ID = "1YNwymggnL9qtwr2n0iRy79JTe1FSt5PiQYL0SH6Cz84"
NEW_TEXT = "Content to append at the end\n"

# Load token
with open(os.path.expanduser("~/.hermes/google_token.json")) as f:
    tok = json.load(f)

token = tok["token"]
headers = {"Authorization": f"Bearer {token}", "Content-Type": "application/json"}

# 1. Fetch document to find the end of body content
resp = requests.get(f"https://docs.googleapis.com/v1/documents/{DOC_ID}", headers=headers)
resp.raise_for_status()
doc = resp.json()

# Find the last endIndex across all body elements
last_idx = 1
for elem in doc["body"]["content"]:
    if "endIndex" in elem:
        last_idx = max(last_idx, elem["endIndex"])

# 2. Insert text at endIndex-1 (write before the last structural boundary)
body = {
    "requests": [
        {
            "insertText": {
                "location": {"index": last_idx - 1},
                "text": NEW_TEXT
            }
        }
    ]
}

resp = requests.post(
    f"https://docs.googleapis.com/v1/documents/{DOC_ID}:batchUpdate",
    headers=headers, json=body
)
resp.raise_for_status()
print("✅ Content appended.")
```

### Key detail: `last_idx - 1`

The Google Docs API uses **`endIndex`** as a boundary marker (like a cursor position between characters). When you insert at `endIndex - 1`, you're inserting *before* the closing boundary of the last paragraph element. Inserting at `last_idx` without the `-1` will fail with an index-out-of-range error because `last_idx` is the exclusive upper bound.

## Partial Updates (Insert at Specific Index)

Instead of replacing everything, you can target specific segments. Use `docs get` to find the startIndex of the paragraph you want to replace, then:

```python
requests = [
    {
        "deleteContentRange": {
            "range": {
                "startIndex": 42,   # paragraph start
                "endIndex": 150     # paragraph end
            }
        }
    },
    {
        "insertText": {
            "location": {"index": 42},
            "text": "Replacement text here\\n"
        }
    }
]
```

## Full Document Reformat: 3-Pass Approach

When the goal is to **reformat an existing doc** (replace all content with clean text, then apply heading styles and bold formatting), use this 3-pass approach:

### Pass 1: Delete existing content
```
GET /v1/documents/{DOC_ID} → find body last endIndex
POST batchUpdate: deleteContentRange(1, lastIdx-1)
```

### Pass 2: Insert clean text
No markdown artifacts (`**`, `*`, `===`, `---` separators, bullet markers). Just clean plain text with `\n` paragraph breaks.

### Pass 3: Re-read doc → classify by text → apply styles
This is the **critical insight**: do NOT pre-compute indices from your source text. Google Docs paragraph indices include invisible structural elements (paragraph boundaries, section breaks) that make simple offset math unreliable. Instead:

1. **Re-fetch the doc** with a fresh `GET /v1/documents/{DOC_ID}` to get actual paragraph elements with real `startIndex`/`endIndex` values
2. **Classify each paragraph** by matching its text content against known patterns
3. **Build style requests** using the actual indices from the API response

```python
# After insertText, re-read the doc:
doc = get_doc(token)  # fresh GET
style_requests = []

for elem in doc["body"]["content"]:
    if "paragraph" not in elem:
        continue
    para = elem["paragraph"]
    if "elements" not in para or not para["elements"]:
        continue

    # Assemble paragraph text from its textRuns
    para_text = "".join(
        run["textRun"]["content"]
        for run in para["elements"]
        if "textRun" in run
    )
    stripped = para_text.strip()
    if not stripped:
        continue

    # Use the actual indices from the API response
    start_idx = para["elements"][0].get("startIndex", 0)
    end_idx = para["elements"][-1].get("endIndex", 0)

    # Classify by text content
    style = None
    if stripped in {"✈️ FLIGHTS", "🏨 HOTELS", "📋 DAILY ITINERARY"}:
        style = "HEADING_1"
    elif re.match(r"^DAY \d —", stripped):
        style = "HEADING_2"
    elif re.match(r"^(Step \d+:|Route [AB]:)", stripped):
        style = "HEADING_3"

    if style:
        style_requests.append({
            "updateParagraphStyle": {
                "range": {"startIndex": start_idx, "endIndex": end_idx},
                "paragraphStyle": {"namedStyleType": style},
                "fields": "namedStyleType"
            }
        })

    # Bold label prefix using actual indices
    for prefix in ["Lunch:", "Dinner:", "Booking Ref:", "Cost:"]:
        if stripped.startswith(prefix):
            style_requests.append({
                "updateTextStyle": {
                    "range": {
                        "startIndex": start_idx,
                        "endIndex": start_idx + len(prefix)
                    },
                    "textStyle": {"bold": True},
                    "fields": "bold"
                }
            })

# Apply in batches of 50
for i in range(0, len(style_requests), 50):
    requests.post(
        f"https://docs.googleapis.com/v1/documents/{DOC_ID}:batchUpdate",
        headers=headers,
        json={"requests": style_requests[i:i+50]}
    ).raise_for_status()
```

### Classification Strategy
Organize your `classify_text()` function with priority order:

1. **Exact match** for section headers (emoji-prefixed like `✈️ FLIGHTS`) → `HEADING_1`
2. **Regex match** for day titles (`^DAY \d —`) → `HEADING_2`
3. **String prefix** for route markers (`Step `, `Route `, `Option `) → `HEADING_3`
4. **Capitalized arrow patterns** (`TOKYO MARRIOTT → ODAIBA`) → `HEADING_3`
5. **Bold label prefixes** (`Lunch:`, `Dinner:`, `Booking Ref:`) → `NORMAL_TEXT` with bold textStyle
6. Everything else → `NORMAL_TEXT`

### Style-Matching Strategy — Matching the Original Doc's Format

When appending an appendix or new section to an existing doc, the new content must **match the original doc's heading hierarchy** visually. The 3-pass approach handles the mechanics; the **classification strategy** determines which paragraphs get which style.

**Before writing any content, inspect the original doc's heading patterns:**

```python
# After fetching the doc, print every styled paragraph
for elem in doc['body']['content']:
    if 'paragraph' not in elem: continue
    style = elem['paragraph'].get('paragraphStyle', {}).get('namedStyleType', 'NORMAL')
    text = ''.join(e.get('textRun',{}).get('content','') for e in elem['paragraph'].get('elements',[]) if 'textRun' in e)
    if style != 'NORMAL_TEXT' and text.strip():
        print(f"{style}: {text.strip()[:80]}")
```

This reveals the actual pattern — e.g., the original doc uses `HEADING_1` for numbered sections ("What Is This?", "Diagram 1:..."), `HEADING_2` for subsections ("Telegram (Main Chat)", "Early Morning"), and `HEADING_3` for minor sub-topics. **Mirror this hierarchy exactly** in your appendix.

**Practical classification for appendices:**
- `HEADING_1` → appendix title and top-level summary sections (e.g., "APPENDIX: PROFILES IN DETAIL", "HOW EVERYTHING CONNECTS")
- `HEADING_2` → each profile/entity name, major sub-sections (e.g., "A Typical Day", "How It Works", "Research Phase")
- `HEADING_3` → time entries (`7:00 AM — Morning Briefing`), workflow step groupings

The key insight: use **exact-string-set matching** for headings (not regex) and build the lookup sets from the planned content, not the source text. This avoids fragile offset math.

Layman-friendly content: When writing new sections for a doc aimed at a general audience, use conversational tone ("Have you ever wished...", "My AI does not sleep...", "You tell it where to go and it plans everything"). Avoid technical jargon (Primary Provider, gbrain, batchUpdate, API endpoints). Focus on **what each thing does** — workflows, schedules, routines — not implementation details.

### Why pre-computing source-text offsets fails
Naive approach: compute paragraph start/end indices from the source text string, then pass those to batchUpdate. This fails because:

| Naive (pre-compute offsets) | 3-pass (re-read after insert) |
|---|---|
| Off-by-one errors from invisible structural chars | Always correct — API tells you the actual boundaries |
| Headings land on wrong paragraphs | Each paragraph classified by its text content |
| Brittle — any change to source text shifts everything | Robust — works regardless of source text structure |

## View-Only Doc Workaround

When the user shares a Google Doc link that shows as "view-only" in the browser (they haven't granted you edit access), the **batchUpdate API still works** if your OAuth token is already authorized with edit scope on the document. The browser's "view-only" status pertains to the web interface, not the API.

This is useful when:
- The user has shared the doc link publicly but not explicitly as "Editor"
- The doc was created with a service account or shared with the OAuth-authenticated account
- You don't need sign-in to the web interface — the API bypasses it

**Always try the API first** before declaring a doc uneditable. Check token scopes first, then attempt the batchUpdate. If it fails with `403`, the token genuinely lacks write access.

## Formatting Rules — Stylistic Preferences (User-Corrected)

These are hard enforcement rules based on user corrections. Violating any of these will result in rejection.

### DO NOT use decorative separator lines

Never use ═══════, -----, ▬▬▬▬▬, ***, or any ASCII-art dividers between sections. Google Docs has proper heading styles for visual hierarchy. Separator lines are a sign the content was dumped as plain text without applying real formatting. Use HEADING_1/2/3 instead.

BAD:
```
═══════════════════════════════════════════════
1. THE MAIN PROFILE
═══════════════════════════════════════════════
```

GOOD: Apply HEADING_2 named style to "1. THE MAIN PROFILE" via batchUpdate.

### DO NOT insert excessive blank paragraphs

Never insert more than one consecutive blank paragraph (`\n\n` at most). Triple blank lines (`\n\n\n\n\n`) or multiple empty paragraph elements produce ugly whitespace gaps in the rendered doc. Use a single `\n` between paragraphs and `\n\n` between sections only.

BAD:
```python
text += "\n\n\n\n\n"
```

GOOD: Single newline between paragraphs, double between section boundaries:
```python
text += "\n\n"
```

### Match the original doc's heading hierarchy exactly

Before writing new content, fetch the doc and inspect every heading style in use:
```python
for elem in doc['body']['content']:
    if 'paragraph' not in elem: continue
    style = elem['paragraph'].get('paragraphStyle', {}).get('namedStyleType', 'NORMAL')
    text = ''.join(e.get('textRun',{}).get('content','') for e in elem['paragraph'].get('elements',[]) if 'textRun' in e)
    if style != 'NORMAL_TEXT' and text.strip():
        print(f"{style}: {text.strip()[:80]}")
```

Mirror the hierarchy exactly — do not invent your own heading levels. If the original uses HEADING_1 for section titles and HEADING_2 for subsections, do the same.

### No "wall of text" paragraphs

Break long descriptions into digestible paragraphs of 2–4 sentences each. Each functional section (one time entry, one feature description) gets its own paragraph.

### Content tone for public-facing docs

When writing doc content for a general audience (not technical):
- Conversational, layman-friendly tone
- Explain what each thing DOES in plain English
- Avoid jargon: Primary Provider → "AI engine", gbrain → "knowledge base", batchUpdate → "formatting"
- Start sections with a one-sentence elevator pitch

### Classification strategy for appendices

For appendix/footer sections appended to an existing doc, use exact-string-set matching (not regex) to classify headings:

- HEADING_1 → appendix title and top-level summary sections ("APPENDIX: PROFILES IN DETAIL", "HOW EVERYTHING CONNECTS")
- HEADING_2 → each profile/entity name, major sub-sections ("A Typical Day", "How It Works", "Research Phase", "Expenses")
- HEADING_3 → time entries ("7:00 AM — Morning Briefing"), workflow step groupings

Build the lookup sets from the planned content, not the source text. This avoids fragile offset math.

## Common Pitfalls

- **Newline character at end of segment** → Deleting up to the final endIndex triggers: "The range cannot include the newline character at the end of the segment." Fix: always use endIndex-1 as the upper bound of the delete range, not the raw endIndex. The final position is a structural boundary, not content.

- **403 Permission Denied** → Token has `documents.readonly` only. Fix: add `documents` write scope to `setup.py`, revoke token, re-auth.
- **Index out of range** → Delete ranges must be within the document's actual extent. Always fetch current doc structure first.
- **Empty doc** → A fresh doc has body = `{"content": [{"startIndex": 1, "endIndex": 2, "paragraph": {}}]}`. Deleting from 1 to 2 removes the empty paragraph, leaving no content location for insert. Safer: don't delete if end_idx <= 2, or ensure your insert text includes at least a newline so the parser creates a paragraph.
- **Text needs newlines** → Google Docs uses `\n` as paragraph breaks. Plain text concatenated without newlines becomes one long paragraph. Always terminate each logical section with `\n`.
- **Sequential batchUpdate calls shift indices (critical!)** → Every write to a doc changes startIndex/endIndex values for ALL subsequent paragraphs. After the first delete+insert, every remaining index position has shifted. If you issue multiple batchUpdate calls sequentially:
  - **Fetching indices once at the start and reusing them across multiple batchUpdate calls will produce wrong results** — you'll delete the wrong content or hit index-out-of-range errors.
  - **Safe approach #1: Process in reverse index order.** Sort your replacements by startIndex descending, then the highest-index replacement runs first and doesn't shift any indexes behind it. This works when you know all your target indices upfront (single `docs get` pass).
  - **Safe approach #2: Fresh fetch between every call.** After each batchUpdate, fetch the doc again with a fresh `docs get` to get the new indices before constructing the next delete range. This handles dependencies where content shifts unpredictably.
  - **Merged paragraphs (worst case):** If you delete content in the middle of what was previously two separate paragraphs, Google Docs may merge them into one. The resulting paragraph's text is a concatenation of both original paragraphs' content. To avoid this, ensure your replacement text includes the `\n` between what should remain separate paragraphs.
  - **Diagnostic technique:** After a batchUpdate returns 200 but visual inspection shows merged/garbled content, fetch the doc and search for telltale signs: two unrelated content topics in one paragraph, or expected text followed directly by text that was in a different section. Document this as a merged-paragraph artifact and plan a cleanup pass.