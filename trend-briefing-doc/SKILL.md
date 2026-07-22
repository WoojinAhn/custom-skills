---
name: trend-briefing-doc
description: >-
  Given just a link (Reddit/HN/X thread) or a single topic phrase — especially
  AI-coding/dev discourse ("vibe coding", "agentic engineering", "Dark Factory",
  "AI coding trends") — automatically research it and produce a Korean HTML
  trend briefing structured as "position A vs position B". Applies even when the
  user only pastes a URL or topic with no other instruction. Pretendard font,
  card-based understated report tone; no courtroom/trial/war metaphors.

  Triggers: pasting a single URL, "이거 트렌드로 정리해줘", "~ 관련 최근 흐름
  알아봐줘", "AI 개발 트렌드 브리핑", "트렌드 브리핑 만들어", "커뮤니티 반응
  html로 발행"

  Do NOT use for: plain text summaries (where markdown suffices),
  visualization-heavy dashboards (use a canvas/dataviz skill), code review or
  security review documents
---

# Trend Briefing Doc

Given only a link or a one-line topic (e.g. the phrase "AI dev-scene trending",
or a single Reddit/HN URL), start researching immediately and produce a Korean
HTML briefing structured as "position A vs position B". When the topic is vague,
dive into research anyway — the only thing to confirm with the user is where to
publish.

## 1. Research

1. Secure the starting thread/comments (if a URL is given, open it first and
   read the original).
   - For sites that block scraping (e.g. Reddit), use Playwright
     `browser_navigate` + `browser_evaluate` to extract comments (author, score,
     depth, body) directly from the DOM. Use this as the bypass when
     `curl`-style fetching is blocked.
2. Find opposing/complementary viewpoints: search Hacker News, X, and
   engineering blogs from the last 1–2 weeks. If `parallel-cli` is installed,
   use `parallel-cli search` (it supports only the `-q` and objective
   positional arguments — there is no `--objective` flag); otherwise fall back
   to your built-in web search tool.
3. Collect at least 5–6 sources and classify them into the two axes
   "position A / position B". Be careful not to gather evidence that leans to
   one side only.

## 2. Writing

Start by copying [template.html](template.html). Fill in every
`{{PLACEHOLDER}}` with real content, and delete optional sections that don't
apply (gauges, diagrams, glossary) in their entirety.

**Hard rules**:

- Translate every quoted comment into Korean. Keep the link to the original.
- No courtroom (plaintiff/defendant/verdict), war, or cringe-inducing
  metaphors. The final section is a "one-line takeaway" that plainly states
  observations and limitations — it does not declare winners or verdicts.
- Comment cards (`.cmt`) use flex + `min-width:0` + `overflow-wrap: anywhere`
  so long Latin usernames don't break layout. Do not convert them to grid.
- Fonts: Pretendard Variable (body/headings) + JetBrains Mono (numbers/labels)
  only. No typewriter faces, grid backgrounds, or stamp-style decorations.
- Responsive: `.positions`, `.gauge-block`, `.res-grid` already carry media
  queries that collapse them to one column below 620–720px — keep them.

## 3. Publishing

After writing, confirm the destination with the user. Default: save the HTML
locally. If the user keeps a Wunderkammer vault (`wk` CLI available), publish
there instead (`wk import` + `wk scan`, `--replace` when updating). Without a
vault, the standalone HTML file is the deliverable — it is fully
self-contained apart from font CDN links.

## 4. Completion report

Report the published location (or file path) together with a one-line summary
of how positions A/B were classified.
