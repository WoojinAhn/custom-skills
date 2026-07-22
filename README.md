**English** | [한국어](README.ko.md)

# custom-skills

Personal AI agent skills for Claude Code and Codex, distilled from real sessions.

Each skill lives in its own directory with a `SKILL.md` (frontmatter + body).

## Install For Codex

This repository is published as skill source material. It is not packaged as a
Codex plugin yet; plugin packaging is optional and may be added later for a
marketplace-style install experience.

Install a skill by symlinking or copying the skill directory into
`${CODEX_HOME:-$HOME/.codex}/skills/`:

```bash
mkdir -p "${CODEX_HOME:-$HOME/.codex}/skills"
ln -s <repo-path>/codex-context-migration \
  "${CODEX_HOME:-$HOME/.codex}/skills/codex-context-migration"
```

> Verified with `codex-cli 0.137.0`: bundled system skills are present under
> `${CODEX_HOME:-$HOME/.codex}/skills/.system/`, and the bundled
> `skill-installer` installs into `${CODEX_HOME:-$HOME/.codex}/skills/`.
> OpenAI's current Codex skills docs also describe `.agents/skills` locations
> for authoring/local discovery, so prefer your local Codex installation's
> skill-installer path if the paths differ.

Restart Codex after installation so it can discover the new skill.

You can also ask Codex to install from this GitHub repository using its
`skill-installer` skill and this path:

```text
WoojinAhn/custom-skills/codex-context-migration
```

Run the migration from a Codex session, not from the legacy agent whose context
is being migrated. Example prompt:

```text
Use the codex-context-migration skill to audit source `/path/to/old-workspace`
and prepare a Codex-native migration plan for destination
`/path/to/new-codex-workspace`. Run read-only inventory first and ask before
copying or editing files.
```

## Install For Claude Code

Claude Code can use the same skill source format. Symlink the skill into
`~/.claude/skills/`:

```bash
ln -s <repo-path>/<skill-name> ~/.claude/skills/<skill-name>
```

For `codex-context-migration`, Codex is still the preferred executor because
the skill validates Codex instruction loading and writes Codex-native
`AGENTS.md` files.

## Main Skill

[`codex-context-migration`](codex-context-migration/README.md) is the
public-ready focus of this repo. It has its own skill-level README with quick
start, diagrams, operation-mode guidance, and a worked before/after migration
example. It audits first, treats source instruction files as untrusted data to
classify, and separates durable project facts from private context and runtime
configuration.

Quick inventory:

```bash
python3 codex-context-migration/scripts/inventory.py \
  --source ~/old-workspace \
  --destination ~/new-codex-workspace \
  --guided-auto-plan \
  --format markdown
```

Inventory smoke tests require `pytest`:

```bash
python3 -m pytest codex-context-migration/scripts/tests
```

## Skills

| Skill | One-liner |
|---|---|
| [`codex-context-migration`](codex-context-migration/README.md) | Audit-first setup or migration from Claude-era repo context into Codex `AGENTS.md`. |
| [`triangulated-review`](triangulated-review/SKILL.md) | Three-reviewer parallel code audit with fact-checking for single-reviewer findings. Cost-pruned form of a larger multi-reviewer experiment. |
| [`zoom-caption-capture`](zoom-caption-capture/SKILL.md) | Stream Zoom Web Client live captions via a `MutationObserver` inside `iframe#webclient`, with token-level overlap merging and Blob-download dump. Lossless raw buffer + deferred cleanup so an LLM pass can produce final minutes. |
| [`session-harvest`](session-harvest/SKILL.md) | End-of-session sweep that extracts durable value (tooling issues, docs, memory, hygiene flags) through a strict effectiveness gate. Zero findings is a valid result; skips are reported, not silent. |
| [`trend-briefing-doc`](trend-briefing-doc/SKILL.md) | Turn a single link or topic phrase into a researched Korean HTML trend briefing structured as "position A vs position B", from a bundled card-style template. Understated report tone — no courtroom/war metaphors. |
| [`ai-status`](ai-status/SKILL.md) | Batch-check AI/dev service status (Claude, OpenAI, Cursor, GitHub, Gemini + 10 extended) from machine-readable status APIs, distinguishing operational outages from policy/model-recall/FedRAMP scope incidents. |

