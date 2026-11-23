"""Local operator commands. Run from the same project and runtime directory as the API."""

import argparse
import hashlib
import json
import os
from pathlib import Path
import platform
import secrets
import time

from backend.db import store
from backend.services import benchmark,datasets,review
from backend.services.common import Problem,canonical,rows


def reproduction(output):
    from PIL import __version__ as pillow_version
    output.mkdir(exist_ok=True,parents=True)
    suite=datasets.build("corrected",100,0)
    did=suite["dataset_id"]
    pack=datasets.export(did)
    (output/"corrected-inputs.zip").write_bytes(pack)
    data=rows("SELECT id,layout,pair,digest,kind,difficulty FROM cases WHERE dataset=? ORDER BY position",(did,))
    import zlib
    code=hashlib.sha256()
    for path in sorted(Path(__file__).parent.rglob("*")):
        if path.suffix in {".sql",".py"}:
            code.update(path.relative_to(Path(__file__).parent).as_posix().encode()+b"\0"+path.read_bytes().replace(b"\r\n",b"\n"))
    record={**suite,"source_sha256":code.hexdigest(),"zip_sha256":hashlib.sha256(pack).hexdigest(),
            "python":platform.python_version(),"os":platform.platform(),"pillow":pillow_version,"zlib":zlib.ZLIB_RUNTIME_VERSION,
            "layout_seeds":list(range(81602,81622)),"generator":datasets.VERSION,"cases":data}
    (output/"reproduction.json").write_text(json.dumps(record,indent=2),encoding="utf8")
    return suite


def local_settings():
    path=store.RUNTIME_DIR/"local-access.json"
    if not path.exists():
        try:
            with path.open("x",encoding="utf8") as f:
                json.dump({k:secrets.token_urlsafe(32) for k in ("MS_OPERATOR_TOKEN","MS_JUDGE_CODE")},f)
            if os.name!="nt":
                path.chmod(0o600)
        except FileExistsError:
            pass
    for k,v in json.loads(path.read_text(encoding="utf8")).items():
        if k in ("MS_OPERATOR_TOKEN","MS_JUDGE_CODE"):
            os.environ.setdefault(k,v)
    return path


def main():
    parser=argparse.ArgumentParser()
    sub=parser.add_subparsers(dest="verb",required=True)
    p=sub.add_parser("serve");p.add_argument("--port",type=int,default=8000)
    p=sub.add_parser("reproduce");p.add_argument("--output",type=Path,default=Path("release"))
    p=sub.add_parser("schema");p.add_argument("--output",type=Path,default=Path("contracts/openapi.json"))
    p=sub.add_parser("worker");p.add_argument("run_id")
    p=sub.add_parser("score");p.add_argument("run_id")
    p=sub.add_parser("replay");p.add_argument("report",type=Path)
    p=sub.add_parser("packets");p.add_argument("dataset_id");p.add_argument("--count",type=int,default=72)
    p.add_argument("--output",type=Path,required=True)
    args=parser.parse_args()
    store.initialize()
    if args.verb=="serve":
        import uvicorn
        path=local_settings()
        print("Local operator and judge credentials:",path.resolve(),flush=True)
        uvicorn.run("backend.main:app",host="127.0.0.1",port=args.port)
        return
    if args.verb=="reproduce":
        result=reproduction(args.output)
    elif args.verb=="schema":
        from backend.main import app
        args.output.parent.mkdir(exist_ok=True,parents=True)
        args.output.write_text(json.dumps(app.openapi(),sort_keys=True,indent=2)+"\n",encoding="utf8")
        result={"schema":str(args.output)}
    elif args.verb=="worker":
        while True:
            result=benchmark.step(args.run_id,1)
            if result["state"]=="complete":
                break
            if not result["states"].get("pending"):
                time.sleep(3)
    elif args.verb=="score":
        result=benchmark.score(args.run_id)
    elif args.verb=="replay":
        from backend.schemas.v3 import Replay
        result=benchmark.replay(Replay.model_validate_json(args.report.read_bytes()).model_dump())
    else:
        existing=rows("SELECT id FROM reviews WHERE dataset=?",(args.dataset_id,))
        rid=existing[0]["id"] if existing else review.create(args.dataset_id,args.count)["review_id"]
        args.output.mkdir(exist_ok=True,parents=True)
        for reviewer in review.REVIEWERS:
            (args.output/(reviewer+".zip")).write_bytes(review.packet(rid,reviewer))
        result={"review_id":rid,"output":str(args.output)}
    print(json.dumps(result,indent=2))


if __name__=="__main__":
    try:
        main()
    except Problem as exc:
        raise SystemExit(f"{exc.status}: {exc.detail}")
