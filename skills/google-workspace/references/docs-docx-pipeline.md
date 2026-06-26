# DOCX → Google Docs Pipeline (for Beautifully Formatted Docs)

When you need to convert structured content (markdown, itinerary, report) into a well-formatted Google Doc with proper heading styles, tables, TOC, and page breaks, the **DOCX upload** approach is far superior to using the batchUpdate API directly.

## Why DOCX > batchUpdate

| Approach | Heading styles | Grouped tables | TOC field | Page breaks | Effort |
|---|---|---|---|---|---|
| `python-docx` → Drive upload | ✅ Native DOCX styles convert to Google Docs heading styles | ✅ Styled tables with colour headers | ✅ Word TOC field (Update Field to generate) | ❌ Need batchUpdate for page breaks | One script |
| batchUpdate text insert | ❌ Must classify and style each paragraph after insert | ❌ Must build each cell with nested requests | ❌ Must recreate manually | ✅ Easy `insertPageBreak` | Two-pass (insert + style) |

The DOCX approach preserves far more styling fidelity because Google Docs' DOCX import keeps heading styles, table formatting, bullets, and font properties intact.

## Pipeline Overview

```
Markdown source
    ↓ (parse + classify content)
python-docx script
    ↓ (cover page, TOC field, H1/H2/H3, styled tables, bullets)
well-formatted .docx
    ↓ (Drive API upload with mimeType conversion)
Google Doc with native heading styles
    ↓ (optional batchUpdate for page breaks)
Perfected Google Doc
```

## Step 1: python-docx Script

Build a Python script using the `python-docx` library (already installed in the Hermes venv).

### Cover page
```python
from docx import Document
from docx.shared import Pt, RGBColor
from docx.enum.text import WD_ALIGN_PARAGRAPH

doc = Document()

# Spacer rows
for _ in range(6):
    doc.add_paragraph()

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('🗾')
run.font.size = Pt(48)

p = doc.add_paragraph()
p.alignment = WD_ALIGN_PARAGRAPH.CENTER
run = p.add_run('Title')
run.font.size = Pt(36)
run.bold = True
run.font.color.rgb = RGBColor(0x1B, 0x2A, 0x4A)  # dark navy
```

### Heading styles that survive DOCX → Drive conversion
- `doc.add_heading('text', level=1)` → Google Docs **Heading 1** (H1)
- `doc.add_heading('text', level=2)` → Google Docs **Heading 2** (H2)
- `doc.add_heading('text', level=3)` → Google Docs **Heading 3** (H3)

These convert reliably. Higher levels (4-9) also work but H1/H2/H3 are most useful for TOC generation.

### Styled tables with header colours
```python
from docx.oxml.ns import qn, nsdecls
from docx.oxml import parse_xml

def set_cell_shading(cell, color_hex):
    shading = parse_xml(f'<w:shd {nsdecls("w")} w:fill="{color_hex}" w:val="clear"/>')
    cell._tc.get_or_add_tcPr().append(shading)

# Header row with dark navy
for i, header in enumerate(headers):
    cell = table.rows[0].cells[i]
    run = cell.paragraphs[0].add_run(header)
    run.bold = True
    run.font.color.rgb = RGBColor(0xFF, 0xFF, 0xFF)
    set_cell_shading(cell, "1B2A4A")

# Alternating row colours
for r_idx, row_data in enumerate(data):
    for c_idx, val in enumerate(row_data):
        cell = table.rows[r_idx + 1].cells[c_idx]
        cell.paragraphs[0].add_run(str(val))
        if r_idx % 2 == 1:
            set_cell_shading(cell, "F0F4F8")
```

### Table of Contents field (Word field code)
```python
p = doc.add_paragraph()
run = p.add_run()
fldChar1 = parse_xml(f'<w:fldChar {nsdecls("w")} w:fldCharType="begin"/>')
run._r.append(fldChar1)

run2 = p.add_run()
instrText = parse_xml(f'<w:instrText {nsdecls("w")} xml:space="preserve"> TOC \\o "1-3" \\h \\z \\u </w:instrText>')
run2._r.append(instrText)

# ... separator, placeholder text, end
```
The TOC field needs **Right-click → Update Field** in Google Docs to populate.

### Page breaks
```python
doc.add_page_break()
```
⚠️ Page breaks in DOCX **do NOT survive** the Drive conversion to Google Docs. They must be added via batchUpdate afterwards (see Step 3).

## Step 2: Upload to Drive with Conversion

