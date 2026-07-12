from __future__ import annotations

import re

from .models import Citation

TERMS = {
    "PFS": ("Progression-Free Survival", "Time from randomization to progression or death, as project-defined."),
    "OS": ("Overall Survival", "Time from a defined origin to death from any cause."),
    "ORR": ("Objective Response Rate", "Proportion with a qualifying objective response."),
    "DOR": ("Duration of Response", "Time from first qualifying response to progression or death, as defined."),
    "BOR": ("Best Overall Response", "Best response achieved over the specified assessment period."),
    "PD": ("Context dependent", "Progressive Disease in efficacy context; Protocol Deviation in DV/quality context."),
    "CR": ("Context dependent", "Complete Response in tumor response context; may mean creatinine in laboratory context."),
    "ITT": ("Intent-to-Treat", "Analysis principle/population that must be defined in the project."),
    "FAS": ("Full Analysis Set", "Population concept aligned as closely as possible with the ITT principle."),
    "TEAE": ("Treatment-Emergent Adverse Event", "AE meeting the project-specified treatment-emergent window."),
    "SAE": ("Serious Adverse Event", "Adverse event meeting seriousness criteria."),
    "AESI": ("Adverse Event of Special Interest", "Event of scientific/medical interest defined for a product or program."),
    "ADSL": ("Subject-Level Analysis Dataset", "One record per subject analysis dataset."),
    "ADTTE": ("Time-to-Event Analysis Dataset", "Basic data structure for time-to-event analyses."),
    "RECIST": ("Response Evaluation Criteria in Solid Tumors", "Standardized solid-tumor response assessment framework."),
}


def search(con, study_id: str, query: str, limit: int = 8) -> list[dict]:
    words = [w for w in re.findall(r"[A-Za-z0-9_-]{2,}", query) if w.lower() not in {"what", "how", "the", "is", "and", "this"}]
    if not words:
        words = [query]
    expression = " OR ".join(f'"{w}"' for w in words[:8])
    try:
        rows = con.execute(
            """SELECT c.* FROM chunks_fts f JOIN chunks c ON c.id=f.id
               WHERE chunks_fts MATCH ? AND c.study_id=? LIMIT ?""",
            (expression, study_id, limit),
        ).fetchall()
    except Exception:
        rows = con.execute(
            "SELECT * FROM chunks WHERE study_id=? AND lower(text) LIKE ? LIMIT ?",
            (study_id, f"%{query.lower()}%", limit),
        ).fetchall()
    return [dict(r) for r in rows]


def extract_terms(con, study_id: str) -> list[dict]:
    corpus = "\n".join(r[0] for r in con.execute("SELECT text FROM chunks WHERE study_id=?", (study_id,)))
    result = []
    for term, (expanded, definition) in TERMS.items():
        count = len(re.findall(rf"\b{re.escape(term)}\b", corpus, re.I))
        if count:
            context = "Oncology efficacy" if term in {"PFS", "OS", "ORR", "DOR", "BOR", "RECIST"} else "Project/clinical data"
            result.append({"term": term, "expanded_name": expanded, "definition": definition, "context": context, "occurrences": count, "confidence": "High" if term not in {"PD", "CR"} else "Context review"})
    return result


def citations_from_hits(hits: list[dict], max_excerpt: int = 260) -> list[Citation]:
    return [Citation(source_id=h["id"], document=h["document"], location=h["location"], excerpt=h["text"][:max_excerpt], source_class=h["source_class"]) for h in hits]
