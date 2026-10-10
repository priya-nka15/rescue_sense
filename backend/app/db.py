import json
import sqlite3
from pathlib import Path
from threading import Lock
from contextlib import contextmanager

from .config import settings

_lock = Lock()


@contextmanager
def connect():
    settings.database_path.parent.mkdir(parents=True, exist_ok=True)
    connection = sqlite3.connect(settings.database_path, check_same_thread=False)
    connection.row_factory = sqlite3.Row
    try:
        with connection:
            yield connection
    finally:
        connection.close()


def insert_job(job_id: str, modality: str, created_at: str) -> bool:
    with _lock, connect() as db:
        db.execute('BEGIN IMMEDIATE')
        if db.execute("SELECT count(*) FROM jobs WHERE status IN ('queued','processing')").fetchone()[0] >= 4:
            return False
        db.execute('INSERT INTO jobs(id,status,stage,modality,created_at) VALUES (?,?,?,?,?)',
                   (job_id, 'queued', 'queued', modality, created_at))
        return True


def initialize() -> None:
    with _lock, connect() as db:
        db.executescript("""
        CREATE TABLE IF NOT EXISTS jobs (
          id TEXT PRIMARY KEY, status TEXT NOT NULL, stage TEXT NOT NULL,
          modality TEXT NOT NULL, error TEXT, result_json TEXT, created_at TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS analyses (
          id TEXT PRIMARY KEY, modality TEXT NOT NULL, verdict TEXT NOT NULL,
          created_at TEXT NOT NULL, result_json TEXT NOT NULL
        );
        CREATE TABLE IF NOT EXISTS evidence_documents (
          id TEXT PRIMARY KEY, title TEXT NOT NULL, body TEXT NOT NULL,
          publisher TEXT, url TEXT, category TEXT NOT NULL, published_at TEXT
        );
        CREATE TABLE IF NOT EXISTS experiment_runs (
          id TEXT PRIMARY KEY, created_at TEXT NOT NULL, config_json TEXT NOT NULL,
          metrics_json TEXT
        );
        """)
        columns = {row[1] for row in db.execute('PRAGMA table_info(evidence_documents)')}
        for name in ('ingested_at', 'source_note', 'reviewed_claim', 'relation', 'reviewer', 'passage', 'content_sha256', 'published_at'):
            if name not in columns:
                db.execute(f'ALTER TABLE evidence_documents ADD COLUMN {name} TEXT')


def transition(job_id: str, old: str, new: str, error: str | None = None) -> bool:
    with _lock, connect() as db:
        return db.execute('UPDATE jobs SET status=?,stage=?,error=? WHERE id=? AND status=?',
                          (new, new, error, job_id, old)).rowcount == 1


def complete_job(job_id: str, result) -> None:
    with _lock, connect() as db:
        payload = result.model_dump_json()
        changed = db.execute("UPDATE jobs SET status='completed',stage='completed',result_json=? WHERE id=? AND status='processing'", (payload, job_id)).rowcount
        if changed:
            db.execute('INSERT INTO analyses (id,modality,verdict,created_at,result_json) VALUES (?,?,?,?,?)',
                       (job_id, result.modality, result.verdict, result.created_at.isoformat(), payload))


def delete_result(analysis_id: str) -> None:
    with _lock, connect() as db:
        db.execute('DELETE FROM analyses WHERE id=?', (analysis_id,))
        db.execute("DELETE FROM jobs WHERE id=? AND status IN ('completed','failed','cancelled')", (analysis_id,))


def execute(sql: str, params: tuple = ()) -> None:
    with _lock, connect() as db:
        db.execute(sql, params)


def one(sql: str, params: tuple = ()) -> dict | None:
    with _lock, connect() as db:
        row = db.execute(sql, params).fetchone()
    return dict(row) if row else None


def many(sql: str, params: tuple = ()) -> list[dict]:
    with _lock, connect() as db:
        rows = db.execute(sql, params).fetchall()
    return [dict(row) for row in rows]


def json_value(value: object) -> str:
    return json.dumps(value, ensure_ascii=True, separators=(",", ":"))
