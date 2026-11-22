const by = id => document.getElementById(id);
const state = { cases: [], items: [], index: 0, selection: null, findings: new Map(), showRay: true };
const pages = [...document.querySelectorAll('[data-page]')];
let currentPage;

function route() {
  const slug = location.hash.slice(1);
  const page = pages.find(item => item.dataset.page === slug) || pages[0];
  for (const item of pages) item.hidden = item !== page;
  for (const link of document.querySelectorAll('nav a')) {
    if (link.hash === '#' + page.dataset.page) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  }
  if (currentPage && currentPage !== page) window.scrollTo(0, 0);
  currentPage = page;
}

function showCase() {
  const item = state.items[state.index];
  if (!item) return;
  const recorded = state.findings.get(item.id);
  state.selection = recorded ?? null;
  state.showRay = true;
  by('scene').src = item.image;
  by('caseId').textContent = 'CASE ' + item.id;
  by('counter').textContent = (state.index + 1) + ' / ' + state.items.length;
  by('prev').disabled = state.index === 0;
  by('next').disabled = state.index === state.items.length - 1;
  by('meta').textContent = 'SCENE ' + (item.id.endsWith('-0') ? 'A' : 'B') + ' · ' + item.difficulty;
  by('prompt').textContent = item.question;
  by('choices').replaceChildren();

  for (const option of item.options) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = option;
    button.setAttribute('aria-pressed', String(state.selection === option));
    button.disabled = recorded !== undefined;
    button.addEventListener('click', () => {
      state.selection = option;
      for (const choice of by('choices').children) choice.setAttribute('aria-pressed', String(choice === button));
      by('record').disabled = false;
    });
    by('choices').append(button);
  }

  by('record').disabled = true;
  by('record').textContent = recorded === undefined ? 'Record finding' : 'Finding recorded';
  by('pair').disabled = false;
  by('toggle-ray').disabled = true;
  by('toggle-ray').textContent = 'Hide ray path';
  by('result').textContent = '';
  by('trace').hidden = true;
  by('ray').setAttribute('hidden', '');

  if (recorded === undefined) return;
  const paired = state.cases.find(other => other.pair === item.pair && other.id !== item.id);
  const pairedFinding = state.findings.get(paired.id);
  if (pairedFinding === undefined) {
    by('result').textContent = 'Finding recorded. Inspect the paired scene to unlock the geometry.';
    return;
  }
  by('toggle-ray').disabled = false;
  const pairSummary = recorded === item.answer && pairedFinding === paired.answer ?
    ' Both paired findings matched.' : ' At least one paired finding differed.';
  by('result').textContent = (recorded === item.answer ? 'Finding matches. ' : 'Reference finding: ') + item.answer + '.' + pairSummary;
  const trace = item.trace;
  by('trace').textContent = trace.blockers.length ?
    'Base path intersects ' + trace.blockers.join(', ') + '. The overlay shows the ideal path before obstruction.' :
    'The reflected base path is clear.';
  by('trace').hidden = false;
  by('ray').setAttribute('viewBox', '0 0 680 ' + (item.type === 'repair' ? 744 : 248));
  by('ray').firstElementChild.setAttribute('points',
    [trace.camera, trace.bounce, trace.target].map(([x, y]) => (40 + x * 6) + ',' + (212 - y * 6)).join(' '));
  by('ray').removeAttribute('hidden');
}

function move(step) {
  const next = state.index + step;
  if (next < 0 || next >= state.items.length) return;
  state.index = next;
  showCase();
}

// Clip a segment against the obstacle rectangle in the planner coordinate space.
function intersects([x, y], [u, v], [left, top, right, bottom]) {
  let enter = 0;
  let exit = 1;
  for (const [start, delta, min, max] of [[x, u - x, left, right], [y, v - y, top, bottom]]) {
    if (delta === 0) {
      if (start < min || start > max) return false;
      continue;
    }
    const a = (min - start) / delta;
    const b = (max - start) / delta;
    enter = Math.max(enter, Math.min(a, b));
    exit = Math.min(exit, Math.max(a, b));
  }
  return enter <= exit;
}

