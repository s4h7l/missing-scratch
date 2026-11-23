"""Checkpoint each model request before sending. Score against every assigned case."""

from collections import defaultdict
import json
import os
from secrets import token_hex
import time

from backend.db.store import database
from . import physical, providers, review
from .common import Problem, canonical, consume, digest, event, one, rows


def settings(limit):
    return {"max_output_tokens":limit,"parser":"exact-option-v1","prompt":"options-v1","tools":False}


def check_gate(did):
    d=one("SELECT suite FROM datasets WHERE id=?",(did,))
    if d["suite"]=="corrected":
        rev=rows("SELECT id FROM reviews WHERE dataset=?",(did,))
        if not rev:
            raise Problem(409,"Corrected evaluation requires sealed and adjudicated blind review")
        report=review.report(rev[0]["id"])
        if not report.get("accepted") or report.get("assigned",0)<72:
            raise Problem(409,"Corrected evaluation requires accepted 72-case blind review")
        if not physical.summary(did)["gate_passed"]:
            raise Problem(409,"Corrected evaluation requires five agreeing calibrated cases covering all task kinds")


def start(did,provider,model,mode,limit=512):
    check_gate(did)
    providers.ready(provider,model)
    rid="B-"+token_hex(12)
    with database() as db:
        db.execute("INSERT INTO runs(id,dataset,provider,model,mode,settings,source) VALUES(?,?,?,?,?,?,?)",
                   (rid,did,provider,model,mode,canonical(settings(limit)),"live"))
        event(db,"benchmark.created",rid)
    return {"run_id":rid,"state":"queued"}


def step(rid,count=1):
    run=one("SELECT * FROM runs WHERE id=?",(rid,))
    if run["source"]!="live":
        raise Problem(409,"Only live runs can issue requests")
    check_gate(run["dataset"])
    providers.ready(run["provider"],run["model"])
    for _ in range(count):
        with database() as db:
            db.execute("BEGIN IMMEDIATE")
            # An abandoned reservation is an unknown provider outcome. Never resend it implicitly.
            db.execute("UPDATE calls SET status='interrupted' WHERE run=? AND status='sending' AND started<?",
                       (rid,time.time()-180))
            case=db.execute("""SELECT id,question,options,png,digest FROM cases c WHERE dataset=? AND NOT EXISTS
               (SELECT 1 FROM calls a WHERE a.task=c.id AND a.run=?) ORDER BY position LIMIT 1""",(run["dataset"],rid)).fetchone()
            if not case:
                break
            if digest(case["png"])!=case["digest"]:
                raise Problem(409,"Stored input image fails its manifest hash")
            consume(db,"benchmark-live",int(os.getenv("MS_BENCHMARK_CALL_CAP","0")))
            db.execute("INSERT INTO calls(run,task,status,metadata,started) VALUES(?,?,'sending','{}',?)",
                       (rid,case["id"],time.time()))
        result=providers.infer(run["provider"],run["model"],run["mode"],case["question"],json.loads(case["options"]),
                               case["png"],json.loads(run["settings"])["max_output_tokens"])
        status,raw,parsed,meta=result
        with database() as db:
            db.execute("UPDATE calls SET status=?,raw=?,parsed=?,metadata=? WHERE run=? AND task=? AND status='sending'",
                       (status,raw,parsed,canonical(meta),rid,case["id"]))
    return score(rid)


def score(rid):
    run=one("SELECT * FROM runs WHERE id=?",(rid,))
    outcomes=rows("""SELECT c.id,c.kind,c.answer,c.pair,c.difficulty,a.status,a.parsed
           FROM cases c LEFT JOIN calls a ON a.task=c.id AND a.run=? WHERE c.dataset=? ORDER BY c.position""",(rid,run["dataset"]))
    pairs=defaultdict(list); groups=defaultdict(lambda:[0,0]); states=defaultdict(int)
    false_pass=hidden=false_reject=visible=correct=0
    for c in outcomes:
        ok=c["status"]=="ok" and c["parsed"]==c["answer"]
        correct+=int(ok)
        pairs[c["pair"]].append(ok)
        for label in (c["kind"],c["difficulty"]):
            groups[label][0]+=int(ok); groups[label][1]+=1
        states[c["status"] or "pending"]+=1
        if c["kind"]=="visibility":
            if c["answer"]=="VISIBLE":
                visible+=1;false_reject+=int(c["parsed"]=="NOT_VISIBLE")
            else:
                hidden+=1;false_pass+=int(c["parsed"]=="VISIBLE")
    return {"run_id":rid,"dataset_id":run["dataset"],"source":run["source"],"provider":run["provider"],
            "model":run["model"],"mode":run["mode"],"settings":json.loads(run["settings"]),
            "state":"complete" if not (states.get("pending") or states.get("sending")) else "in_progress",
            "states":dict(states),"correct":correct,"assigned":len(outcomes),
            "strict_pairs_correct":sum(len(p)==2 and all(p) for p in pairs.values()),"pairs":len(pairs),
            "false_pass":{"count":false_pass,"hidden":hidden},"false_reject":{"count":false_reject,"visible":visible},
            "groups":{k:{"correct":v[0],"assigned":v[1]} for k,v in groups.items()}}


