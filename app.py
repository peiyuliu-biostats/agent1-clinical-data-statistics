from __future__ import annotations

import json
import sys
import uuid
import zipfile
from io import BytesIO
from pathlib import Path

ROOT = Path(__file__).resolve().parent
sys.path.insert(0, str(ROOT / "src"))

import pandas as pd
import streamlit as st

from clinical_stat_agent.agent import answer_question
from clinical_stat_agent.config import settings
from clinical_stat_agent.database import ISSUE_TRANSITIONS, audit, connect, load_qa, save_feedback, save_qa, update_issue_status
from clinical_stat_agent.ingestion import ingest
from clinical_stat_agent.reporting import excel_report, html_report
from clinical_stat_agent.service import STUDY_ID, initialize_demo, snapshot
from clinical_stat_agent.specs import check_spec

st.set_page_config(page_title="Clinical Statistics Agent", page_icon="🧬", layout="wide")
st.markdown(
    """<style>
    .block-container{padding-top:1.4rem}.small-note{color:#64748b;font-size:.85rem}
    .source-card{border-left:4px solid #3b82f6;padding:.65rem 1rem;background:#f8fafc;margin:.4rem 0}
    div[data-testid="stMetric"]{background:#f8fafc;border:1px solid #e2e8f0;padding:.7rem;border-radius:.6rem}
    </style>""",
    unsafe_allow_html=True,
)


def open_app_connection():
    con = connect(settings.db_path)
    exists = con.execute("SELECT 1 FROM studies WHERE id=?", (STUDY_ID,)).fetchone()
    if exists:
        return con
    con.close()
    initialized, *_ = initialize_demo(ROOT, settings.db_path)
    return initialized


def persist_spec_issues(con, path: Path, kind: str) -> int:
    _, issues = check_spec(path, kind)
    for issue in issues:
        con.execute(
            "INSERT OR REPLACE INTO issues(issue_id,study_id,payload) VALUES(?,?,?)",
            (issue.issue_id, STUDY_ID, issue.model_dump_json()),
        )
    con.commit()
    return len(issues)


def synthetic_zip() -> bytes:
    buffer = BytesIO()
    data_root = ROOT / "sample_studies" / STUDY_ID / "data"
    with zipfile.ZipFile(buffer, "w", zipfile.ZIP_DEFLATED) as archive:
        for path in data_root.rglob("*"):
            if path.is_file():
                archive.write(path, path.relative_to(data_root))
    return buffer.getvalue()


def render_answer(answer: dict) -> None:
    st.markdown(answer.get("answer", ""))
    with st.expander("Evidence interpretation（证据解释）", expanded=False):
        st.markdown(f"**Project definition（项目定义）:** {answer.get('project_definition') or 'Not established.'}")
        st.markdown(f"**Disease/general context（疾病/通用背景）:** {answer.get('disease_context') or answer.get('general_definition') or 'Not provided.'}")
        st.markdown(f"**Statistical impact（统计影响）:** {answer.get('statistical_impact') or 'Not provided.'}")
        st.markdown(f"**Data impact（数据影响）:** {answer.get('data_impact') or 'Not provided.'}")
    citations = answer.get("citations", [])
    if citations:
        with st.expander(f"Validated citations（已验证出处） · {len(citations)}", expanded=True):
            for citation in citations:
                st.markdown(f"**{citation['document']} — {citation['location']}** · `{citation['source_class']}`")
                st.code(citation["excerpt"], language=None)
    else:
        st.warning("No validated project citation was returned.")
    if answer.get("uncertainties"):
        st.warning("Uncertainties: " + " | ".join(answer["uncertainties"]))
    if answer.get("questions_for_review"):
        st.info("Questions requiring review: " + " | ".join(answer["questions_for_review"]))
    st.caption(f"Confidence: {answer.get('confidence', 'unknown')}")


con = open_app_connection()
if "session_id" not in st.session_state:
    st.session_state.session_id = uuid.uuid4().hex
state = snapshot(con, ROOT)
study = state["study"]

st.title("Clinical Statistics Agent")
st.caption("Evidence-grounded assistant for clinical statisticians · Powered by Gemini")

