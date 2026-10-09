import { ANALYZER_VERSION, DEFAULT_CONFIG_HASH, LIMIT_VERSION, parseGitHubUrl, PROFILE_VERSION } from './browser-scan.mjs';

const $ = (selector) => document.querySelector(selector);
const form = $('#scan-form');
const input = $('#repo-url');
const scanButton = $('#scan-button');
const cancelButton = $('#cancel-scan');
const progress = $('#scan-progress');
const progressBar = $('#progress-bar');
const progressValue = $('#progress-value');
const progressTitle = $('#progress-title');
const progressStage = $('#progress-stage');
const runLog = $('#run-log');
const runLogStatus = $('#run-log-status');
const runLogEntries = $('#run-log-entries');
const reportSection = $('#browser-report');
const errorSection = $('#scan-error');
const sampleReportLink = $('#sample-report-link');

const STATUS = {
  pass: ['✓', 'Pass'], warn: ['▲', 'Warn'], fail: ['×', 'Fail'], na: ['–', 'N/A'], cli: ['–', 'CLI only'], info: ['i', 'Info'],
};
const DB_NAME = 'slopmeeter-browser-reports';
const CACHE_NAMESPACE = `${ANALYZER_VERSION}:${PROFILE_VERSION}:${DEFAULT_CONFIG_HASH}:${LIMIT_VERSION}`;
let activeRun = null;
let renderedReport = null;
let normalizedTarget = null;

function cliCommands(target) {
  return {
    pipx: 'pipx install slop-meeter',
    uv: 'uv tool install slop-meeter',
    run: target ? `slopmeter https://github.com/${target} --online --format html --output slopmeeter-report.html` : 'pipx install slop-meeter',
  };
}

function setCommands(target) {
  const commands = cliCommands(target);
  $('#pipx-command').textContent = commands.pipx;
  $('#uv-command').textContent = commands.uv;
  $('#run-command').textContent = commands.run;
  $('#error-command').textContent = commands.run;
}

function updateProgress(percent, title, detail) {
  progressBar.style.width = `${Math.max(0, Math.min(100, percent))}%`;
  progressValue.textContent = `${percent}%`;
  progressTitle.textContent = title;
  progressStage.textContent = detail;
}

function appendLog(percent, title, detail, complete = false) {
  const item = document.createElement('li');
  item.classList.toggle('complete', complete);
  const marker = document.createElement('span');
  marker.textContent = complete ? '✓' : `${percent}%`;
  const copy = document.createElement('p');
  const heading = document.createElement('strong');
  heading.textContent = title;
  const description = document.createElement('small');
  description.textContent = detail;
  copy.append(heading, description);
  item.append(marker, copy);
  runLogEntries.append(item);
}

function resetRun() {
  runLogEntries.replaceChildren();
  runLog.hidden = false;
  runLog.open = false;
  runLogStatus.textContent = 'Assessment running';
  progress.hidden = false;
  scanButton.disabled = true;
  scanButton.querySelector('span').textContent = 'Assessing repository…';
  cancelButton.hidden = false;
  errorSection.hidden = true;
  sampleReportLink.hidden = true;
  updateProgress(0, 'Loading browser analyzer', 'Starting an isolated module worker.');
}

function finishRun() {
  progress.hidden = true;
  scanButton.disabled = false;
  scanButton.querySelector('span').textContent = 'Run browser assessment';
  cancelButton.hidden = true;
  sampleReportLink.hidden = false;
}

function openDatabase() {
  return new Promise((resolve, reject) => {
    if (!('indexedDB' in window)) return reject(new Error('IndexedDB unavailable'));
    const request = indexedDB.open(DB_NAME, 1);
    request.onupgradeneeded = () => {
      const store = request.result.createObjectStore('reports', { keyPath: 'key' });
      store.createIndex('target', 'target');
      store.createIndex('createdAt', 'createdAt');
    };
    request.onsuccess = () => resolve(request.result);
    request.onerror = () => reject(request.error);
  });
}

