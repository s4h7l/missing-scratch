import secrets
import time
from backend.db.store import database
from .common import digest


def active(token):
    if not token or len(token)>160:
        return False
    with database() as db:
        return bool(db.execute("SELECT 1 FROM sessions WHERE id=? AND expires>?",(digest(token),time.time())).fetchone())


def issue():
    token=secrets.token_urlsafe(32)
    with database() as db:
        db.execute("DELETE FROM sessions WHERE expires<?",(time.time(),))
        db.execute("INSERT INTO sessions VALUES(?,?)",(digest(token),time.time()+8*3600))
    return token
