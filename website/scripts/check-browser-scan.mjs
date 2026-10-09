import assert from 'node:assert/strict';

import { acquireRepository, BROWSER_LIMITS, parseGitHubUrl, ScanError, selectCandidates } from '../public/browser-scan.mjs';

assert.deepEqual(parseGitHubUrl('https://github.com/owner/repository'), {
  owner: 'owner', repository: 'repository', target: 'owner/repository', url: 'https://github.com/owner/repository',
});
assert.equal(parseGitHubUrl('https://github.com/owner/repository.git/').repository, 'repository');
for (const value of [
  'http://github.com/owner/repository',
  'https://example.com/owner/repository',
  'https://github.com/owner/repository/issues',
  'https://token@github.com/owner/repository',
  'https://github.com/owner/repository?token=nope',
]) {
  assert.throws(() => parseGitHubUrl(value), ScanError);
}

const selected = selectCandidates({
  truncated: false,
  tree: [
    { path: 'src/main.py', type: 'blob', mode: '100644', sha: 'a'.repeat(40), size: 12 },
    { path: 'node_modules/ignored.js', type: 'blob', mode: '100644', sha: 'b'.repeat(40), size: 99 },
    { path: 'link', type: 'blob', mode: '120000', sha: 'c'.repeat(40), size: 4 },
    { path: 'src', type: 'tree', mode: '040000', sha: 'd'.repeat(40) },
  ],
});
assert.equal(selected.candidates.length, 1);
assert.equal(selected.totalBytes, 12);
assert.throws(() => selectCandidates({ truncated: true, tree: [] }), /truncated/i);
assert.throws(() => selectCandidates({ truncated: false, tree: [{ path: '../escape', type: 'blob', mode: '100644', size: 1 }] }), /unsafe/i);
assert.throws(
  () => selectCandidates({ truncated: false, tree: [{ path: 'huge.bin', type: 'blob', mode: '100644', size: BROWSER_LIMITS.maxFileBytes + 1 }] }),
  /1 MB browser file limit/i,
);

const requested = [];
const revision = 'f'.repeat(40);
const originalFetch = globalThis.fetch;
globalThis.fetch = async (url) => {
  requested.push(String(url));
  if (String(url).endsWith('/repos/owner/repository')) {
    return Response.json({ private: false, default_branch: 'main' });
  }
  if (String(url).includes('/commits/main')) return Response.json({ sha: revision });
  if (String(url).includes('/git/trees/')) {
    return Response.json({ truncated: false, tree: [{ path: 'src/main.py', type: 'blob', mode: '100644', sha: 'a'.repeat(40), size: 3 }] });
  }
  if (String(url).includes('/tags?')) return new Response('upstream failure', { status: 500 });
  if (String(url).startsWith('https://raw.githubusercontent.com/')) return new Response(new Uint8Array([1, 2, 3]));
  throw new Error(`unexpected URL ${url}`);
};
try {
  const acquired = await acquireRepository('https://github.com/owner/repository');
  const rawRequest = requested.find((url) => url.startsWith('https://raw.githubusercontent.com/'));
  assert.match(rawRequest, new RegExp(`/${revision}/src/main\\.py$`));
  assert.doesNotMatch(rawRequest, /\/main\/src\//);
  assert.deepEqual(acquired.tags, ['unavailable', [], 'GitHub returned HTTP 500.']);
} finally {
  globalThis.fetch = originalFetch;
}

console.log('Browser acquisition contract checks passed.');