with st.sidebar:
    st.subheader("NSCLC-DEMO-001")
    st.write("Phase III · Oncology · PFS / OS / ORR")
    mode = "LIVE API" if settings.live_ready else "MOCK / OFFLINE"
    st.info(f"Mode: {mode}\n\nProvider: {settings.provider}\n\nModel: {settings.active_model}")

    st.divider()
    st.subheader("Quick Upload")
    with st.form("sidebar_upload", clear_on_submit=True):
        uploaded = st.file_uploader("Upload document", type=["pdf", "docx", "xlsx", "xlsm"], label_visibility="collapsed")
        kind = st.selectbox("Type", ["Protocol", "SAP", "SDTM Spec", "ADaM Spec"])
        sidebar_submit = st.form_submit_button("Parse & Index", type="primary", use_container_width=True)
    if sidebar_submit:
        if uploaded is None:
            st.error("Choose a file first.")
        else:
            target = ROOT / "data" / "uploads" / STUDY_ID / uploaded.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(uploaded.getbuffer())
            try:
                result = ingest(con, STUDY_ID, target, kind)
                issue_count = 0
                if kind in {"SDTM Spec", "ADaM Spec"}:
                    issue_count = persist_spec_issues(con, target, "SDTM" if kind == "SDTM Spec" else "ADAM")
                audit(con, STUDY_ID, "document_uploaded", {"name": uploaded.name, "kind": kind, "chunks": result["chunks"], "issues": issue_count})
                st.success(f"Parsed {result['chunks']} chunks; {issue_count} issues detected.")
                st.rerun()
            except Exception as exc:
                audit(con, STUDY_ID, "document_parse_failed", {"name": uploaded.name, "kind": kind, "error_type": type(exc).__name__})
                st.error(f"Parse error: {type(exc).__name__}: {exc}")

    st.divider()
    st.subheader("Export")
    report_html = html_report(study, state["disease"], state["terms"], state["relationships"], state["issues"])
    report_xlsx = excel_report(study, state["disease"], state["documents"], state["terms"], state["relationships"], state["issues"])
    st.download_button("Export HTML Report", report_html, f"{STUDY_ID}_review.html", "text/html", use_container_width=True)
    st.download_button("Export Excel Report", report_xlsx, f"{STUDY_ID}_review.xlsx", "application/vnd.openxmlformats-officedocument.spreadsheetml.sheet", use_container_width=True)

    st.divider()
    if st.button("Reset Demo Study", use_container_width=True):
        con.close()
        fresh, *_ = initialize_demo(ROOT, settings.db_path)
        fresh.close()
        st.rerun()
    st.markdown("<div class='small-note'>Synthetic data only. All outputs require professional review.</div>", unsafe_allow_html=True)

tabs = st.tabs([
    "Study Overview",
    "Documents",
    "Disease Context",
    "Ask & Evidence",
    "Terminology",
    "Issues & Questions",
])

# --- Tab 0: Study Overview ---
with tabs[0]:
    st.header("Study Overview")
    c1, c2, c3, c4 = st.columns(4)
    c1.metric("Study", study["id"])
    c2.metric("Therapeutic Area", study["therapeutic_area"])
    c3.metric("Indication", "NSCLC")
    c4.metric("Phase", study["phase"])
    st.subheader(study["title"])
    st.write(study["design"])
    left, right = st.columns(2)
    with left:
        st.markdown("#### Objectives and Endpoints")
        st.markdown("- **Primary:** evaluate efficacy based on PFS")
        st.markdown("- **Secondary:** OS, ORR and DOR")
        st.markdown("- **Safety:** TEAE, SAE and AESI summaries")
    with right:
        st.markdown("#### Current Evidence Status")
        st.metric("Parsed documents", len(state["documents"]))
        st.metric("Open review issues", sum(i["status"] not in {"Resolved", "Rejected"} for i in state["issues"]))

    st.subheader("Synthetic Data Package")
    manifest_path = ROOT / "sample_studies" / STUDY_ID / "data" / "manifest.json"
    if manifest_path.exists():
        manifest = json.loads(manifest_path.read_text(encoding="utf-8"))
        d1, d2, d3 = st.columns(3)
        d1.metric("Synthetic subjects", manifest["subjects"])
        d2.metric("Datasets", len(manifest["datasets"]))
        d3.metric("Generation seed", manifest["seed"])
        inventory = pd.DataFrame(manifest["datasets"])
        st.dataframe(inventory, width='stretch', hide_index=True)
        selected_dataset = st.selectbox("Preview dataset", inventory["name"].tolist())
        selected_meta = next(x for x in manifest["datasets"] if x["name"] == selected_dataset)
        folder = selected_meta["layer"].lower()
        csv_path = ROOT / "sample_studies" / STUDY_ID / "data" / folder / f"{selected_dataset}.csv"
        if csv_path.exists():
            preview = pd.read_csv(csv_path).head(20)
            st.dataframe(preview, width='stretch', hide_index=True)
        st.download_button("Download complete synthetic package", synthetic_zip(), f"{STUDY_ID}_synthetic_data.zip", "application/zip")
        st.caption(manifest["disclaimer"])
    else:
        st.warning("Synthetic manifest is not available. Run scripts/generate_demo.py.")

