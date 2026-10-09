const form = document.querySelector('#scan-form');
const input = document.querySelector('#repo-url');
const scanButton = document.querySelector('#scan-button');
const progress = document.querySelector('#scan-progress');
const progressBar = document.querySelector('#progress-bar');
const progressValue = document.querySelector('#progress-value');
const progressTitle = document.querySelector('#progress-title');
const progressStage = document.querySelector('#progress-stage');
const runLog = document.querySelector('#run-log');
const runLogStatus = document.querySelector('#run-log-status');
const runLogEntries = document.querySelector('#run-log-entries');
const report = document.querySelector('#sample-report');
const target = document.querySelector('#report-target');
const sampleReportLink = document.querySelector('#sample-report-link');

const stages = [
  [18, 'Preparing representative preview', 'No repository data was fetched or analyzed.'],
  [43, 'Simulating history and structure checks', 'Demonstrating how commit and composition checks would appear.'],
  [71, 'Simulating evidence checks', 'Demonstrating tests, claims and dependency findings.'],
  [92, 'Simulating maintenance checks', 'Demonstrating how maintenance signals would appear.'],
  [100, 'Rendering representative report', 'Scores and findings are fixed examples in this preview.'],
];

function shortTarget(value) {
  return value.replace(/^https?:\/\/(www\.)?/, '').replace(/\/$/, '') || 'github.com/example/some-tool';
}

function updateStage([percent, title, detail]) {
  progressBar.style.width = `${percent}%`;
  progressValue.textContent = `${percent}%`;
  progressTitle.textContent = title;
  progressStage.textContent = detail;
}

function appendLogEntry([percent, title, detail]) {
  const item = document.createElement('li');
  const marker = document.createElement('span');
  const message = document.createElement('p');
  const heading = document.createElement('strong');
  const description = document.createElement('small');

  marker.textContent = `${percent}%`;
  heading.textContent = title;
  description.textContent = detail;
  message.append(heading, description);
  item.append(marker, message);
  runLogEntries.append(item);
}

function startRunLog() {
  runLogEntries.replaceChildren();
  runLog.hidden = false;
  runLog.open = false;
  runLogStatus.textContent = 'Preview running';
  appendLogEntry(stages[0]);
}

form.addEventListener('submit', (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;

  scanButton.disabled = true;
  sampleReportLink.hidden = true;
    scanButton.querySelector('span').textContent = 'Preparing preview…';
  progress.hidden = false;
  updateStage(stages[0]);
  startRunLog();

  let index = 1;
  const timer = window.setInterval(() => {
    updateStage(stages[index]);
    appendLogEntry(stages[index]);
    index += 1;
    if (index === stages.length) {
      window.clearInterval(timer);
      window.setTimeout(() => {
        target.replaceChildren();
        const icon = document.createElement('span');
        icon.setAttribute('aria-hidden', 'true');
        icon.textContent = '</>';
        target.append(icon, ` ${shortTarget(input.value)}`);
        progress.hidden = true;
        scanButton.disabled = false;
        scanButton.querySelector('span').textContent = 'Preview analysis';
        runLogStatus.textContent = 'Preview complete';
        const completion = document.createElement('li');
        completion.className = 'complete';
        const marker = document.createElement('span');
        marker.textContent = '✓';
        const message = document.createElement('p');
        const heading = document.createElement('strong');
        heading.textContent = 'Representative report displayed — results are not derived from the submitted repository.';
        const description = document.createElement('small');
        description.textContent = 'Install the CLI for a real analysis; live website analysis is not connected yet.';
        message.append(heading, description);
        completion.append(marker, message);
        runLogEntries.append(completion);
        report.classList.remove('flash');
        window.requestAnimationFrame(() => report.classList.add('flash'));
        report.scrollIntoView({ behavior: 'smooth', block: 'start' });
      }, 280);
    }
  }, 380);
});

document.querySelectorAll('[data-repo]').forEach((button) => {
  button.addEventListener('click', () => {
    input.value = button.dataset.repo;
    input.focus();
  });
});

const filterButtons = [...document.querySelectorAll('[data-filter]')];
const rows = [...document.querySelectorAll('tbody tr[data-status]')];
const emptyFilter = document.querySelector('#empty-filter');

filterButtons.forEach((button) => {
  button.addEventListener('click', () => {
    const filter = button.dataset.filter;
    filterButtons.forEach((item) => item.classList.toggle('active', item === button));
    let visible = 0;
    rows.forEach((row) => {
      const show = filter === 'all' || row.dataset.status === filter;
      row.hidden = !show;
      visible += show ? 1 : 0;
    });
    emptyFilter.hidden = visible !== 0;
  });
});
