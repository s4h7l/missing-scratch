"""Neutral reviewer packets and sealed, immutable response sheets."""

from collections import defaultdict
import json
from random import SystemRandom
from secrets import token_hex

from backend.db.store import database
from .common import Problem, archive, canonical, digest, event, one, rows

REVIEWERS = ("R1","R2")


def create(dataset, count=72):
    records = rows("SELECT id,kind,pair,layout,difficulty FROM cases WHERE dataset=? ORDER BY position",(dataset,))
    if not records or count < 2 or count%2 or count > len(records):
        raise Problem(422,"Choose an even review size within the dataset")
    pairs = defaultdict(list)
    for record in records:
        pairs[record["pair"]].append(record)
    groups = defaultdict(list)
    for pair in pairs.values():
        groups[pair[0]["kind"]].append(pair)
    rng = SystemRandom()
    used = defaultdict(int)
    chosen = []
    while len(chosen)<count:
        for kind in sorted(groups):
            options = groups[kind]
            if not options or len(chosen)>=count:
                continue
            rng.shuffle(options)
            options.sort(key=lambda p:(used["layout",p[0]["layout"]],sum(used["level",r["difficulty"]] for r in p)))
            pair = options.pop(0)
            used["layout",pair[0]["layout"]] += 1
            for r in pair:
                used["level",r["difficulty"]] += 1
                chosen.append(r["id"])
    rid = "H-"+token_hex(12)
    maps = {}
    for reviewer in REVIEWERS:
        order = rng.sample(chosen,len(chosen))
        maps[reviewer] = {f"{reviewer}-Q{i:03}":cid for i,cid in enumerate(order,1)}
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        old = db.execute("SELECT id FROM reviews WHERE dataset=?", (dataset,)).fetchone()
        if old:
            raise Problem(409,"A frozen packet already exists for this dataset")
        db.execute("INSERT INTO reviews VALUES(?,?,?)",(rid,dataset,canonical(maps)))
        event(db,"review.created",rid,digest(canonical(maps)))
    return {"review_id":rid,"dataset_id":dataset,"tasks_per_reviewer":count}


def packet(rid, reviewer):
    mapping = json.loads(one("SELECT maps FROM reviews WHERE id=?",(rid,))["maps"])[reviewer]
    files, form = [], []
    with database() as db:
        for code,cid in mapping.items():
            rec = db.execute("SELECT png,question,options,digest FROM cases WHERE id=?",(cid,)).fetchone()
            files.append((code+".png",rec["png"]))
            form.append({"code":code,"question":rec["question"],"options":json.loads(rec["options"]),
                         "image":code+".png","image_sha256":rec["digest"]})
    files.append(("questions.json",canonical(form)))
    files.append(("sheet.json",canonical({"responses":[{"code":f["code"],"answer":None,
                         "evidence":"","ambiguity":"","confidence":None} for f in form]})))
    return archive(files)


def submit(rid, reviewer, responses):
    review = one("SELECT maps FROM reviews WHERE id=?",(rid,))
    mapping = json.loads(review["maps"])[reviewer]
    actual = {r["code"] for r in responses}
    if actual != set(mapping) or len(responses)!=len(mapping):
        raise Problem(422,"Include every assigned code exactly once. Use null for a missing answer.")
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        for r in responses:
            options = json.loads(db.execute("SELECT options FROM cases WHERE id=?", (mapping[r["code"]],)).fetchone()[0])
            if r["answer"] is not None and r["answer"] not in options:
                raise Problem(422,"A response is outside its displayed options")
        raw = canonical(responses)
        checksum = digest(raw)
        old = db.execute("SELECT digest FROM sheets WHERE review=? AND reviewer=?",(rid,reviewer)).fetchone()
        if old and old[0]!=checksum:
            raise Problem(409,"Reviewer sheet is already sealed")
        if not old:
            db.execute("INSERT INTO sheets(review,reviewer,raw,digest) VALUES(?,?,?,?)",(rid,reviewer,raw,checksum))
            event(db,"review.sealed",rid,checksum)
    return {"reviewer":reviewer,"status":"sealed","sha256":checksum}


def report(rid, detail=False):
    review = one("SELECT * FROM reviews WHERE id=?",(rid,))
    sheets = rows("SELECT * FROM sheets WHERE review=? ORDER BY reviewer",(rid,))
    result = {"review_id":rid,"sealed_sheets":len(sheets),"state":"pending"}
    if len(sheets)!=2:
        return result
    maps = json.loads(review["maps"])
    truth = {r["id"]:r["answer"] for r in rows("SELECT id,answer FROM cases WHERE dataset=?",(review["dataset"],))}
    answers, scores = {}, {}
    for sheet in sheets:
        name = sheet["reviewer"]
        entries = {maps[name][r["code"]]:r for r in json.loads(sheet["raw"])}
        scores[name] = {"assigned":len(entries),"correct":sum(r["answer"]==truth[k] for k,r in entries.items()),
                        "missing":sum(r["answer"] is None for r in entries.values()),"sha256":sheet["digest"]}
        answers[name]=entries
    a,b = (answers[r] for r in REVIEWERS)
    comparable = [k for k in a if a[k]["answer"] is not None and b[k]["answer"] is not None]
    issues = [k for k in a if a[k]["answer"]!=truth[k] or b[k]["answer"]!=truth[k] or
              a[k].get("ambiguity") or b[k].get("ambiguity")]
    decision = rows("SELECT accepted,notes FROM decisions WHERE review=?",(rid,))
    result.update(state="sealed",reviewers=scores,assigned=len(a),comparable=len(comparable),
                  agree=sum(a[k]["answer"]==b[k]["answer"] for k in comparable),
                  both_correct=sum(a[k]["answer"]==b[k]["answer"]==truth[k] for k in comparable),
                  cases_for_review=len(issues),accepted=bool(decision and decision[0]["accepted"]))
    if detail:
        result["issues"]=[{"task_id":k,"truth":truth[k],"R1":a[k],"R2":b[k]} for k in issues]
        result["decision"]=decision
    return result


def adjudicate(rid, accepted, notes):
    if report(rid)["state"]!="sealed":
        raise Problem(409,"Both original sheets must be sealed")
    with database() as db:
        db.execute("BEGIN IMMEDIATE")
        if db.execute("SELECT 1 FROM decisions WHERE review=?",(rid,)).fetchone():
            raise Problem(409,"Decision already recorded. Revised diagrams require a new dataset.")
        db.execute("INSERT INTO decisions(review,notes,accepted) VALUES(?,?,?)",(rid,notes,int(accepted)))
        event(db,"review.adjudicated",rid,digest(notes))
    return report(rid)
