// Install a MutationObserver inside iframe#webclient that streams caption
// fragments into `iframe.contentWindow.__transcript`. Run via the
// claude-in-chrome `javascript_tool` on the Zoom Web Client meeting tab.
//
// State stored on contentWindow so it survives between tool invocations:
//   __captionObs       — the MutationObserver instance
//   __transcript       — array of { speaker, text, startedAt, updatedAt }
//   __mergeTranscript  — post-hoc re-merge function (run at dump time)
(() => {
  const f = document.getElementById('webclient');
  const w = f.contentWindow;
  const doc = f.contentDocument;

  if (w.__captionObs) { try { w.__captionObs.disconnect(); } catch (e) {} }
  w.__captionBuf = [];
  w.__transcript = [];

  const norm = s => s.replace(/[\.,!?]+/g, '').replace(/\s+/g, ' ').trim();
  const tokens = s => norm(s).split(' ').filter(Boolean);

  // Token-level overlap merger. Zoom's caption box is a rolling window, so
  // consecutive snapshots usually overlap by a suffix-prefix. Find that
  // overlap and append only the new tail. Returns null if no overlap is
  // found (caller treats the snapshot as a new utterance).
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
        for (let j = 0; j < n; j++) if (tail[j] !== bT[i + j]) { ok = false; break; }
        if (ok) {
          const remaining = bT.slice(i + n).join(' ');
          return remaining ? a + ' ' + remaining : a;
        }
      }
    }
    return null;
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
