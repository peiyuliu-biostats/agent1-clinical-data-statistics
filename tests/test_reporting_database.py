from io import BytesIO

import openpyxl

from clinical_stat_agent.reporting import excel_report, html_report
from clinical_stat_agent.service import snapshot


def test_snapshot_and_reports(demo):
    root, con, *_ = demo
    state = snapshot(con, root)
    html = html_report(state["study"], state["disease"], state["terms"], state["relationships"], state["issues"])
    assert b"AI-assisted draft" in html
    xlsx = excel_report(state["study"], state["disease"], state["documents"], state["terms"], state["relationships"], state["issues"])
    wb = openpyxl.load_workbook(BytesIO(xlsx), read_only=True)
    assert {"Study_Summary", "Disease_Context", "Documents", "Terminology", "Relationships", "Issues", "Read_Me"}.issubset(wb.sheetnames)


def test_audit_log_exists(demo):
    _, con, *_ = demo
    count = con.execute("SELECT count(*) FROM audit WHERE study_id='NSCLC-DEMO-001'").fetchone()[0]
    assert count >= 1
