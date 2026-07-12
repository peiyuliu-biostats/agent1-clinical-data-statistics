from __future__ import annotations

import json
from pathlib import Path

from .database import audit, connect, reset_study
from .ingestion import ingest
from .knowledge import extract_terms
from .specs import check_spec, demo_relationships

STUDY_ID = "NSCLC-DEMO-001"


def demo_root(root: Path) -> Path:
    return root / "sample_studies" / STUDY_ID


def load_disease(root: Path) -> dict:
    return json.loads((demo_root(root) / "disease_context.json").read_text(encoding="utf-8"))


def initialize_demo(root: Path, db_path: Path | None = None):
    con = connect(db_path)
    reset_study(con, STUDY_ID)
    study = {"id": STUDY_ID, "title": "Randomized Phase III NSCLC Study", "therapeutic_area": "Oncology", "indication": "Non-Small Cell Lung Cancer", "phase": "Phase III", "design": "Randomized, double-blind, active-controlled"}
    con.execute("INSERT INTO studies(id,title,therapeutic_area,indication,phase,design) VALUES(:id,:title,:therapeutic_area,:indication,:phase,:design)", study)
    base = demo_root(root)
    files = [
        (base / "documents" / "Protocol_NSCLC_DEMO.txt", "Protocol", "project"),
        (base / "documents" / "SAP_NSCLC_DEMO.txt", "SAP", "project"),
        (base / "disease_context.json", "Disease Context", "disease"),
        (base / "specifications" / "SDTM_Spec.xlsx", "SDTM Spec", "project"),
        (base / "specifications" / "ADaM_Spec.xlsx", "ADaM Spec", "project"),
        (base / "metadata" / "raw_metadata.csv", "Raw Metadata", "project"),
    ]
    parsed = [ingest(con, STUDY_ID, p, kind, source) for p, kind, source in files]
    all_issues = []
    for path, kind in [(files[3][0], "SDTM"), (files[4][0], "ADAM")]:
        _, issues = check_spec(path, kind)
        all_issues.extend(issues)
    for issue in all_issues:
        con.execute("INSERT OR REPLACE INTO issues(issue_id,study_id,payload) VALUES(?,?,?)", (issue.issue_id, STUDY_ID, issue.model_dump_json()))
    audit(con, STUDY_ID, "demo_initialized", {"documents": len(parsed), "issues": len(all_issues)})
    con.commit()
    return con, study, parsed, all_issues


def snapshot(con, root: Path) -> dict:
    study = dict(con.execute("SELECT * FROM studies WHERE id=?", (STUDY_ID,)).fetchone())
    documents = [dict(r) for r in con.execute("SELECT name,kind,status,version,details FROM documents WHERE study_id=?", (STUDY_ID,))]
    issues = [json.loads(r[0]) for r in con.execute("SELECT payload FROM issues WHERE study_id=?", (STUDY_ID,))]
    history = [dict(r) for r in con.execute(
        "SELECT issue_id,from_status,to_status,actor,rationale,created_at FROM issue_history WHERE study_id=? ORDER BY id DESC",
        (STUDY_ID,),
    )]
    return {"study": study, "documents": documents, "disease": load_disease(root), "terms": extract_terms(con, STUDY_ID), "relationships": [r.model_dump() for r in demo_relationships()], "issues": issues, "issue_history": history}
