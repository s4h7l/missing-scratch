"""Versioned input-only datasets. Blind case IDs never enter the interactive task store."""

from dataclasses import replace
from math import atan2, degrees, sin, cos, hypot
from random import Random
from secrets import randbits
import json

from backend.core.factory import (RejectedLayout, checked, disk_pair, layouts, make_task,
                                 repair_pair, separation, sight_angle, distance_to_leg)
from backend.core.factory import QUESTIONS
from backend.services.render import render_task
from backend.services.description import describe
from backend.db.store import database
from .common import Problem, archive, canonical, digest, event, one, rows

VERSION = "v3-suite-1"


def difficulty(task):
    margins = []
    for trial in [task.base, *task.alternatives.values()]:
        s, hit = trial.scene, trial.checks[0].hit
        if hit is None:
            continue
        margins.append(min(separation(hit, p) for p in (s.mirror_start, s.mirror_end))/5)
        angle = sight_angle(s.camera, hit)-s.camera_heading
        margins.append(abs(degrees(abs(atan2(sin(angle),cos(angle)))-s.camera_fov/2))/3)
        for disk in s.blockers:
            d = min(distance_to_leg(disk.center,a,b) for a,b in ((s.camera,hit),(hit,s.target)))
            margins.append(abs(d-disk.radius)/3)
    score = min(margins)
    return "HARD" if score < 1.6 else "MEDIUM" if score < 3.5 else "EASY"


def optical_pair(seed, rng, scenes, broken, boundary):
    a = checked(scenes[0])
    if not a.visible:
        raise RejectedLayout()
    if boundary == "edge":
        b = checked(broken)
        if b.checks[0].reason != "outside_finite_mirror":
            raise RejectedLayout()
    else:
        b = checked(replace(a.scene, camera_heading=a.scene.camera_heading+0.95))
        if b.checks[0].reason != "outside_camera_fov":
            raise RejectedLayout()
    pair = [make_task("visibility",seed,t,{}) for t in (a,b)]
    rng.shuffle(pair)
    return pair


def group(seed, count, index):
    rng = Random(seed)
    for _ in range(400):
        choices, broken = layouts(rng)
        pairs = []
        try:
            for kind in ("visibility","obstruction","repair","boundary","obstruction")[:count]:
                if kind == "repair":
                    pair = repair_pair(seed,rng,choices,broken)
                elif kind == "boundary":
                    pair = optical_pair(seed,rng,choices,broken,"edge" if index%2 == 0 else "fov")
                else:
                    pair = disk_pair(kind,seed,rng,choices)
                    rng.shuffle(pair)
                if pair[0].answer == pair[1].answer:
                    raise RejectedLayout()
                pairs.append(pair)
            return pairs
        except RejectedLayout:
            continue
    raise Problem(503,"Generator exhausted its bounded layout search")


def build(suite="pilot", pairs=3, seed=None):
    if suite not in {"pilot","corrected"} or not 1 <= pairs <= 100:
        raise Problem(422,"Invalid suite or pair count")
    if suite == "corrected":
        pairs = 100
    seed = (0 if suite == 'corrected' else randbits(55)) if seed is None else seed
    layout_seed = lambda i: 81602+i if suite=="corrected" and seed==0 else (seed+i)
    stamp = digest(canonical([VERSION,suite,pairs,seed]))
    items, manifest = [], []
    for index in range((pairs+4)//5):
        for j, pair in enumerate(group(layout_seed(index),min(5,pairs-index*5),index)):
            pair_id = "P-"+digest(f"{stamp}/pair/{index}/{j}")[:20]
            for task in pair:
                pos = len(items)
                cid = "C-"+digest(f"{stamp}/case/{pos}")[:24]
                png = render_task(task)
                prompt = QUESTIONS[task.kind]
                options = list(task.options)
                level = difficulty(task)
                evidence = describe(task.base)
                evidence["alternatives"] = {k:describe(v) for k,v in task.alternatives.items()}
                meta = {"task_id":cid,"kind":task.kind,"question":prompt,"options":options,
                        "difficulty":level,"image":f"inputs/{cid}.png","image_sha256":digest(png)}
                manifest.append(meta)
                items.append((cid,pos,pair_id,index,task.kind,level,prompt,canonical(options),task.answer,
                              canonical(evidence),png,meta["image_sha256"]))
    key = digest(canonical(manifest))
    did = "D-"+key[:24]
    with database() as db:
        if not db.execute("SELECT 1 FROM datasets WHERE id=?",(did,)).fetchone():
            db.execute("INSERT INTO datasets(id,suite,seed,manifest,digest) VALUES(?,?,?,?,?)",
                       (did,suite,seed,canonical(manifest),key))
            db.executemany("""INSERT INTO cases(id,dataset,position,pair,layout,kind,difficulty,question,options,answer,evidence,png,digest)
                VALUES(?,?,?,?,?,?,?,?,?,?,?,?,?)""", ((r[0],did,*r[1:]) for r in items))
            event(db,"dataset.created",did,key)
    return {"dataset_id":did,"suite":suite,"tasks":len(items),"pairs":pairs,"layouts":(pairs+4)//5,"manifest_sha256":key}


def export(did):
    d = one("SELECT manifest,digest FROM datasets WHERE id=?", (did,))
    files = [(f"inputs/{r['id']}.png", r["png"]) for r in rows("SELECT id,png FROM cases WHERE dataset=? ORDER BY position",(did,))]
    files += [("tasks.jsonl","".join(canonical(m)+"\n" for m in json.loads(d["manifest"]))),
              ("manifest.sha256",d["digest"]+"\n")]
    return archive(files)


def case(cid):
    return one("SELECT * FROM cases WHERE id=?",(cid,))