```python
from google.oauth2.credentials import Credentials
from googleapiclient.discovery import build
from googleapiclient.http import MediaFileUpload

creds = Credentials.from_authorized_user_file(
    TOKEN_PATH,
    scopes=["https://www.googleapis.com/auth/drive.file"]
)
# Refresh if needed
from google.auth.transport.requests import Request
if creds.expired and creds.refresh_token:
    creds.refresh(Request())
    with open(TOKEN_PATH, 'w') as f:
        f.write(creds.to_json())

drive = build("drive", "v3", credentials=creds)

media = MediaFileUpload(
    DOCX_PATH,
    mimetype='application/vnd.openxmlformats-officedocument.wordprocessingml.document',
    resumable=True
)

body = {
    'name': 'Document Title',
    'mimeType': 'application/vnd.google-apps.document'  # ← converts to Google Doc!
}

file = drive.files().create(body=body, media_body=media, fields='id,webViewLink').execute()
```

The key trick: set `mimeType` to `application/vnd.google-apps.document` in the request body. This tells Drive to **convert** the uploaded DOCX to native Google Docs format.

### Optional: Delete the old doc first
```python
results = drive.files().list(
    q="name = 'Document Title' and trashed = false",
    fields="files(id, name, mimeType)"
).execute()
for existing in results.get('files', []):
    drive.files().delete(fileId=existing['id']).execute()
```

## Step 3: Add Page Breaks via batchUpdate (Post-Upload)

Since DOCX page breaks don't survive Drive conversion, use the Docs batchUpdate API:

```python
from googleapiclient.discovery import build

service = build("docs", "v1", credentials=creds)
doc = service.documents().get(documentId=DOC_ID).execute()

# Find Day/section headings that need page breaks before them
day_headings = []
for el in doc.get('body', {}).get('content', []):
    para = el.get('paragraph', {})
    style = para.get('paragraphStyle', {}).get('namedStyleType', 'NORMAL_TEXT')
    if style == 'HEADING_1':
        text = ''.join([r.get('textRun', {}).get('content', '') for r in para.get('elements', [])])
        if text.strip().startswith('Day '):
            elements = para.get('elements', [])
            if elements:
                day_headings.append((elements[0]['startIndex'], text.strip()))

# Process in REVERSE order to preserve index offsets
requests = []
for start_idx, txt in reversed(day_headings):
    requests.append({
        'insertPageBreak': {
            'location': {'index': start_idx}
        }
    })

result = service.documents().batchUpdate(
    documentId=DOC_ID,
    body={'requests': requests}
).execute()
```

**Critical: process insertions in REVERSE index order.** Each `insertPageBreak` shifts all subsequent indices. Working backwards avoids index drift.

## Verifying the Result

Use the Docs API to check heading styles applied:
```python
doc = service.documents().get(documentId=DOC_ID).execute()
headings = {'HEADING_1': 0, 'HEADING_2': 0, 'HEADING_3': 0}
for el in doc.get('body', {}).get('content', []):
    para = el.get('paragraph', {})
    style = para.get('paragraphStyle', {}).get('namedStyleType', 'NORMAL_TEXT')
    if style in headings:
        headings[style] += 1

# Check page break elements (not sectionBreak — insertPageBreak creates paragraph-level pageBreak elements)
pb_count = sum(1 for el in doc.get('body', {}).get('content', [])
               for e in el.get('paragraph', {}).get('elements', [])
               if 'pageBreak' in e)
```

## Important Caveats

1. **TOC needs manual update** — the Word TOC field code converts but doesn't auto-populate. Tell user to right-click → Update Field in Google Docs, or Insert → Table of Contents.
2. **Page breaks in DOCX are lost** during Drive's DOCX → Google Doc conversion. Always add them via batchUpdate post-upload.
3. **Drive upload scope** — `drive.file` scope is sufficient. You do NOT need the wider `drive` scope.
4. **Token path** — Use `get_hermes_home()` from the skill script for portability:
   ```python
   sys.path.insert(0, '.../skills/productivity/google-workspace/scripts')
   from _hermes_home import get_hermes_home
   TOKEN_PATH = str(get_hermes_home() / "google_token.json")
   ```
5. **Heading styles from DOCX convert** — H1 → Heading 1, H2 → Heading 2, etc. This is reliable.
6. **Syntax check gotcha** — `write_file` auto-lints Python. If the patch tool mangles `get_hermes_home()` call (e.g. `get_hermes_home()` → `ge...me()`), write scripts via `cat << 'PYEOF'` heredoc in terminal instead.