const defaults = { camera: 135, mirror: 335, block: 225 };
function simulate() {
  const camera = by('camera').valueAsNumber;
  const mirror = by('mirror').valueAsNumber;
  const block = by('block').valueAsNumber;
  const source = [camera, 95];
  const target = [555, 119];
  const plane = 314;
  const reflection = [camera + (target[0] - camera) * (plane - source[1]) / (2 * plane - source[1] - target[1]), plane];
  const inside = Math.abs(reflection[0] - mirror) <= 89;
  const obstacle = [block, 174, block + 52, 216];
  const blocked = inside && (intersects(source, reflection, obstacle) || intersects(reflection, target, obstacle));
  by('sim-camera').setAttribute('cx', camera);
  by('sim-camera-label').setAttribute('x', camera - 24);
  by('sim-mirror').setAttribute('x1', mirror - 89);
  by('sim-mirror').setAttribute('x2', mirror + 89);
  by('sim-mirror-label').setAttribute('x', mirror - 23);
  by('sim-block').setAttribute('x', block);
  by('sim-block-label').setAttribute('x', block - 2);
  by('sim-ray').setAttribute('points', [source, reflection, target].map(point => point.join(',')).join(' '));
  by('sim-ray').setAttribute('stroke', inside && !blocked ? '#85f1df' : '#f7aa70');
  const status = !inside ? 'Mirror misses the sightline' : blocked ? 'Coverage obstructed' : 'Target covered';
  if (by('coverage').textContent !== status) by('coverage').textContent = status;
  by('coverage-detail').textContent = !inside ? 'The reflection point lies outside the mirror span.' :
    blocked ? 'The ideal reflected path crosses the obstacle.' : 'The reflection point falls on the mirror and both path segments are clear.';
  for (const key of Object.keys(defaults)) by(key + '-value').value = by(key).value;
}

function bindCases() {
  by('kind').addEventListener('change', () => {
    state.items = state.cases.filter(item => by('kind').value === 'all' || by('kind').value === item.type);
    state.index = 0;
    showCase();
  });
  by('prev').addEventListener('click', () => move(-1));
  by('next').addEventListener('click', () => move(1));
  by('record').addEventListener('click', () => {
    if (state.selection === null) return;
    state.findings.set(state.items[state.index].id, state.selection);
    showCase();
  });
  by('pair').addEventListener('click', () => {
    const active = state.items[state.index];
    const index = state.items.findIndex(item => item.pair === active.pair && item.id !== active.id);
    if (index >= 0) {
      state.index = index;
      showCase();
    }
  });
  by('toggle-ray').addEventListener('click', () => {
    state.showRay = !state.showRay;
    by('ray').toggleAttribute('hidden', !state.showRay);
    by('toggle-ray').textContent = state.showRay ? 'Hide ray path' : 'Show ray path';
  });
}

window.addEventListener('hashchange', route);
route();
for (const key of Object.keys(defaults)) by(key).addEventListener('input', simulate);
by('reset').addEventListener('click', () => {
  for (const [key, value] of Object.entries(defaults)) by(key).value = value;
  simulate();
});
simulate();

fetch('cases.json').then(response => {
  if (!response.ok) throw new Error('Dataset unavailable');
  return response.text();
}).then(raw => {
  const { cases } = JSON.parse(raw);
  state.cases = state.items = cases;
  by('scene-count').textContent = cases.length;
  by('pair-count').textContent = new Set(cases.map(item => item.pair)).size;
  by('landing-scenes').textContent = by('scene-count').textContent;
  by('landing-pairs').textContent = by('pair-count').textContent;
  const first = cases.find(item => item.type === 'visibility');
  const pair = cases.filter(item => item.pair === first.pair);
  for (const [i, id] of ['a', 'b'].entries()) {
    by('landing-' + id).src = pair[i].image;
    by('landing-' + id + '-caption').textContent = 'Scene ' + id.toUpperCase() + ' · ' + pair[i].answer;
  }
  bindCases();
  showCase();
  void loadReports(raw);
}).catch(() => { by('prompt').textContent = 'The synthetic dataset could not be loaded.'; });

