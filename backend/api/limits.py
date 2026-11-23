"""Bound request bodies before JSON or multipart parsing and throttle interactive generation."""
import json
import os
import time
from urllib.parse import urlsplit

from backend.db.store import database
from backend.services.common import Problem,consume,digest


class Limits:
    def __init__(self,app):
        self.app=app

    async def __call__(self,scope,receive,send):
        if scope["type"]!="http":
            return await self.app(scope,receive,send)
        if scope["method"]!="POST":
            return await self.app(scope,receive,send)
        headers=dict(scope["headers"])
        async def fail(status,detail):
            await send({"type":"http.response.start","status":status,"headers":[(b"content-type",b"application/json"),(b"cache-control",b"no-store")]})
            await send({"type":"http.response.body","body":json.dumps({"detail":detail}).encode()})
        origin=headers.get(b"origin",b"").decode("latin1")
        allowed={s.strip() for s in os.getenv("MISSING_SCRATCH_UI_ORIGINS","").split(",") if s.strip()}
        # Browser writes must originate from this API host or an explicitly configured UI.
        if origin and origin not in allowed and origin!=scope["scheme"]+"://"+headers.get(b"host",b"").decode("latin1"):
            return await fail(403,"Origin is not allowed")
        limit=9*1024*1024 if scope["path"].endswith("/observations") else 4*1024*1024
        parts=[]; size=0
        while True:
            message=await receive()
            if message["type"]=="http.disconnect":
                return
            data=message.get("body",b"");size+=len(data)
            if size>limit:
                return await fail(413,"Request too large")
            parts.append(data)
            if not message.get("more_body"):
                break
        if scope["path"] in ("/api/tasks/generate","/api/tasks/generate-pair"):
            hour=int(time.time()//3600)
            addr=(scope.get("client") or ("local",))[0]
            try:
                with database() as db:
                    db.execute("BEGIN IMMEDIATE")
                    consume(db,f"hour:{hour}:{digest(addr)[:16]}",int(os.getenv("MS_GENERATE_PER_HOUR","120")))
                    consume(db,f"hour:{hour}:global",int(os.getenv("MS_GLOBAL_GENERATE_PER_HOUR","1200")))
                    db.execute("DELETE FROM quotas WHERE bucket LIKE 'hour:%' AND bucket<?",(f"hour:{hour-1}:",))
            except Problem as exc:
                return await fail(exc.status,exc.detail)
        body=b"".join(parts)
        delivered=False
        async def buffered():
            nonlocal delivered
            if delivered:
                return await receive()
            delivered=True
            return {"type":"http.request","body":body,"more_body":False}
        await self.app(scope,buffered,send)
