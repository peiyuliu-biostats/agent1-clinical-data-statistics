from __future__ import annotations

import json
from pathlib import Path
import sys
from datetime import date, timedelta

import numpy as np
import pandas as pd

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from clinical_stat_agent.specs import ADAM_REQUIRED, SDTM_REQUIRED

BASE = ROOT / "sample_studies" / "NSCLC-DEMO-001"

PROTOCOL = """NSCLC-DEMO-001 — SIMULATED PROTOCOL
Version 1.0. This document is synthetic and for demonstration only.

1. Study Design
This is a randomized, double-blind, active-controlled Phase III study in adults with advanced non-small cell lung cancer (NSCLC). Subjects are randomized 1:1 to Drug X or Control and stratified by PD-L1 category and disease stage.

3. Objectives
Primary objective: evaluate efficacy of Drug X versus Control based on progression-free survival (PFS).
Secondary objectives: compare overall survival (OS), objective response rate (ORR), duration of response (DOR), and safety.

5. Disease Assessment
Tumor assessments are performed every 6 weeks through Week 48 and every 12 weeks thereafter using RECIST 1.1. Responses include complete response (CR), partial response (PR), stable disease (SD), and progressive disease (PD).

9.2.1 Primary Endpoint
PFS is time from randomization to the first documented disease progression per investigator assessment or death from any cause, whichever occurs first. A subject without an event is censored at the last adequate tumor assessment. If two or more consecutive scheduled tumor assessments are missing before progression, the subject is censored at the last adequate assessment before the gap.

9.2.2 Secondary Endpoint
OS is time from randomization to death from any cause. Subjects alive at analysis cutoff are censored at the last known alive date.

9.3 Analysis Population
The intent-to-treat (ITT) population includes all randomized subjects. The safety population includes all subjects receiving at least one dose and is analyzed according to actual treatment received.

10 Statistical Analysis
The primary comparison uses a stratified log-rank test. A stratified Cox model estimates the hazard ratio and confidence interval. Multiplicity follows a hierarchical strategy: PFS, then OS, then ORR. Target enrollment is 420 subjects; detailed assumptions are in the SAP.
"""

SAP = """NSCLC-DEMO-001 — SIMULATED STATISTICAL ANALYSIS PLAN
Version 0.9 Draft. This document is synthetic and for demonstration only.

4 Analysis Sets
The ITT analysis set includes randomized subjects with a valid randomization record. The handling of subjects randomized in error is unresolved. The safety set includes treated subjects.

6 Estimand Framework
The PFS estimand compares randomized treatments in the ITT population. Death is part of the composite endpoint. New anticancer therapy is handled with a treatment-policy strategy. The strategy for prolonged missing tumor assessments requires final confirmation.

7.1 PFS Analysis
PFS is analyzed by stratified log-rank test and summarized by Kaplan-Meier methods. Hazard ratio and 95% confidence interval use a stratified Cox model. Contrary to Protocol Section 9.2.1, progression after two or more missed assessments is currently counted as an event at the progression date. This discrepancy must be resolved before SAP finalization.

7.2 OS Analysis
OS is analyzed using stratified log-rank and Cox methods. Subjects alive are censored at last known alive date.

7.3 ORR
Confirmed CR or PR is summarized and compared using a stratified Cochran-Mantel-Haenszel method. Exact derivation traceability to RS/TR/TU is pending.

9 Missing Data and Sensitivity Analyses
Sensitivity analyses for PFS will assess alternative handling of prolonged missing assessments. Exact algorithms are not yet specified.

12 Safety
Treatment-emergent adverse events (TEAEs), serious adverse events (SAEs), and adverse events of special interest (AESIs) are summarized in the safety population.
"""

DISEASE = {
    "indication": "Non-Small Cell Lung Cancer (NSCLC)",
    "scope": "Synthetic Phase III solid-tumor demonstration context",
    "summary": "NSCLC is the major class of lung cancer and includes clinically and molecularly heterogeneous subtypes. Trial interpretation depends on stage, histology, biomarkers, prior therapy, response criteria and assessment schedule.",
    "trial_relevance": ["Tumor response and progression require predefined assessment criteria.", "Biomarkers and disease stage can influence eligibility, stratification and subgroup analyses.", "Subsequent anticancer therapy and missing tumor assessments are important intercurrent events."],
    "common_endpoints": ["PFS", "OS", "ORR", "DOR"],
    "common_sdtm_domains": ["DM", "DS", "AE", "EX", "RS", "TR", "TU"],
    "common_adam_datasets": ["ADSL", "ADTTE", "ADEFF", "ADAE"],
    "statistical_considerations": ["Define event and censoring rules before unblinding.", "Align assessment schedule and missing-assessment rules with the estimand.", "Predefine treatment switching/new anticancer therapy handling.", "Maintain traceability from response records to efficacy parameters."],
    "source_note": "Educational summary requiring clinician and senior statistician review; project definitions take priority."
}


