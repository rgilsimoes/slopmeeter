export const ANALYZER_VERSION = '0.4.1';
export const PROFILE_VERSION = 'browser-reduced-v1';
export const LIMIT_VERSION = 'browser-limits-v1';
export const DEFAULT_CONFIG_HASH = 'sha256-48b708dcfb53f93a033f2f7528252626ffbcfaed6d390a5428810adbd76387c9';

export const BROWSER_LIMITS = Object.freeze({
  maxFiles: 3000,
  maxTotalBytes: 60 * 1024 * 1024,
  maxFileBytes: 1_000_000,
  concurrency: 12,
  acquisitionTimeoutMs: 30_000,
  analysisTimeoutMs: 15_000,
});

const IGNORED_PARTS = new Set([
  '.git', '.hg', '.svn', '.venv', 'venv', 'node_modules', 'vendor', 'dist', 'build', '__pycache__',
]);

export class ScanError extends Error {
  constructor(code, message, details = {}) {
    super(message);
    this.name = 'ScanError';
    this.code = code;
    this.details = details;
  }
}

export function parseGitHubUrl(value) {
  let url;
  try {
    url = new URL(value);
  } catch {
    throw new ScanError('invalid_repository', 'Enter a canonical public GitHub repository URL.');
  }
  const parts = url.pathname.split('/').filter(Boolean);
  if (
    url.protocol !== 'https:' || url.hostname !== 'github.com' || url.port || url.username ||
    url.password || url.search || url.hash || parts.length !== 2
  ) {
    throw new ScanError('invalid_repository', 'Only canonical https://github.com/owner/repository URLs are supported.');
  }
  const owner = parts[0];
  const repository = parts[1].replace(/\.git$/, '');
  const component = /^[A-Za-z0-9_.-]+$/;
  if (!owner || !repository || !component.test(owner) || !component.test(repository)) {
    throw new ScanError('invalid_repository', 'The GitHub owner or repository name is invalid.');
  }
  return {
    owner,
    repository,
    target: `${owner}/${repository}`,
    url: `https://github.com/${owner}/${repository}`,
  };
}

function apiUrl(slug, path) {
  return `https://api.github.com/repos/${encodeURIComponent(slug.owner)}/${encodeURIComponent(slug.repository)}${path}`;
}

async function githubJson(url, signal) {
  const response = await fetch(url, {
    signal,
    headers: { Accept: 'application/vnd.github+json', 'X-GitHub-Api-Version': '2022-11-28' },
  });
  if (!response.ok) {
    if (response.status === 403 || response.status === 429 || response.headers.get('x-ratelimit-remaining') === '0') {
      throw new ScanError('rate_limited', 'GitHub’s anonymous API limit is exhausted. Please retry after the reset window.');
    }
    if (response.status === 404) {
      throw new ScanError('not_found', 'The public repository was not found. Private repositories are not supported.');
    }
    throw new ScanError('github_api', `GitHub returned HTTP ${response.status}.`);
  }
  return response.json();
}

export async function resolveRepository(slug, signal) {
  const repository = await githubJson(apiUrl(slug, ''), signal);
  if (repository.private) {
    throw new ScanError('private_repository', 'Private repositories are not supported.');
  }
  const branch = String(repository.default_branch || '');
  if (!branch) throw new ScanError('missing_default_branch', 'The repository has no default branch.');
  const commit = await githubJson(apiUrl(slug, `/commits/${encodeURIComponent(branch)}`), signal);
  const revision = String(commit.sha || '');
  if (!/^[0-9a-f]{40}$/i.test(revision)) {
    throw new ScanError('invalid_revision', 'GitHub did not return a full commit SHA.');
  }
  return { branch, revision: revision.toLowerCase() };
}

function safeTreePath(path) {
  if (typeof path !== 'string' || path.startsWith('/') || path.includes('\\')) return false;
  const parts = path.split('/');
  return parts.length > 0 && parts.every((part) => part && part !== '.' && part !== '..');
}

export function selectCandidates(tree, limits = BROWSER_LIMITS) {
  if (!tree || tree.truncated) {
    throw new ScanError('truncated_tree', 'GitHub returned a truncated repository tree, so an absence-based assessment would be unreliable.');
  }
  const candidates = [];
  for (const entry of tree.tree || []) {
    if (!safeTreePath(entry.path)) throw new ScanError('unsafe_path', 'The repository contains an unsafe path.');
    const parts = entry.path.split('/');
    if (parts.some((part) => IGNORED_PARTS.has(part))) continue;
    if (entry.type !== 'blob' || entry.mode === '120000') continue;
    if (!Number.isSafeInteger(entry.size) || entry.size < 0) {
      throw new ScanError('unknown_file_size', `GitHub did not provide a safe size for ${entry.path}.`);
    }
    if (entry.size > limits.maxFileBytes) {
      throw new ScanError('file_limit', `${entry.path} exceeds the published 1 MB browser file limit.`, { path: entry.path, size: entry.size });
    }
    candidates.push({ path: entry.path, size: entry.size, mode: String(entry.mode), sha: String(entry.sha) });
  }
  const totalBytes = candidates.reduce((total, entry) => total + entry.size, 0);
  if (candidates.length > limits.maxFiles) {
    throw new ScanError('file_count_limit', `This repository has ${candidates.length.toLocaleString()} eligible files; the browser limit is ${limits.maxFiles.toLocaleString()}.`);
  }
  if (totalBytes > limits.maxTotalBytes) {
    throw new ScanError('total_bytes_limit', `This repository has ${(totalBytes / 1048576).toFixed(1)} MiB of eligible files; the browser limit is ${limits.maxTotalBytes / 1048576} MiB.`);
  }
  return { candidates, totalBytes };
}

