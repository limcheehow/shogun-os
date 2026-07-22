---
name: gbrain-media-ingest
description: "Ingest video, audio, PDFs, and screenshots into gbrain — extract transcripts/OCR, describe content, extract entities, file correctly."
version: 1.0.0
author: user
tags: [gbrain, ingest, media, video, audio, pdf]
---
# gbrain Media Ingest

Ingest media files — video, audio, PDF, screenshots — into the brain with transcript/OCR extraction, description, entity extraction, and cross-linking.

## Ingestion Types

| Type | Extraction pipeline | Brain path |
|------|-------------------|-----------|
| **Video** | Download → transcribe (youtube-content skill) → summarize → entities | `references/media/` or `references/<topic>/` |
| **Audio/voice note** | Transcribe via Whisper/API → preserve exact phrasing → entities | `ideas/` or `references/media/` |
| **PDF** | OCR via pymupdf/marker-pdf → extract text → summarize → entities | `references/<topic>/` or `projects/<project>/` |
| **Screenshot/image** | Vision describe → extract text → summarize → entities | `references/media/` or `references/<topic>/` |

## Standard Pipeline

1. **Classify** — video? audio? PDF? screenshot?
2. **Extract** — text content from the media (transcription, OCR, description)
3. **Summarize** — key points, decisions, action items
4. **Entity extraction** — people, companies, projects, dates
5. **Brain check** — search entities against gbrain
6. **Write** — create page under the correct path
7. **Cross-link** — link from entities to the new page
8. **Timeline** — add timeline entries for dated events

## Page Template

```yaml
---
title: "[Type]: [Descriptive title]"
type: reference
tags: [reference, media, <type>]
source: "file:///path/or/url"
ingested: "2026-06-10"
media_type: video | audio | pdf | screenshot
---

## Summary
What this media contains.

## Key Content
- Key point 1
- Key point 2

## Entities
- [[people/someone]]
- [[companies/some-company]]

## Transcript / Text (if applicable)
Extracted verbatim text under a details/collapsible section.
```

## Preservation Rule

- **Exact phrasing** for voice notes, quotes, and direct statements — never paraphrase
- **Summarize** for long-form video/audio extracts
- **Describe** for images/screenshots — the visual content, not interpretation

## Tools

- YouTube: `youtube-content` skill for transcripts
- PDF: `ocr-and-documents` skill (pymupdf, marker-pdf)
- Screenshots: `vision_analyze` for description + text extraction
- Audio: `text_to_speech` / Whisper pipeline if available

## Pitfalls

- ❌ Paraphrasing verbatim quotes from voice notes
- ❌ Missing visual information in screenshots (describe what's actually there)
- ❌ Skipping entity extraction because it's media (media content has entities too)
- ❌ Not checking if the media content duplicates existing brain pages