def build_synthetic_data() -> dict[str, pd.DataFrame]:
    """Create a deterministic, clinically plausible demonstration package with no real patients."""
    rng = np.random.default_rng(20260712)
    n = 60
    start = date(2025, 1, 6)
    records = []
    for i in range(1, n + 1):
        arm = "Drug X" if i % 2 else "Control"
        randdt = start + timedelta(days=int(i * 2 + rng.integers(0, 4)))
        records.append({
            "STUDYID": "NSCLC-DEMO-001", "USUBJID": f"NSCLC-001-{i:03d}", "SUBJID": f"{i:03d}",
            "SITEID": f"{101 + (i % 6)}", "RANDDT": randdt.isoformat(), "ARMCD": "DRUGX" if arm == "Drug X" else "CTRL",
            "ARM": arm, "AGE": int(rng.integers(42, 82)), "SEX": "F" if i % 3 == 0 else "M",
            "RACE": ["WHITE", "ASIAN", "BLACK OR AFRICAN AMERICAN"][i % 3],
            "STAGE": "IV" if i % 4 else "IIIB", "PDL1": ["<1%", "1-49%", ">=50%"][i % 3],
        })
    demog = pd.DataFrame(records)

    raw_tumor, tu, tr, rs = [], [], [], []
    raw_ae, ae, raw_ex, ex, ds = [], [], [], [], []
    adtte, adeff = [], []
    ae_terms = ["NAUSEA", "FATIGUE", "RASH", "ANEMIA", "DECREASED APPETITE", "NEUTROPENIA"]
    visit_days = [0, 42, 84, 126, 168, 210]
    for idx, subject in demog.iterrows():
        uid, arm = subject.USUBJID, subject.ARM
        randdt = date.fromisoformat(subject.RANDDT)
        baseline = float(rng.integers(32, 91))
        pfs_event = bool(rng.random() < (0.48 if arm == "Drug X" else 0.68))
        pfs_day = int(rng.integers(90, 300)) if pfs_event else 336
        death_event = bool(rng.random() < (0.20 if arm == "Drug X" else 0.32))
        death_day = max(pfs_day + int(rng.integers(15, 150)), 180) if death_event else 420
        responses = []
        for v, day in enumerate(visit_days, 1):
            if day > pfs_day and pfs_event:
                continue
            trend = (0.83 if arm == "Drug X" else 0.93) ** v
            measure = max(5.0, baseline * trend + float(rng.normal(0, 3)))
            pct = (measure - baseline) / baseline * 100
            response = "PR" if pct <= -30 else ("PD" if pct >= 20 else "SD")
            if day == 0:
                response = "NE"
            assessdt = randdt + timedelta(days=day)
            raw_tumor.append({"SUBJID": subject.SUBJID, "VISIT": "BASELINE" if day == 0 else f"WEEK {day // 7}", "ASSESSDT": assessdt.isoformat(), "LESION": "L1", "MEASURE_MM": round(measure, 1), "RESPONSE": response})
            tu.append({"STUDYID": subject.STUDYID, "DOMAIN": "TU", "USUBJID": uid, "TUSEQ": 1, "TULNKID": "L1", "TUTESTCD": "TUMIDENT", "TUSTRESC": "TARGET LESION", "TULOC": "LUNG"})
            tr.append({"STUDYID": subject.STUDYID, "DOMAIN": "TR", "USUBJID": uid, "TRSEQ": v, "TRLNKID": "L1", "TRTESTCD": "LDIAM", "TRSTRESN": round(measure, 1), "TRSTRESU": "mm", "TRDTC": assessdt.isoformat(), "VISITNUM": v})
            rs.append({"STUDYID": subject.STUDYID, "DOMAIN": "RS", "USUBJID": uid, "RSSEQ": v, "RSTESTCD": "OVRLRESP", "RSSTRESC": response, "RSEVAL": "INVESTIGATOR", "RSDTC": assessdt.isoformat(), "VISITNUM": v})
            responses.append(response)
        if pfs_event:
            eventdt = randdt + timedelta(days=pfs_day)
            rs.append({"STUDYID": subject.STUDYID, "DOMAIN": "RS", "USUBJID": uid, "RSSEQ": len(responses) + 1, "RSTESTCD": "OVRLRESP", "RSSTRESC": "PD", "RSEVAL": "INVESTIGATOR", "RSDTC": eventdt.isoformat(), "VISITNUM": 99})
        bor = "PR" if "PR" in responses else ("SD" if "SD" in responses else "NE")
        adeff.append({"STUDYID": subject.STUDYID, "USUBJID": uid, "PARAMCD": "BOR", "PARAM": "Best Overall Response", "AVALC": bor, "ITTFL": "Y", "TRT01P": arm})
        adtte.extend([
            {"STUDYID": subject.STUDYID, "USUBJID": uid, "PARAMCD": "PFS", "PARAM": "Progression-Free Survival", "STARTDT": subject.RANDDT, "ADT": (randdt + timedelta(days=pfs_day)).isoformat(), "AVAL": pfs_day + 1, "CNSR": 0 if pfs_event else 1, "EVNTDESC": "PROGRESSION" if pfs_event else "CENSORED", "SRCDOM": "RS", "TRT01P": arm},
            {"STUDYID": subject.STUDYID, "USUBJID": uid, "PARAMCD": "OS", "PARAM": "Overall Survival", "STARTDT": subject.RANDDT, "ADT": (randdt + timedelta(days=death_day)).isoformat(), "AVAL": death_day + 1, "CNSR": 0 if death_event else 1, "EVNTDESC": "DEATH" if death_event else "ALIVE", "SRCDOM": "DS", "TRT01P": arm},
        ])
        cycles = int(rng.integers(4, 9))
        for cycle in range(1, cycles + 1):
            exdt = randdt + timedelta(days=(cycle - 1) * 21)
            dose = 200 if arm == "Drug X" else 150
            raw_ex.append({"SUBJID": subject.SUBJID, "CYCLE": cycle, "EXDT": exdt.isoformat(), "TREATMENT": arm, "DOSE": dose, "UNIT": "mg"})
            ex.append({"STUDYID": subject.STUDYID, "DOMAIN": "EX", "USUBJID": uid, "EXSEQ": cycle, "EXTRT": arm.upper(), "EXDOSE": dose, "EXDOSU": "mg", "EXSTDTC": exdt.isoformat()})
        for seq in range(1, int(rng.integers(1, 5))):
            term = ae_terms[int(rng.integers(0, len(ae_terms)))]
            aedt = randdt + timedelta(days=int(rng.integers(3, 150)))
            grade = int(rng.choice([1, 1, 2, 2, 3]))
            serious = "Y" if grade == 3 and rng.random() < .25 else "N"
            raw_ae.append({"SUBJID": subject.SUBJID, "AETERM": term.title(), "AESTDT": aedt.isoformat(), "GRADE": grade, "SERIOUS": serious})
            ae.append({"STUDYID": subject.STUDYID, "DOMAIN": "AE", "USUBJID": uid, "AESEQ": seq, "AETERM": term.title(), "AEDECOD": term, "AESTDTC": aedt.isoformat(), "AETOXGR": str(grade), "AESER": serious, "TRTEMFL": "Y"})
        ds_status = "DEATH" if death_event and death_day <= 420 else ("COMPLETED" if idx % 5 else "WITHDRAWAL BY SUBJECT")
        ds.append({"STUDYID": subject.STUDYID, "DOMAIN": "DS", "USUBJID": uid, "DSSEQ": 1, "DSTERM": ds_status, "DSDECOD": ds_status, "DSCAT": "DISPOSITION EVENT", "DSDTC": (randdt + timedelta(days=min(death_day, 420))).isoformat()})

    dm = demog.assign(DOMAIN="DM", RFSTDTC=demog["RANDDT"], AGEU="YEARS")[["STUDYID", "DOMAIN", "USUBJID", "SUBJID", "SITEID", "RFSTDTC", "AGE", "AGEU", "SEX", "RACE", "ARMCD", "ARM"]]
    adsl = demog.rename(columns={"ARM": "TRT01P", "ARMCD": "TRT01PN"}).copy()
    adsl["TRT01A"] = adsl["TRT01P"]
    adsl["ITTFL"] = "Y"; adsl["SAFFL"] = "Y"
    adsl = adsl[["STUDYID", "USUBJID", "TRT01P", "TRT01A", "AGE", "SEX", "RACE", "STAGE", "PDL1", "RANDDT", "ITTFL", "SAFFL"]]
    return {
        "raw_demog": demog, "raw_tumor": pd.DataFrame(raw_tumor), "raw_ae": pd.DataFrame(raw_ae), "raw_exposure": pd.DataFrame(raw_ex),
        "dm": dm, "ds": pd.DataFrame(ds), "ae": pd.DataFrame(ae), "ex": pd.DataFrame(ex), "tu": pd.DataFrame(tu).drop_duplicates(["USUBJID", "TULNKID"]), "tr": pd.DataFrame(tr), "rs": pd.DataFrame(rs),
        "adsl": adsl, "adtte": pd.DataFrame(adtte), "adeff": pd.DataFrame(adeff),
    }


