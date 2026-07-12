from clinical_stat_agent.database import load_qa, save_feedback, save_qa


def test_qa_history_and_feedback_are_persistent(demo):
    _, con, *_ = demo
    answer = {"answer": "Bilingual answer（双语回答）", "citations": [], "confidence": "medium"}
    qa_id = save_qa(con, "NSCLC-DEMO-001", "session-test", "What is PFS?（什么是PFS？）", answer, "mock")
    history = load_qa(con, "NSCLC-DEMO-001", "session-test")
    assert len(history) == 1
    assert history[0]["question"].endswith("（什么是PFS？）")
    assert history[0]["answer"]["answer"] == answer["answer"]
    save_feedback(con, qa_id, "Helpful")
    assert load_qa(con, "NSCLC-DEMO-001", "session-test")[0]["feedback"] == "Helpful"