const heroImage = document.querySelector('.hero-picture img');
const revealHero = () => heroImage.classList.add('ready');
if (heroImage.complete) revealHero();
else {
  heroImage.addEventListener('load', revealHero, { once: true });
  heroImage.addEventListener('error', () => heroImage.hidden = true, { once: true });
}
for (const button of document.querySelectorAll('[data-scroll]')) {
  button.addEventListener('click', () => by(button.dataset.scroll).scrollIntoView({
    behavior: matchMedia('(prefers-reduced-motion: reduce)').matches ? 'instant' : 'smooth'
  }));
}
if ('IntersectionObserver' in window) {
  const reveal = new IntersectionObserver(entries => {
    for (const entry of entries) {
      if (!entry.isIntersecting) continue;
      entry.target.classList.add('seen');
      reveal.unobserve(entry.target);
    }
  }, { rootMargin: '0px 0px -6% 0px' });
  for (const section of document.querySelectorAll('.reveal')) {
    section.classList.add('reveal-ready');
    reveal.observe(section);
  }
}
function progress() {
  const range = document.documentElement.scrollHeight - innerHeight;
  document.documentElement.style.setProperty('--scroll', (range > 0 ? Math.min(100, scrollY * 100 / range) : 0) + '%');
}
addEventListener('scroll', progress, { passive: true });
addEventListener('resize', progress);
addEventListener('hashchange', progress);
progress();

const logos = { gemini: 'gemini', openai: 'openai', openrouter: 'openrouter' };
const lineup = ['Gemini', 'Claude', 'Qwen-VL', 'OpenAI'];
function brandFor(run) {
  const id = run.model.toLowerCase();
  if (id.includes('claude')) return 'claude';
  if (id.includes('qwen')) return 'qwen';
  if (id.includes('gemini')) return 'gemini';
  if (id.startsWith('openai/')) return 'openai';
  return logos[run.provider];
}
function scoreText(score) {
  return Number.isFinite(score?.accuracy) ? (score.accuracy * 100).toFixed(1) + '% · ' + score.correct + '/' + score.total : '—';
}
function modelRow(name, brand, values) {
  const row = by('model-rows').insertRow();
  const title = document.createElement('th');
  title.scope = 'row';
  const logo = document.createElement('img');
  logo.alt = '';
  logo.className = 'model-logo';
  logo.src = 'logo-' + brand + '.svg';
  title.append(logo, document.createTextNode(name));
  row.append(title);
  for (const value of values) row.insertCell().textContent = value;
}
async function loadReports(raw) {
  try {
    const response = await fetch('model-reports.json');
    if (!response.ok) throw new Error('Report file unavailable');
    const report = await response.json();
    if (report.reports.length) {
      const digest = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(raw));
      const hex = Array.from(new Uint8Array(digest), byte => byte.toString(16).padStart(2, '0')).join('');
      if (hex !== report.dataset) throw new Error('Reports belong to another dataset');
    }
    const status = report.reports.length ? report.reports.length + ' recorded model configurations on this dataset.' : 'Model evaluation pending. Scores appear here after the frozen dataset is run.';
    by('report-status').textContent = by('landing-report-status').textContent = status;
    if (!report.reports.length) {
      for (const [i, name] of lineup.entries()) modelRow(name, ['gemini','claude','qwen','openai'][i], ['Pending','Pending','Pending']);
    }
    for (const run of report.reports) {
      const vision = run.modes.vision?.scores;
      const baseline = run.modes['question-only']?.scores;
      modelRow(run.model, brandFor(run), [scoreText(vision?.overall), scoreText(baseline?.overall), scoreText(vision?.both_pair_members)]);
      const details = document.createElement('details');
      const summary = document.createElement('summary');
      summary.textContent = run.model + ' · Task breakdown';
      details.append(summary);
      for (const mode of ['vision','question-only']) {
        const scores = run.modes[mode]?.scores;
        if (!scores) continue;
        const p = document.createElement('p');
        p.className = 'detail';
        p.textContent = mode + ' · ' + ['visibility','blocker','repair','both_pair_members'].map(key =>
          (key === 'both_pair_members' ? 'Pairs' : key) + ' ' + scoreText(scores[key])).join(' · ');
        details.append(p);
      }
      by('report-details').append(details);
    }
  } catch {
    by('report-status').textContent = by('landing-report-status').textContent = 'No reports could be verified for this dataset.';
  } finally {
    by('report-loading').hidden = true;
  }
}
