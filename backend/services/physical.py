"""Bind measured setups and original camera observations to specific diagram stages."""

import json
from io import BytesIO
from math import atan2, degrees, dist, hypot
from PIL import Image, UnidentifiedImageError
from xml.sax.saxutils import escape

from backend.db import store
from .common import Problem, archive, canonical, digest, event, one, rows


def stages(cid):
    found = rows("SELECT kind,evidence FROM cases WHERE id=?", (cid,))
    if found:
        kind, ev = found[0]["kind"], json.loads(found[0]["evidence"])
    else:
        public, private = store.metadata(cid), store.metadata(cid,True)
        if not private or "evidence" not in private:
            raise Problem(404,"Unknown validation case")
        kind, ev = public["kind"],private["evidence"]
    if kind=="visibility":
        return {"setup":ev}
    if kind=="obstruction":
        return {"all":ev,**{"remove-"+k:v for k,v in ev["alternatives"].items()}}
    return ev["alternatives"]


def dimensions(scene):
    # Coordinates in millimetres from the upper-left registration origin on the kit.
    a,b = scene["mirror"]
    scale = 62/dist(a,b)
    point = lambda p: [round(14+x*scale,3) for x in p]
    return {"camera_mm":point(scene["camera"]),"target_mm":point(scene["target"]),
            "mirror_start_mm":point(a),"mirror_end_mm":point(b),
            "camera_yaw_deg":degrees(scene["camera_heading"]),
            "camera_fov_deg":degrees(scene["camera_fov"]),
            "blockers":[{"id":d["id"],"center_mm":point(d["center"]),"radius_mm":d["radius"]*scale}
                        for d in scene["blockers"]]}


def fixture(cid):
    files, targets = [], {}
    for name,trial in stages(cid).items():
        dims = dimensions(trial["scene"])
        targets[name]=dims
        def line(a,b,color):
            return f'<line x1="{a[0]}" y1="{a[1]}" x2="{b[0]}" y2="{b[1]}" stroke="{color}" stroke-width=".6"/>'
        def mark(p,label):
            return f'<circle cx="{p[0]}" cy="{p[1]}" r="1"/><text x="{p[0]+2}" y="{p[1]+4}" font-size="3">{escape(label)}</text>'
        drawing = [f'<svg xmlns="http://www.w3.org/2000/svg" width="210mm" height="297mm" viewBox="0 0 210 297">',
                   line([12,140],[62,140],"black"),'<text x="12" y="147" font-size="4">50 mm | Print at 100%</text>',
                   f'<text x="12" y="159" font-size="4">{escape(name)} | {escape(cid)}</text>',
                   line(dims["mirror_start_mm"],dims["mirror_end_mm"],"#1877a1"),
                   mark(dims["camera_mm"],"CAM"),mark(dims["target_mm"],"X")]
        for d in dims["blockers"]:
            x,y=d["center_mm"]
            drawing.append(f'<circle cx="{x}" cy="{y}" r="{d["radius_mm"]}" fill="none" stroke="black" stroke-width=".4"/>')
            drawing.append(mark([x,y],d["id"]))
        files.append((name+".svg","".join(drawing)+"</svg>"))
    files.append(("nominal-geometry.json",canonical(targets)))
    return archive(files)


def calibrate(cid, record):
    expected = stages(cid)
    if set(record["measurements"]) != set(expected):
        raise Problem(422,"Measure every prescribed stage")
    if abs(record["scale_bar_mm"]-50)>1 or abs(record["mirror_width_mm"]-62)>1 or abs(record["lens_height_mm"]-record["target_height_mm"])>2:
        raise Problem(422,"Scale, mirror width or lens/target heights exceed fixture tolerances")
    for stage,trial in expected.items():
        target = dimensions(trial["scene"]); observed = record["measurements"][stage]
        for field in ("camera_mm","target_mm","mirror_start_mm","mirror_end_mm"):
            if dist(target[field],observed[field])>2:
                raise Problem(422,f"{stage}: {field} exceeds 2 mm tolerance")
        if abs((target["camera_yaw_deg"]-observed["camera_yaw_deg"]+180)%360-180)>2 or abs(target["camera_fov_deg"]-observed["camera_fov_deg"])>2:
            raise Problem(422,f"{stage}: camera aim or field of view differs by more than 2 degrees")
        actual={d["id"]:d for d in observed["blockers"]}
        if len(actual)!=len(observed["blockers"]) or set(actual)!={d["id"] for d in target["blockers"]}:
            raise Problem(422,f"{stage}: blockers differ")
        for d in target["blockers"]:
            m=actual[d["id"]]
            if dist(m["center_mm"],d["center_mm"])>2 or abs(m["radius_mm"]-d["radius_mm"])>1:
                raise Problem(422,f"{stage}: blocker measurements exceed tolerance")
    raw = canonical(record); key = digest(canonical([cid,record]))
    with store.database() as db:
        db.execute("INSERT OR IGNORE INTO calibrations(id,task,record) VALUES(?,?,?)",(key,cid,raw))
        event(db,"calibration.measured",cid,key)
    return {"calibration_sha256":key,"task_id":cid,"stages":list(expected)}


