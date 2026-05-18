---
name: zoom-caption-capture
description: Use when capturing real-time live captions / transcription from a Zoom Web Client meeting via browser automation to build a transcript or meeting minutes. Triggers include live caption capture, STT streaming, meeting transcription, Zoom 자막 캡처, 회의록 만들기, Zoom STT, ATT 회의록.
---

# Zoom Caption Capture

## Overview

Zoom Web Client renders live captions (Live Transcription) into the DOM. A `MutationObserver` attached inside the `#webclient` iframe streams the caption text as it grows, and a token-level overlap merger collapses Zoom's rolling-window duplication into utterance entries that can be dumped as JSON / Markdown.

Core principle: **capture raw fragments without loss, defer cleanup to dump time** — Zoom's caption box is a rolling display, so the safest path is to record every snapshot and dedup later, never assume an inline merge will be perfect.

## When to Use

- The user is already joined to a Zoom meeting via the Web Client (`app.zoom.us/wc/...`)
- Live captions / transcription are visible (host enabled CC)
- Goal is a transcript / meeting minutes, not real-time translation
- Browser is reachable via `claude-in-chrome` MCP tools (or playwright)

Do NOT use if:
- The user has not yet joined the meeting — joining requires user confirmation (name, ToS) and is out of scope of this skill
- Captions are not enabled by the host (no DOM target exists)
- The meeting is in the native Zoom app, not the web client

## Prerequisites

1. `claude-in-chrome` MCP loaded (`tabs_context_mcp`, `javascript_tool`, etc.)
2. Active MCP tab whose URL is the Zoom Web Client meeting page
3. User has joined the meeting and captions are showing

## Quick Reference

| Step | Tool | Action |
|------|------|--------|
| 1 | `javascript_tool` | Install observer (see Setup) |
| 2 | `javascript_tool` | Spot-check `__transcript.length` periodically |
| 3 | `javascript_tool` | Build payload + trigger downloads (see Dump) |
| 4 | `Bash` (node) | Convert downloaded JSON → Markdown if MD download was blocked |
| 5 | `tabs_close_mcp` | Close tab → auto-leaves the meeting |

## DOM Target

The meeting UI lives inside `iframe#webclient` (cross-document — must access `contentDocument`). Caption nodes:

- `#live-transcription-subtitle` — container (stable id)
- `.live-transcription-subtitle__box` — current speaker row
- `.zmu-data-selector-item__icon` — speaker initial (e.g. `M`, `T`) — Zoom only exposes initials, not full names, in the caption box
- `.live-transcription-subtitle__item` — current caption text (rolling)

## Setup (install observer)

Run via `javascript_tool` on the meeting tab. Stores state on `iframe.contentWindow` so it survives between calls.

```javascript
(() => {
  const f = document.getElementById('webclient');
  const w = f.contentWindow;
  const doc = f.contentDocument;

  if (w.__captionObs) { try { w.__captionObs.disconnect(); } catch(e){} }
  w.__captionBuf = [];
  w.__transcript = [];

  const norm = s => s.replace(/[\.,!?]+/g, '').replace(/\s+/g, ' ').trim();
  const tokens = s => norm(s).split(' ').filter(Boolean);

  // Find suffix-of-A as substring-in-B (token level) and append the tail.
  const overlapAppend = (a, b) => {
    if (!a) return b;
    const aN = norm(a), bN = norm(b);
    if (bN.includes(aN)) return b;
    if (aN.includes(bN)) return a;
    const aT = tokens(a), bT = tokens(b);
    for (let n = Math.min(aT.length, 20); n >= 2; n--) {
      const tail = aT.slice(-n);
      for (let i = 0; i + n <= bT.length; i++) {
        let ok = true;
        for (let j = 0; j < n; j++) if (tail[j] !== bT[i+j]) { ok = false; break; }
        if (ok) {
          const remaining = bT.slice(i + n).join(' ');
          return remaining ? a + ' ' + remaining : a;
        }
      }
    }
    return null; // no overlap — caller treats as new utterance
  };

  const tick = () => {
    const box = doc.querySelector('.live-transcription-subtitle__box');
    if (!box) return;
    const speakerEl = box.querySelector('.zmu-data-selector-item__icon');
    const textEl = box.querySelector('.live-transcription-subtitle__item');
    if (!textEl) return;
    const speaker = speakerEl ? (speakerEl.innerText || '').trim() : '?';
    const text = (textEl.innerText || '').trim();
    if (!text) return;
    const now = new Date().toISOString();
    const last = w.__transcript[w.__transcript.length - 1];
    if (last && last.speaker === speaker) {
      const merged = overlapAppend(last.text, text);
      if (merged !== null) {
        if (merged !== last.text) { last.text = merged; last.updatedAt = now; }
        return;
      }
    }
    w.__transcript.push({ speaker, text, startedAt: now, updatedAt: now });
  };

  // Post-hoc re-merge over the full transcript (run again at dump time).
  w.__mergeTranscript = () => {
    const out = [];
    for (const u of w.__transcript) {
      const last = out[out.length - 1];
      if (last && last.speaker === u.speaker) {
        const m = overlapAppend(last.text, u.text);
        if (m !== null) { last.text = m; last.updatedAt = u.updatedAt; continue; }
      }
      out.push({ ...u });
    }
    return out;
  };

  const root = doc.getElementById('live-transcription-subtitle') || doc.body;
  w.__captionObs = new MutationObserver(tick);
  w.__captionObs.observe(root, { childList: true, subtree: true, characterData: true });
  tick();
  return { status: 'started', entries: w.__transcript.length };
})()
```