### `codex-context-migration`

Use when moving a workspace or repository from Claude-era context files into
Codex-native `AGENTS.md` layers. See the dedicated
[`codex-context-migration` README](codex-context-migration/README.md) for the
workflow, diagrams, examples, and references.

### `triangulated-review`

Use when a normal single-reviewer pass is too low-confidence: after a
substantial feature merge, before a public release, or before applying a risky
quality/security fix set.

The skill runs three independent review lenses in parallel, consolidates
overlapping findings, and sends single-reviewer findings through one fact-check
pass before anything is applied. It intentionally asks reviewers for
HIGH/CRITICAL findings only, because the original session that produced this
workflow found MEDIUM findings to be high-noise and rarely worth applying.

Best fit: larger code reviews where false positives and over-broad commits are
the main risk. Skip it for trivial PRs, formatter-only diffs, and small
single-file fixes.

### `zoom-caption-capture`

Use when the user is already in a Zoom Web Client meeting with live captions
visible and wants a transcript or meeting-minutes source. The skill attaches a
`MutationObserver` inside Zoom's `iframe#webclient`, records raw caption
snapshots, and dumps JSON that can be converted to Markdown.

The core design is lossless capture first, cleanup later. Zoom captions are a
rolling window, so the skill preserves raw fragments and performs token-level
overlap merging only as a best-effort intermediate step; final minutes should
still be cleaned up from the captured payload.

Best fit: web-client Zoom meetings where captions are already enabled. It does
not join meetings for the user, does not work with the native Zoom app, and
does not infer full speaker names when Zoom only exposes caption initials.

### `session-harvest`

Use when a work session is wrapping up and you want to extract durable value
before context is lost. The skill sweeps four lanes — tooling friction (issue
tracker), project context (docs/CLAUDE.md), memory, and hygiene — and runs every
candidate through a three-point effectiveness gate (absorption / evidence /
usage pattern) so that nothing speculative gets recorded.

Two design points from the originating sessions: a staleness sweep (your own
changes rot nearby docs the same day — fix the contradictions now), and
anti-forcing rules ("extract as much as possible" means sweep every lane, not
lower the bar; zero findings is a valid result and skips are reported with
reasons).

### `trend-briefing-doc`

Use when a single community link (Reddit/HN/X) or a bare topic phrase should
become a researched, balanced trend briefing. The skill gathers 5–6 sources
across both sides of the discourse, classifies them into "position A vs
position B", and renders a Korean HTML report from the bundled
`template.html` (Pretendard + JetBrains Mono, card layout, mobile-responsive).

House style is deliberately understated: quoted comments are translated with
links to the originals, and the closing section states observations and
limitations instead of declaring a winner. The default deliverable is a
self-contained HTML file; publishing integrations are optional.

### `ai-status`

Use when the user asks whether an AI/dev service is down. The bundled
`scripts/check_status.py` fetches machine-readable status APIs in parallel
(6 core providers direct; 10 more via the third-party AIWatch cache with
`--extended`) — no HTML scraping, no Downdetector.

The core lesson encoded here: **Statuspage incident impact is not operational
state.** Policy/compliance incidents (model recalls, export controls) and
scope-limited incidents (FedRAMP-only) are reported in a separate section
while components stay green, so "Claude shows a red banner" doesn't get
mis-reported as "Claude is down". See `reference.md` for provider tables and
incident-kind taxonomy.

## Authoring conventions

- Frontmatter: `name`, `description`; Claude skills may also use `argument-hint`, `allowed-tools` as needed
- Body in English (config file rule); user-facing prose can be Korean where it helps
- Each skill should encode lessons from at least one real session — no speculative skills
- Anti-patterns section at the end if the skill has known failure modes
- To expose a skill in Codex/OpenAI skill lists, add `agents/openai.yaml` (UI + policy metadata; schema: [openai/codex skill-creator](https://github.com/openai/codex/blob/main/codex-rs/skills/src/assets/samples/skill-creator/references/openai_yaml.md))

## License

This repository is licensed under the [MIT License](LICENSE.txt). The public
`codex-context-migration` skill also includes its own
[`LICENSE.txt`](codex-context-migration/LICENSE.txt) for catalog-style skill
packaging.