# --- Tab 1: Documents ---
with tabs[1]:
    st.header("Document Center")
    st.write("Upload and index clinical trial documents. Parsed evidence becomes searchable in Ask & Evidence and Terminology.")
    docs = pd.DataFrame(state["documents"])
    if not docs.empty:
        st.dataframe(docs[["name", "kind", "status", "version"]], width='stretch', hide_index=True)
    else:
        st.info("No documents indexed yet. Upload via the sidebar or the form below.")
    with st.form("document_upload", clear_on_submit=True):
        uploaded_main = st.file_uploader("Protocol / SAP / SDTM Spec / ADaM Spec", type=["pdf", "docx", "xlsx", "xlsm"])
        kind_main = st.selectbox("Document type", ["Protocol", "SAP", "SDTM Spec", "ADaM Spec"])
        submitted = st.form_submit_button("Upload, parse and index", type="primary")
    if submitted:
        if uploaded_main is None:
            st.error("Choose a file before submitting.")
        else:
            target = ROOT / "data" / "uploads" / STUDY_ID / uploaded_main.name
            target.parent.mkdir(parents=True, exist_ok=True)
            target.write_bytes(uploaded_main.getbuffer())
            try:
                result = ingest(con, STUDY_ID, target, kind_main)
                issue_count = 0
                if kind_main in {"SDTM Spec", "ADaM Spec"}:
                    issue_count = persist_spec_issues(con, target, "SDTM" if kind_main == "SDTM Spec" else "ADAM")
                audit(con, STUDY_ID, "document_uploaded", {"name": uploaded_main.name, "kind": kind_main, "chunks": result["chunks"], "issues": issue_count})
                st.success(f"Parsed {result['chunks']} evidence chunks; detected {issue_count} specification issues.")
                st.rerun()
            except Exception as exc:
                audit(con, STUDY_ID, "document_parse_failed", {"name": uploaded_main.name, "kind": kind_main, "error_type": type(exc).__name__})
                st.error(f"Parsing failed safely: {type(exc).__name__}: {exc}")

# --- Tab 2: Disease Context ---
with tabs[2]:
    st.header("Disease & Study Context")
    disease = state["disease"]
    st.subheader(disease["indication"])
    st.write(disease["summary"])
    c1, c2 = st.columns(2)
    with c1:
        st.markdown("#### Trial Relevance")
        for x in disease["trial_relevance"]:
            st.markdown(f"- {x}")
        st.markdown("#### Common Endpoints")
        st.write(", ".join(disease["common_endpoints"]))
    with c2:
        st.markdown("#### Statistical Considerations")
        for x in disease["statistical_considerations"]:
            st.markdown(f"- {x}")
        st.markdown("#### Typical Data Structures")
        st.write("SDTM: " + ", ".join(disease["common_sdtm_domains"]))
        st.write("ADaM: " + ", ".join(disease["common_adam_datasets"]))
    st.info("This is a curated knowledge card. It is not generated in real time, and project definitions always take priority.")
    st.warning(disease["source_note"])

# --- Tab 3: Ask & Evidence (BILINGUAL) ---
with tabs[3]:
    st.header("Ask & Evidence（问答与证据）")
    st.write("Ask questions about the study in English or Chinese. Answers are bilingual where useful. Project claims require locally validated citations.（项目事实必须有本地验证出处。）")
    prompts = [
        "How is PFS defined in this study, and are the Protocol and SAP consistent?（本研究如何定义PFS，Protocol与SAP是否一致？）",
        "What does PD mean in the efficacy and data-quality contexts?（PD在疗效与数据质量语境中分别是什么意思？）",
        "Which datasets support the PFS analysis?（哪些数据集支持PFS分析？）",
        "What questions should be escalated to the senior statistician?（哪些问题需要向Senior Statistician确认？）",
        "Explain the ITT population definition and its unresolved issue.（解释ITT人群定义及未解决问题。）",
        "How is OS defined and analyzed?（OS如何定义和分析？）",
        "Describe the safety analysis plan.（描述安全性分析计划。）",
        "What are the stratification factors?（分层因素是什么？）",
        "What is the tumor assessment schedule?（肿瘤评估时间表是什么？）",
    ]
    selected_prompt = st.selectbox("Suggested questions（建议问题）", ["Custom question（自定义问题）"] + prompts)
    default_question = "" if selected_prompt.startswith("Custom") else selected_prompt
    with st.form("qa_form", clear_on_submit=True):
        question = st.text_area("Your question（你的问题）", value=default_question, height=90, placeholder="Ask in English, Chinese, or bilingual format...（可使用英文、中文或双语提问）")
        ask = st.form_submit_button("Ask with evidence（带证据提问）", type="primary")
    if ask:
        if not question.strip():
            st.error("Enter a question.（请输入问题。）")
        else:
            with st.spinner("Retrieving, answering and validating citations...（检索、回答并验证出处...）"):
                try:
                    ans = answer_question(con, STUDY_ID, question)
                    qa_id = save_qa(con, STUDY_ID, st.session_state.session_id, question, ans.model_dump(), settings.mode)
                    audit(con, STUDY_ID, "question_answered", {"qa_id": qa_id, "question": question, "mode": settings.mode, "citation_count": len(ans.citations)})
                    st.rerun()
                except Exception as exc:
                    audit(con, STUDY_ID, "answer_failed", {"error_type": type(exc).__name__})
                    st.error(f"Answer failed: {type(exc).__name__}: {exc}")

    history = load_qa(con, STUDY_ID, st.session_state.session_id)
    st.subheader("Conversation history（对话历史）")
    if not history:
        st.caption("No questions in this browser session yet.（当前浏览器会话尚无问题。）")
    for item in reversed(history):
        with st.chat_message("user"):
            st.markdown(item["question"])
        with st.chat_message("assistant"):
            render_answer(item["answer"])
            fb1, fb2 = st.columns([1, 5])
            if fb1.button("👍 Helpful", key=f"helpful-{item['id']}"):
                save_feedback(con, item["id"], "Helpful"); st.rerun()
            if fb2.button("👎 Needs improvement", key=f"improve-{item['id']}"):
                save_feedback(con, item["id"], "Needs improvement"); st.rerun()
            if item.get("feedback"):
                st.caption(f"Feedback recorded: {item['feedback']}")

