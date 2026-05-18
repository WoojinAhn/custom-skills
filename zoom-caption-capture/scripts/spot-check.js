// Cheap status probe. Returns observer liveness + counts + tail of the last
// utterance. Use between long sleeps to confirm capture is still running.
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
