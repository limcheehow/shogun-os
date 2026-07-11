# Document-to-Brain Enrichment

When a user uploads a company deck, brochure, or PDF about a company/person/deal, run this pipeline to extract and cross-reference the intel across all relevant brain files.

## Full Pipeline

### Step 1: Archive the document
Save to `~/brain/attachments/YYYY-MM-DD-description.ext` before processing.

```bash
cp <source_path> ~/brain/attachments/2026-06-01-description.pdf
```

### Step 2: Extract text
Use pymupdf (always installed, ~25MB, instant):

```bash
python3 -c "
import pymupdf
doc = pymupdf.open('~/brain/attachments/2026-06-01-description.pdf')
print(f'Pages: {len(doc)}')
for i, page in enumerate(doc):
    print(f'--- PAGE {i+1} ---')
    print(page.get_text())
"
```

For scanned PDFs, fall back to vision_analyze on each page (render at 300 DPI).

### Step 3: Cross-reference with existing brain files
Read all existing files that relate to the document's subject:

- `~/brain/companies/<company>.md` — may need updates to clients, projects, products
- `~/brain/people/<contact>.md` — title, role, achievements
- `~/brain/deals/<deal>.md` — confirmation that a target is already a live client, or new partnership angle

### Step 4: Update all relevant files
For **companies**: new clients/projects, corrected revenue, new products, updated relationships.

For **people**: corrected title (e.g. Director → Group CEO), new achievements, direct phone.

For **deals**: move from assumption to confirmed fact (e.g. "Petronas is a lead" → "Petronas Gas is a live client per their deck"), update timeline.

For **activity-log.md**: add a line documenting the enrichment.

### Step 5: Deliver summary to user
Key findings from the deck, especially anything that changes deal strategy (e.g. confirmed live client relationship, project scope, revenue figures).

## Multi-Partner Deal Frontmatter

The `partner` field in deal YAML supports a YAML list for multiple partners:

```yaml
partner:
  - Strateq Group
  - Graffiquo Asia Sdn Bhd
```

This is valid YAML and works in the frontmatter. The `relationship` field documents the chain (e.g. `customer > partners > your-company`). For commercial execution, clarify invoicing chain separately as the deal progresses.

## Pitfalls
- **PDF must be archived first** — never process without saving to ~/brain/attachments/
- **web_extract won't work on local files** — `file:///` URLs are blocked as private/internal. Always use pymupdf locally.
- **pymupdf is available** — installed in the system Python. No need to install anything.
- **Don't over-infer from a pitch deck** — decks are aspirational. Distinguish between "named client" (confirmed live) and "logo on slide" (may be prospective). Look for specific project names vs generic client logos.
- **Update all files that reference the same entity** — a new client mention in a deck may need updates to company file, person file, and deal file.
- **Activity log is chronological** — insert entries in the correct date position, not appended to bottom.
- **`file:///` protocol blocked** — web_extract refuses local PDF files. Always use inline pymupdf extraction for local documents.