# --- Tab 4: Terminology ---
with tabs[4]:
    st.header("Terminology")
    st.write("Merged view of terms found in parsed project documents and the curated clinical-statistics dictionary.")
    terms = pd.DataFrame(state["terms"])
    query = st.text_input("Filter by abbreviation, meaning or context")
    if query and not terms.empty:
        mask = terms.astype(str).apply(lambda row: row.str.contains(query, case=False, regex=False).any(), axis=1)
        terms = terms[mask]
    st.dataframe(terms, width='stretch', hide_index=True)
    st.info("PD and CR are context-dependent: response, protocol-deviation and laboratory contexts must not be merged without evidence.")

# --- Tab 5: Issues & Questions ---
with tabs[5]:
    st.header("Issues & Questions")
    st.write("Deterministic checks and Agent suggestions remain drafts until a human reviewer records a decision and rationale.")
    issues = state["issues"]
    if not issues:
        st.success("No issues detected.")
    else:
        issue_df = pd.DataFrame(issues)
        f1, f2 = st.columns(2)
        severity = f1.multiselect("Severity", sorted(issue_df["severity"].unique()), default=sorted(issue_df["severity"].unique()))
        status = f2.multiselect("Status", sorted(issue_df["status"].unique()), default=sorted(issue_df["status"].unique()))
        filtered = issue_df[issue_df["severity"].isin(severity) & issue_df["status"].isin(status)]
        st.dataframe(filtered, width='stretch', hide_index=True)

        st.subheader("Human Confirmation Workflow")
        selected_id = st.selectbox("Issue", filtered["issue_id"].tolist() if not filtered.empty else issue_df["issue_id"].tolist())
        selected = next(i for i in issues if i["issue_id"] == selected_id)
        st.markdown(f"**Current status:** `{selected['status']}`  |  **Owner:** {selected['owner']}  |  **Severity:** {selected['severity']}")
        st.write(selected["description"])
        st.caption(f"Evidence: {selected['location']} · Impact: {selected['impact']}")
        allowed = sorted(ISSUE_TRANSITIONS.get(selected["status"], set()))
        default_idx = allowed.index("Under Review") if "Under Review" in allowed else 0
        with st.form("issue_transition"):
            next_status = st.selectbox("Next status", allowed, index=default_idx)
            actor = st.text_input("Reviewer", value="Human Reviewer")
            rationale = st.text_area("Decision rationale", placeholder="Required: record the evidence and reason for this human decision.")
            transition = st.form_submit_button("Record human decision", type="primary")
        if transition:
            try:
                update_issue_status(con, STUDY_ID, selected_id, next_status, rationale, actor)
                audit(con, STUDY_ID, "issue_transition", {"issue_id": selected_id, "to_status": next_status, "actor": actor})
                st.success(f"Issue moved to {next_status} with an audit record.")
                st.rerun()
            except Exception as exc:
                st.error(str(exc))

        st.subheader("Decision History")
        history = pd.DataFrame(state["issue_history"])
        if history.empty:
            st.caption("No human decisions recorded yet.")
        else:
            st.dataframe(history, width='stretch', hide_index=True)

con.close()
