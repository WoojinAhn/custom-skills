# Setup — zoom-caption-capture

One-time install. After this, the skill's per-session checklist in `SKILL.md` is enough.

## 1. Chrome + `claude-in-chrome` MCP

The skill drives the meeting tab via `claude-in-chrome` MCP tools (`javascript_tool`, `tabs_context_mcp`, `tabs_close_mcp`). You need:

1. Google Chrome installed and signed in (so the Zoom Web Client can use your account context).
2. The `claude-in-chrome` Chrome extension installed (consult the `claude-in-chrome` project for the current install path — link not pinned here to avoid drift).
3. The MCP server registered in Claude Code so the `mcp__claude-in-chrome__*` tools resolve. Typically this means an entry in your Claude Code MCP settings; see the `claude-in-chrome` README for the canonical config snippet.

Verify by asking Claude to list browser tabs:

```
Run mcp__claude-in-chrome__tabs_context_mcp
```

If it returns a tab list, the MCP is wired up. If it errors with a missing-tool message, the MCP server is not registered. If it returns an empty list with no error, the extension is installed but not connected to Chrome.

## 2. Node.js (for Markdown conversion only)

`scripts/to-markdown.js` is plain Node — no dependencies. Any Node 18+ on `PATH` works:

```bash
node --version
```

If you only ever need the JSON dump (e.g. you'll feed it to an LLM directly), you can skip Node entirely.

## 3. Zoom side (per meeting, not one-time)

Not part of setup, but called out so the host knows what to enable:

- The host must turn on **Live Transcription** (or **Closed Captions** with auto-transcription) before the skill can see anything. Without it, `iframe#webclient` has no `.live-transcription-subtitle__box` DOM node and the observer attaches to nothing.
- You must **join the meeting in the Web Client** (`app.zoom.us/wc/...`), not the native Zoom app. Joining requires accepting Zoom's name/ToS prompt — do that yourself before starting the skill.

## Failure modes during setup

| Symptom | Cause |
|---|---|
| `mcp__claude-in-chrome__*` tools don't exist | MCP server not registered in Claude Code settings |
| `tabs_context_mcp` returns `[]` with no error | Extension installed, but Chrome isn't connected (or the extension is disabled) |
| `javascript_tool` runs but `document.getElementById('webclient')` is `null` | Active tab is not the Zoom Web Client meeting page |
| Observer installs (`status: started`) but `rawCount` stays at 0 | Host has not enabled Live Transcription, or the caption box is collapsed in the UI |
