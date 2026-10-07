const form = document.querySelector('#scan-form');
const input = document.querySelector('#repo-url');
const scanButton = document.querySelector('#scan-button');
const progress = document.querySelector('#scan-progress');
const progressBar = document.querySelector('#progress-bar');
const progressValue = document.querySelector('#progress-value');
const progressTitle = document.querySelector('#progress-title');
const progressStage = document.querySelector('#progress-stage');
const report = document.querySelector('#sample-report');
const target = document.querySelector('#report-target');
const sampleReportLink = document.querySelector('#sample-report-link');

const stages = [
  [18, 'Fetching repository metadata', 'Nothing from the target repository is being executed.'],
  [43, 'Reading history and project structure', 'Commit depth, time spread and repository composition.'],
  [71, 'Checking tests, claims and dependencies', 'Static inspection only—no imports, hooks or installers.'],
  [92, 'Reviewing maintenance signals', 'Online evidence is bounded by request and time limits.'],
  [100, 'Building the evidence report', 'Every finding includes a reason and inspectable evidence.'],
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

form.addEventListener('submit', (event) => {
  event.preventDefault();
  if (!form.reportValidity()) return;

  scanButton.disabled = true;
  sampleReportLink.hidden = true;
    scanButton.querySelector('span').textContent = 'Preparing preview…';
  progress.hidden = false;
  updateStage(stages[0]);

  let index = 1;
  const timer = window.setInterval(() => {
    updateStage(stages[index]);
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
