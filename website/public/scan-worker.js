import { acquireRepository, BROWSER_LIMITS, ScanError } from './browser-scan.mjs';

let active = null;
let pyodidePromise = null;

function emit(runId, type, payload = {}) {
  self.postMessage({ runId, type, ...payload });
}

function progress(runId, percent, title, detail) {
  emit(runId, 'progress', { percent, title, detail });
}

async function loadAnalyzer(runId) {
  if (!pyodidePromise) {
    pyodidePromise = (async () => {
      const runtimeBase = new URL('./vendor/pyodide-0.27.7/', self.location.href);
      const runtime = await import(new URL('pyodide.mjs', runtimeBase));
      const pyodide = await runtime.loadPyodide({ indexURL: runtimeBase.href });
      const wheelUrl = new URL('./vendor/slop_meeter-0.4.1-py3-none-any.whl', self.location.href);
      const wheel = await fetch(wheelUrl, { cache: 'force-cache' });
      if (!wheel.ok) throw new Error(`browser analyzer wheel unavailable (HTTP ${wheel.status})`);
      const sitePackages = pyodide.runPython("import sysconfig; sysconfig.get_paths()['purelib']");
      pyodide.unpackArchive(await wheel.arrayBuffer(), 'zip', { extractDir: sitePackages });
      pyodide.runPython('from slopmeter.browser import analyze_browser_snapshot');
      return pyodide;
    })();
  }
  progress(runId, 7, 'Loading browser analyzer', 'Loaded the pinned, self-hosted Pyodide runtime and Slop Meeter wheel.');
  return pyodidePromise;
}

function progressFromAcquisition(runId, event) {
  if (event.stage === 'resolve') progress(runId, 12, 'Resolving default branch', event.message);
  if (event.stage === 'resolved') progress(runId, 18, 'Resolved exact revision', event.message);
  if (event.stage === 'resolved') emit(runId, 'resolved', { target: event.target, revision: event.revision });
  if (event.stage === 'tree') progress(runId, 24, 'Listing repository files', event.message);
  if (event.stage === 'limits') progress(runId, 30, 'Checking browser limits', event.message);
  if (event.stage === 'download') {
    const percent = 30 + Math.round((event.current / Math.max(event.total, 1)) * 45);
    progress(runId, percent, `Downloading file ${event.current} of ${event.total}`, event.path);
  }
  if (event.stage === 'tags') progress(runId, 79, 'Reading release tags', event.message);
  emit(runId, 'log', { event });
}

async function runScan(runId, value) {
  const controller = new AbortController();
  let acquisitionTimedOut = false;
  const acquisitionDeadline = setTimeout(() => {
    acquisitionTimedOut = true;
    controller.abort();
  }, BROWSER_LIMITS.acquisitionTimeoutMs);
  active = { runId, controller };
  const started = performance.now();
  try {
    progress(runId, 2, 'Loading browser analyzer', 'Starting the module worker.');
    const analyzerPromise = loadAnalyzer(runId);
    const acquired = await acquireRepository(value, {
      signal: controller.signal,
      limits: BROWSER_LIMITS,
      onProgress: (event) => progressFromAcquisition(runId, event),
    });
    clearTimeout(acquisitionDeadline);
    if (controller.signal.aborted || active?.runId !== runId) return;
    const pyodide = await analyzerPromise;
    progress(runId, 84, 'Running 14 browser checks', 'Analyzing the complete eligible snapshot without executing repository code.');
    const pythonEntries = pyodide.toPy(acquired.entries);
    const pythonTags = pyodide.toPy(acquired.tags);
    try {
      const analyze = pyodide.globals.get('analyze_browser_snapshot');
      const serialized = analyze(
        pythonEntries,
        pythonTags,
        acquired.slug.target,
        acquired.revision,
        new Date().toISOString(),
        Math.round(performance.now() - started),
      );
      analyze.destroy?.();
      if (controller.signal.aborted || active?.runId !== runId) return;
      progress(runId, 96, 'Building reduced report', 'Serializing the versioned browser report.');
      emit(runId, 'complete', {
        report: JSON.parse(String(serialized)),
        summary: {
          revision: acquired.revision,
          files: acquired.entries.length,
          bytes: acquired.totalBytes,
          elapsedMs: Math.round(performance.now() - started),
        },
      });
    } finally {
      pythonEntries.destroy?.();
      pythonTags.destroy?.();
    }
  } catch (error) {
    if (acquisitionTimedOut) {
      emit(runId, 'error', {
        code: 'acquisition_timeout',
        message: 'Repository acquisition exceeded the published 30-second browser limit.',
      });
      return;
    }
    if (controller.signal.aborted || active?.runId !== runId) {
      emit(runId, 'cancelled');
      return;
    }
    const known = error instanceof ScanError;
    emit(runId, 'error', {
      code: known ? error.code : 'worker_failure',
      message: known ? error.message : 'The browser analyzer could not complete this scan.',
    });
  } finally {
    clearTimeout(acquisitionDeadline);
    if (active?.runId === runId) active = null;
  }
}

self.addEventListener('message', (event) => {
  const { type, runId, repository } = event.data || {};
  if (type === 'cancel' && active?.runId === runId) {
    active.controller.abort();
    return;
  }
  if (type === 'start' && typeof runId === 'string') {
    if (active) active.controller.abort();
    void runScan(runId, repository);
  }
});
