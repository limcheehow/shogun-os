# Editing DOCX Table Cells (Drive Download → XML Edit → Re-Upload)

Use this when you need to modify specific cells in a table inside a .docx file stored on Google Drive. The technique downloads the DOCX, edits the XML inside the ZIP archive, and re-uploads.

## Why not Google Docs API?

Some .docx files are uploaded as Office files (not converted to native Google Docs). The Docs API refuses them with:
```
This operation is not supported for this document. The document must not be an Office file.
```

For these, you must download, edit locally, and re-upload.

## How DOCX Works

A .docx file is a ZIP archive containing XML files:
- `word/document.xml` — the main content (paragraphs, tables, formatting)
- `word/styles.xml` — style definitions
- `word/_rels/document.xml.rels` — relationships to images, etc.

The main content uses the Office Open XML namespace:
- `http://schemas.openxmlformats.org/wordprocessingml/2006/main`

## Technique: Download → XML Edit → Re-Zip → Upload

### Step 1: Download from Drive

Use Drive API with `supportsAllDrives=true` for shared drives:

```python
import json, os, requests

DOC_ID = "your_drive_file_id"

with open(os.path.expanduser("~/.hermes/google_token.json")) as f:
    tok = json.load(f)

token = tok["token"]
headers = {"Authorization": f"Bearer {token}"}

resp = requests.get(
    f"https://www.googleapis.com/drive/v3/files/{DOC_ID}?alt=media&supportsAllDrives=true",
    headers=headers,
    stream=True
)
content = resp.content  # bytes of the .docx
```

### Step 2: Read XML and edit table cells

```python
import zipfile, xml.etree.ElementTree as ET, io

ns = 'http://schemas.openxmlformats.org/wordprocessingml/2006/main'
ET.register_namespace('w', ns)

with zipfile.ZipFile(io.BytesIO(content), 'r') as z:
    xml_content = z.read('word/document.xml')

root = ET.fromstring(xml_content)

# Find all tables
tables = list(root.iter(f'{{{ns}}}tbl'))
table = tables[0]  # first table (the compliance matrix)

# Find all rows
rows = list(table.iter(f'{{{ns}}}tr'))

def get_cell_text(cell):
    """Read text content of a table cell."""
    texts = []
    for t in cell.iter(f'{{{ns}}}t'):
        if t.text:
            texts.append(t.text)
    return ''.join(texts)

def set_cell_text(cell, new_text):
    """Replace all text in a cell, preserving paragraph structure."""
    existing_paras = list(cell.iter(f'{{{ns}}}p'))
    for pi, para in enumerate(existing_paras):
        if pi == 0:
            # Clear existing runs and add one containing our text
            for run in list(para.iter(f'{{{ns}}}r')):
                para.remove(run)
            run_elem = ET.SubElement(para, f'{{{ns}}}r')
            t_elem = ET.SubElement(run_elem, f'{{{ns}}}t')
            t_elem.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')
            t_elem.text = new_text
        else:
            cell.remove(para)

# Modify specific rows by requirement text match
for ri, row in enumerate(rows):
    cells = list(row.iter(f'{{{ns}}}tc'))
    if len(cells) < 3:
        continue
    sol_text = get_cell_text(cells[2])
    
    # Example: fix a row mentioning the wrong database
    if 'ApsaraDB RDS PostgreSQL' in sol_text:
        set_cell_text(cells[2], "MySQL 8 on-prem at DC + DRC — no cloud database.")
```

### Step 3: Re-zip and upload

```python
# Write modified XML back into a new ZIP
modified_xml = ET.tostring(root, encoding='unicode')
output_buffer = io.BytesIO()

with zipfile.ZipFile(io.BytesIO(original_content), 'r') as zin:
    with zipfile.ZipFile(output_buffer, 'w', zipfile.ZIP_DEFLATED) as zout:
        for item in zin.infolist():
            data = zin.read(item.filename)
            if item.filename == 'word/document.xml':
                zout.writestr(item, modified_xml.encode('utf-8'))
            else:
                zout.writestr(item, data)

# Save locally or upload to Drive
with open('/tmp/modified.docx', 'wb') as f:
    f.write(output_buffer.getvalue())

# Upload to Drive
upload_headers = {
    'Authorization': f'Bearer {token}',
    'Content-Type': 'application/json; charset=UTF-8',
    'X-Upload-Content-Type': 'application/vnd.openxmlformats-officedocument.wordprocessingml.document'
}

metadata = {
    'name': 'Updated File.docx',
    'parents': [FOLDER_ID],
}

resp = requests.post(
    'https://www.googleapis.com/upload/drive/v3/files?uploadType=resumable&supportsAllDrives=true',
    headers=upload_headers,
    json=metadata
)
upload_url = resp.headers.get('Location')

with open('/tmp/modified.docx', 'rb') as f:
    resp2 = requests.put(upload_url, data=f)
```

## Use Cases

- **Compliance matrices**: Fill in large tables in tender/RFP response documents
- **Form templates**: Populate pre-structured forms with specific values
- **Report tables**: Update data cells without altering formatting or structure

## Pitfalls

1. **Namespace registration is critical** — `ET.register_namespace('w', ns)` must be called before any `ET.SubElement()` calls that create new `w:` elements. Without it, `ET.tostring()` writes unprefixed elements and the DOCX is corrupted.

2. **XML space preservation** — Always set `xml:space="preserve"` on `<w:t>` elements or leading/trailing whitespace is stripped by the XML parser. Use `t_elem.set('{http://www.w3.org/XML/1998/namespace}space', 'preserve')`.

3. **Multiple paragraphs in a cell** — DOCX table cells can contain multiple `<w:p>` elements. `set_cell_text()` above keeps only the first paragraph and removes the rest. For multi-paragraph cell content, you need to find the right paragraph index.

4. **Empty cells break iteration** — If `get_cell_text()` returns empty string for a cell that visually has content, check for `t_elem.text is None` (text in a child `<w:tab/>` or `<w:br/>` element).

5. **Compliance matrices** have continuation rows (adjacent rows under the same Area heading with blank Area cells). These share the Area of the previous row. When matching by requirement text, account for empty req cells.

6. **Always verify source documents first** — Before filling in any compliance/tender document that references technical specs (architecture, database, infrastructure), read the actual source document. Filling in answers from assumptions or memory will produce errors. The workflow is:
   a. Read the source architecture/spec document
   b. Note every technical detail that contradicts assumptions
   c. Only then edit the compliance matrix
   d. Verify every row after editing — check for stale references (old product names, wrong DB, wrong cloud services)

7. **Upload to shared drives** — Always include `supportsAllDrives=true` in the Drive API upload URL. Without it, Google returns `404 File not found` for folders in shared drives.