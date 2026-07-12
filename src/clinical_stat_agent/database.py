from __future__ import annotations

import json
import sqlite3
from pathlib import Path

from .config import settings

SCHEMA = """
CREATE TABLE IF NOT EXISTS studies (
 id TEXT PRIMARY KEY, title TEXT NOT NULL, therapeutic_area TEXT, indication TEXT,
 phase TEXT, design TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS documents (
 id TEXT PRIMARY KEY, study_id TEXT, name TEXT, kind TEXT, sha256 TEXT, status TEXT,
 version TEXT, details TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS chunks (
 id TEXT PRIMARY KEY, study_id TEXT, document_id TEXT, document TEXT, location TEXT,
 source_class TEXT, text TEXT
);
CREATE VIRTUAL TABLE IF NOT EXISTS chunks_fts USING fts5(id UNINDEXED, text);
CREATE TABLE IF NOT EXISTS issues (
 issue_id TEXT PRIMARY KEY, study_id TEXT, payload TEXT, created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS issue_history (
 id INTEGER PRIMARY KEY AUTOINCREMENT, issue_id TEXT, study_id TEXT,
 from_status TEXT, to_status TEXT, actor TEXT, rationale TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS qa_history (
 id INTEGER PRIMARY KEY AUTOINCREMENT, study_id TEXT, session_id TEXT,
 question TEXT, answer_json TEXT, mode TEXT, feedback TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
CREATE TABLE IF NOT EXISTS audit (
 id INTEGER PRIMARY KEY AUTOINCREMENT, study_id TEXT, event_type TEXT, details TEXT,
 created_at TEXT DEFAULT CURRENT_TIMESTAMP
);
"""


def connect(path: Path | None = None) -> sqlite3.Connection:
    db = path or settings.db_path
    db.parent.mkdir(parents=True, exist_ok=True)
    con = sqlite3.connect(db)
    con.row_factory = sqlite3.Row
    con.executescript(SCHEMA)
    return con


ISSUE_TRANSITIONS = {
    "Open": {"Under Review", "Rejected"},
    "Under Review": {"Confirmed", "Rejected", "Open"},
    "Confirmed": {"Resolved", "Under Review"},
    "Resolved": {"Under Review"},
    "Rejected": {"Under Review"},
}


def update_issue_status(
    con: sqlite3.Connection,
    study_id: str,
    issue_id: str,
    to_status: str,
    rationale: str,
    actor: str = "Human Reviewer",
) -> dict:
    row = con.execute(
        "SELECT payload FROM issues WHERE study_id=? AND issue_id=?",
        (study_id, issue_id),
    ).fetchone()
    if row is None:
        raise KeyError(f"Unknown issue: {issue_id}")
    payload = json.loads(row[0])
    from_status = payload.get("status", "Open")
    if to_status not in ISSUE_TRANSITIONS.get(from_status, set()):
        raise ValueError(f"Invalid issue transition: {from_status} -> {to_status}")
    if not rationale.strip():
        raise ValueError("A human decision rationale is required.")
    payload["status"] = to_status
    con.execute(
        "UPDATE issues SET payload=? WHERE study_id=? AND issue_id=?",
        (json.dumps(payload, ensure_ascii=False), study_id, issue_id),
    )
    con.execute(
        """INSERT INTO issue_history
        (issue_id,study_id,from_status,to_status,actor,rationale)
        VALUES(?,?,?,?,?,?)""",
        (issue_id, study_id, from_status, to_status, actor, rationale.strip()),
    )
    con.commit()
    return payload


def reset_study(con: sqlite3.Connection, study_id: str) -> None:
    for table in ("documents", "chunks", "issues", "issue_history", "qa_history", "audit"):
        con.execute(f"DELETE FROM {table} WHERE study_id=?", (study_id,))
    con.execute("DELETE FROM chunks_fts WHERE id NOT IN (SELECT id FROM chunks)")
    con.execute("DELETE FROM studies WHERE id=?", (study_id,))
    con.commit()


def save_qa(con: sqlite3.Connection, study_id: str, session_id: str, question: str, answer: dict, mode: str) -> int:
    cur = con.execute(
        "INSERT INTO qa_history(study_id,session_id,question,answer_json,mode) VALUES(?,?,?,?,?)",
        (study_id, session_id, question, json.dumps(answer, ensure_ascii=False), mode),
    )
    con.commit()
    return int(cur.lastrowid)


def load_qa(con: sqlite3.Connection, study_id: str, session_id: str, limit: int = 30) -> list[dict]:
    rows = con.execute(
        """SELECT id,question,answer_json,mode,feedback,created_at FROM qa_history
        WHERE study_id=? AND session_id=? ORDER BY id DESC LIMIT ?""",
        (study_id, session_id, limit),
    ).fetchall()
    result = []
    for row in reversed(rows):
        item = dict(row)
        item["answer"] = json.loads(item.pop("answer_json"))
        result.append(item)
    return result


def save_feedback(con: sqlite3.Connection, qa_id: int, feedback: str) -> None:
    if feedback not in {"Helpful", "Needs improvement"}:
        raise ValueError("Unsupported feedback value.")
    con.execute("UPDATE qa_history SET feedback=? WHERE id=?", (feedback, qa_id))
    con.commit()


def audit(con: sqlite3.Connection, study_id: str, event_type: str, details: dict | str) -> None:
    value = details if isinstance(details, str) else json.dumps(details, ensure_ascii=False)
    con.execute(
        "INSERT INTO audit(study_id,event_type,details) VALUES(?,?,?)",
        (study_id, event_type, value),
    )
    con.commit()
