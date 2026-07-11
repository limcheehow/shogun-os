# Google Slides / Company Profile Extraction

Use this technique when a user shares a Google Slides URL and you need to extract text content for enrichment or resume building.

## URL Formats

| Format | Works With | Notes |
|--------|-----------|-------|
| `https://docs.google.com/presentation/d/ID/edit` | View-only & editor | Use when `preview` is blocked |
| `https://docs.google.com/presentation/d/ID/preview` | Public slides | Simpler UI, easier navigation |
| `https://docs.google.com/presentation/d/ID/export/txt` | Public slides | Blocked by auth for private decks |

Use `edit` with view-only mode as fallback — it works even for shared-drive files that block `preview` and `export`.

## Workflow

### Step 1: Navigate to the Presentation

```python
browser_navigate("https://docs.google.com/presentation/d/ID/edit")
```

If the `edit` URL shows a sign-in wall, try `preview` instead.

### Step 2: Use vision_analyze Per Slide

For each slide, call `browser_vision` with a question asking for ALL text content.

```python
# First slide loaded automatically
browser_vision("Read ALL visible text on this slide word for word. Every bullet point, heading, sentence, number. Complete content.")
```

### Step 3: Navigate Between Slides

**Best method: Keyboard navigation**

```python
browser_press(key="ArrowDown")   # Next slide
browser_press(key="ArrowUp")     # Previous slide
```

This works more reliably than clicking UI buttons because it doesn't depend on element references that change per session.

**Alternative: Click next button**
```python
# Check the snapshot for the next/previous button ref first
browser_snapshot()  # Look for "Next" button
browser_click(ref="@e3")
```

### Step 4: Handle Empty Responses

If `browser_vision` returns an empty response after navigation, check with a fresh `browser_vision` call — sometimes the tool response is empty but the slide DID change.

If the slide appears blank or as a transition slide, skip it and move to the next.

### Step 5: Use Accessibility Tree as Backup

```python
browser_snapshot()  # Shows text extracted from accessibility tree
```

The snapshot often reveals slide titles, headings, and text even when the visual screenshot isn't clear. Check this before relying solely on vision.

### Step 6: Compile All Data

After extracting all slides, compile the data into structured notes:
- Slide 1: Title slide — company name, tagline, subsidiary info
- Slide 2: Overview — key metrics, industries, partners
- Slide 3: Parent company info (if applicable) — scale, infrastructure numbers
- Middle slides: Product details, use cases, capabilities
- Later slides: Awards, deployment info, pricing, contact

## When to Use This

This technique is useful when:
- The user shares their company profile deck for resume building
- Someone sends you a pitch deck you need to extract info from
- You're enriching a company file and need current stats
- The user says "here's my company profile" without a PDF

## Limitations

- Google Slides `export/pdf` URL is blocked by auth — use `preview` instead
- Only text that the AI vision model can READ from the screenshot will be captured
- Icons, logos, and text embedded in images may not be readable
- Interactive elements (hover-over tooltips, clickable hotspots) won't show their content
- Long presentations (30+ slides) require many iterative calls
- Some slides may be image-only with no extractable text
