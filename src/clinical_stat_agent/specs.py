from __future__ import annotations

import re
from pathlib import Path

import pandas as pd

from .models import Issue, Relationship

SDTM_REQUIRED = ["Domain", "Variable", "Label", "Type", "Source", "Mapping", "Origin", "Controlled_Terminology"]
ADAM_REQUIRED = ["Dataset", "Variable", "Label", "Type", "Source", "Derivation", "Analysis_Purpose", "Traceability"]


def _norm_columns(df: pd.DataFrame) -> dict[str, str]:
    return {re.sub(r"[^a-z0-9]", "", str(c).lower()): c for c in df.columns}


def check_spec(path: Path, spec_type: str) -> tuple[pd.DataFrame, list[Issue]]:
    df = pd.read_excel(path, dtype=str).fillna("")
    required = SDTM_REQUIRED if spec_type.upper() == "SDTM" else ADAM_REQUIRED
    normalized = _norm_columns(df)
    issues: list[Issue] = []
    for column in required:
        key = re.sub(r"[^a-z0-9]", "", column.lower())
        if key not in normalized:
            issues.append(Issue(issue_id=f"{spec_type}-COL-{key}", category="Missing", severity="High", description=f"Required column '{column}' is missing.", location=path.name, impact="The specification cannot be reviewed or executed consistently.", recommendation=f"Add and populate the {column} column.", owner="Statistical Programmer"))
    if issues:
        return df, issues
    source_col = normalized["source"]
    logic_col = normalized["mapping"] if spec_type.upper() == "SDTM" else normalized["derivation"]
    type_col = normalized["type"]
    variable_col = normalized["variable"]
    for idx, row in df.iterrows():
        loc = f"{path.name}, row {idx + 2}, {row[variable_col]}"
        if not str(row[source_col]).strip():
            issues.append(Issue(issue_id=f"{spec_type}-SRC-{idx+2}", category="Traceability gap", severity="High", description="Source is missing.", location=loc, impact="Target value cannot be traced to collected or predecessor data.", recommendation="Specify source dataset/variable or an explicit assigned origin.", owner="Statistical Programmer"))
        if not str(row[logic_col]).strip():
            issues.append(Issue(issue_id=f"{spec_type}-LOGIC-{idx+2}", category="Non-executable", severity="High", description=f"{logic_col} is missing.", location=loc, impact="Implementation and independent QC are ambiguous.", recommendation="Write an executable rule including conditions, timing and null handling.", owner="Statistician" if spec_type.upper() == "ADAM" else "Statistical Programmer"))
        if str(row[type_col]).strip().lower() not in {"char", "num", "character", "numeric"}:
            issues.append(Issue(issue_id=f"{spec_type}-TYPE-{idx+2}", category="Invalid type", severity="Medium", description=f"Unrecognized type '{row[type_col]}'.", location=loc, impact="Dataset metadata may be invalid.", recommendation="Use Char/Num according to the selected standard.", owner="Statistical Programmer"))
    return df, issues


def demo_relationships() -> list[Relationship]:
    return [
        Relationship(objective="Evaluate efficacy of Drug X versus control", endpoint="PFS", estimand="Treatment effect on PFS; intercurrent-event strategy requires final confirmation", data_source="Tumor assessments and death", sdtm="RS/TR/TU, DM/DS", adam="ADTTE PARAMCD=PFS", method="Stratified log-rank test and Cox model", tlf="T14.2.1 / F14.2.1", status="Gap", evidence="Protocol §9.2.1 and SAP §7.1 contain inconsistent missing-assessment handling."),
        Relationship(objective="Evaluate overall survival", endpoint="OS", estimand="Treatment effect on time to death from any cause", data_source="Survival follow-up and death", sdtm="DM/DS", adam="ADTTE PARAMCD=OS", method="Stratified log-rank test and Cox model", tlf="T14.2.2 / F14.2.2", status="Confirmed", evidence="Protocol §9.2.2; SAP §7.2."),
        Relationship(objective="Characterize objective response", endpoint="ORR", estimand="Difference in confirmed objective response probability", data_source="Investigator tumor response", sdtm="RS/TR/TU", adam="ADEFF PARAMCD=ORR", method="Stratified Cochran-Mantel-Haenszel method", tlf="T14.2.3", status="Inferred", evidence="Protocol §9.2.3; ADaM draft lacks explicit traceability."),
    ]


def draft_spec(kind: str) -> pd.DataFrame:
    if kind == "SDTM":
        return pd.DataFrame([
            ["DM", "USUBJID", "Unique Subject Identifier", "Char", "RAW.DM.SUBJID", "Concatenate STUDYID, site and subject ID per sponsor convention", "Predecessor", ""],
            ["RS", "RSTESTCD", "Response Assessment Short Name", "Char", "RAW.TUMOR.RESP", "Map response assessment test to approved controlled terminology", "Assigned", "RSTESTCD"],
            ["RS", "RSSTRESC", "Character Result/Finding in Std Format", "Char", "RAW.TUMOR.RESULT", "Normalize response result; unresolved values require review", "Derived", "RSSTRESC"],
        ], columns=SDTM_REQUIRED)
    return pd.DataFrame([
        ["ADSL", "ITTFL", "Intent-to-Treat Population Flag", "Char", "SDTM.DM/IRT", "Y if randomized; treatment of erroneous randomization requires confirmation", "Primary efficacy population", "DM/IRT to ADSL"],
        ["ADTTE", "AVAL", "Analysis Value", "Num", "ADT/STARTDT", "ADT - STARTDT + 1", "PFS/OS time-to-event analysis", "RS/DS/DM to ADTTE"],
        ["ADTTE", "CNSR", "Censoring Indicator", "Num", "Event/censoring algorithm", "0=event; 1=censored; exact missing-assessment rule requires senior confirmation", "PFS analysis", "Protocol/SAP + RS/DS to ADTTE"],
    ], columns=ADAM_REQUIRED)
