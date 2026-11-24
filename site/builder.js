(() => {
  const by = id => document.getElementById(id);
  const types = {
    camera:{label:'Camera', w:44, d:32, h:34, colors:['#91c8fc','#3875a6','#245881'], single:true},
    target:{label:'Target', w:32, d:28, h:13, colors:['#daf099','#7d9d42','#547330'], single:true},
    mirror:{label:'Mirror', w:178, d:12, h:54, colors:['#c6ffff','#63aab8','#428596'], single:true},
    carton:{label:'Carton', w:52, d:42, h:48, colors:['#dfaa72','#a67346','#784c32']},
    pallet:{label:'Pallet', w:70, d:52, h:24, colors:['#d0a575','#896342','#63442f']},
    rack:{label:'Rack', w:82, d:36, h:62, colors:['#9aa9b1','#596e7b','#3c4f5c']},
  };
  const presets = {
    warehouse:[['camera',135,95],['target',555,119],['mirror',335,314],['rack',251,195],['pallet',510,260]],
    dock:[['camera',135,95],['target',555,119],['mirror',335,314],['carton',112,195]],
    cell:[['camera',155,95],['target',555,119],['mirror',235,314],['rack',120,218],['carton',490,260]],
    empty:[],
  };
  const limits = {left:20,top:55,right:657,bottom:354};
  const maxParts = 24;
  const storageKey = 'missing-scratch-layouts-v1';
  const offsets = {ArrowLeft:[-1,0],ArrowRight:[1,0],ArrowUp:[0,-1],ArrowDown:[0,1]};
  let active = false;
  let traceOptics;
  let parts = fromPreset('warehouse');
  let resetParts = structuredClone(parts);
  let site = 'warehouse';
  let resetSite = site;
  let selection = parts[3].id;
  let baseline;
  let repair;
  const history = [];

  function fromPreset(name) {
    return presets[name].map(([type,x,y],index) => ({id:index+1,type,x,y}));
  }
  function range(type) {
    const {w,d} = types[type];
    return {left:limits.left+w/2, right:limits.right-w/2,
      top:limits.top+(type === 'mirror' ? 0 : d/2), bottom:limits.bottom-(type === 'mirror' ? d : d/2)};
  }
  function footprint(part) {
    const {w,d} = types[part.type];
    const top = part.type === 'mirror' ? part.y : part.y-d/2;
    return [part.x-w/2,top,part.x+w/2,top+d];
  }
  function clampPart(part, x, y) {
    const r = range(part.type);
    return {...part,x:Math.round(Math.min(r.right,Math.max(r.left,x))),
      y:Math.round(Math.min(r.bottom,Math.max(r.top,y)))};
  }
  function labelFor(part) {
    const type = types[part.type];
    return type.single ? type.label : type.label + ' ' + part.id;
  }
  function sceneResult(items) {
    const camera = items.find(part => part.type === 'camera');
    const target = items.find(part => part.type === 'target');
    const mirror = items.find(part => part.type === 'mirror');
    const result = {ray:[], clear:false};
    if (!camera || !target || !mirror) {
      return {...result, title:'Setup incomplete', detail:'Add a camera, target, and mirror to test coverage.'};
    }
    if (camera.y >= mirror.y || target.y >= mirror.y) {
      return {...result, title:'Outside the supported layout', detail:'Place the camera and target above the reflective edge of the mirror.'};
    }
    const obstacles = items.filter(part => !types[part.type].single)
      .map(part => ({id:part.id,label:labelFor(part),box:footprint(part)}));
    const {source,reflection,target:destination,first,second,inside,clear} = traceOptics(
      [camera.x,camera.y],[target.x,target.y],mirror.x,mirror.y,types.mirror.w/2,obstacles);
    const stop = (a,b,t) => a.map((value,index) => value+(b[index]-value)*t);
    if (first) return {...result,reflection,ray:[source,stop(source,reflection,first.entry)],
      blocker:first.label,title:'Path blocked',detail:first.label+' stops the ray before it reaches the mirror.'};
    if (!inside) return {...result,reflection,ray:[source,reflection],title:'Mirror missed',
      detail:'The reflection point falls outside the mirror span.'};
    if (second) return {...result,reflection,ray:[source,reflection,stop(reflection,destination,second.entry)],
      blocker:second.label,title:'Path blocked',detail:second.label+' stops the reflected ray before it reaches the target.'};
    return {...result,reflection,ray:[source,reflection,destination],clear,title:'Target visible',
      detail:'The ray reaches the target through the mirror.'};
  }

  function verifiedRepair(current) {
    if (!current.blocker) return null;
    const part = parts.find(item => labelFor(item) === current.blocker);
    for (const [x,y] of [[100,275],[585,270],[78,125],[590,115]]) {
      const candidate = clampPart(part,x,y);
      const box = footprint(candidate);
      const overlaps = parts.some(other => {
        if (other.id === part.id) return false;
        const b = footprint(other);
        return box[0] < b[2] && box[2] > b[0] && box[1] < b[3] && box[3] > b[1];
      });
      if (overlaps) continue;
      const amended = parts.map(item => item.id === part.id ? candidate : item);
      if (sceneResult(amended).clear) return {parts:amended,label:labelFor(part),x:candidate.x,y:candidate.y};
    }
    return null;
  }

  function snapshot(title, items, result) {
    const figure = document.createElement('figure');
    const canvas = document.createElement('canvas');
    canvas.width = 640; canvas.height = 310;
    canvas.setAttribute('aria-label',title + '. ' + result.title + '. ' + result.detail);
    canvas.setAttribute('role','img');
    const ctx = canvas.getContext('2d');
    ctx.translate(-19,-54);
    ctx.fillStyle = '#152532';
    ctx.fillRect(19,54,640,310);
    for (const part of items) {
      const [x,y,u,v] = footprint(part);
      ctx.fillStyle = types[part.type].colors[0];
      ctx.fillRect(x,y,u-x,v-y);
    }
    if (result.ray.length) {
      ctx.beginPath();
      ctx.moveTo(...result.ray[0]);
      for (const point of result.ray.slice(1)) ctx.lineTo(...point);
      ctx.lineWidth = 4;
      ctx.strokeStyle = result.clear ? '#65ff9c' : '#ff6672';
      ctx.stroke();
    }
    const caption = document.createElement('figcaption');
    caption.textContent = title + ' · ' + result.title;
    figure.append(canvas,caption);
    return figure;
  }

  function refreshSelection() {
    const picker = by('builder-selection');
    picker.replaceChildren(new Option('Choose equipment',''));
    for (const part of parts) picker.add(new Option(labelFor(part),part.id));
    const part = parts.find(item => item.id === selection);
    picker.value = part?.id ?? '';
    by('builder-properties').disabled = !part;
    by('builder-duplicate').disabled = !part || types[part.type].single || parts.length >= maxParts;
    for (const [axis,lower,upper] of [['x','left','right'],['y','top','bottom']]) {
      const input = by('builder-'+axis);
      input.value = part?.[axis] ?? '';
      if (part) {
        const bounds = range(part.type);
        input.min = bounds[lower]; input.max = bounds[upper];
      }
    }
    for (const button of by('builder-tray').querySelectorAll('button')) {
      button.disabled = parts.length >= maxParts ||
        Boolean(types[button.dataset.component].single && parts.some(item => item.type === button.dataset.component));
    }
    by('builder-undo').disabled = history.length === 0;
  }

  function render(sync = false) {
    const result = sceneResult(parts);
    const models = parts.map(part => {
      const type = types[part.type];
      return ['builder-'+part.id,labelFor(part),footprint(part),type.h,type.colors,part.type,part.id === selection];
    });
    window.opticsBench.draw({customModels:models,ray:result.ray,reflection:result.reflection,
      clear:result.clear,locked:false,scene:site,decor:[]});
    const outcome = by('builder-outcome');
    const wording = result.title + '. ' + result.detail;
    if (outcome.textContent !== wording) outcome.textContent = wording;
    outcome.dataset.grade = result.clear ? 'correct' : result.ray.length ? 'wrong' : '';
    if (!sync) return;
    refreshSelection();
    repair = verifiedRepair(result);
    by('builder-repair').hidden = !repair;
    by('builder-repair-note').hidden = !repair;
    if (repair) by('builder-repair-note').textContent = 'Move '+repair.label+' to ('+repair.x+', '+repair.y+') to restore the path.';
    by('builder-compare').hidden = !baseline;
    by('builder-restore').disabled = !baseline;
    if (baseline) by('builder-compare').replaceChildren(
      snapshot('Baseline',baseline.parts,sceneResult(baseline.parts)), snapshot('Current',parts,result));
  }

  function remember() {
    history.push({parts:structuredClone(parts),selection,site});
    if (history.length > 40) history.shift();
  }
  function change(items, selected = selection, nextSite = site) {
    remember();
    parts = items; selection = selected; site = nextSite;
    render(true);
  }
  function updatePart(part) {
    if (!parts.some(item => item.id === part.id && (item.x !== part.x || item.y !== part.y))) return;
    change(parts.map(item => item.id === part.id ? part : item));
  }
  function add(type, origin) {
    let id = 1;
    while (parts.some(item => item.id === id)) id++;
    const start = {camera:[135,95],target:[555,119],mirror:[335,314],carton:[250,195],pallet:[265,225],rack:[280,245]};
    const [x,y] = origin ? [origin.x+24,origin.y+24] : start[type];
    const part = clampPart({id,type},x,y);
    change([...parts,part],id);
  }
  function validate(raw) {
    if (raw?.version !== 1 || !['dock','warehouse','cell'].includes(raw.site) ||
        typeof raw.name !== 'string' || !raw.name.trim() || raw.name.length > 60 ||
        !Array.isArray(raw.parts) || raw.parts.length > maxParts) {
      throw new Error('Invalid layout header or component count.');
    }
    const ids = new Set(), singles = new Set();
    const clean = raw.parts.map(part => {
      if (!part || !Object.hasOwn(types,part.type) || !Number.isSafeInteger(part.id) || part.id < 1 ||
          part.id > 99999 || ids.has(part.id) || !Number.isInteger(part.x) || !Number.isInteger(part.y) ||
          (types[part.type].single && singles.has(part.type))) throw new Error('Invalid or duplicate equipment.');
      const {id,type,x,y} = part;
      const bounded = clampPart({id,type},x,y);
      if (bounded.x !== x || bounded.y !== y) throw new Error('Equipment is outside the floor plan.');
      ids.add(id);
      if (types[type].single) singles.add(type);
      return {id,type,x,y};
    });
    return {version:1,name:raw.name.trim(),site:raw.site,parts:clean};
  }

  function savedLayouts() {
    const data = JSON.parse(localStorage.getItem(storageKey) ?? '[]');
    return Array.isArray(data) ? data.map(validate) : [];
  }
  function refreshSaved() {
    const picker = by('builder-saved');
    picker.replaceChildren(new Option('Choose a layout',''));
    try {
      for (const item of savedLayouts()) picker.add(new Option(item.name,item.name));
    } catch { message('Saved layouts could not be read.'); }
  }
  function payload() {
    return validate({version:1,name:by('builder-name').value.trim() || 'Inspection setup',site,parts});
  }
  function message(text) { by('builder-message').textContent = text; }
  function applySaved(layout) {
    change(layout.parts,layout.parts[0]?.id,layout.site);
    resetParts = structuredClone(layout.parts);
    resetSite = layout.site;
    by('builder-name').value = layout.name;
    message('Opened '+layout.name+'.');
  }
  function bind(trace) {
    traceOptics = trace;
    by('builder-load').addEventListener('click',() => {
      const preset = by('builder-preset').value;
      const next = fromPreset(preset);
      resetParts = structuredClone(next);
      resetSite = preset === 'empty' ? site : preset;
      change(next,next.find(item => item.type === 'rack')?.id ?? next[0]?.id,resetSite);
      message(preset === 'empty' ? 'Empty floor loaded.' : 'Preset loaded.');
    });
    by('builder-reset').addEventListener('click',() => change(structuredClone(resetParts),resetParts[0]?.id,resetSite));
    by('builder-undo').addEventListener('click',() => {
      const prior = history.pop();
      if (prior) ({parts,selection,site} = prior);
      render(true);
    });
    by('builder-tray').addEventListener('click',event => {
      const button = event.target.closest('[data-component]');
      if (button && !button.disabled) add(button.dataset.component);
    });
    by('builder-selection').addEventListener('change',event => { selection = Number(event.target.value); render(true); });
    by('builder-position').addEventListener('click',() => {
      const part = parts.find(item => item.id === selection);
      const x = by('builder-x'), y = by('builder-y');
      if (part && x.reportValidity() && y.reportValidity()) updatePart(clampPart(part,x.valueAsNumber,y.valueAsNumber));
    });
    by('builder-duplicate').addEventListener('click',() => {
      const part = parts.find(item => item.id === selection);
      if (part && !types[part.type].single && parts.length < maxParts) add(part.type,part);
    });
    by('builder-delete').addEventListener('click',() => change(parts.filter(item => item.id !== selection),null));
    by('builder-baseline').addEventListener('click',() => {
      baseline = {parts:structuredClone(parts),site};
      render(true);
      message('Baseline saved for this workspace.');
    });
    by('builder-restore').addEventListener('click',() => {
      if (baseline) change(structuredClone(baseline.parts),baseline.parts[0]?.id,baseline.site);
    });
    by('builder-repair').addEventListener('click',() => {
      if (!repair || !sceneResult(repair.parts).clear) return;
      const candidate = repair;
      change(candidate.parts);
      message('Verified repair applied. The target is visible.');
    });
    by('builder-save').addEventListener('click',() => {
      try {
        const layout = payload();
        const remaining = savedLayouts().filter(item => item.name !== layout.name);
        localStorage.setItem(storageKey,JSON.stringify([...remaining,layout]));
        refreshSaved();
        by('builder-saved').value = layout.name;
        message('Saved '+layout.name+' in this browser.');
      } catch { message('Unable to save this layout.'); }
    });
    by('builder-open').addEventListener('click',() => {
      try {
        const layout = savedLayouts().find(item => item.name === by('builder-saved').value);
        if (layout) applySaved(layout);
        else message('Choose a saved layout first.');
      } catch { message('Unable to open the saved layout.'); }
    });
    by('builder-export').addEventListener('click',() => {
      const layout = payload();
      const url = URL.createObjectURL(new Blob([JSON.stringify(layout,null,2)],{type:'application/json'}));
      const link = document.createElement('a');
      link.href = url;
      link.download = 'missing-scratch-setup.json';
      link.click();
      setTimeout(() => URL.revokeObjectURL(url),1000);
    });
    by('builder-import').addEventListener('change',async event => {
      const file = event.target.files[0];
      if (!file) return;
      try {
        if (file.size > 65536) throw new Error('Layout file exceeds 64 KB.');
        applySaved(validate(JSON.parse(await file.text())));
      } catch (error) { message('Import rejected. '+error.message); }
      finally { event.target.value = ''; }
    });
  }

  window.setupBuilder = {
    get active() { return active; },
    bind, render,
    activate(value) {
      active = value;
      by('setup-builder').hidden = !value;
      if (active) { refreshSaved(); render(true); }
    },
    beginDrag(id) {
      const part = parts.find(item => id === 'builder-'+item.id);
      if (!part) return null;
      selection = part.id;
      const before = {parts:structuredClone(parts),selection,site};
      render(true);
      return {part,before};
    },
    dragTo(drag, dx, dy) {
      const moved = clampPart(drag.part,drag.part.x+dx,drag.part.y+dy);
      parts = parts.map(item => item.id === moved.id ? moved : item);
      render(true);
    },
    endDrag(drag) {
      const item = parts.find(part => part.id === drag.part.id);
      if (item && (item.x !== drag.part.x || item.y !== drag.part.y)) {
        history.push(drag.before);
        if (history.length > 40) history.shift();
      }
      render(true);
    },
    nudge(key, large) {
      const part = parts.find(item => item.id === selection);
      if (!part) return false;
      const [x,y] = offsets[key];
      const step = large ? 10 : 1;
      updatePart(clampPart(part,part.x+x*step,part.y+y*step));
      return true;
    },
  };
})();
