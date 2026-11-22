(() => {
  const canvas = document.getElementById('motion-canvas');
  const ctx = canvas.getContext('2d');
  const scrub = document.getElementById('motion-scrub');
  const play = document.getElementById('motion-play');
  const reset = document.getElementById('motion-reset');
  const outcome = document.getElementById('motion-outcome');
  const reduced = matchMedia('(prefers-reduced-motion: reduce)');
  let endpoints;
  let progress = 0;
  let frame = null;
  let started = null;

  function entry(a, b, box) {
    let enter = 0;
    let exit = 1;
    for (let axis = 0; axis < 2; axis++) {
      const d = b[axis] - a[axis];
      if (!d) {
        if (a[axis] < box[axis] || a[axis] > box[axis + 2]) return Infinity;
        continue;
      }
      const first = (box[axis] - a[axis]) / d;
      const last = (box[axis + 2] - a[axis]) / d;
      enter = Math.max(enter, Math.min(first, last));
      exit = Math.min(exit, Math.max(first, last));
    }
    return enter <= exit ? enter : Infinity;
  }

  const mix = (a, b, t) => a + (b - a) * t;
  const point = ([x, y]) => [48 + x * 7, 249 - y * 7];
  function line(a, b, color, width, dashed = false) {
    ctx.setLineDash(dashed ? [7, 7] : []);
    ctx.strokeStyle = color;
    ctx.lineWidth = width;
    ctx.beginPath();
    ctx.moveTo(...point(a));
    ctx.lineTo(...point(b));
    ctx.stroke();
    ctx.setLineDash([]);
  }

  function marker(p, label, color) {
    const [x,y] = point(p);
    ctx.fillStyle = color;
    ctx.beginPath();
    ctx.arc(x, y, 6, 0, Math.PI * 2);
    ctx.fill();
    ctx.font = '600 15px system-ui';
    ctx.fillText(label, x + 12, y - 10);
  }

  function render() {
    const [first, last] = endpoints;
    const scene = first.scene;
    const boxes = Object.entries(scene.blocks).map(([name, box]) => [name,
      box.map((value, i) => mix(value, last.scene.blocks[name][i], progress))]);
    const bounce = [first.bounce, 0];
    const legs = [[scene.camera,bounce],[bounce,scene.target]];
    ctx.fillStyle = '#101821';
    ctx.fillRect(0,0,800,310);
    for (let x = 0; x <= 100; x += 5) line([x,0],[x,30],'#23303d',1);
    for (let y = 0; y <= 30; y += 5) line([0,y],[100,y],'#23303d',1);
    line([0,0],[100,0],'#465967',1);
    line([scene.mirror[0],0],[scene.mirror[1],0],'#82e7ef',6);
    for (const [name, box] of boxes) {
      const [x,y] = point([box[0],box[3]]);
      ctx.fillStyle = name === 'A' ? '#f4ad73' : '#445563';
      ctx.fillRect(x,y,(box[2]-box[0])*7,(box[3]-box[1])*7);
      ctx.fillStyle = name === 'A' ? '#211912' : '#fff';
      ctx.font = '600 14px system-ui';
      ctx.fillText(name,x+6,y+17);
    }
    let blocked = false;
    for (const [a,b] of legs) {
      line(a,b,'#506272',2,true);
      if (blocked) continue;
      const distance = Math.min(...boxes.map(([,box]) => entry(a,b,box)));
      const stop = Number.isFinite(distance) ? [mix(a[0],b[0],distance),mix(a[1],b[1],distance)] : b;
      line(a,stop,'#a4f4e1',3);
      if (Number.isFinite(distance)) {
        blocked = true;
        marker(stop,'','#ffceaa');
      }
    }
    marker(scene.camera,'Camera','#91caff');
    marker(scene.target,'Target',blocked ? '#bac2ca' : '#b8f49b');
    const [mirrorX, mirrorY] = point(bounce);
    ctx.fillStyle = '#82e7ef';
    ctx.font = '600 14px system-ui';
    ctx.textAlign = 'center';
    ctx.fillText('Mirror', mirrorX, mirrorY+25);
    ctx.textAlign = 'start';
    const status = blocked ? 'Target blocked' : 'Target visible';
    if (outcome.textContent !== status) outcome.textContent = status;
    canvas.setAttribute('aria-label', 'Synthetic optical scene: ' + status);
    scrub.value = String(Math.round(progress * 1000));
  }

  function pause() {
    if (frame !== null) cancelAnimationFrame(frame);
    frame = started = null;
    play.textContent = progress >= 1 ? 'Replay transition' : 'Play transition';
  }

  function step(time) {
    if (started === null) started = time - progress * 2200;
    progress = Math.min(1, (time - started) / 2200);
    render();
    if (progress >= 1) pause();
    else frame = requestAnimationFrame(step);
  }

  fetch('replay.json').then(response => {
    if (!response.ok) throw Error('Replay unavailable');
    return response.json();
  }).then(data => {
    endpoints = data;
    for (const control of [scrub,play,reset]) control.disabled = false;
    render();
  }).catch(() => { outcome.textContent = 'Replay unavailable'; });

  play.addEventListener('click', () => {
    if (frame !== null) { pause(); return; }
    if (reduced.matches) {
      progress = progress >= 1 ? 0 : 1;
      render();
      pause();
      return;
    }
    if (progress >= 1) progress = 0;
    play.textContent = 'Pause';
    frame = requestAnimationFrame(step);
  });
  reset.addEventListener('click', () => { pause(); progress = 0; render(); pause(); });
  scrub.addEventListener('input', () => { pause(); progress = scrub.valueAsNumber / 1000; render(); pause(); });
  addEventListener('hashchange', pause);
})();
