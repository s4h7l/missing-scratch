(() => {
  const svg = document.getElementById('layout');
  const floor = document.getElementById('bench-floor');
  const objects = document.getElementById('bench-objects');
  const path = document.getElementById('bench-ray');
  const toggle = document.getElementById('bench-view');
  const orbit = document.getElementById('bench-orbit');
  const zoomIn = document.getElementById('bench-in');
  const zoomOut = document.getElementById('bench-out');
  const heading = document.getElementById('bench-heading');
  const tilt = document.getElementById('bench-tilt');
  const initial = {heading: 330, tilt: 42, zoom: 1, x: 0, y: 0};
  const view = {...initial};
  const clamp = (x,min,max) => Math.max(min, Math.min(max,x));
  const wrap = x => (x % 360 + 360) % 360;
  const radians = degrees => degrees * Math.PI / 180;
  let drag;
  let orbitMode = false;
  let lastTilt = initial.tilt;
  let refreshView;
  let orbitFrame;
  let autoFrame;
  const auto = document.getElementById('bench-auto');
  function stopAuto() {
    cancelAnimationFrame(autoFrame);
    auto.setAttribute('aria-pressed','false');
    auto.textContent = 'Auto-rotate';
  }

  auto.addEventListener('click',() => {
    if (auto.getAttribute('aria-pressed') === 'true') {
      stopAuto();
      return;
    }
    cancelAnimationFrame(orbitFrame);
    if (view.tilt === 0) view.tilt = initial.tilt;
    auto.setAttribute('aria-pressed','true');
    auto.textContent = 'Pause rotation';
    let previous = performance.now();
    function rotate(now) {
      view.heading = wrap(view.heading + Math.min(50,now-previous)*.019);
      previous = now;
      refreshView();
      autoFrame = requestAnimationFrame(rotate);
    }
    autoFrame = requestAnimationFrame(rotate);
  });
  const reducedMotion = matchMedia('(prefers-reduced-motion: reduce)');

  function point([x,y], height = 0) {
    const angle = radians(view.heading);
    const pitch = radians(view.tilt);
    const dx = x - 340, dy = y - 205;
    const horizontal = dx*Math.cos(angle) - dy*Math.sin(angle);
    const depth = dx*Math.sin(angle) + dy*Math.cos(angle);
    const scale = .84 * view.zoom;
    return [380 + view.x + horizontal * scale,
      205 + view.y + (depth*Math.cos(pitch) - height*Math.sin(pitch))*scale];
  }

  function element(tag, attributes, parent) {
    const node = document.createElementNS('http://www.w3.org/2000/svg', tag);
    for (const [key, value] of Object.entries(attributes)) node.setAttribute(key, value);
    parent.append(node);
    return node;
  }

  function polygon(vertices, fill, parent, height = 0) {
    return element('polygon', {
      points: vertices.map(p => point(p, height).join(',')).join(' '), fill
    }, parent);
  }

  function texture(asset, a, b, d, parent) {
    const [x,y] = a;
    element('image',{href:'dock-'+asset+'.webp',width:1,height:1,preserveAspectRatio:'none',
      transform:`matrix(${b[0]-x} ${b[1]-y} ${d[0]-x} ${d[1]-y} ${x} ${y})`,
      'pointer-events':'none'},parent);
  }

  function solid(id, label, [x,y,u,v], height, palette, locked) {
    const group = element('g', {'data-bench-object': id, class: locked ? 'bench-object locked' : 'bench-object'}, objects);
    const a = [x,y], b = [u,y], c = [u,v], d = [x,v];
    if (view.tilt > 0) {
      const edges = [[a,b],[b,c],[c,d],[d,a]];
      edges.sort(([p,q],[r,s]) => (point(p)[1] + point(q)[1]) - (point(r)[1] + point(s)[1]));
      for (const [i,[start,end]] of edges.slice(-2).entries()) {
        element('polygon', {
          points: [point(start),point(end),point(end,height),point(start,height)].map(p => p.join(',')).join(' '),
          fill:palette[i+1]
        },group);
      }
    }
    const topFace = polygon([a,b,c,d],palette[0],group,height);
    topFace.setAttribute('stroke','#ffffff');
    topFace.setAttribute('stroke-opacity','.26');
    const [mx,my] = point([(x+u)/2,(y+v)/2],height);
    if (view.tilt > 0 && id === 'camera') {
      const [lx,ly] = point([(x+u)/2,v],22);
      element('ellipse',{cx:lx,cy:ly,rx:11,ry:7,fill:'#142333',stroke:'#a4bed6','stroke-width':2},group);
      element('ellipse',{cx:lx,cy:ly,rx:5,ry:3,fill:'#6bcdef'},group);
    }
    if (view.tilt > 0 && id.startsWith('block-')) {
      for (const fraction of [.18,.45,.72]) {
        const [x1,y1] = point([x,v],height*fraction);
        const [x2,y2] = point([u,v],height*fraction);
        element('line',{x1,y1,x2,y2,stroke:'#b2c0cd','stroke-width':3},group);
      }
    }
    if (view.tilt > 0 && id === 'block') {
      const packages = [[a, b, c, d], [[x+3,y+4],[u-3,y+4],[u-3,v-4],[x+3,v-4]]];
      polygon(packages[0], '#523922', group, height-8);
      polygon(packages[1], palette[0], group, height);
      for (const fraction of [.33,.66]) {
        const stripX = x + (u-x)*fraction;
        const [sx,sy] = point([stripX,y+4],height);
        const [ex,ey] = point([stripX,v-4],height);
        element('line',{x1:sx,y1:sy,x2:ex,y2:ey,stroke:'#f3dfbc','stroke-width':2,'stroke-opacity':.75},group);
      }
    }
    if (id === 'camera' || id === 'target') {
      element('circle',{cx:mx,cy:my,r:5,fill:'#101b2b',stroke:'#e1f2ff','stroke-width':1.4},group);
    }
    if (id === 'mirror' && view.tilt > 0) {
      element('polygon',{points:[point(a),point(b),point(b,height),point(a,height)]
        .map(p => p.join(',')).join(' '),fill:'url(#mirror-finish)','fill-opacity':'.8'},group);
    }
    const assets = {camera:'camera',target:'target',block:'carton',mirror:'mirror'};
    if (assets[id]) {
      if (id === 'mirror' && view.tilt > 0) {
        texture('mirror',point(a,height),point(b,height),point(a,6),group);
      } else {
        const inset = id === 'target' ? 2 : 0;
        texture(assets[id],point([x+inset,y],height),point([u-inset,y],height),point([x+inset,v],height),group);
      }
    }
    const [tx,ty] = point([(x+u)/2,y], height);
    element('text',{x:tx,y:ty-9,'text-anchor':'middle','class':'bench-label'},group).textContent = label;
  }

  function draw({source,target,mirror,plane,obstacles,ray,reflection,clear,awaiting,locked,scene,decor}) {
    floor.replaceChildren();
    objects.replaceChildren();
    path.replaceChildren();
    const deck = [[20,55],[657,55],[657,354],[20,354]];
    const rail = [[8,43],[669,43],[669,366],[8,366]];
    polygon(rail,'#080e16',floor,-11);
    polygon(rail,'url(#bench-rail)',floor);
    const rim = polygon(rail,'none',floor);
    rim.setAttribute('stroke','#708598');
    rim.setAttribute('stroke-opacity','.55');
    const surfaces = {dock:'#334338',warehouse:'#293b4d',cell:'#403b46'};
    const surface = polygon(deck,surfaces[scene],floor);
    surface.setAttribute('stroke','#75bda8');
    surface.setAttribute('stroke-opacity','.52');
    surface.setAttribute('stroke-width','2');
    texture('floor',point(deck[0]),point(deck[1]),point(deck[3]),floor);
    for (const x of [45,145,245,345,445,545,645]) {
      for (const y of [49,360]) {
        const [cx,cy] = point([x,y]);
        element('circle',{cx,cy,r:2,fill:'#becad3','fill-opacity':.75},floor);
      }
    }
    function gridLine(a,b) {
      const [x1,y1]=point(a), [x2,y2]=point(b);
      element('line',{x1,y1,x2,y2,stroke:'#c3f5e3','stroke-opacity':.12},floor);
    }
    for (let x=25;x<=650;x+=25) gridLine([x,55],[x,354]);
    for (let y=55;y<=354;y+=25) gridLine([20,y],[657,y]);
    for (const [x,y,u,v] of decor) {
      polygon([[x,y],[u,y],[u,v],[x,v]], '#111e2a', floor);
      for (let strip=x+5;strip<u-2;strip+=8) {
        polygon([[strip,y],[strip+2,y],[strip+2,v],[strip,v]], '#917c59', floor);
      }
    }
    const [cx,cy] = source, [tx,ty] = target;
    const models = [
      ['camera','Camera',[cx-22,cy-16,cx+22,cy+16],34,['#91c8fc','#3875a6','#245881']],
      ['target','Target',[tx-16,ty-14,tx+16,ty+14],13,['#daf099','#7d9d42','#547330']],
      ...obstacles.map(({label,box},i) => [i === 0 ? 'block' : 'block-' + i, label, box, i === 0 ? 48 : 58,
        i === 0 ? ['#dfaa72','#a67346','#784c32'] : ['#9aa9b1','#596e7b','#3c4f5c']]),
      ['mirror','Mirror',[mirror-89,plane,mirror+89,plane+12],54,['#c6ffff','#63aab8','#428596']]
    ];
    models.sort((a,b) => {
      const depth = ([,,[x,y,u,v]]) => point([(x+u)/2,(y+v)/2])[1];
      return depth(a) - depth(b);
    });
    for (const [id,label,box,height,palette] of models) solid(id,label,box,height,palette,locked);
    if (awaiting) return;
    const points = ray.map(p => point(p,22));
    const outline = points.map(p=>p.join(',')).join(' ');
    element('polyline',{points:outline,fill:'none',stroke:clear?'#65ff9c':'#ff4f5f','stroke-opacity':.18,
      'stroke-width':15,'stroke-linecap':'round','stroke-linejoin':'round'},path);
    element('polyline',{points:outline,fill:'none',stroke:clear?'#65ff9c':'#ff4f5f',
      class:'bench-laser-core','stroke-width':2.5,'stroke-linecap':'round','stroke-linejoin':'round'},path);
    element('polyline',{points:outline,fill:'none',stroke:'#ffffff',pathLength:100,
      class:'bench-laser-pulse',style:'animation-delay:-'+(performance.now()%1800)+'ms','stroke-width':2,'stroke-linecap':'round'},path);
    if (ray.length === 3) {
      const [cx,cy] = point(reflection,22);
      element('circle',{cx,cy,r:6,fill:'#f2fbff',stroke:'#1b5e57','stroke-width':2},path);
    }
    const [x,y] = points.at(-1);
    element('circle',{cx:x,cy:y,r:5,fill:clear?'#65ff9c':'#ff4f5f',stroke:'#0e1724','stroke-width':2},path);
  }

  function bind(update) {
    function refresh() {
      heading.value = Math.round(view.heading) % 360;
      tilt.value = Math.round(view.tilt);
      document.getElementById('bench-heading-value').value = heading.value + '°';
      document.getElementById('bench-tilt-value').value = tilt.value + '°';
      toggle.setAttribute('aria-pressed',String(view.tilt === 0));
      toggle.textContent = view.tilt === 0 ? '3D view' : '2D view';
      document.getElementById('bench-view-tag').textContent = view.tilt === 0 ? '2D · Top view' : '3D · Orbit view';
      zoomIn.disabled = view.zoom >= 2.4;
      zoomOut.disabled = view.zoom <= .65;
      update();
    }
    refreshView = refresh;
    function zoom(factor) {
      view.zoom = clamp(view.zoom * factor,.65,2.4);
      refresh();
    }
    const pointer = event => new DOMPoint(event.clientX,event.clientY)
      .matrixTransform(svg.getScreenCTM().inverse());
    svg.addEventListener('pointerdown',event => {
      if (!event.isPrimary || event.button !== 0) return;
      cancelAnimationFrame(orbitFrame);
      stopAuto();
      const group = event.target.closest('[data-bench-object]');
      const slider = group ? document.getElementById(group.dataset.benchObject) : null;
      const mode = orbitMode || event.shiftKey ? 'orbit' : slider && !slider.disabled ? 'object' : 'pan';
      if (mode === 'object' && !slider) return;
      drag = {id:event.pointerId, start:pointer(event), mode, slider, value:slider?.valueAsNumber, view:{...view}};
      svg.setPointerCapture(event.pointerId);
    });
    svg.addEventListener('pointermove',event => {
      if (!drag || drag.id !== event.pointerId) return;
      const p = pointer(event);
      const dx = p.x - drag.start.x, dy = p.y - drag.start.y;
      if (drag.mode === 'object') {
        if (drag.slider.disabled) return;
        const a = point([0,0]), b = point([1,0]);
        const x = b[0]-a[0], y = b[1]-a[1];
        drag.slider.value = Math.round(drag.value + (dx*x + dy*y)/(x*x+y*y));
      } else if (drag.mode === 'orbit') {
        view.heading = wrap(drag.view.heading + dx*.55);
        view.tilt = clamp(drag.view.tilt - dy*.35,0,75);
      } else {
        view.x = clamp(drag.view.x + dx,-510,510);
        view.y = clamp(drag.view.y + dy,-300,300);
      }
      refresh();
    });
    for (const name of ['pointerup','pointercancel','lostpointercapture']) {
      svg.addEventListener(name,event => { if (drag?.id === event.pointerId) drag = null; });
    }
    heading.addEventListener('input',() => { stopAuto(); cancelAnimationFrame(orbitFrame); view.heading = heading.valueAsNumber; refresh(); });
    tilt.addEventListener('input',() => { stopAuto(); cancelAnimationFrame(orbitFrame); view.tilt = tilt.valueAsNumber; refresh(); });
    toggle.addEventListener('click',() => {
      stopAuto();
      cancelAnimationFrame(orbitFrame);
      if (view.tilt > 0) { lastTilt = view.tilt; view.tilt = 0; }
      else view.tilt = lastTilt;
      refresh();
    });
    orbit.addEventListener('click',() => {
      orbitMode = !orbitMode;
      orbit.setAttribute('aria-pressed',String(orbitMode));
      svg.classList.toggle('orbit-mode',orbitMode);
    });
    zoomIn.addEventListener('click',() => zoom(1.2));
    zoomOut.addEventListener('click',() => zoom(1/1.2));
    document.getElementById('bench-home').addEventListener('click',() => {
      stopAuto();
      cancelAnimationFrame(orbitFrame);
      Object.assign(view,initial);
      lastTilt = initial.tilt;
      orbitMode = false;
      orbit.setAttribute('aria-pressed','false');
      svg.classList.remove('orbit-mode');
      refresh();
    });
    svg.addEventListener('keydown',event => {
      const offsets = {ArrowUp:[0,-22],ArrowDown:[0,22],ArrowLeft:[-22,0],ArrowRight:[22,0]};
      if (event.key === '+' || event.key === '=' || event.key === '-') {
        event.preventDefault();
        zoom(event.key === '-' ? 1/1.2 : 1.2);
      } else if (Object.hasOwn(offsets,event.key)) {
        event.preventDefault();
        const [x,y] = offsets[event.key];
        view.x = clamp(view.x+x,-510,510);
        view.y = clamp(view.y+y,-300,300);
        refresh();
      }
    });
    refresh();
  }

  const page = document.getElementById('simulator-page');
  const fullscreen = document.getElementById('bench-fullscreen');
  const label = document.getElementById('fullscreen-label');
  const open = () => document.fullscreenElement === page || page.classList.contains('bench-fallback-full');
  function refreshFullscreen() {
    fullscreen.setAttribute('aria-pressed',String(open()));
    label.textContent = open() ? 'Exit fullscreen' : 'Expand fullscreen';
  }
  async function closeFullscreen() {
    page.classList.remove('bench-fallback-full');
    document.body.classList.remove('bench-fullscreen-scroll-lock');
    if (document.fullscreenElement === page) await document.exitFullscreen();
    refreshFullscreen();
  }
  fullscreen.addEventListener('click',async () => {
    if (open()) { await closeFullscreen(); return; }
    try {
      if (!page.requestFullscreen) throw Error('Fullscreen unavailable');
      await page.requestFullscreen();
    } catch {
      if (page.hidden) return;
      page.classList.add('bench-fallback-full');
      document.body.classList.add('bench-fullscreen-scroll-lock');
      page.scrollTop = 0;
    }
    refreshFullscreen();
  });
  document.addEventListener('fullscreenchange',refreshFullscreen);
  document.addEventListener('keydown',event => {
    if (event.key === 'Escape' && page.classList.contains('bench-fallback-full')) void closeFullscreen();
  });
  addEventListener('hashchange',() => {
    stopAuto();
    cancelAnimationFrame(orbitFrame);
    if (open()) void closeFullscreen();
  });

  function framePlan() {
    stopAuto();
    cancelAnimationFrame(orbitFrame);
    Object.assign(view, initial, {heading:0, tilt:0});
    refreshView();
  }

  function revealOrbit() {
    cancelAnimationFrame(orbitFrame);
    if (reducedMotion.matches || auto.getAttribute('aria-pressed') === 'true') return;
    if (view.tilt > 0) {
      auto.click();
      return;
    }
    const start = performance.now();
    const heading = view.heading;
    function step(now) {
      const progress = clamp((now - start) / 620, 0, 1);
      const eased = 1 - (1 - progress) ** 3;
      view.heading = wrap(heading - 24 * eased);
      view.tilt = initial.tilt * eased;
      refreshView();
      if (progress < 1) orbitFrame = requestAnimationFrame(step);
      else auto.click();
    }
    orbitFrame = requestAnimationFrame(step);
  }

  function preview(trace, scene, decor) {
    const canvas = document.createElement('canvas');
    canvas.width = 600;
    canvas.height = 384;
    canvas.setAttribute('aria-hidden','true');
    const ctx = canvas.getContext('2d');
    const backdrop = ctx.createLinearGradient(0, 0, 600, 384);
    backdrop.addColorStop(0, '#243847');
    backdrop.addColorStop(1, '#0c1824');
    ctx.fillStyle = backdrop;
    ctx.fillRect(0, 0, 600, 384);
    const project = (x,y,z=0) => [42 + .69*x + .16*y, 64 + .53*y - .12*x - .8*z];
    const face = (points,color) => {
      ctx.beginPath();
      for(const [x,y,z] of points) ctx.lineTo(...project(x,y,z));
      ctx.closePath();
      ctx.fillStyle = color;
      ctx.fill();
    };
    const box = ([x,y,u,v],h,[top,front,side]) => {
      face([[x,v,0],[u,v,0],[u,v,h],[x,v,h]],front);
      face([[u,y,0],[u,v,0],[u,v,h],[u,y,h]],side);
      face([[x,y,h],[u,y,h],[u,v,h],[x,v,h]],top);
    };
    const floors = {dock:'#617063',warehouse:'#516c82',cell:'#6b6578'};
    box([12,50,670,355],4,[floors[scene],'#182932','#293c4a']);
    for (const stripe of decor) box(stripe,3,['#9b8969','#786344','#574733']);
    const [cx,cy] = trace.source;
    const [tx,ty] = trace.target;
    const parts = [
      [[cx-20,cy-14,cx+20,cy+14],36,['#c8e5f4','#3a7898','#214e65']],
      [[tx-18,ty-14,tx+18,ty+14],22,['#dcee9b','#72924d','#495c2e']],
      [[trace.mirror-89,trace.plane,trace.mirror+89,trace.plane+11],45,['#d2fffb','#559e9b','#346a78']],
      ...trace.obstacles.map(({box:bounds},index)=>[bounds,48+index*5,index ?
        ['#9eaeb4','#556e7d','#384a5b'] : ['#dca774','#926541','#66452f']]),
    ];
    parts.sort((a,b)=>project(a[0][2],a[0][3])[1]-project(b[0][2],b[0][3])[1]);
    for(const part of parts) box(...part);
    return canvas;
  }

  window.opticsBench = {draw, bind, framePlan, revealOrbit, preview};
})();