async function cachedReports(target) {
  try {
    const db = await openDatabase();
    return await new Promise((resolve, reject) => {
      const transaction = db.transaction('reports', 'readonly');
      const request = transaction.objectStore('reports').index('target').getAll(target);
      request.onsuccess = () => resolve(request.result.sort((a, b) => b.createdAt - a.createdAt));
      request.onerror = () => reject(request.error);
      transaction.oncomplete = () => db.close();
    });
  } catch {
    return [];
  }
}

async function cacheReport(report) {
  try {
    const db = await openDatabase();
    const key = `${CACHE_NAMESPACE}:${report.revision}`;
    await new Promise((resolve, reject) => {
      const transaction = db.transaction('reports', 'readwrite');
      transaction.objectStore('reports').put({ key, target: report.target, revision: report.revision, createdAt: Date.now(), report });
      transaction.oncomplete = resolve;
      transaction.onerror = () => reject(transaction.error);
    });
    const all = await new Promise((resolve, reject) => {
      const transaction = db.transaction('reports', 'readonly');
      const request = transaction.objectStore('reports').index('createdAt').getAll();
      request.onsuccess = () => resolve(request.result.sort((a, b) => b.createdAt - a.createdAt));
      request.onerror = () => reject(request.error);
    });
    if (all.length > 10) {
      await new Promise((resolve, reject) => {
        const transaction = db.transaction('reports', 'readwrite');
        for (const stale of all.slice(10)) transaction.objectStore('reports').delete(stale.key);
        transaction.oncomplete = resolve;
        transaction.onerror = () => reject(transaction.error);
      });
    }
    db.close();
  } catch {
    // Storage denial never prevents a completed assessment from being shown.
  }
}

function renderCategories(report) {
  const container = $('#category-list');
  container.replaceChildren();
  for (const category of report.categories.filter((item) => item.score !== null)) {
    const row = document.createElement('div');
    row.className = 'category-row';
    const name = document.createElement('span');
    name.textContent = category.name;
    const score = document.createElement('strong');
    score.textContent = Math.round(category.score);
    const bar = document.createElement('progress');
    bar.max = 100;
    bar.value = category.score;
    bar.className = category.score >= 80 ? 'pass-bar' : category.score >= 60 ? 'accent-bar' : 'warn-bar';
    bar.setAttribute('aria-label', `${category.name} score ${Math.round(category.score)} out of 100`);
    const note = document.createElement('small');
    note.textContent = 'Based on applicable browser evidence.';
    row.append(name, score, bar, note);
    container.append(row);
  }
}

function renderChecks(report) {
  const body = $('#checks-body');
  body.replaceChildren();
  const counts = { all: report.checks.length, pass: 0, warn: 0, fail: 0, na: 0, cli: 0, info: 0 };
  for (const check of report.checks) {
    const cliOnly = report.coverage.unavailable.includes(check.id);
    const displayStatus = check.category === 'info' ? 'info' : cliOnly ? 'cli' : check.status;
    counts[displayStatus] += 1;
    const row = document.createElement('tr');
    row.dataset.status = displayStatus;
    const name = document.createElement('td');
    const id = document.createElement('code');
    id.textContent = check.id;
    name.append(id, document.createTextNode(check.name));
    const statusCell = document.createElement('td');
    const pill = document.createElement('span');
    pill.className = `status ${displayStatus}`;
    pill.textContent = `${STATUS[displayStatus][0]} ${STATUS[displayStatus][1]}`;
    statusCell.append(pill);
    const finding = document.createElement('td');
    finding.textContent = check.message;
    const evidence = document.createElement('td');
    if (check.evidence.length) {
      const list = document.createElement('ul');
      list.className = 'evidence-items';
      for (const value of check.evidence) {
        const item = document.createElement('li');
        item.textContent = value;
        list.append(item);
      }
      evidence.append(list);
    } else {
      const empty = document.createElement('span');
      empty.textContent = '—';
      evidence.append(empty);
    }
    row.append(name, statusCell, finding, evidence);
    body.append(row);
  }
  document.querySelectorAll('[data-filter]').forEach((button) => {
    button.querySelector('b').textContent = counts[button.dataset.filter];
  });
}

