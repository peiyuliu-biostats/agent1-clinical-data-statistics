from pathlib import Path

from clinical_stat_agent.specs import check_spec, demo_relationships, draft_spec


def test_demo_specs_find_seeded_issues(demo):
    root, *_ = demo
    base = root / "sample_studies" / "NSCLC-DEMO-001" / "specifications"
    _, sdtm_issues = check_spec(base / "SDTM_Spec.xlsx", "SDTM")
    _, adam_issues = check_spec(base / "ADaM_Spec.xlsx", "ADAM")
    categories = {i.category for i in sdtm_issues + adam_issues}
    assert {"Traceability gap", "Non-executable", "Invalid type"}.issubset(categories)


def test_draft_specs_have_required_rows():
    assert len(draft_spec("SDTM")) >= 3
    assert len(draft_spec("ADAM")) >= 3


def test_relationships_include_pfs_gap():
    rel = demo_relationships()
    assert len(rel) == 3
    assert any(x.endpoint == "PFS" and x.status == "Gap" for x in rel)
