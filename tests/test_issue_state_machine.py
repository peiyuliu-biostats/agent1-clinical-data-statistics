import pytest

from clinical_stat_agent.database import update_issue_status
from clinical_stat_agent.service import snapshot


def test_valid_issue_transition_is_audited(demo):
    root, con, *_ = demo
    state = snapshot(con, root)
    issue_id = state["issues"][0]["issue_id"]
    updated = update_issue_status(con, "NSCLC-DEMO-001", issue_id, "Under Review", "Reviewed source evidence.", "Test Reviewer")
    assert updated["status"] == "Under Review"
    row = con.execute("SELECT from_status,to_status,actor,rationale FROM issue_history WHERE issue_id=?", (issue_id,)).fetchone()
    assert tuple(row) == ("Open", "Under Review", "Test Reviewer", "Reviewed source evidence.")


def test_invalid_transition_is_rejected(demo):
    _, con, *_ = demo
    issue_id = con.execute("SELECT issue_id FROM issues LIMIT 1").fetchone()[0]
    with pytest.raises(ValueError, match="Invalid issue transition"):
        update_issue_status(con, "NSCLC-DEMO-001", issue_id, "Resolved", "Skipping review is not allowed.")


def test_rationale_is_required(demo):
    _, con, *_ = demo
    issue_id = con.execute("SELECT issue_id FROM issues LIMIT 1").fetchone()[0]
    with pytest.raises(ValueError, match="rationale"):
        update_issue_status(con, "NSCLC-DEMO-001", issue_id, "Under Review", "")
