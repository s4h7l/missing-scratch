from hashlib import sha256
from io import BytesIO
import json
from zipfile import ZipFile, ZipInfo, ZIP_DEFLATED

from backend.db.store import database


class Problem(Exception):
    def __init__(self, status, detail):
        self.status, self.detail = status, detail
        super().__init__(detail)


def canonical(obj):
    return json.dumps(obj, ensure_ascii=False, sort_keys=True, separators=(",", ":"), allow_nan=False)


def digest(data):
    if isinstance(data, str):
        data = data.encode()
    return sha256(data).hexdigest()


def one(query, args=()):
    with database() as db:
        row = db.execute(query, args).fetchone()
    if row is None:
        raise Problem(404, "Resource not found")
    return dict(row)


def rows(query, args=()):
    with database() as db:
        return [dict(r) for r in db.execute(query, args)]


def archive(files):
    out = BytesIO()
    with ZipFile(out, "w") as z:
        for name, data in files:
            info = ZipInfo(name, (2026, 1, 1, 0, 0, 0))
            info.compress_type = ZIP_DEFLATED
            z.writestr(info, data)
    return out.getvalue()


def event(db, action, obj, checksum=""):
    db.execute("INSERT INTO events(action,object_id,digest) VALUES(?,?,?)", (action,obj,checksum))


def consume(db, key, limit):
    cursor = db.execute("""INSERT INTO quotas VALUES(?,1) ON CONFLICT(bucket)
        DO UPDATE SET count=count+1 WHERE count<?""", (key, limit))
    if not cursor.rowcount or limit <= 0:
        raise Problem(429, "Request budget exhausted")
