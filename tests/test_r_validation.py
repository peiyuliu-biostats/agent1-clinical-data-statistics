from clinical_stat_agent.r_validation import validate_csv_with_r


def test_r_validation_on_demo_data(demo):
    root, *_ = demo
    path = root / "sample_studies" / "NSCLC-DEMO-001" / "data" / "adsl_sample.csv"
    result = validate_csv_with_r(path)
    assert result["engine"] == "R"
    assert result["rows"] == 60
    assert result["passed"] is True
