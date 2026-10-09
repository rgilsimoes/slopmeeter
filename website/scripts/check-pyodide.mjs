import assert from 'node:assert/strict';
import { readFile } from 'node:fs/promises';
import { join } from 'node:path';
import { fileURLToPath } from 'node:url';
import { loadPyodide } from 'pyodide';

const website = fileURLToPath(new URL('../', import.meta.url));
const pyodide = await loadPyodide();
const wheel = new Uint8Array(await readFile(join(website, 'public/vendor/slop_meeter-0.4.0-py3-none-any.whl')));
const sitePackages = pyodide.runPython("import sysconfig; sysconfig.get_paths()['purelib']");
pyodide.unpackArchive(wheel, 'zip', { extractDir: sitePackages });
pyodide.runPython('from slopmeter.browser import analyze_browser_snapshot');

const analyze = pyodide.globals.get('analyze_browser_snapshot');
const content = new TextEncoder().encode('# Demo\n\nA small documented project.\n');
const entries = pyodide.toPy([['README.md', content.byteLength, '100644', 'a'.repeat(40), content]]);
const tags = pyodide.toPy(['unavailable', [], 'tag API unavailable']);
try {
  const report = JSON.parse(analyze(entries, tags, 'owner/repository', 'b'.repeat(40), new Date().toISOString(), 1));
  assert.equal(report.analysis_profile, 'browser-reduced-v1');
  assert.equal(report.coverage.run.length, 15);
  assert.equal(report.coverage.unavailable.length, 9);
  assert.equal(report.maturity_note, null);
  assert.equal(report.checks.find((check) => check.id === 'D3').status, 'na');
  assert.equal(Math.round(report.coverage.maximum_confidence), 63);
} finally {
  analyze.destroy();
  entries.destroy();
  tags.destroy();
}

console.log('Pinned Pyodide runs the shared browser profile successfully.');
