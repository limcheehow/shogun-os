# Vision/Auxiliary Provider Resolution

## Problem

`auxiliary.vision.provider: auto` resolves to the main model provider. If the main provider is `custom:dashscope-anthropic` (Anthropic-compatible endpoint), the vision calls go to the same endpoint. Anthropic-compatible backends may not support image inputs, causing:

- Silent failures (no error logged, but image not analyzed)
- Very slow responses (616s+ with 10 API calls for a single image)
- Confused agent responses (tool calls without vision context)

## Symptoms in Logs

Normal: `Image routing: text (mode=text). Pre-analyzing 1 image(s) via vision_analyze.`
Abnormal: no "Pre-analyzing" line, extremely long `response ready` times, or the agent using clarify() instead of processing the image.

## Fix

Set an explicit vision provider that supports images. For DashScope:
```bash
hermes config set auxiliary.vision.provider custom:dashscope-openai
hermes config set auxiliary.vision.model <vision-capable-model>
```

Or use a different provider entirely (OpenRouter, etc.):
```yaml
auxiliary:
  vision:
    provider: openrouter
    model: google/gemini-2.5-flash
```

Same issue affects other auxiliary features: title_generation, compression, web_extract. Each may need its own explicit provider if `auto` resolution fails.

## Verification

After restart, send an image from Telegram and check the log for `Pre-analyzing 1 image(s) via vision_analyze`.