function renderInspections(report) {
  const container = $('#inspection-list');
  container.replaceChildren();
  const items = report.checks
    .filter((check) => check.category !== 'info' && ['fail', 'warn'].includes(check.status))
    .sort((a, b) => (a.status === b.status ? b.weight - a.weight : a.status === 'fail' ? -1 : 1))
    .slice(0, 3);
  if (!items.length) {
    const item = document.createElement('li');
    const copy = document.createElement('div');
    const title = document.createElement('strong');
    title.textContent = 'No warning or failed browser checks';
    copy.append(title);
    item.append(copy);
    container.append(item);
    return;
  }
  items.forEach((check, index) => {
    const item = document.createElement('li');
    const number = document.createElement('span');
    number.textContent = index + 1;
    const copy = document.createElement('div');
    const title = document.createElement('strong');
    title.textContent = check.name;
    const finding = document.createElement('p');
    finding.textContent = check.message;
    copy.append(title, finding);
    item.append(number, copy);
    container.append(item);
  });
}

function renderReport(report, cacheAge = null) {
  renderedReport = report;
  normalizedTarget = report.target;
  setCommands(report.target);
  const reportTarget = $('#report-target');
  reportTarget.replaceChildren();
  const icon = document.createElement('span');
  icon.setAttribute('aria-hidden', 'true');
  icon.textContent = '</>';
  reportTarget.append(icon, document.createTextNode(` github.com/${report.target}`));
  $('#report-revision').textContent = `commit ${report.revision}`;
  $('#report-score').textContent = Math.round(report.evidence_score);
  $('#score-ring').style.background = `conic-gradient(var(--green) 0 ${report.evidence_score}%, #e4e5e1 ${report.evidence_score}% 100%)`;
  $('#score-ring').setAttribute('aria-label', `Browser evidence score ${Math.round(report.evidence_score)} out of 100`);
  $('#report-slop').replaceChildren(document.createTextNode(`${report.slop_level} `));
  const slopSuffix = document.createElement('small');
  slopSuffix.textContent = '/ 10';
  $('#report-slop').append(slopSuffix);
  $('#report-confidence').textContent = `${Math.round(report.confidence)}%`;
  const weightedRun = report.coverage.run.filter((id) => id !== 'I1').length;
  $('#coverage-summary').textContent = `${weightedRun} of 23 checks run · maximum confidence ${Math.round(report.coverage.maximum_confidence)}%`;
  $('#report-verdict').textContent = report.verdict;
  renderCategories(report);
  renderChecks(report);
  renderInspections(report);
  const note = reportSection.querySelector('.prototype-note');
  note.lastChild.textContent = cacheAge === null
    ? ' Results are from the exact commit shown below.'
    : ` Cached result shown immediately (${cacheAge}). Checking the default branch now.`;
  errorSection.hidden = true;
  reportSection.hidden = false;
  reportSection.classList.remove('flash');
  requestAnimationFrame(() => reportSection.classList.add('flash'));
}

function showError(message, target = normalizedTarget) {
  setCommands(target);
  $('#error-message').textContent = message;
  errorSection.hidden = false;
  reportSection.hidden = true;
  errorSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
}

function formatAge(timestamp) {
  const minutes = Math.max(0, Math.floor((Date.now() - timestamp) / 60000));
  if (minutes < 1) return 'less than a minute old';
  if (minutes < 60) return `${minutes} minute${minutes === 1 ? '' : 's'} old`;
  const hours = Math.floor(minutes / 60);
  return `${hours} hour${hours === 1 ? '' : 's'} old`;
}

