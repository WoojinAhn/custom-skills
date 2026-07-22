# ai-status reference

No agent runtime required — provider list, contribution, and verification notes.

## Install

```bash
# Claude Code
ln -sf "$(pwd)/ai-status" ~/.claude/skills/ai-status
# Cursor
ln -sf "$(pwd)/ai-status" ~/.cursor/skills/ai-status
# Codex
ln -sf "$(pwd)/ai-status" "${CODEX_HOME:-$HOME/.codex}/skills/ai-status"
```

## Core providers (direct)

| id | Source |
|----|--------|
| `claude` | `status.claude.com/api/v2/summary.json` |
| `openai` | `status.openai.com/api/v2/summary.json` |
| `cursor` | `status.cursor.com/api/v2/summary.json` |
| `github` | `githubstatus.com/api/v2/summary.json` |
| `gemini_workspace` | Google Workspace `incidents.json` |
| `gemini_vertex` | GCP `incidents.json` (gemini/vertex filter) |

## Extended providers (`--extended`, AIWatch cached)

| id | AIWatch id |
|----|------------|
| `mistral` | mistral |
| `xai` | xai |
| `deepseek` | deepseek |
| `copilot` | copilot |
| `groq` | groq |
| `perplexity` | perplexity |
| `openrouter` | openrouter |
| `windsurf` | windsurf |
| `bedrock` | bedrock |
| `cohere` | cohere |

AIWatch URL: `https://aiwatch-worker.p2c2kbf.workers.dev/api/status/cached?src=ai-status-skill`

This is the public cache endpoint of the third-party
[AIWatch](https://github.com/bentleypark/aiwatch) project (the URL is hardcoded
in that repo). If it disappears, only `--extended` degrades — core providers
are unaffected.

## Status normalization

| normalized | meaning |
|------------|---------|
| `operational` | healthy |
| `degraded` | minor degradation |
| `partial_outage` | partial outage |
| `major_outage` | major outage |
| `unknown` | fetch failed |

## incident_kind (Statuspage)

| kind | description |
|------|-------------|
| `operational_outage` | infrastructure/service unavailable |
| `operational_degraded` | latency/error-rate elevation |
| `scope_limited` | specific orgs/tenants only (e.g. FedRAMP) |
| `policy_compliance` | export control / model recall (e.g. Mythos/Fable 5) |
| `maintenance` | planned maintenance |
| `informational` | announcement-style |

**Principle**: if every tracked component is `operational`, do not raise the
aggregate to incident `impact: major`. Report via `alerts.policy` /
`alerts.scope_limited` separately.

**Reporting**: default = two-column Service|Status table + policy bullets when
applicable. Detail/links on request.

### Reference case (Claude Mythos/Fable 5)

| Item | Value |
|------|-------|
| Kind | `policy_compliance` |
| Components | all operational |
| Correct | 🟢 + policy section |
| Wrong | 🔴 major_outage |
| Notice | https://www.anthropic.com/news/fable-mythos-access |

## Verification

```bash
python3 <skill-dir>/scripts/check_status.py --providers claude --format json 2>/dev/null | python3 -m json.tool
```

## Contributing (adding a provider)

- Core: `scripts/check_status.py` → `PROVIDERS`
- Extended: `EXTENDED_PROVIDERS` (AIWatch id mapping)
- Do not copy AIWatch code (AGPL)
