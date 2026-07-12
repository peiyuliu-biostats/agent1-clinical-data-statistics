import json

import pandas as pd


def test_complete_synthetic_package_exists(demo):
    root, *_ = demo
    data = root / "sample_studies" / "NSCLC-DEMO-001" / "data"
    manifest = json.loads((data / "manifest.json").read_text(encoding="utf-8"))
    assert manifest["synthetic"] is True
    assert manifest["subjects"] == 60
    names = {x["name"] for x in manifest["datasets"]}
    assert {"raw_demog", "raw_tumor", "raw_ae", "raw_exposure", "dm", "ds", "ae", "ex", "tu", "tr", "rs", "adsl", "adtte", "adeff"}.issubset(names)
    adsl = pd.read_csv(data / "adam" / "adsl.csv")
    adtte = pd.read_csv(data / "adam" / "adtte.csv")
    assert adsl.USUBJID.nunique() == 60
    assert len(adtte) == 120
    assert set(adtte.PARAMCD) == {"PFS", "OS"}
