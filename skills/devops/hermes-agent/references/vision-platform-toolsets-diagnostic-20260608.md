# Vision Tool Diagnostic Flow — Session 2026-06-08

## Trigger
User sent an image to DM (default profile). Agent responded "I can't view the image" despite `vision_analyze` being configured under `auxiliary.vision`.

## Step-by-step diagnostic that surfaced the issue

1. **Checked image on disk**: `file img_59431dc74625.jpg` → valid 549×1280 JPEG, 112KB. Not a file issue.

2. **Checked auxiliary.vision config**: `grep -A8 "auxiliary:" config.yaml` → provider `custom:dashscope-openai`, model `qwen3-vl-flash`. Backend looks correct.

3. **Tried delegate_task with vision toolset**: Subagent tried `computer.screenshot_view` — wrong tool, vision_analyze not in its list either.

4. **Checked ALL profiles for vision**: `grep "vision\|platform_toolsets" ~/.hermes/profiles/*/config.yaml` → 8/8 named profiles had `platform_toolsets: [vision]`. But main `config.yaml` had NO `platform_toolsets` key at all.

5. **Root cause confirmed**: Default profile (DMs) uses main `config.yaml` which lacked `platform_toolsets`. Vision backend config (`auxiliary.vision`) was correct but the tool never registered.

## Fix
```yaml
# Add to main ~/.hermes/config.yaml under the platform section:
platform_toolsets:
  - vision
```
Then restart gateway.

## Lesson
`auxiliary.vision` ≠ vision tool available. Two-layer check required:
- Layer 1: Backend configured (`hermes config get auxiliary.vision.provider`)
- Layer 2: Tool registered (`platform_toolsets` includes `vision`)
