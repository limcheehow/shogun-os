---
name: hermes-tui
description: How to use the Hermes TUI (terminal UI) — keybindings, slash commands, navigation, and editor-style input behavior for the `hermes chat` interface.
category: devops
tags: [hermes, tui, keybindings, terminal, text-input, shortcuts]
---

# Hermes TUI — Keybindings & Usage

Load this skill when the user asks about using the Hermes TUI chat interface — multiline input, text editing shortcuts, navigation, slash commands, or any interaction within `hermes chat`.

The TUI is built with Ink + React (`ui-tui/` in the Hermes repo). The text input component lives at `ui-tui/src/components/textInput.tsx`.

## Quick Reference

| Want to... | Do this |
|---|---|
| Send a message | **Enter** |
| Go to next line / multiline | **Shift+Enter** (or Ctrl+Enter, Alt+Enter) |
| Navigate in multi-line text | **Up/Down Arrow** |
| Undo | **Ctrl+Z** |
| Redo | **Ctrl+Y** |
| Paste | **Ctrl+V** (Cmd+V on Mac) |
| Word skip left | **Alt+Left** (or Ctrl+Left) |
| Word skip right | **Alt+Right** (or Ctrl+Right) |
| Delete to start of line | **Ctrl+U** |
| Delete to end of line (kill) | **Ctrl+K** |
| Delete word backward | **Ctrl+W** |

> On WSL / SSH / Ghostty terminals, bare **Ctrl+J** also inserts a newline (the terminal delivers `\n` as the raw sequence and Hermes preserves it via `shouldPreserveCtrlJNewline()`).

## Full Keybinding Reference

See `references/tui-keybindings.md` for the complete keybinding table (cursor movement, selection, clipboard, mouse gestures, undo/redo stack limits).

## Slash Commands

Slash commands are intercepted at the app level, not by the text input. Type `/` to see available commands, or `/help` for the full list. Common ones:

- `/new` — Fresh session
- `/model <name>` — Change model
- `/retry` — Resend last message
- `/undo` — Remove last exchange
- `/title <name>` — Name the session

## Pitfalls

- **Alt+Enter doesn't work on Windows Terminal** — Windows Terminal intercepts Alt+Enter at the terminal layer to toggle fullscreen. Use **Ctrl+Enter** instead on Windows.
- **Shift+Enter might collapse to plain Enter on some terminals** — most terminals deliver Shift+Enter as a distinct keycode, but some (particularly old xterm emulators) collapse it to plain Enter. On those, use Ctrl+Enter or Alt+Enter.
- **The TUI is NOT the gateway** — TUI keybindings apply only to the `hermes chat` CLI session. The gateway (Telegram/Slack bots) has its own interaction model with slash commands and button-based approvals.
- **Ctrl+C is globally intercepted** — in the TUI, Ctrl+C copies selected text (Mac) or is a system interrupt. It does NOT submit the message.

## Source

The authoritative source for all keybinding logic is `ui-tui/src/components/textInput.tsx` in the Hermes repo — the `useInput` handler starting around line 902. If behavior changes between Hermes versions, check there first.
