from clinical_stat_agent.agent import answer_question
from clinical_stat_agent.knowledge import extract_terms, search


def test_retrieval_and_terms(demo):
    _, con, *_ = demo
    hits = search(con, "NSCLC-DEMO-001", "PFS progression")
    assert hits
    terms = {x["term"] for x in extract_terms(con, "NSCLC-DEMO-001")}
    assert {"PFS", "OS", "ORR", "PD", "ITT", "ADSL", "ADTTE"}.issubset(terms)


def test_mock_answer_is_cited_and_flags_conflict(demo, monkeypatch):
    from clinical_stat_agent.config import Settings
    mock_settings = Settings(mode="mock")
    monkeypatch.setattr("clinical_stat_agent.agent.settings", mock_settings)
    _, con, *_ = demo
    answer = answer_question(con, "NSCLC-DEMO-001", "本项目的 PFS 如何定义？")
    assert answer.citations
    assert answer.questions_for_review
    valid_ids = {r[0] for r in con.execute("SELECT id FROM chunks")}
    assert all(c.source_id in valid_ids for c in answer.citations)


def test_no_evidence_fails_safely(demo, monkeypatch):
    from clinical_stat_agent.config import Settings
    monkeypatch.setattr("clinical_stat_agent.agent.settings", Settings(mode="mock"))
    _, con, *_ = demo
    answer = answer_question(con, "NSCLC-DEMO-001", "ZXQJ nonexistent concept")
    assert answer.confidence == "low"
    assert answer.uncertainties
