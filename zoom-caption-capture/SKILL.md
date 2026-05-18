---
name: zoom-caption-capture
description: Use when the user is in a Zoom Web Client meeting (app.zoom.us/wc/...) with live captions visible and wants the captions captured. Triggers include live caption capture, STT streaming, meeting transcription, Zoom 자막 캡처, 회의록 만들기, Zoom STT, ATT 회의록.
allowed-tools: Bash, mcp__claude-in-chrome__tabs_context_mcp, mcp__claude-in-chrome__javascript_tool, mcp__claude-in-chrome__tabs_close_mcp
---

# Zoom Caption Capture

## Overview

Zoom Web Client renders live captions (Live Transcription) into the DOM. A `MutationObserver` attached inside the `#webclient` iframe streams the caption text as it grows, and a token-level overlap merger collapses Zoom's rolling-window duplication into utterance entries that can be dumped as JSON / Markdown.

Core principle: **capture raw fragments without loss, defer cleanup to dump time** — Zoom's caption box is a rolling display, so the safest path is to record every snapshot and dedup later, never assume an inline merge will be perfect.

## When to Use

- The user is already joined to a Zoom meeting via the Web Client (`app.zoom.us/wc/...`)
- Live captions / transcription are visible (host enabled CC)
- Goal is a transcript / meeting minutes, not real-time translation
- Browser is reachable via `claude-in-chrome` MCP tools

Do NOT use if:
- The user has not yet joined the meeting — joining requires user confirmation (name, ToS) and is out of scope of this skill
- Captions are not enabled by the host (no DOM target exists)
- The meeting is in the native Zoom app, not the web client

## Quick Reference

| Step | Tool | Script |
|------|------|--------|
| 1 | `javascript_tool` | `scripts/install-observer.js` |
| 2 | `javascript_tool` | `scripts/spot-check.js` (every few minutes) |
| 3 | `javascript_tool` | `scripts/dump.js` → JSON lands in `~/Downloads/` |
| 4 | `Bash` | `node scripts/to-markdown.js ~/Downloads/meeting-*.json` |
| 5 | `tabs_close_mcp` | Close tab → auto-leaves the meeting |

To stop capturing without leaving: run `scripts/stop.js`.

## DOM Target

The meeting UI lives inside `iframe#webclient` (cross-document — must access `contentDocument`). Caption nodes:

- `#live-transcription-subtitle` — container (stable id)
- `.live-transcription-subtitle__box` — current speaker row
- `.zmu-data-selector-item__icon` — speaker initial (e.g. `M`, `T`) — Zoom only exposes initials, not full names, in the caption box
- `.live-transcription-subtitle__item` — current caption text (rolling)

## How to Run a Script

`javascript_tool` accepts the script body as a single argument and executes it in the page context. Read the file and pass its contents:

```
javascript_tool(<contents of scripts/install-observer.js>)
```

Scripts store state on `iframe.contentWindow.__transcript`, so they survive between tool invocations.

## Known Limitations

1. **Speaker identity = initial only.** Zoom only renders a 1-letter avatar (e.g. `M`, `T`) in the caption box. Full-name mapping requires reading the active-speaker video tile — out of scope here. Tell the user up front.
2. **Inline dedup is imperfect.** Korean captions have shifting punctuation/whitespace (`많지는.` ↔ `많지는 않은거`). The token-level overlap will fail to merge ~20–40% of consecutive fragments. The raw buffer is lossless — recommend an LLM cleanup pass on `payload.raw` (or `payload.merged`) for the final minutes doc.
3. **Caption box truncates old text.** If the speaker monologues for >~10s without pause, Zoom drops the head of the box. The observer catches each snapshot before truncation, but the merger's overlap window is 20 tokens — very long single utterances will fragment into multiple entries.
4. **`get_page_text` / `read_page` don't reach the iframe directly** for these nodes — always go through `iframe#webclient`'s `contentDocument` via `javascript_tool`.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Trying to query captions on the top-level document (returns 0 hits) | Access `document.getElementById('webclient').contentDocument` |
| Long `setTimeout` inside one `javascript_tool` call (≥45s) | `javascript_tool` has a ~45s CDP timeout. Sleep between separate tool calls; observer keeps running between them |
| Returning the full JSON as a tool result | Use `scripts/dump.js` — Blob download routes it to `~/Downloads/` |
| Triggering both JSON and MD downloads in one JS run | Chrome blocks the 2nd; convert locally with `scripts/to-markdown.js` |
| Assuming the inline merged output is the final minutes | It's not — run an LLM cleanup pass on the dump for the user-facing doc |

## Lifecycle / Cleanup

- **Stop capture, stay in meeting**: run `scripts/stop.js`
- **Leave meeting**: close the tab via `tabs_close_mcp` — Zoom Web Client treats tab close as participant exit

## Real-World Result

Reference run (ATT 26/05/18, ~31 min): 1006 raw fragments → 233 merged utterances → 559 KB JSON / 94 KB Markdown. Inline merger handled ~75% of consecutive fragments; post-hoc LLM pass cleaned the rest.

## Skill Maturity Disclosure

This skill was **distilled from a single real session** (ATT 26/05/18) rather than the synthetic subagent baseline that `superpowers:writing-skills` mandates as the RED phase. The Iron Law was bent: deployment is the first real test. Each invocation is treated as a delayed RED run — observed rationalizations and loopholes get logged here and the skill refactored.

### Refactor log

| Date | Trigger | Rationalization / loophole observed | Fix applied |
|------|---------|-------------------------------------|-------------|
| _(empty — first real invocation will populate)_ |  |  |  |

### Open loopholes (untested)

These are paths the original session didn't stress; future invocations should watch for them.

- The 20–40% inline-merger failure rate on Korean captions is a single-session datapoint. Other languages, faster speakers, or different host caption engines may produce different distributions. Re-measure on the next real run.
- Chrome's programmatic-download throttling (which forces the JSON-only dump + local Markdown conversion) is version-dependent and was observed on one Chrome build only. A future Chrome may queue both downloads cleanly, or block both.
- The token-overlap window of 20 (in `scripts/install-observer.js`) was tuned for an ATT-style monologue cadence. Long single-speaker stretches (>~10s without pause) still fragment in practice; an even longer window may help or may merge across genuinely-distinct utterances.
- The observer's reliance on the `.live-transcription-subtitle__*` class names assumes Zoom Web Client UI stability. A UI rewrite invalidates the entire skill without warning — guard the spot-check by surfacing `rawCount === 0` loudly.
- The skill has only been run on Zoom Web Client English UI Chrome on macOS. Other OS/browser/locale combos are untested.

Closing a loophole = add a row to the refactor log and tighten the relevant section above.