async function startScan(repositoryUrl) {
  let slug;
  try {
    slug = parseGitHubUrl(repositoryUrl);
  } catch (error) {
    showError(error.message, null);
    return;
  }
  normalizedTarget = slug.target;
  setCommands(slug.target);
  resetRun();
  const cached = (await cachedReports(slug.target)).find((item) => item.key.startsWith(CACHE_NAMESPACE));
  if (cached) renderReport(cached.report, formatAge(cached.createdAt));

  const runId = crypto.randomUUID();
  const worker = new Worker(new URL('./scan-worker.js', import.meta.url), { type: 'module' });
  const deadline = window.setTimeout(() => {
    if (activeRun?.runId !== runId) return;
    worker.terminate();
    activeRun = null;
    finishRun();
    runLogStatus.textContent = 'Timed out';
    showError('The browser time budget expired before a complete report could be produced.', slug.target);
  }, 70_000);
  activeRun = { runId, worker, deadline, analysisDeadline: null, lastLogged: '' };
  worker.addEventListener('message', async (event) => {
    const message = event.data || {};
    if (activeRun?.runId !== runId || message.runId !== runId) return;
    if (message.type === 'progress') {
      updateProgress(message.percent, message.title, message.detail);
      const logKey = message.title.startsWith('Downloading file')
        ? `download-${Math.floor(message.percent / 5)}`
        : message.title;
      if (activeRun.lastLogged !== logKey) {
        appendLog(message.percent, message.title, message.detail);
        activeRun.lastLogged = logKey;
      }
      if (message.title === 'Running 14 browser checks' && !activeRun.analysisDeadline) {
        activeRun.analysisDeadline = window.setTimeout(() => {
          if (activeRun?.runId !== runId) return;
          worker.terminate();
          window.clearTimeout(deadline);
          activeRun = null;
          finishRun();
          runLogStatus.textContent = 'Analysis timed out';
          showError('Analysis exceeded the published 15-second browser limit. No partial score was produced.', slug.target);
        }, 15_000);
      }
    }
    if (message.type === 'resolved' && cached?.revision === message.revision) {
      window.clearTimeout(deadline);
      worker.terminate();
      activeRun = null;
      finishRun();
      renderReport(cached.report);
      runLogStatus.textContent = 'Current cached assessment';
      appendLog(100, 'Cached commit is current', `${message.revision} · no repository files were downloaded again.`, true);
    }
    if (message.type === 'complete') {
      window.clearTimeout(deadline);
      window.clearTimeout(activeRun.analysisDeadline);
      worker.terminate();
      activeRun = null;
      finishRun();
      renderReport(message.report);
      await cacheReport(message.report);
      runLogStatus.textContent = 'Assessment complete';
      appendLog(100, 'Reduced browser assessment complete', `${message.summary.revision} · ${message.summary.files.toLocaleString()} files · ${(message.summary.bytes / 1048576).toFixed(1)} MiB · 14 checks run · 9 unavailable · ${(message.summary.elapsedMs / 1000).toFixed(1)} seconds`, true);
      reportSection.scrollIntoView({ behavior: 'smooth', block: 'start' });
    }
    if (message.type === 'error') {
      window.clearTimeout(deadline);
      window.clearTimeout(activeRun.analysisDeadline);
      worker.terminate();
      activeRun = null;
      finishRun();
      runLogStatus.textContent = 'Assessment failed';
      showError(message.message, slug.target);
    }
    if (message.type === 'cancelled') {
      window.clearTimeout(deadline);
      window.clearTimeout(activeRun.analysisDeadline);
      worker.terminate();
      activeRun = null;
      finishRun();
      runLogStatus.textContent = 'Cancelled';
      showError('The browser assessment was cancelled. No partial score was produced.', slug.target);
    }
  });
  worker.addEventListener('error', () => {
    if (activeRun?.runId !== runId) return;
    window.clearTimeout(deadline);
    window.clearTimeout(activeRun.analysisDeadline);
    worker.terminate();
    activeRun = null;
    finishRun();
    runLogStatus.textContent = 'Worker failed';
    showError('The browser worker stopped before producing a complete report.', slug.target);
  });
  worker.postMessage({ type: 'start', runId, repository: slug.url });
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  if (form.reportValidity()) void startScan(input.value);
});

cancelButton.addEventListener('click', () => {
  if (!activeRun) return;
  const { worker, deadline, analysisDeadline } = activeRun;
  activeRun = null;
  window.clearTimeout(deadline);
  window.clearTimeout(analysisDeadline);
  worker.terminate();
  finishRun();
  runLogStatus.textContent = 'Cancelled';
  showError('The browser assessment was cancelled. No partial score was produced.', normalizedTarget);
});

document.querySelectorAll('[data-repo]').forEach((button) => {
  button.addEventListener('click', () => {
    input.value = button.dataset.repo;
    input.focus();
  });
});

