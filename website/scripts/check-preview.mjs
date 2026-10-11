import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const [html, app, sampleReport] = await Promise.all([
  readFile(new URL('../public/index.html', import.meta.url), 'utf8'),
  readFile(new URL('../public/app.js', import.meta.url), 'utf8'),
  readFile(new URL('../public/sample-report.html', import.meta.url), 'utf8'),
]);

assert.match(html, /<details id="run-log"[^>]*>/, 'the preview exposes a collapsed run log');
assert.match(html, /id="run-log-entries"/, 'the run log has an entry container');
assert.doesNotMatch(html, /<details id="run-log"[^>]*\sopen(?:\s|>)/, 'the run log starts collapsed');

assert.match(html, /Reduced browser assessment/, 'the UI labels reduced results clearly');
assert.match(html, /14 of 23 checks/, 'the UI publishes browser coverage');
assert.match(html, /Run the complete assessment/, 'the UI provides the CLI route');
assert.match(html, /href="sample-report\.html">Sample report<\/a>/, 'the navigation links to the CLI sample report');
assert.match(sampleReport, /CLI sample report/, 'the sample is clearly identified as a CLI report');
assert.match(sampleReport, /Online analysis/, 'the sample includes full CLI online-analysis output');
assert.match(sampleReport, /History &amp; substance/, 'the sample includes CLI-only history evidence');
assert.match(app, /new Worker\(/, 'the scan runs in a Web Worker');
assert.match(app, /indexedDB/, 'successful reports use browser caching');
assert.doesNotMatch(app, /representative report/i, 'the old representative-data simulation is gone');

console.log('Browser assessment disclosure check passed.');
