(() => {
  'use strict';
  const el = id => document.getElementById(id);
  const area = el('live-cases'), generate = el('live-generate');
  let cases = [], busy = false;
  const node = (tag, text) => {
    const n = document.createElement(tag);
    if (text !== undefined) n.textContent = text;
    return n;
  };
  async function api(path, body) {
    const res = await fetch(path, {method: body === undefined ? 'GET' : 'POST', credentials:'same-origin',
      headers: body === undefined ? {} : {'Content-Type':'application/json'},
      body: body === undefined ? undefined : JSON.stringify(body), cache:'no-store'});
    if (!res.ok) {
      const problem = await res.json().catch(() => ({}));
      throw new Error(typeof problem.detail === 'string' ? problem.detail : 'Request failed (' + res.status + ').');
    }
    return res.json();
  }
  function button(label, action) {
    const b = node('button',label);
    b.type = 'button'; b.disabled = busy;
    b.addEventListener('click', () => run(action));
    return b;
  }
  function draw() {
    generate.disabled = busy;
    area.replaceChildren();
    const locked = cases.length > 0 && cases.every(c => c.prediction);
    for (const [i,c] of cases.entries()) {
      const box = node('article'), heading = node('h2','Scene ' + (i+1));
      const img = node('img'); img.src = c.result?.evidence.reveal_image_url || c.image_url;
      img.alt = c.result ? 'Verified reflection diagram' : c.question;
      img.className = 'live-diagram'; box.append(heading,node('p',c.question),img);
      const choices = node('div'); choices.className = 'tool-row';
      if (!c.prediction) {
        for (const option of c.options) choices.append(button(option,async () => {
          await api('/api/tasks/'+c.task_id+'/predict',{prediction:option});
          c.prediction=option;
          el('live-status').textContent=cases.every(x=>x.prediction) ? 'Predictions locked. Reveal the answers below.' : 'Prediction locked. Answer the other scene.';
        }));
      } else {
        box.append(node('p','Your prediction: '+c.prediction));
        if (c.result) box.append(node('strong',(c.result.correct?'Correct. ':'Incorrect. ')+'Verified answer: '+c.result.ground_truth));
        else if (locked) choices.append(button('Reveal answer',async () => {
          c.result=await api('/api/tasks/'+c.task_id+'/reveal');
          el('live-status').textContent='Answer revealed.';
        }));
      }
      box.append(choices); area.append(box);
    }
  }
  async function run(action) {
    if (busy) return;
    busy=true; draw();
    try {await action();} catch(e){el('live-status').textContent=e.message;}
    finally {busy=false;draw();}
  }
  generate.addEventListener('click',()=>run(async ()=>{
    el('live-status').textContent='Generating…';
    const paired=el('live-pair').checked;
    const data=await api('/api/tasks/'+(paired?'generate-pair':'generate'),{kind:el('live-kind').value});
    cases=paired?data.tasks:[data];
    el('live-status').textContent='Choose a prediction to lock it.';
  }));
  el('live-reports').addEventListener('toggle',async ()=>{
    if (!el('live-reports').open) return;
    const out=el('live-summary');
    try {
      const [report,validation]=await Promise.all([api('/api/benchmark/results'),api('/api/v1/validation/status')]);
      out.replaceChildren(node('p',report.runs.length+' completed V3 runs · '+validation.blind_review.sealed_sheets+' sealed reviewer sheets · '+validation.physical.agreeing_complete_cases+' agreeing camera cases.'));
      for (const r of report.runs) out.append(node('p',r.model+' · '+r.source+' · '+r.mode+' · '+r.correct+'/'+r.assigned+' tasks · '+r.strict_pairs_correct+'/'+r.pairs+' pairs'));
    } catch(e) {out.textContent=e.message;}
  });
})();