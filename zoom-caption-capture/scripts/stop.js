// Stop the observer without leaving the meeting. The transcript array is
// preserved on contentWindow, so a later dump.js still works.
(() => {
  const w = document.getElementById('webclient').contentWindow;
  if (w.__captionObs) w.__captionObs.disconnect();
  return { stopped: true, captured: w.__transcript.length };
})()
