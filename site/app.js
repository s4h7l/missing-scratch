const by = id => document.getElementById(id);
const state = { cases: [], items: [], index: 0, selection: null, mode: 'instant', findings: {instant: new Map(), paired: new Map()}, showRay: true };
const pages = [...document.querySelectorAll('[data-page]')];
let currentPage;

function route() {
  const [slug] = location.hash.slice(1).split('/');
  const page = pages.find(item => item.dataset.page === slug) || pages[0];
  for (const item of pages) item.hidden = item !== page;
  for (const link of document.querySelectorAll('nav a')) {
    if (link.hash === '#' + page.dataset.page) link.setAttribute('aria-current', 'page');
    else link.removeAttribute('aria-current');
  }
  if (currentPage && currentPage !== page) window.scrollTo(0, 0);
  currentPage = page;
}

const judgeQuestions = {
  visibility: ['Can the camera see the target in the mirror?',
    'Look for a clear route from the camera to the mirror and from the mirror to the target.'],
  blocker: ['Which obstacle does the reflected path meet first?',
    'Follow the route from the camera toward the mirror first, then toward the target. Choose the first obstacle along that route.'],
  repair: ['Which move makes the target visible again?',
    'Compare the two alternative panels below the base scene. Choose the move that leaves both parts of the reflected path clear.'],
};