def capture(cid, cal, stage, observer, observed, raw):
    if len(raw)>8*1024*1024:
        raise Problem(413,"Image exceeds 8 MiB")
    try:
        with Image.open(BytesIO(raw)) as im:
            if im.format not in {"JPEG","PNG"} or im.width*im.height>12_000_000 or min(im.size)<64 or getattr(im,"n_frames",1)!=1:
                raise Problem(422,"Use one full PNG or JPEG frame, up to 12 megapixels")
            im.verify()
        with Image.open(BytesIO(raw)) as im:
            output=BytesIO()
            im.convert("RGB").save(output,"PNG")
    except (UnidentifiedImageError,OSError,ValueError,Image.DecompressionBombError) as exc:
        raise Problem(422,"Invalid image") from exc
    clean=output.getvalue(); key=digest(clean)
    if stage not in stages(cid) or observed not in ("YES","NO") or not observer.strip():
        raise Problem(422,"Invalid observation")
    with store.database() as db:
        db.execute("BEGIN IMMEDIATE")
        active=db.execute("SELECT id FROM calibrations WHERE task=? ORDER BY rowid DESC LIMIT 1",(cid,)).fetchone()
        if not active or active[0]!=cal:
            raise Problem(409,"Active measured calibration required")
        if db.execute("SELECT 1 FROM captures WHERE (cal=? AND stage=?) OR digest=?",(cal,stage,key)).fetchone():
            raise Problem(409,"Stage or frame already recorded")
        db.execute("INSERT INTO captures(cal,stage,observed,observer,png,digest,original,original_digest) VALUES(?,?,?,?,?,?,?,?)",
                   (cal,stage,observed,observer,clean,key,raw,digest(raw)))
        event(db,"capture.recorded",cid,key)
    return {"status":"recorded","image_sha256":key,"original_sha256":digest(raw)}


def status(cid):
    expected=stages(cid)
    calibrations=rows("SELECT id FROM calibrations WHERE task=? ORDER BY rowid DESC LIMIT 1",(cid,))
    result={"task_id":cid,"required_stages":list(expected),"recorded":[],"state":"pending"}
    if not calibrations:
        return result
    cal=calibrations[0]["id"]
    captures=rows("SELECT stage,observed,digest,png,original,original_digest FROM captures WHERE cal=? ORDER BY stage",(cal,))
    result.update(calibration_sha256=cal,recorded=[r["stage"] for r in captures],state="calibrated" if not captures else "partial")
    if any(digest(r["png"])!=r["digest"] or digest(r["original"])!=r["original_digest"] for r in captures):
        result["state"]="integrity_error"
    elif len(captures)==len(expected):
        matched=all((r["observed"]=="YES")==expected[r["stage"]]["solver_checks"][0]["visible"] for r in captures)
        result["state"]="complete_agrees" if matched else "complete_disagrees"
    return result


def summary(dataset=None):
    query="SELECT DISTINCT task FROM calibrations"
    args=()
    if dataset:
        query+=" WHERE task IN (SELECT id FROM cases WHERE dataset=?)"; args=(dataset,)
    cases=[status(r["task"]) for r in rows(query,args)]
    agreeing=[r["task_id"] for r in cases if r["state"]=="complete_agrees"]
    kinds={len(stages(cid)) for cid in agreeing}
    disputes=sum(r["state"] in {"complete_disagrees","integrity_error"} for r in cases)
    return {"calibrated_cases":len(cases),"agreeing_complete_cases":len(agreeing),"disagreeing_complete_cases":disputes,
            "partial_cases":len(cases)-len(agreeing)-disputes,
            "gate_passed":len(agreeing)>=5 and len(kinds)==3 and disputes==0}
