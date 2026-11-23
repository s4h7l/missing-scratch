"""SQLite storage for task metadata, images and immutable first predictions."""

from contextlib import contextmanager, closing
import json
import os
from pathlib import Path
import sqlite3

RUNTIME_DIR = Path(os.getenv("MISSING_SCRATCH_RUNTIME", "runtime"))


@contextmanager
def database():
    with closing(sqlite3.connect(RUNTIME_DIR / "missing_scratch.sqlite3", timeout=10)) as db:
        db.row_factory = sqlite3.Row
        db.execute("PRAGMA foreign_keys=ON")
        with db:
            yield db


def initialize() -> None:
    RUNTIME_DIR.mkdir(parents=True, exist_ok=True)
    with database() as db:
        db.execute("PRAGMA journal_mode=WAL")
        db.executescript(Path(__file__).with_name("v3.sql").read_text(encoding="utf-8-sig"))
        db.executescript("""
            CREATE TABLE IF NOT EXISTS tasks (
                task_id TEXT PRIMARY KEY, public_json TEXT NOT NULL,
                private_json TEXT NOT NULL, image_path TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now'))
            );
            CREATE TABLE IF NOT EXISTS predictions (
                session_id TEXT NOT NULL, task_id TEXT NOT NULL REFERENCES tasks(task_id),
                prediction TEXT NOT NULL,
                created_at TEXT NOT NULL DEFAULT (strftime('%Y-%m-%dT%H:%M:%fZ','now')),
                PRIMARY KEY (session_id, task_id)
            );
            CREATE TABLE IF NOT EXISTS task_images (
                task_id TEXT PRIMARY KEY REFERENCES tasks(task_id),
                input_png BLOB NOT NULL, reveal_png BLOB NOT NULL
            );
            CREATE TABLE IF NOT EXISTS pair_members (
                task_id TEXT PRIMARY KEY REFERENCES tasks(task_id), pair_id TEXT NOT NULL
            );
            CREATE INDEX IF NOT EXISTS pair_lookup ON pair_members(pair_id);
        """)


def save_batch(records):
    with database() as db:
        for public, private, input_png, reveal_png in records:
            task_id = public["task_id"]
            db.execute("INSERT INTO tasks(task_id,public_json,private_json,image_path) VALUES(?,?,?,'')",
                       (task_id, json.dumps(public), json.dumps(private)))
            db.execute("INSERT INTO task_images VALUES(?,?,?)", (task_id, input_png, reveal_png))
            if public["pair_id"]:
                db.execute("INSERT INTO pair_members VALUES(?,?)", (task_id, public["pair_id"]))


def metadata(task_id, private=False):
    query = "SELECT private_json FROM tasks WHERE task_id=?" if private else "SELECT public_json FROM tasks WHERE task_id=?"
    with database() as db:
        row = db.execute(query, (task_id,)).fetchone()
    return json.loads(row[0]) if row else None


def image_bytes(task_id, reveal=False):
    query = "SELECT reveal_png FROM task_images WHERE task_id=?" if reveal else "SELECT input_png FROM task_images WHERE task_id=?"
    with database() as db:
        row = db.execute(query, (task_id,)).fetchone()
        if row:
            return row[0]
        # Old visibility tasks stored their public PNG on disk.
        if not reveal:
            old = db.execute("SELECT image_path FROM tasks WHERE task_id=?", (task_id,)).fetchone()
            if old and old[0] and Path(old[0]).is_file():
                return Path(old[0]).read_bytes()
    return None


def save_prediction(session_id, task_id, prediction):
    with database() as db:
        db.execute("""INSERT INTO predictions(session_id,task_id,prediction) VALUES(?,?,?)
                      ON CONFLICT(session_id,task_id) DO NOTHING""", (session_id, task_id, prediction))
        saved = db.execute("SELECT prediction FROM predictions WHERE session_id=? AND task_id=?",
                           (session_id, task_id)).fetchone()
        return saved[0] == prediction


def locked_prediction(session_id, task_id, pair_id):
    with database() as db:
        if pair_id:
            missing = db.execute("""
                SELECT 1 FROM pair_members m WHERE m.pair_id=? AND NOT EXISTS (
                    SELECT 1 FROM predictions p WHERE p.task_id=m.task_id AND p.session_id=?
                ) LIMIT 1
            """, (pair_id, session_id)).fetchone()
            if missing:
                return None
        row = db.execute("SELECT prediction FROM predictions WHERE session_id=? AND task_id=?",
                         (session_id, task_id)).fetchone()
    return row[0] if row else None
