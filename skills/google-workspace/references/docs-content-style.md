# Google Docs Content Style — Writing & Formatting

When adding or updating content in an existing Google Doc, the SINGLE most important rule is:

**Match the existing document's voice, tone, heading hierarchy, and formatting style.**

The user will notice and complain if the new content looks or reads differently from the original document.

## Voice & Tone

- Read the first few paragraphs of the document to detect its voice before writing
- If the doc is friendly and conversational ("Have you ever wished..."), write in that same voice
- If the doc is formal and professional, keep it formal
- If the doc uses technical jargon sparingly, avoid technical jargon
- The user explicitly prefers: **layman-friendly language, no unnecessary technical jargon**
- Use "it" rather than "it" unless the doc explicitly uses emoji/cheerful tone

## Heading Hierarchy

Use the original document's heading pattern — don't invent your own:

| Original H1 style | Your appendix should use |
|-------------------|-------------------------|
| H1 for major sections | H1 for major sections |
| H2 for subsections | H2 for subsections |
| H3 for sub-subsections | H3 for sub-subsections |

Example: If the doc uses `HEADING_1` for "Diagram 1: How Everything Fits Together" and `HEADING_2` for "Telegram (Main Chat)", then your appendix should use `HEADING_1` for "APPENDIX: PROFILES IN DETAIL" and `HEADING_2` for "1. THE MAIN PROFILE".

**Do NOT use bold labels in body text** unless the original doc does. Google Docs' bold formatting on body labels looks unnatural when the rest of the doc uses clean plain text.

## Body Text Style

The Google Docs API inserts text as paragraphs. Keep it clean:

- One paragraph per idea
- Use `\n` for paragraph breaks (two `\n` for section spacing)
- Do NOT include markdown artifacts (`**`, `*`, `===`, `---`) in the insert text — those don't render
- If you want visual separators, insert them as plain text like `═══════════════════════════════` (but ONLY if the existing doc uses them)

## Content Writing Approach

1. **Read the existing doc first** — understand its structure and voice
2. **Plan where your content fits** — does it go at the end as an appendix? Middle as a new section?
3. **Write in the doc's voice** — mimic sentence structure, vocabulary level, and length
4. **Insert clean plain text** with `\n` paragraph breaks
5. **Apply heading styles** via batchUpdate after insertion (see docs-batch-update.md for the API approach)
6. **Verify** — check that no content was merged into one paragraph (the `\n` was respected)

## BatchUpdate Index Pitfall

When deleting + inserting content, indices shift. The safe pattern is:

1. `GET /v1/documents/{id}` → find the last `endIndex`
2. `POST batchUpdate: deleteContentRange(startIndex=N, endIndex=M)` where endIndex = last_idx - 1 (exclude trailing newline)
3. `POST batchUpdate: insertText(location={index: N-1}, text="...")`
4. `GET /v1/documents/{id}` again → get NEW indices for every paragraph
5. `POST batchUpdate: updateParagraphStyle` for each heading (use actual indices from step 4)

Never re-use pre-computed indices after an insert — they all shift.

## Common Mistakes

- ❌ Dumping raw markdown text into one giant paragraph — use `\n` separators
- ❌ Using bold labels in body text when the doc doesn't — looks inconsistent
- ❌ Writing in a different voice than the original doc — jarring for the reader
- ❌ Using technical jargon in a friendly, accessible doc
- ❌ Applying heading levels inconsistently (H1→H3→H2 instead of H1→H2→H3)