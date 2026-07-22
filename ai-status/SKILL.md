---
name: ai-status
description: |
  Use when checking whether AI/dev services (Claude, OpenAI, Cursor, GitHub,
  Gemini, etc.) are actually usable, or whether a Statuspage incident is an
  operational outage vs a policy/model-recall/FedRAMP scope notice. Even when
  Statuspage impact says "major", do not conclude an outage while every tracked
  component is green.

  Triggers:
  - Command: /ai-status
  - Natural language: "AI 상태", "AI 장애", "클로드 장애", "ChatGPT down",
    "OpenAI status", "Gemini 장애", "Cursor 상태", "model status",
    "API outage check", "frontier AI status"

  Do NOT use for: WebFetching individual HTML status pages, third-party sources
  like Downdetector, or diagnosing the user's own app/network (local ping/DNS).
---

# AI Service Status — Batch Check

**Statuspage incident impact ≠ operational outage.** `status`/`display_status`
are **component-based operational state**. Policy/scope incidents are reported
in a **separate section** via `alerts.policy` / `incidents[].kind`.

Core 6 providers are fetched direct (live); 10 extended providers via
`--extended` (AIWatch cache, ~5 min). Full provider list: `reference.md`.

## Execution (no re-discovery)

Run the bundled script from wherever this skill is installed
(e.g. `~/.claude/skills/ai-status`, `~/.cursor/skills/ai-status`,
`${CODEX_HOME:-$HOME/.codex}/skills/ai-status`):

```bash
python3 <skill-dir>/scripts/check_status.py --format json 2>/dev/null
python3 <skill-dir>/scripts/check_status.py --extended --format json 2>/dev/null
python3 <skill-dir>/scripts/check_status.py --providers claude openai
```

- **`--format json` only** (stdout). No HTML WebFetch, no Downdetector.

## Agent workflow

1. Run the command once (default = core 6 providers; `--extended` /
   `--providers` **only on request**)
2. JSON → **compact report** (below). Full tables and status-page links **only
   when the user asks for detail/full**
3. `status` follows components first — never declare an outage from a
   policy/scope incident

## Reporting (default)

**Principles:** no long summary sentences · no empty sections · status-page
links only on detail request. **Scan-first:** short table + bullets only when
needed.

Emoji: 🟢 operational · 🟡 degraded · 🟠 partial · 🔴 major · ⚪ unknown

### Default shape (always this structure)

```markdown
## AI Service Status ({checked_at} UTC)

| Service | Status |
|---------|--------|
| Claude | 🟢 |
| OpenAI | 🟢 |
| Cursor | 🟢 |
| GitHub | 🟢 |
| Gemini | 🟢 |

{the two blocks below only when applicable — omit otherwise}
```

- Gemini: if Workspace and Vertex are **both 🟢, one row** `Gemini | 🟢`.
  Split into two rows when either is off-green.
- Add a **Summary** column only for providers with operational issues:
  `| Service | Status | Summary |`
- If everything is 🟢, **no Summary or Source columns at all**

### Policy/scope (NOT an operational outage — when `alerts.policy` / `scope_limited` present)

```markdown
**Policy/scope** (no impact on general API/Code usage)

- **Claude** — Fable/Mythos 5 access suspended
- **OpenAI** — FedRAMP orgs only
```

- **One bullet line per provider**; impact scope goes in parentheses or a short
  trailing clause
- If `reference_url` exists, at most one link per bullet

### Operational outage/degradation (`status` != 🟢)

Mark the affected table row 🟡/🟠/🔴 + a one-phrase summary. No separate
long-form section.

### Detail (explicit request: "full", "detail", `--extended`)

Source column · component breakdown · `status_url` · the 10 extended providers

## Interpretation guide

1. **Policy/compliance** (`kind=policy_compliance`, `alerts.policy`): model
   **recalls/export controls** (e.g. Mythos/Fable 5). While components are
   green, **never report "Claude outage"**.
2. **Scope limited** (`scope_limited`, FedRAMP): state explicitly that general
   ChatGPT/Codex usage is **unaffected**.
3. **OpenAI/Gemini/Cursor/AIWatch**: as before — component vs page,
   Workspace/Vertex split, AIWatch as secondary source, `ok:false` affects that
   provider only.

**FAQ**: "Claude shows 🔴 — does the API still work?" → if it's policy, **yes**.
Details on request.
