// Dump captured transcript as a JSON file via Blob download. Return values
// from javascript_tool are size-truncated, so we route the payload through
// the browser's download channel — the file lands in ~/Downloads/.
//
// Chrome blocks back-to-back programmatic downloads, so this only dumps
// JSON. Convert to Markdown locally with `scripts/to-markdown.js`.
(() => {
  const w = document.getElementById('webclient').contentWindow;
  const doc = document.getElementById('webclient').contentDocument;
  const merged = w.__mergeTranscript();
  const meta = {
    title: document.title,
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