function rawUrl(slug, revision, path) {
  const encodedPath = path.split('/').map(encodeURIComponent).join('/');
  return `https://raw.githubusercontent.com/${encodeURIComponent(slug.owner)}/${encodeURIComponent(slug.repository)}/${revision}/${encodedPath}`;
}

async function readBounded(response, expectedSize, limit) {
  if (!response.body) {
    const data = new Uint8Array(await response.arrayBuffer());
    if (data.byteLength > limit) throw new ScanError('response_limit', 'A raw file exceeded the browser response limit.');
    return data;
  }
  const reader = response.body.getReader();
  const chunks = [];
  let total = 0;
  while (true) {
    const { done, value } = await reader.read();
    if (done) break;
    total += value.byteLength;
    if (total > limit || total > expectedSize) {
      await reader.cancel();
      throw new ScanError('response_limit', 'A raw file exceeded its declared or published size limit.');
    }
    chunks.push(value);
  }
  if (total !== expectedSize) throw new ScanError('size_mismatch', 'A downloaded file did not match the immutable tree metadata.');
  const data = new Uint8Array(total);
  let offset = 0;
  for (const chunk of chunks) {
    data.set(chunk, offset);
    offset += chunk.byteLength;
  }
  return data;
}

async function downloadOne(slug, revision, entry, signal, limits) {
  const response = await fetch(rawUrl(slug, revision, entry.path), { signal, cache: 'no-store' });
  if (!response.ok) throw new ScanError('download_failed', `A required file could not be downloaded (HTTP ${response.status}).`, { path: entry.path });
  const contents = await readBounded(response, entry.size, limits.maxFileBytes);
  return [entry.path, entry.size, entry.mode, entry.sha, contents];
}

async function downloadAll(slug, revision, candidates, signal, limits, onProgress) {
  const entries = new Array(candidates.length);
  let next = 0;
  let complete = 0;
  const worker = async () => {
    while (true) {
      const index = next;
      next += 1;
      if (index >= candidates.length) return;
      entries[index] = await downloadOne(slug, revision, candidates[index], signal, limits);
      complete += 1;
      onProgress?.({ stage: 'download', current: complete, total: candidates.length, path: candidates[index].path });
    }
  };
  await Promise.all(Array.from({ length: Math.min(limits.concurrency, candidates.length || 1) }, worker));
  return entries;
}

async function lookupTags(slug, signal) {
  try {
    const tags = await githubJson(apiUrl(slug, '/tags?per_page=1'), signal);
    return ['available', Array.isArray(tags) ? tags.map((tag) => String(tag.name)).slice(0, 1) : [], null];
  } catch (error) {
    if (error?.name === 'AbortError') throw error;
    return ['unavailable', [], error instanceof ScanError ? error.message : 'Release tag lookup was unavailable.'];
  }
}

export async function acquireRepository(value, { signal, limits = BROWSER_LIMITS, onProgress } = {}) {
  const slug = typeof value === 'string' ? parseGitHubUrl(value) : value;
  onProgress?.({ stage: 'resolve', message: 'Resolving default branch.' });
  const { branch, revision } = await resolveRepository(slug, signal);
  onProgress?.({ stage: 'resolved', message: `Resolved ${branch} to ${revision}.`, target: slug.target, revision });
  const tree = await githubJson(apiUrl(slug, `/git/trees/${revision}?recursive=1`), signal);
  onProgress?.({ stage: 'tree', message: 'Listed the complete recursive Git tree.' });
  const selected = selectCandidates(tree, limits);
  onProgress?.({ stage: 'limits', message: `${selected.candidates.length.toLocaleString()} files and ${(selected.totalBytes / 1048576).toFixed(1)} MiB are within browser limits.` });
  const entries = await downloadAll(slug, revision, selected.candidates, signal, limits, onProgress);
  onProgress?.({ stage: 'tags', message: 'Reading release tags.' });
  const tags = await lookupTags(slug, signal);
  return { slug, branch, revision, entries, tags, totalBytes: selected.totalBytes };
}
