# Google Doc Append — Style & Voice Consistency

When appending content to an existing Google Doc, **matching the original doc's tone, format, and content density** is more important than completeness.

This user (CH) has strong preferences on this — getting it wrong generates frustration.

## Pre-check: Analyze the Original Doc's Voice

Before writing a single word, read the source doc first to characterize its:

1. **Tone** — Is it conversational ("Have you ever wished...") or formal ("The system architecture comprises...")?
2. **Jargon level** — Does it use "GPU inference", "batchUpdate", "gbrain"? Or "it helps you", "it runs automatically"?
3. **Heading style** — What heading levels does it use, and for what?
4. **Body text style** — Are labels bolded inline? Or is bold only used for titles?
5. **Audience** — Is this a showcase doc for external readers, or an internal reference?

CH's Personal Butler doc is:
- **Conversational, friendly** — "My AI does not sleep. Here is what it does every day without me asking"
- **Zero jargon** — "It checks your task list and reminds you what's due today" (not "gbrain task management cron")
- **H1 for major sections**, H2 for subsections, H3 for time entries
- **No bold inline labels** in body paragraphs — plain flowing text
- **Audience: external** — someone curious about how to set up an AI butler

## Write in the Original's Voice

Once you've characterized the voice, **rewrite your content to match it**. The worst outcome is a jarring tone shift mid-document.

### Don't:
```
Purpose: Dedicated meeting notes processor. Syncs calendar, prepares briefs.
Model: DeepSeek V4 Flash via Primary Provider.
```

### Do:
```
After every meeting, this profile jumps in. It checks Google Drive for the 
meeting transcript, downloads it, and saves it to your brain.
```

### Voice Checklist
- ❌ Technical specs ("Primary Provider", "gbrain", "batchUpdate", "Bukku API")
- ❌ Raw data dumps ("RM 31,390/month training phase × 3 months")
- ❌ Bullet-point catalogue style
- ✅ Full sentences that tell a story
- ✅ "It..." or "This..." to start paragraphs (makes it feel like a tour)
- ✅ Examples of what happens, not just what's configured

## Structure Matching

Match the original doc's heading hierarchy exactly:

| Original usage | Your appendix should use |
|---------------|------------------------|
| H1 for major sections | H1 for appendix title and major dividers |
| H2 for profile names or key topics | H2 for each profile name and major sub-sections |
| H3 for subdivisions or time entries | H3 for time slots, phase names |

## The 3-Pass Format Pipeline

1. **Delete old content** (if redoing) — find the exact start/end indices via `docs get`
2. **Insert clean text** — plain `\n` paragraph breaks, no markdown, no bold markers
3. **Re-read doc → classify → apply styles** — never pre-compute indices. After insert, fetch the doc fresh and match paragraphs by their text content to assign H1/H2/H3/bold

## Pitfalls

- ❌ **Assuming technical detail adds value.** It doesn't for external docs. CH's guide is a showcase, not an operations manual. Strip every technical term you can.
- ❌ **Inconsistent heading levels.** If the original uses H2 for profile names, your appendix must too — don't switch to H3 or H1 mid-doc.
- ❌ **Bold labels in body text.** Unless the original doc uses them, stick to plain NORMAL_TEXT paragraphs.
- ❌ **Inserting at wrong index.** Always: `last_idx - 1` because endIndex in the Docs API is exclusive. Inserting at `last_idx` causes index-out-of-range errors.
- ❌ **The newline at the end of the last paragraph.** Cannot include it in delete ranges. Always use `last_idx - 1` not `last_idx` when deleting content up to the document end.