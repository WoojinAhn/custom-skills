#!/usr/bin/env node
// Convert a transcript JSON dump (from scripts/dump.js) into Markdown.
// Usage: node scripts/to-markdown.js ~/Downloads/meeting-YYYY-MM-DD-transcript.json
//
// Done locally rather than in-browser because Chrome blocks back-to-back
// programmatic downloads — the second one (Markdown) usually drops.
const fs = require('fs');

const path = process.argv[2];
if (!path) {
  console.error('usage: node scripts/to-markdown.js <transcript.json>');
  process.exit(1);
}

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
  ...d.merged.map(u => '**[' + u.startedAt.slice(11, 19) + '] ' + u.speaker + '**: ' + u.text)
].join('\n');

const outPath = path.replace(/\.json$/, '.md');
fs.writeFileSync(outPath, md);
console.log('wrote', outPath);