def export_run(rid):
    run=one("SELECT * FROM runs WHERE id=?",(rid,))
    records=rows("""SELECT c.id AS task_id,c.digest AS image_sha256,c.question,c.options,c.pair,c.answer,
                     a.status,a.raw,a.metadata FROM calls a JOIN cases c ON c.id=a.task WHERE a.run=? ORDER BY c.position""",(rid,))
    for r in records:
        r["metadata"]=json.loads(r["metadata"])
        r["prompt_sha256"]=digest(providers.prompt(r.pop("question"),json.loads(r.pop("options"))))
    return {"schema":1,"dataset_id":run["dataset"],"manifest_sha256":one("SELECT digest FROM datasets WHERE id=?",(run["dataset"],))["digest"],
            "provider":run["provider"],"model":run["model"],"mode":run["mode"],"settings":json.loads(run["settings"]),
            "source":run["source"],"records":records,"summary":score(rid)}


def replay(data):
    dataset=one("SELECT digest FROM datasets WHERE id=?",(data["dataset_id"],))
    if dataset["digest"]!=data["manifest_sha256"]:
        raise Problem(409,"Dataset manifest differs from the captured run")
    rid="R-"+token_hex(12)
    cases={c["id"]:c for c in rows("SELECT id,digest,options,question FROM cases WHERE dataset=?",(data["dataset_id"],))}
    seen=set()
    with database() as db:
        db.execute("INSERT INTO runs(id,dataset,provider,model,mode,settings,source) VALUES(?,?,?,?,?,?,?)",
                   (rid,data["dataset_id"],data["provider"],data["model"],data["mode"],canonical(data["settings"]),"replay"))
        for rec in data["records"]:
            cid=rec["task_id"];c=cases.get(cid)
            if not c or cid in seen or rec["image_sha256"]!=c["digest"]:
                raise Problem(422,"Unknown, duplicate or changed input")
            seen.add(cid);opts=json.loads(c["options"]); raw=rec.get("raw") or ""
            if rec["prompt_sha256"]!=digest(providers.prompt(c["question"],opts)):
                raise Problem(409,"Prompt digest mismatch")
            parsed=providers.parse(raw,opts)
            status=rec["status"]
            if status in {"ok","invalid"}:
                status="ok" if parsed else "invalid"
            else:
                status="error" if status=="error" else "interrupted"; parsed=None
            db.execute("INSERT INTO calls VALUES(?,?,?,?,?,?,?)",
                       (rid,cid,status,raw,parsed,canonical(rec.get("metadata",{})),time.time()))
        for cid in cases.keys()-seen:
            db.execute("INSERT INTO calls VALUES(?,?,'missing','',NULL,'{}',?)",(rid,cid,time.time()))
        event(db,"benchmark.replayed",rid,dataset["digest"])
    return score(rid)


def results():
    all_runs=[score(r["id"]) for r in rows("SELECT id FROM runs ORDER BY rowid DESC LIMIT 100")]
    completed=[r for r in all_runs if r["state"]=="complete"]
    matched={}
    for r in completed:
        key=(r["dataset_id"],r["provider"],r["model"],r["source"],canonical(r["settings"]))
        matched.setdefault(key,{}).setdefault(r["mode"],r)
    uplifts=[]
    for modes in matched.values():
        if "vision" in modes and "question-only" in modes:
            a,b=modes["vision"],modes["question-only"]
            uplifts.append({"vision_run":a["run_id"],"baseline_run":b["run_id"],
                            "percentage_points":round(100*(a["correct"]-b["correct"])/a["assigned"],2)})
    return {"runs":completed,"matched_visual_uplift":uplifts}
