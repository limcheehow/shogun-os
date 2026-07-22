# Hermes TUI Keybindings

Reverse-engineered from `ui-tui/src/components/textInput.tsx` in the Hermes repo.
Applies to the `hermes chat` TUI (Ink/React terminal interface), not the gateway.

## Input / Line Editing

| Key | Action |
|-----|--------|
| **Enter** | Submit / send message |
| **Shift+Enter** | Insert newline (multiline input) |
| **Ctrl+Enter** | Insert newline |
| **Alt+Enter** | Insert newline (meta key on non-Mac) |
| **Ctrl+J** | Insert newline on WSL / SSH / Ghostty terminals (bare `\n` sequence is preserved) |
| **Up Arrow** | Move cursor up one line (multiline navigation) |
| **Down Arrow** | Move cursor down one line (multiline navigation) |

## Cursor Movement

| Key | Action |
|-----|--------|
| **Left Arrow** | Move cursor left one grapheme |
| **Right Arrow** | Move cursor right one grapheme |
| **Alt+Left** / **Ctrl+Left** | Move cursor one word left |
| **Alt+Right** / **Ctrl+Right** | Move cursor one word right |
| **Home** / **Ctrl+A** (non-Mac) | Move cursor to start of line |
| **End** / **Ctrl+E** | Move cursor to end of line |
| **Alt+B** | Move cursor one word backward |
| **Alt+F** | Move cursor one word forward |

*Holding Shift with any movement key extends the selection.*

## Editing / Deletion

| Key | Action |
|-----|--------|
| **Backspace** | Delete character before cursor |
| **Delete** / **Forward Delete** | Delete character after cursor |
| **Alt+Backspace** / **Ctrl+W** | Delete word backward |
| **Ctrl+U** | Delete from cursor to start of line |
| **Ctrl+K** | Delete from cursor to end of line (kill) |

## Undo / Redo

| Key | Action |
|-----|--------|
| **Ctrl+Z** | Undo |
| **Ctrl+Y** | Redo |
| **Shift+Ctrl+Z** | Redo (alternative) |

Undo stack holds up to 200 entries.

## Clipboard

| Key | Action |
|-----|--------|
| **Ctrl+V** (non-Mac) | Paste from clipboard |
| **Cmd+V** (Mac) | Paste from clipboard |
| **Alt+V** | Hotkey paste (triggers `onPaste` handler) |
| **Ctrl+C** (with Mac selection) | Copy selected text to clipboard |
| **Right-click** | Copy if selection exists, otherwise paste |

Mouse-driven selection also auto-copies on Mac (via `writeClipboardText` on mouse-up).

## Selection (Mouse)

| Gesture | Action |
|---------|--------|
| **Click** | Move cursor to click position |
| **Click-drag** | Select text |
| **Double-click at same offset** | Select all |
| **Right-click** | Copy (if selection) or paste (if no selection) |

## Voice

The voice record keybinding is configurable. Default check is handled by
`isVoiceToggleKey()` — the TUI passes this through to the global handler.
Default voice key is mapped via `DEFAULT_VOICE_RECORD_KEY`.

## Globally Passed Through (not handled by the text input)

These are intercepted by the app-level handler rather than the input component:

| Key | Action |
|-----|--------|
| **Ctrl+C** | Copy (on Mac with selection) or system interrupt |
| **Ctrl+X** | System interrupt |
| **Tab** / **Shift+Tab** | Cycle focus / navigation |
| **Page Up / Page Down** | Scroll history |
| **Escape** | Cancel / close overlay |
| **Slash commands** (`/`) | Handled by slash command parser, not text input |

## Source

All keybinding logic lives in `ui-tui/src/components/textInput.tsx` in the Hermes repo,
in the `useInput` handler starting around line 902. The `Key` interface from
`@hermes/ink` provides the key event shape.