## Monitoring

Don't poll aggressively — observer is event-driven. Spot-check every few minutes:

```javascript
(() => {
  const w = document.getElementById('webclient').contentWindow;
  const buf = w.__transcript || [];
  const last = buf[buf.length - 1];
  return {
    observerAlive: !!w.__captionObs,
    rawCount: buf.length,
    mergedCount: w.__mergeTranscript ? w.__mergeTranscript().length : null,
    lastSpeaker: last?.speaker,
    lastTextTail: last?.text.slice(-100),
    lastUpdatedAt: last?.updatedAt
  };
})()
```

**Pitfall:** `javascript_tool` has a ~45s CDP timeout. Do not `await setTimeout(... 90000)` inside the JS — the call will fail. Sleep between separate tool invocations instead.

## Dump (end of session)

The caption JSON can be 300KB+ — return values get truncated in transit. Trigger a **browser download** instead of returning the text:

```javascript
(() => {
  const w = document.getElementById('webclient').contentWindow;
  const doc = document.getElementById('webclient').contentDocument;
  const merged = w.__mergeTranscript();
  const meta = {
    title: document.title,            // meeting title
    startedAt: w.__transcript[0]?.startedAt,
    endedAt: w.__transcript.at(-1)?.updatedAt,
    speakers: [...new Set(w.__transcript.map(u => u.speaker))]
  };
  const payload = { meta, raw: w.__transcript, merged };
  const json = JSON.stringify(payload, null, 2);
  const stamp = (meta.startedAt || new Date().toISOString()).slice(0, 10);
  const blob = new Blob([json], { type: 'application/json' });
  const url = URL.createObjectURL(blob);
  const a = doc.createElement('a');
  a.href = url;
  a.download = `meeting-${stamp}-transcript.json`;
  doc.body.appendChild(a); a.click();
  setTimeout(() => { URL.revokeObjectURL(url); a.remove(); }, 1000);
  return { jsonBytes: json.length, mergedCount: merged.length, rawCount: w.__transcript.length };
})()
```

File lands in `~/Downloads/`. Verify with `ls -lh ~/Downloads/meeting-*.json`.

### Markdown conversion (recommended)

Chrome blocks back-to-back programmatic downloads, so triggering JSON + MD in one shot usually drops the second. Convert locally instead:

```bash
node -e "
const fs = require('fs');
const path = process.argv[1];
const d = JSON.parse(fs.readFileSync(path, 'utf8'));
const md = [
  '# ' + (d.meta.title || 'Meeting'),
  '',
  '- Captured: ' + d.meta.startedAt + ' → ' + d.meta.endedAt,
  '- Speakers: ' + d.meta.speakers.join(', '),
  '- Raw: ' + d.raw.length + ' / Merged: ' + d.merged.length,
  '',
  '## Transcript',
  '',
  ...d.merged.map(u => '**[' + u.startedAt.slice(11,19) + '] ' + u.speaker + '**: ' + u.text)
].join('\n');
fs.writeFileSync(path.replace(/\.json$/, '.md'), md);
" ~/Downloads/meeting-YYYY-MM-DD-transcript.json
```

## Known Limitations

1. **Speaker identity = initial only.** Zoom only renders a 1-letter avatar (e.g. `M`, `T`) in the caption box. Full-name mapping requires reading the active-speaker video tile — out of scope here. Tell the user up front.
2. **Inline dedup is imperfect.** Korean captions have shifting punctuation/whitespace (`많지는.` ↔ `많지는 않은거`). The token-level overlap will fail to merge ~20–40% of consecutive fragments. The raw buffer is lossless — recommend an LLM cleanup pass on `payload.raw` (or `payload.merged`) for the final minutes doc.
3. **Caption box truncates old text.** If the speaker monologues for >~10s without pause, Zoom drops the head of the box. The observer catches each snapshot before truncation, but the merger's overlap window is 20 tokens — very long single utterances will fragment into multiple entries.
4. **`get_page_text` / `read_page` don't reach the iframe directly** for these nodes — always go through `iframe#webclient`'s `contentDocument` via `javascript_tool`.

## Common Mistakes

| Mistake | Fix |
|---------|-----|
| Trying to query captions on the top-level document (returns 0 hits) | Access `document.getElementById('webclient').contentDocument` |
| Long `setTimeout` inside one `javascript_tool` call (≥45s) | Sleep between separate tool calls; observer keeps running between them |
| Returning the full JSON as a tool result | Trigger a Blob download → file lands in `~/Downloads/` |
| Triggering both JSON and MD downloads in one JS run | Chrome blocks the 2nd; convert locally with `node` after the JSON arrives |
| Assuming the inline merged output is the final minutes | It's not — run an LLM cleanup pass on the dump for the user-facing doc |

## Lifecycle / Cleanup

To stop capturing without leaving the meeting:

```javascript
(() => {
  const w = document.getElementById('webclient').contentWindow;
  if (w.__captionObs) w.__captionObs.disconnect();
  return { stopped: true, captured: w.__transcript.length };
})()
```

To leave the meeting: close the tab via `tabs_close_mcp` — Zoom Web Client treats tab close as participant exit.

## Real-World Result

Reference run (ATT 26/05/18, ~31 min): 1006 raw fragments → 233 merged utterances → 559 KB JSON / 94 KB Markdown. Inline merger handled ~75% of consecutive fragments; post-hoc LLM pass cleaned the rest.
