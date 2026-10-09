import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';

const [html, app] = await Promise.all([
  readFile(new URL('../public/index.html', import.meta.url), 'utf8'),
  readFile(new URL('../public/app.js', import.meta.url), 'utf8'),
]);

assert.match(html, /<details id="run-log"[^>]*>/, 'the preview exposes a collapsed run log');
assert.match(html, /id="run-log-entries"/, 'the run log has an entry container');
assert.doesNotMatch(html, /<details id="run-log"[^>]*\sopen(?:\s|>)/, 'the run log starts collapsed');

assert.match(
  app,
  /Representative report displayed[^'"`]*not derived from/i,
  'completion says the report was not derived from the submitted repository',
);
assert.match(
  app,
  /No repository data (?:was|is being) fetched or analyzed/i,
  'the log discloses that the preview performs no repository analysis',
);

console.log('Preview disclosure check passed.');