function showCase() {
  const item = state.items[state.index];
  if (!item) return;
  const history = state.findings[state.mode];
  const recorded = history.get(item.id);
  const paired = state.items.find(other => other.pair === item.pair && other.id !== item.id);
  const pairedFinding = paired ? history.get(paired.id) : undefined;
  const revealed = recorded !== undefined && (state.mode === 'instant' || pairedFinding !== undefined);
  const answered = state.items.filter(candidate => history.has(candidate.id)).length;
  by('inspection-progress').max = state.items.length;
  by('inspection-progress').value = answered;
  by('inspection-progress-text').textContent = answered + ' of ' + state.items.length + ' answered';
  const onward = by('continue-inspection');
  onward.hidden = recorded === undefined;
  if (recorded !== undefined) {
    onward.textContent = !revealed ? 'Answer the paired scene →' :
      state.items.some(candidate => !history.has(candidate.id)) ? 'Next unanswered →' : 'See validation evidence →';
  }
  if (state.displayedCase !== item.id) {
    state.displayedCase = item.id;
    if (!matchMedia('(prefers-reduced-motion: reduce)').matches) {
      for (const panel of [by('scene').parentElement, by('prompt').parentElement]) {
        panel.getAnimations().forEach(animation => animation.cancel());
        panel.animate([{opacity:.55,transform:'translateY(4px)'},{opacity:1,transform:'none'}],
          {duration:190,easing:'ease-out'});
      }
    }
  }
  state.selection = recorded ?? null;
  state.showRay = true;
  by('scene').src = item.image;
  by('caseId').textContent = 'CASE ' + item.id;
  by('counter').textContent = (state.index + 1) + ' / ' + state.items.length;
  by('prev').disabled = state.index === 0;
  by('next').disabled = state.index === state.items.length - 1;
  by('meta').textContent = 'SCENE ' + (item.id.endsWith('-0') ? 'A' : 'B') + ' · ' + item.difficulty;
  const [question,guide] = judgeQuestions[item.type] ?? [item.question,''];
  by('prompt').textContent = question;
  by('question-guide').textContent = guide;
  by('exact-question').textContent = item.question;
  by('choices').replaceChildren();

  for (const option of item.options) {
    const button = document.createElement('button');
    button.type = 'button';
    const label = document.createElement('span');
    label.textContent = option;
    button.append(label);
    if (revealed && (option === item.answer || option === recorded)) {
      const correct = option === item.answer;
      button.classList.add(correct ? 'answer-correct' : 'answer-wrong');
      const badge = document.createElement('span');
      badge.className = 'answer-badge';
      badge.textContent = correct ? (option === recorded ? '✓ Your answer · Correct' : '✓ Correct answer') : '× Your answer · Incorrect';
      button.append(badge);
    }
    button.setAttribute('aria-pressed', String(state.selection === option));
    button.disabled = recorded !== undefined;
    button.addEventListener('click', () => {
      if (state.mode === 'instant') {
        history.set(item.id, option);
        showCase();
        by('result').focus({preventScroll:true});
        return;
      }
      state.selection = option;
      for (const choice of by('choices').children) choice.setAttribute('aria-pressed', String(choice === button));
      by('record').disabled = false;
    });
    by('choices').append(button);
  }

  by('record').hidden = state.mode === 'instant';
  by('record').disabled = true;
  by('record').textContent = recorded === undefined ? 'Lock prediction' : 'Prediction locked';
  by('pair').disabled = false;
  by('pair').textContent = item.id.endsWith('-0') ? 'Open Scene B ↗' : 'Open Scene A ↗';
  by('toggle-ray').disabled = true;
  by('toggle-ray').textContent = 'Hide ray path';
  by('result').textContent = '';
  by('answer-feedback').hidden = recorded === undefined;
  by('answer-feedback').dataset.outcome = revealed ? (recorded === item.answer ? 'correct' : 'incorrect') : 'pending';
  by('trace').hidden = true;
  by('ray').setAttribute('hidden', '');

  if (recorded === undefined) return;
  if (!revealed) {
    by('result').textContent = 'Prediction locked. Answer the paired scene to reveal both results.';
    return;
  }
  by('toggle-ray').disabled = false;
  const pairSummary = pairedFinding === undefined ? '' :
    recorded === item.answer && pairedFinding === paired.answer ? ' Both predictions in the pair are correct.' :
    ' At least one prediction in the pair is incorrect.';
  by('result').textContent = (recorded === item.answer ? 'Correct. ' : 'Incorrect. Correct answer: ') + item.answer + '.' + pairSummary;
  const trace = item.trace;
  if (item.type === 'repair') {
    by('trace').textContent = item.answer + ' restores the sightline. The dashed ray marks the original path in the base scene.';
  } else if (item.type === 'blocker') {
    by('trace').textContent = 'Obstacle ' + item.answer + ' is the first intersection along the camera → mirror → target path.';
  } else {
    by('trace').textContent = trace.visible ? 'The ray reaches the mirror and continues to the target without hitting an obstacle.' :
      'Obstacle ' + trace.blockers.join(', ') + ' interrupts the sightline. The dashed ray shows where it would travel if clear.';
  }
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
function segmentEntry([x, y], [u, v], [left, top, right, bottom]) {
  let enter = 0;
  let exit = 1;
  for (const [start, delta, min, max] of [[x, u - x, left, right], [y, v - y, top, bottom]]) {
    if (delta === 0) {
      if (start < min || start > max) return null;
      continue;
    }
    const a = (min - start) / delta;
    const b = (max - start) / delta;
    enter = Math.max(enter, Math.min(a, b));
    exit = Math.min(exit, Math.max(a, b));
  }
  return enter <= exit ? enter : null;
}

const defaults = { camera: 135, mirror: 335, block: 225, target: 555 };
let trialActive = false;
const missions = {
  easy: [
    {name:'Dock inspection', layout:{...defaults}, obstacle:'Pallet A', blocks:[],
      question:'Can the mirror camera inspect the marked carton?', choices:['Visible','Hidden']},
    {name:'Dock inspection', layout:{...defaults, block:92}, obstacle:'Pallet A', blocks:[],
      question:'Can the mirror camera inspect the marked carton?', choices:['Visible','Hidden']},
  ],
  medium: [
    {name:'Warehouse aisle', layout:{...defaults}, obstacle:'Pallet A', blocks:[
      {label:'Rack B', box:[415,174,465,218]}, {label:'Rack C', box:[87,241,141,272]}],
      question:'Which obstacle stops the reflected path first?', choices:['Pallet A','Rack B','Rack C']},
    {name:'Warehouse aisle', layout:{...defaults, block:92}, obstacle:'Pallet A', blocks:[
      {label:'Rack B', box:[415,174,465,218]}, {label:'Rack C', box:[87,241,141,272]}],
      question:'Which obstacle stops the reflected path first?', choices:['Pallet A','Rack B','Rack C']},
  ],
  hard: [
    {name:'Inspection cell', layout:{...defaults, mirror:270}, obstacle:'Crate A', blocks:[
      {label:'Rack B', box:[188,256,242,279]}, {label:'Rack C', box:[543,171,592,211]}],
      question:'Which single change restores coverage of the inspection marker?',
      actions:[{label:'Move crate A to staging', block:90}, {label:'Move rack B to staging', remove:'Rack B'},
        {label:'Slide the mirror right', mirror:390}]},
    {name:'Inspection cell', layout:{...defaults, block:92, mirror:230}, obstacle:'Crate A', blocks:[
      {label:'Rack B', box:[188,256,242,279]}, {label:'Rack C', box:[543,171,592,211]}],
      question:'Which single change restores coverage of the inspection marker?',
      actions:[{label:'Move crate A to staging', block:90}, {label:'Move rack B to staging', remove:'Rack B'},
        {label:'Slide the mirror right', mirror:390}]},
  ],
};
let mission = null;
const sites = {
  dock: {name:'Loading dock', shift:0, target:'marked carton', decor:[[508,236,622,283]]},
  warehouse: {name:'Warehouse aisle', shift:18, target:'end-of-aisle label', decor:[[25,110,60,284],[621,149,648,270]]},
  cell: {name:'Inspection cell', shift:-18, target:'inspection marker', decor:[[95,233,155,284],[594,185,636,230]]},
};
let selectedSite = 'dock';


function sceneFor(level, index) {
  const location = sites[selectedSite];
  const template = missions[level][index];
  const shift = location.shift;
  const offset = layout => Object.fromEntries(Object.entries(layout).map(([key,value]) => [key,value + shift]));
  return {...template, name:location.name, layout:offset(template.layout),
    question:template.question.replace(/marked carton|inspection marker/,location.target),
    blocks:template.blocks.map(({label,box}) => ({label,box:box.map((value,axis) => value + (axis % 2 ? 0 : shift))})),
    actions:template.actions?.map(({block,mirror,...action}) =>
      ({...action,...(block === undefined ? {} : {block:block+shift}),...(mirror === undefined ? {} : {mirror:mirror+shift})})),
  };
}

let trialPrediction = null;

let baseline;
let currentBenchOutcome;
const practiceCases = {
  blocked: defaults,
  clear: {...defaults, block: 85},
  miss: {...defaults, mirror: 150, block: 85},
};
const layoutValues = () => Object.fromEntries(Object.keys(defaults).map(key => [key, by(key).valueAsNumber]));
function applyLayout(values) {
  for (const [key,value] of Object.entries(values)) by(key).value = value;
  simulate();
}

const objectNames = {camera:'Camera',mirror:'Mirror',block:'Obstacle',target:'Target'};

function updateComparison(layout, outcome) {
  currentBenchOutcome = outcome;
  if (!baseline || trialActive) return;
  const names = Object.keys(layout).filter(key => layout[key] !== baseline.layout[key])
    .map(key => objectNames[key]);
  by('comparison-readout').hidden = false;
  by('baseline-outcome').textContent = baseline.outcome;
  by('current-outcome').textContent = outcome;
  const change = by('comparison-change');
  change.hidden = false;
  const text = names.length ? names.join(', ') + ' moved. ' + (outcome === baseline.outcome ?
    'Coverage outcome stayed the same.' : 'Coverage outcome changed.') : 'The current layout matches the saved setup.';
  if (change.textContent !== text) change.textContent = text;
  change.dataset.changed = String(outcome !== baseline.outcome);
  by('restore-baseline').disabled = !names.length;
}

function setTrial(active) {
  trialActive = active;
  trialPrediction = null;
  by('trial-actions').hidden = !active;
  by('mission-context').hidden = !active;
  by('layout-controls').hidden = active;
  by('trial-result').hidden = true;
  for (const button of document.querySelectorAll('[data-trial-answer]')) button.disabled = false;
  for (const key of Object.keys(defaults)) by(key).disabled = active;
}
function traceBench(layout, blocks, obstacleName) {
  const {camera, mirror, block, target:targetX} = layout;
  const source = [camera, 95];
  const target = [targetX, 119];
  const plane = 314;
  const reflection = [camera + (targetX - camera) * (plane - source[1]) /
    (2 * plane - source[1] - target[1]), plane];
  const inside = Math.abs(reflection[0] - mirror) <= 89;
  const obstacle = [block, 174, block + 52, 216];
  const obstacles = [{label:obstacleName, box:obstacle}, ...blocks];
  function closest(a, b) {
    let first = null;
    for (const {label, box} of obstacles) {
      const entry = segmentEntry(a, b, box);
      if (entry !== null && (!first || entry < first.entry)) first = {label, entry};
    }
    return first;
  }
  const first = closest(source, reflection);
  const second = inside ? closest(reflection, target) : null;
  return {source, target, mirror, plane, reflection, inside, obstacles, first, second,
    clear:inside && !first && !second};
}

function simulate() {
  const activeMission = trialActive ? mission : null;
  const layout = layoutValues();
  const planned = activeMission?.actions?.filter(action =>
    traceBench({...layout, ...action}, activeMission.blocks.filter(item => item.label !== action.remove),
      activeMission.obstacle).clear);
  const repair = trialPrediction === null ? null : planned?.[0];
  const {source, target, mirror, plane, reflection, inside, obstacles, first, second, clear} =
    traceBench({...layout, ...repair}, (activeMission?.blocks ?? []).filter(item => item.label !== repair?.remove),
      activeMission?.obstacle ?? 'Obstacle');
  const firstHit = first?.entry ?? null;
  const secondHit = second?.entry ?? null;
  const blocked = inside && !clear;
  const awaiting = trialActive && trialPrediction === null;
  const stopAt = (a, b, t) => a.map((value, axis) => value + (b[axis] - value) * t);
  const ray = firstHit !== null ? [source, stopAt(source, reflection, firstHit)] :
    !inside ? [source, reflection] : [source, reflection,
      secondHit === null ? target : stopAt(reflection, target, secondHit)];
  window.opticsBench.draw({source, target, mirror, plane, obstacles, ray, reflection,
    clear: inside && !blocked, awaiting, locked: trialActive, scene:selectedSite, decor:sites[selectedSite].decor});
  by('bench-step').textContent = awaiting ? 'Step 1 of 2 · Predict' : trialActive ? 'Step 2 of 2 · Reveal' : 'Free exploration';
  const outcome = blocked ? 'Obstructed' : !inside ? 'Mirror out of reach' : 'Visible';
  const status = awaiting ? activeMission.question :
    firstHit !== null ? 'Coverage obstructed' : !inside ? 'Mirror misses the sightline' :
    blocked ? 'Coverage obstructed' : 'Target covered';
  if (by('coverage').textContent !== status) by('coverage').textContent = status;
  by('coverage').dataset.outcome = awaiting ? 'predict' : inside && !blocked ? 'clear' : 'blocked';
  by('coverage-detail').textContent = awaiting ? 'The layout is locked. Rotate the view if you like, then pick an answer to reveal the ray.' :
    firstHit !== null ? first.label + ' stops the ray before it reaches the mirror.' :
    !inside ? 'The reflection point lies outside the mirror span.' :
    blocked ? second.label + ' stops the reflected ray before it reaches the target.' :
    'The reflection point falls on the mirror and both path segments are clear.';
  updateComparison(layoutValues(), firstHit !== null ? 'Obstructed' : outcome);
  for (const key of Object.keys(defaults)) by(key + '-value').value = by(key).value;
  if (!trialActive) by('bench-case').value = Object.entries(practiceCases).find(([,values]) =>
    Object.entries(values).every(([key,value]) => by(key).valueAsNumber === value))?.[0] ?? 'custom';
  if (trialPrediction !== null) {
    const expected = repair?.label ?? (activeMission?.choices.includes('Visible') ?
      (clear ? 'Visible' : 'Hidden') : (first ?? second)?.label);
    const result = by('trial-result');
    result.textContent = (trialPrediction === expected ? 'Correct. ' : 'Your prediction: ' + trialPrediction + '. ') +
      'Verified answer: ' + expected + '.' + (repair ? ' The scene shows that repair.' : '');
    by('trial-actions').hidden = true;
    result.hidden = false;
  }
}

function bindCases() {
  for (const button of document.querySelectorAll('[data-feedback-mode]')) {
    button.addEventListener('click', () => {
      state.mode = button.dataset.feedbackMode;
      for (const mode of document.querySelectorAll('[data-feedback-mode]')) {
        mode.setAttribute('aria-pressed',String(mode === button));
      }
      by('feedback-instructions').textContent = state.mode === 'instant' ?
        'Choose one answer. The correct option and ray path appear immediately.' :
        'Lock a prediction for each scene. Feedback appears after both are recorded.';
      showCase();
    });
  }
  by('kind').addEventListener('change', () => {
    state.items = state.cases.filter(item => by('kind').value === 'all' || by('kind').value === item.type);
    state.index = 0;
    showCase();
  });
  by('prev').addEventListener('click', () => move(-1));
  by('next').addEventListener('click', () => move(1));
  by('continue-inspection').addEventListener('click', () => {
    const history = state.findings[state.mode];
    const current = state.items[state.index];
    const other = state.items.findIndex(caseItem => caseItem.pair === current.pair && caseItem.id !== current.id);
    if (state.mode === 'paired' && other >= 0 && !history.has(state.items[other].id)) {
      state.index = other;
    } else {
      const remaining = state.items.findIndex((item,index) => index > state.index && !history.has(item.id));
      const next = remaining >= 0 ? remaining : state.items.findIndex(item => !history.has(item.id));
      if (next < 0) { location.hash = '#evidence'; return; }
      state.index = next;
    }
    showCase();
    by('prompt').focus({preventScroll:true});
  });
  by('record').addEventListener('click', () => {
    if (state.selection === null) return;
    state.findings[state.mode].set(state.items[state.index].id, state.selection);
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
function openSimulation() {
  const [page, site, level, number] = location.hash.slice(1).split('/');
  if (page !== 'simulator') return;
  const index = Number(number) - 1;
  const isCase = Object.hasOwn(sites, site) && Object.hasOwn(missions, level) &&
    Number.isInteger(index) && index >= 0 && index < missions[level].length;
  const isSandbox = site === 'sandbox';
  by('sim-gallery').hidden = isCase || isSandbox;
  by('sim-workspace').hidden = !isCase && !isSandbox;
  if (!isCase && !isSandbox) return;
  selectedSite = isCase ? site : 'dock';
  by('bench-site-name').textContent = isCase ? sites[site].name : 'Free exploration';
  mission = isCase ? sceneFor(level, index) : null;
  setTrial(isCase);
  window.opticsBench.framePlan();
  if (!isCase) {
    applyLayout(defaults);
    return;
  }
  by('mission-context').textContent = mission.name + ' · ' + level + ' · Case ' + number;
  const answers = by('trial-actions');
  answers.replaceChildren();
  for (const choice of mission.choices ?? mission.actions.map(action => action.label)) {
    const button = document.createElement('button');
    button.type = 'button';
    button.textContent = choice;
    button.dataset.trialAnswer = choice;
    button.addEventListener('click', () => {
      trialPrediction = choice;
      simulate();
      window.opticsBench.revealOrbit();
      by('coverage').focus({preventScroll:true});
    });
    answers.append(button);
  }
  applyLayout(mission.layout);
  window.scrollTo(0, 0);
  by('coverage').focus({preventScroll:true});
}

function buildSimulationGallery() {
  const titles = {easy:'Check visibility', medium:'Find the first obstruction', hard:'Restore coverage'};
  for (const [site, location] of Object.entries(sites)) {
    const group = document.createElement('section');
    const heading = document.createElement('h2');
    heading.textContent = location.name;
    const cards = document.createElement('div');
    cards.className = 'sim-post-grid';
    selectedSite = site;
    for (const [level, cases] of Object.entries(missions)) {
      for (const index of cases.keys()) {
        const scenario = sceneFor(level, index);
        const trace = traceBench(scenario.layout, scenario.blocks, scenario.obstacle);
        const link = document.createElement('a');
        link.className = 'sim-post';
        link.href = '#simulator/' + site + '/' + level + '/' + (index + 1);
        link.append(window.opticsBench.preview(trace, site, location.decor));
        const caption = document.createElement('div');
        const tag = document.createElement('span');
        tag.textContent = level + ' · Case ' + (index + 1);
        const title = document.createElement('strong');
        title.textContent = titles[level];
        caption.append(tag, title);
        link.append(caption);
        cards.append(link);
      }
    }
    group.append(heading,cards);
    by('sim-posts').append(group);
  }
  selectedSite = 'dock';
}
by('reset').addEventListener('click', () => {
  setTrial(false);
  applyLayout(defaults);
});
by('save-baseline').addEventListener('click', () => {
  baseline = {layout:layoutValues(), outcome:currentBenchOutcome};
  by('save-baseline').textContent = 'Replace saved setup';
  updateComparison(baseline.layout, baseline.outcome);
});
by('restore-baseline').addEventListener('click', () => {
  if (!baseline) return;
  applyLayout(baseline.layout);
  by('save-baseline').focus({preventScroll:true});
});
by('bench-case').addEventListener('change', event => {
  const values = practiceCases[event.target.value];
  if (values) applyLayout(values);
});
window.opticsBench.bind(simulate);
buildSimulationGallery();
openSimulation();
window.addEventListener('hashchange', openSimulation);
simulate();

fetch('cases.json').then(response => {
  if (!response.ok) throw new Error('Dataset unavailable');
  return response.text();
}).then(raw => {
  const { cases } = JSON.parse(raw);
  state.cases = state.items = cases;
  by('scene-count').textContent = cases.length;
  by('evidence-count').textContent = cases.length;
  const digest = manifestDigest(raw);
  void loadAudit(digest);
  void loadReproduction(digest, cases.length);
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
  void loadReports(digest);
}).catch(() => {
  by('prompt').textContent = 'The synthetic dataset could not be loaded.';
});

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

const logos = { gemini: 'gemini', openai: 'openai', openrouter: 'openrouter', anthropic: 'claude', groq: 'groq' };
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
function appendPairEvidence(details, pairs) {
  if (!pairs?.answer_flips) return;
  const summary = document.createElement('p');
  summary.className = 'detail';
  summary.textContent = 'On ' + pairs.answer_flips + ' pairs where the reference answer changed, ' +
    pairs.exactly_one_correct + ' had exactly one correct response and ' +
    pairs.repeated_answer + ' received the same valid response twice.';
  details.append(summary);
  if (!pairs.example) return;
  const evidence = document.createElement('div');
  evidence.className = 'report-pair';
  const title = document.createElement('h3');
  title.textContent = pairs.example.failure + ' · ' + 'Matched pair ' + pairs.example.pair;
  const consequence = document.createElement('p');
  consequence.className = 'detail';
  consequence.textContent = pairs.example.consequence;
  evidence.append(title, consequence);
  const scenes = document.createElement('div');
  scenes.className = 'report-pair-scenes';
  for (const member of pairs.example.cases) {
    const scene = state.cases.find(item => item.id === member.case);
    if (!scene) continue;
    const figure = document.createElement('figure');
    const link = document.createElement('a');
    link.href = scene.image;
    const image = document.createElement('img');
    image.loading = 'lazy';
    image.alt = 'Open the full benchmark diagram for ' + scene.id;
    image.src = scene.image;
    link.append(image);
    const caption = document.createElement('figcaption');
    caption.textContent = scene.id + ' · Model: ' + member.predicted + ' · Expected: ' + member.expected;
    figure.append(link, caption);
    scenes.append(figure);
  }
  evidence.append(scenes);
  details.append(evidence);
}
async function manifestDigest(raw) {
  if (!globalThis.crypto?.subtle) return null;
  const hash = await crypto.subtle.digest('SHA-256', new TextEncoder().encode(raw));
  return Array.from(new Uint8Array(hash), byte => byte.toString(16).padStart(2, '0')).join('');
}
async function loadReports(digest) {
  try {
    const response = await fetch('model-reports.json');
    if (!response.ok) throw new Error('Report file unavailable');
    const report = await response.json();
    if (report.reports.length) {
      const hex = await digest;
      if (!hex || hex !== report.dataset) throw new Error('Reports belong to another dataset');
    }
    const status = report.reports.length ? report.reports.length + ' recorded model configurations on this dataset.' : 'Model evaluation pending. Scores appear here after the frozen dataset is run.';
    by('report-status').textContent = status;
    by('score-table').hidden = !report.reports.length;
    for (const run of report.reports) {
      const vision = run.modes.vision?.scores;
      const baseline = run.modes['question-only']?.scores;
      modelRow(run.model, brandFor(run), [scoreText(vision?.overall), scoreText(baseline?.overall),
        scoreText(vision?.both_pair_members), scoreText(baseline?.both_pair_members)]);
      const details = document.createElement('details');
      const summary = document.createElement('summary');
      summary.textContent = run.model + ' · ' + run.provider + ' · Score breakdown and examples';
      details.append(summary);
      for (const mode of ['vision','question-only']) {
        const scores = run.modes[mode]?.scores;
        if (!scores) continue;
        const p = document.createElement('p');
        p.className = 'detail';
        p.textContent = mode + ' · ' + ['visibility','blocker','repair','both_pair_members'].map(key =>
          (key === 'both_pair_members' ? 'Pairs' : key) + ' ' + scoreText(scores[key])).join(' · ');
        details.append(p);
        const difficulty = document.createElement('ul');
        difficulty.className = 'detail report-difficulty';
        for (const task of ['visibility', 'blocker', 'repair']) {
          const item = document.createElement('li');
          item.textContent = (task === 'blocker' ? 'obstruction' : task) + ' · ' +
            ['easy', 'medium', 'hard'].map(level => level + ' ' + scoreText(scores[task + '/' + level])).join(' · ');
          difficulty.append(item);
        }
        details.append(difficulty);
        if (mode === 'vision') appendPairEvidence(details, run.modes[mode].pairs);
        for (const finding of run.modes[mode].failures ?? []) {
          const item = document.createElement('p');
          item.className = 'detail';
          const examples = finding.examples.map(example =>
            example.case + ' (' + (example.predicted ?? 'invalid choice') + ' → expected ' + example.expected + ')').join(', ');
          item.textContent = finding.label + ': ' + finding.count + '. ' + finding.consequence + ' Cases: ' + examples;
          details.append(item);
        }
      }
      by('report-details').append(details);
    }
  } catch {
    by('report-status').textContent = 'No reports could be verified for this dataset.';
  } finally {
    by('report-loading').hidden = true;
  }
}

async function loadReproduction(digest, imageCount) {
  try {
    const response = await fetch('reproduction.json');
    if (!response.ok) return;
    const record = await response.json();
    const hex = await digest;
    if (!hex || hex !== record.manifest_sha256 || record.images_byte_identical !== imageCount) return;
    by('reproduction-images').textContent = record.images_byte_identical;
    by('reproduction-proof').hidden = false;
  } catch {
    by('reproduction-proof').hidden = true;
  }
}

async function loadAudit(digest) {
  const display = by('shortcut-audit');
  try {
    const response = await fetch('validity-audit.json');
    if (!response.ok) throw new Error('Audit unavailable');
    const audit = await response.json();
    const hex = await digest;
    if (!hex || audit.dataset !== hex) throw new Error('Audit belongs to another dataset');
    display.textContent = 'Across ' + audit.total + ' visibility cases, the best horizontal interval, vertical interval, and exact coordinate lookup each got ' +
      [audit.horizontal_interval_correct, audit.vertical_interval_correct, audit.coordinate_lookup_correct].join(', ') + ' answers right, respectively.' +
      (audit.held_out ? ' With whole layout groups held out, the same three methods scored ' +
        [audit.held_out.horizontal, audit.held_out.vertical, audit.held_out.coordinate_lookup].join(', ') +
        ' out of ' + audit.held_out.total + ' across ' + audit.held_out.groups + ' groups.' : '');
    for (const [name, result] of Object.entries(audit.other_tasks ?? {})) {
      const row = document.createElement('p');
      row.textContent = (name === 'blocker' ? 'Obstruction' : 'Repair') + ': ' +
        Object.entries(result.correct).map(([rule,correct]) =>
          rule.replaceAll('_',' ') + ' ' + correct + '/' + result.total).join(' · ') +
        ' on held-out pairs.';
      by('shortcut-audit').after(row);
    }
  } catch {
    display.textContent = 'No shortcut diagnostic could be verified for this dataset.';
  }
}