def main() -> None:
    for folder in ("documents", "specifications", "metadata", "data", "expected_results"):
        (BASE / folder).mkdir(parents=True, exist_ok=True)
    (BASE / "documents" / "Protocol_NSCLC_DEMO.txt").write_text(PROTOCOL, encoding="utf-8")
    (BASE / "documents" / "SAP_NSCLC_DEMO.txt").write_text(SAP, encoding="utf-8")
    (BASE / "disease_context.json").write_text(json.dumps(DISEASE, indent=2, ensure_ascii=False), encoding="utf-8")

    sdtm = pd.DataFrame([
        ["DM", "USUBJID", "Unique Subject Identifier", "Char", "RAW.DEMOG.SUBJID", "Concatenate study/site/subject identifiers", "Predecessor", ""],
        ["RS", "RSTESTCD", "Response Assessment Short Name", "Char", "RAW.TUMOR.TEST", "Direct map after terminology normalization", "Predecessor", "RSTESTCD"],
        ["RS", "RSSTRESC", "Character Result/Finding in Std Format", "Character", "RAW.TUMOR.RESULT", "", "Derived", "RSSTRESC"],
        ["TR", "TRSTRESN", "Numeric Result/Finding in Standard Units", "Num", "", "Convert target lesion measurement to mm", "Derived", ""],
        ["DV", "DVTERM", "Protocol Deviation Term", "Text", "RAW.DEVIATION.TERM", "Direct map", "Predecessor", ""],
    ], columns=SDTM_REQUIRED)
    adam = pd.DataFrame([
        ["ADSL", "ITTFL", "Intent-to-Treat Population Flag", "Char", "DM/IRT", "Y if randomized with valid record; erroneous randomization unresolved", "Primary efficacy population", "DM/IRT to ADSL"],
        ["ADTTE", "AVAL", "Analysis Value", "Num", "ADT and STARTDT", "ADT - STARTDT + 1", "PFS analysis", "RS/DS/DM to ADTTE"],
        ["ADTTE", "CNSR", "Censoring Indicator", "Num", "", "", "PFS analysis", "Protocol/SAP to ADTTE"],
        ["ADEFF", "AVALC", "Analysis Value (C)", "Character", "RS.RSSTRESC", "Derive confirmed BOR", "ORR analysis", ""],
    ], columns=ADAM_REQUIRED)
    sdtm.to_excel(BASE / "specifications" / "SDTM_Spec.xlsx", index=False)
    adam.to_excel(BASE / "specifications" / "ADaM_Spec.xlsx", index=False)

    raw = pd.DataFrame([
        ["DEMOG", "SUBJID", "Subject Identifier", "character", "required"],
        ["TUMOR", "TEST", "Assessment Test", "character", "required"],
        ["TUMOR", "RESULT", "Assessment Result", "character", "required"],
        ["TUMOR", "ASSESSDT", "Assessment Date", "date", "required"],
        ["DEATH", "DTHDT", "Death Date", "date", "optional"],
    ], columns=["Dataset", "Variable", "Label", "Type", "Requirement"])
    raw.to_csv(BASE / "metadata" / "raw_metadata.csv", index=False)
    datasets = build_synthetic_data()
    for name, frame in datasets.items():
        layer = "raw" if name.startswith("raw_") else ("adam" if name in {"adsl", "adtte", "adeff"} else "sdtm")
        folder = BASE / "data" / layer
        folder.mkdir(parents=True, exist_ok=True)
        frame.to_csv(folder / f"{name}.csv", index=False)
    # Compatibility copy used by the independent R integration test.
    datasets["adsl"].to_csv(BASE / "data" / "adsl_sample.csv", index=False)
    manifest = {
        "synthetic": True,
        "seed": 20260712,
        "subjects": 60,
        "datasets": [{"name": name, "layer": "RAW" if name.startswith("raw_") else ("ADaM" if name in {"adsl", "adtte", "adeff"} else "SDTM"), "rows": len(frame), "columns": len(frame.columns)} for name, frame in datasets.items()],
        "disclaimer": "Entirely synthetic demonstration data; no real patient or company data."
    }
    (BASE / "data" / "manifest.json").write_text(json.dumps(manifest, indent=2), encoding="utf-8")
    expected = {"minimum_issue_categories": ["Traceability gap", "Non-executable", "Invalid type"], "required_terms": ["PFS", "OS", "ORR", "PD", "ITT", "ADSL", "ADTTE"], "relationship_count": 3, "subjects": 60, "dataset_count": len(datasets)}
    (BASE / "expected_results" / "gold.json").write_text(json.dumps(expected, indent=2), encoding="utf-8")
    print(f"Generated demo package at {BASE}")


if __name__ == "__main__":
    main()