document.querySelectorAll('[data-filter]').forEach((button) => {
  button.addEventListener('click', () => {
    const filter = button.dataset.filter;
    document.querySelectorAll('[data-filter]').forEach((item) => item.classList.toggle('active', item === button));
    let visible = 0;
    document.querySelectorAll('#checks-body tr').forEach((row) => {
      const show = filter === 'all' || row.dataset.status === filter;
      row.hidden = !show;
      if (show) visible += 1;
    });
    $('#empty-filter').hidden = visible !== 0;
  });
});

document.addEventListener('click', async (event) => {
  const copyButton = event.target.closest('[data-copy]');
  if (copyButton) {
    const command = document.getElementById(copyButton.dataset.copy)?.textContent || '';
    if (command) await navigator.clipboard.writeText(command);
    copyButton.textContent = 'Copied';
    window.setTimeout(() => { copyButton.textContent = copyButton.dataset.copy === 'error-command' ? 'Copy command' : 'Copy'; }, 1200);
  }
  if (event.target.closest('[data-show-cli]')) $('#cli-panel').scrollIntoView({ behavior: 'smooth' });
});

function escapeHtml(value) {
  return String(value).replace(/[&<>"']/g, (character) => ({ '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;' })[character]);
}

function downloadableHtml(report) {
  const commands = cliCommands(report.target);
  const rows = report.checks.map((check) => {
    const status = check.category === 'info' ? 'info' : report.coverage.unavailable.includes(check.id) ? 'cli' : check.status;
    return `<tr><td><b>${escapeHtml(check.id)}</b> ${escapeHtml(check.name)}</td><td>${escapeHtml(STATUS[status][1])}</td><td>${escapeHtml(check.message)}</td><td>${escapeHtml(check.evidence.join(' · ') || '—')}</td></tr>`;
  }).join('');
  return `<!doctype html><html lang="en"><head><meta charset="utf-8"><meta name="viewport" content="width=device-width,initial-scale=1"><meta http-equiv="Content-Security-Policy" content="default-src 'none';style-src 'unsafe-inline'"><title>Slop Meeter browser report · ${escapeHtml(report.target)}</title><style>body{max-width:1100px;margin:40px auto;padding:0 20px;color:#111a2a;background:#f6f2ea;font:15px/1.5 system-ui}section{padding:24px;margin:18px 0;border:1px solid #dedbd1;border-radius:14px;background:#fff}h1{margin-bottom:4px}code{display:block;overflow:auto;padding:12px;background:#142238;color:#fff}table{width:100%;border-collapse:collapse}th,td{padding:9px;border-bottom:1px solid #ddd;text-align:left;vertical-align:top}.badge{display:inline-block;padding:6px 9px;border-radius:99px;background:#fff0d7;font-weight:700}</style></head><body><header><span class="badge">Reduced browser assessment</span><h1>Repository evidence report</h1><p>${escapeHtml(report.target)} · ${escapeHtml(report.revision)}</p></header><section><h2>${Math.round(report.evidence_score)} / 100 browser evidence score</h2><p>${escapeHtml(report.verdict)} · ${Math.round(report.coverage.maximum_confidence)}% maximum confidence</p><p><b>14 of 23 checks run.</b> The verdict applies only to the reduced browser evidence set.</p></section><section><h2>Run the complete assessment</h2><p>Commit history, dependency registry verification and maintenance signals require the CLI.</p><code>${escapeHtml(commands.pipx)}\n${escapeHtml(commands.uv)}\n${escapeHtml(commands.run)}</code></section><section><h2>Evidence checks</h2><table><thead><tr><th>Check</th><th>Status</th><th>Finding</th><th>Evidence</th></tr></thead><tbody>${rows}</tbody></table></section><footer><p>A score is a prompt for scrutiny, not a verdict on the authors.</p></footer></body></html>`;
}

$('#download-report').addEventListener('click', () => {
  if (!renderedReport) return;
  const blob = new Blob([downloadableHtml(renderedReport)], { type: 'text/html;charset=utf-8' });
  const link = document.createElement('a');
  link.href = URL.createObjectURL(blob);
  link.download = `slopmeeter-${renderedReport.target.replace('/', '-')}-${renderedReport.revision.slice(0, 12)}.html`;
  link.click();
  URL.revokeObjectURL(link.href);
});
