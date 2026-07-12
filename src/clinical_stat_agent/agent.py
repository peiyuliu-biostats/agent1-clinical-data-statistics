from __future__ import annotations

import json

import httpx
from openai import OpenAI

from .config import settings
from .knowledge import citations_from_hits, search
from .models import Citation, EvidenceAnswer


def _mock_answer(question: str, hits: list[dict]) -> EvidenceAnswer:
    citations = citations_from_hits(hits[:4])
    evidence = " ".join(h["text"] for h in hits).lower()
    q0 = question.lower()
    if ("pfs" in q0 or "progression" in q0) and any(x in q0 for x in ("define", "defined", "consistent", "definition", "如何定义", "一致")):
        return EvidenceAnswer(
            answer="PFS (Progression-Free Survival, 无进展生存期) is defined as the time from randomization to the first documented disease progression or death from any cause (从随机化至首次疾病进展或任何原因死亡). However, the Protocol and SAP have an inconsistency (不一致) regarding handling of two or more consecutive missing tumor assessments — this must be resolved before SAP finalization.",
            project_definition="Time from randomization to first documented progression (per investigator) or death from any cause (随机化至首次记录的疾病进展或任何原因死亡). Protocol §9.2.1.",
            general_definition="PFS event/censoring rules, assessment windows and intercurrent-event handling must be pre-specified in project documents (PFS的事件、删失、评估窗口和插入事件处理必须由项目文件预先规定).",
            disease_context="In NSCLC, PFS depends on evaluable tumor assessments, death information and response criteria (NSCLC中PFS依赖可评价的肿瘤评估、死亡信息和疗效评估标准).",
            statistical_impact="Inconsistent censoring rules can change event time, estimates and treatment effect (不一致的删失规则可能改变事件时间、估计量和治疗效应).",
            data_impact="Requires RS/TR/TU tumor assessment data and DM/DS death/follow-up information (需要RS/TR/TU肿瘤评估数据及DM/DS死亡或随访信息).",
            citations=citations,
            uncertainties=["The exact rule for prolonged missing assessments is unresolved between Protocol and SAP (连续缺失评估后的具体规则尚未统一)."],
            questions_for_review=["Senior Statistician and Clinician should confirm the handling rule for progression after consecutive missing assessments (请Senior Statistician与Clinician确认连续缺失assessment后progression的处理规则)."],
            confidence="high" if citations else "low",
        )
    q = question.lower()
    if "pd" in q or "数据质量" in question:
        return EvidenceAnswer(
            answer="PD is context-dependent（PD依赖语境）: in oncology efficacy it usually means Progressive Disease（疾病进展）; in a protocol-deviation or DV-domain context it means Protocol Deviation（方案偏离）.",
            project_definition="The Protocol uses PD with CR/PR/SD under RECIST response assessment（Protocol在RECIST疗效评估中将PD与CR/PR/SD并列）.",
            general_definition="DV-domain or quality-review usage must be interpreted as Protocol Deviation unless project evidence indicates otherwise.",
            statistical_impact="Confusing the meanings can corrupt endpoint derivation or deviation summaries.",
            data_impact="Use document section, domain and neighboring terms to disambiguate before mapping.",
            citations=citations,
            uncertainties=["Each occurrence still requires local contextual review."],
            questions_for_review=["Confirm ambiguous PD occurrences with the relevant statistician or data manager."],
            confidence="high" if citations else "medium",
        )
    if "which datasets" in q or "哪些数据集" in question:
        return EvidenceAnswer(
            answer="PFS is supported by RS/TR/TU tumor-assessment records together with DM/DS subject and death/disposition information, and is represented for analysis in ADTTE with PARAMCD=PFS（PFS由RS/TR/TU及DM/DS支持，并在ADTTE中形成PFS参数）.",
            project_definition="Tumor assessment supplies progression; death/disposition sources supply death and follow-up information.",
            disease_context="RECIST response assessment requires traceable target-lesion and overall-response records.",
            statistical_impact="Event/censoring derivation must reconcile assessment gaps and death.",
            data_impact="RAW tumor/survival → SDTM RS/TR/TU/DM/DS → ADaM ADTTE.",
            citations=citations,
            questions_for_review=["Confirm exact source priority and missing-assessment algorithm."],
            confidence="high" if citations else "medium",
        )
    if "senior" in q or "向senior" in question.lower():
        return EvidenceAnswer(
            answer="Escalate the prolonged-missing-assessment PFS rule, erroneous-randomization handling, exact sensitivity-analysis algorithms, and incomplete ORR traceability（需升级确认：PFS连续缺失评估规则、错误随机化处理、敏感性分析算法及ORR追溯）.",
            statistical_impact="These choices can alter the estimand, analysis population, event status and treatment-effect estimate.",
            data_impact="Final decisions must be reflected consistently in Protocol, SAP and ADaM specifications.",
            citations=citations,
            uncertainties=["Final resolution is intentionally absent from the synthetic draft documents."],
            questions_for_review=["Which PFS rule is final?", "Are erroneously randomized subjects retained in ITT?", "What exact sensitivity analyses are required?"],
            confidence="high" if citations else "medium",
        )
    if "itt" in q:
        return EvidenceAnswer(
            answer="The Protocol includes all randomized subjects in ITT（Protocol规定所有随机受试者进入ITT）. The draft SAP adds a valid-randomization-record condition and leaves erroneous randomization unresolved, creating a project inconsistency.",
            project_definition="Protocol: all randomized subjects. SAP draft: randomized subjects with a valid randomization record.",
            statistical_impact="Excluding randomized-in-error subjects can change the treatment-policy population and introduce post-randomization selection concerns.",
            data_impact="ADSL.ITTFL derivation cannot be finalized until this discrepancy is resolved.",
            citations=citations,
            uncertainties=["Erroneous-randomization handling is unresolved."],
            questions_for_review=["Should all randomized subjects remain in ITT, including randomized-in-error subjects?"],
            confidence="high" if citations else "medium",
        )
    if "os" in q or "overall survival" in q or "总生存" in question:
        return EvidenceAnswer(
            answer="OS (Overall Survival, 总生存期) is defined as the time from randomization to death from any cause (从随机化至任何原因死亡的时间). Subjects alive at the analysis cutoff are censored at the last known alive date.",
            project_definition="Time from randomization to death from any cause; censored at last known alive date (Protocol §9.2.2).",
            general_definition="OS is the most definitive efficacy endpoint in oncology trials, not subject to assessment bias.",
            disease_context="In NSCLC, OS is a key secondary endpoint often tested hierarchically after PFS.",
            statistical_impact="Analyzed by stratified log-rank test and Cox model (SAP §7.2).",
            data_impact="Requires DM (demographics) and DS (disposition/death) domains; represented in ADTTE PARAMCD=OS.",
            citations=citations,
            confidence="high" if citations else "medium",
        )
    if "safety" in q or "ae" in q or "adverse" in q or "安全" in question or "不良" in question:
        return EvidenceAnswer(
            answer="Safety analysis covers TEAEs (Treatment-Emergent Adverse Events, 治疗期间不良事件), SAEs (Serious Adverse Events, 严重不良事件) and AESIs (Adverse Events of Special Interest, 特别关注不良事件), analyzed in the safety population (所有接受至少一剂治疗的受试者).",
            project_definition="Safety population: all subjects receiving at least one dose, analyzed by actual treatment received.",
            statistical_impact="Safety is descriptive; no formal hypothesis testing for AE endpoints in this study.",
            data_impact="Requires AE domain mapped to MedDRA; safety population flag in ADSL.",
            citations=citations,
            confidence="high" if citations else "medium",
        )
    if "stratif" in q or "分层" in question:
        return EvidenceAnswer(
            answer="Subjects are randomized 1:1 and stratified by PD-L1 category and disease stage (按PD-L1类别和疾病分期分层). Stratification factors are used in both the log-rank test and Cox model.",
            project_definition="Stratification factors: PD-L1 category and disease stage (Protocol §1).",
            statistical_impact="Stratified analysis must use the same factors; misalignment between IRT and analysis can bias the HR estimate.",
            data_impact="Stratification factors must be traceable from IRT/randomization system to ADSL.",
            citations=citations,
            confidence="high" if citations else "medium",
        )
    if "population" in q or "分析集" in question or "人群" in question:
        return EvidenceAnswer(
            answer="The study defines ITT (Intent-to-Treat, 意向性治疗分析集) as all randomized subjects, and the Safety Population (安全性分析集) as all subjects receiving at least one dose. However, there is an unresolved discrepancy: the SAP draft adds a 'valid randomization record' condition to ITT.",
            project_definition="Protocol: all randomized subjects. SAP draft: randomized subjects with a valid randomization record.",
            statistical_impact="Excluding randomized-in-error subjects can change the treatment-policy population and introduce post-randomization selection concerns.",
            data_impact="ADSL.ITTFL derivation cannot be finalized until the Protocol/SAP discrepancy is resolved.",
            citations=citations,
            uncertainties=["Erroneous-randomization handling is unresolved between Protocol and SAP."],
            questions_for_review=["Should all randomized subjects remain in ITT, including randomized-in-error subjects?"],
            confidence="high" if citations else "medium",
        )
    if "recist" in q or "tumor" in q or "肿瘤" in question or "评估" in question:
        return EvidenceAnswer(
            answer="Tumor assessments (肿瘤评估) are performed every 6 weeks through Week 48 and every 12 weeks thereafter using RECIST 1.1. Response categories include CR (Complete Response, 完全缓解), PR (Partial Response, 部分缓解), SD (Stable Disease, 疾病稳定), and PD (Progressive Disease, 疾病进展).",
            project_definition="RECIST 1.1 assessment schedule: Q6W to Week 48, then Q12W (Protocol §5).",
            disease_context="RECIST 1.1 is the standard solid-tumor response framework used in NSCLC trials.",
            data_impact="Tumor data flows through RS/TR/TU SDTM domains to ADaM ADEFF and ADTTE.",
            citations=citations,
            confidence="high" if citations else "medium",
        )
    summary = hits[0]["text"][:500] if hits else "No sufficient project evidence was found for this question (当前项目材料中未找到足够证据)."
    return EvidenceAnswer(
        answer=summary,
        citations=citations,
        uncertainties=[] if hits else ["No project evidence was retrieved (未检索到项目证据)."],
        questions_for_review=[] if hits else ["Please confirm whether additional project documents are needed or consult the relevant SME (请确认是否需要补充项目文件或咨询相应SME)."],
        confidence="medium" if hits else "low",
    )


def answer_question(con, study_id: str, question: str) -> EvidenceAnswer:
    hits = search(con, study_id, question)
    if not settings.live_ready:
        return _mock_answer(question, hits)
    context_parts = []
    for h in hits:
        context_parts.append(
            f"[SOURCE_ID={h['id']}] DOCUMENT={h['document']} | LOCATION={h['location']} | CLASS={h['source_class']}\n{h['text']}"
        )
    context = "\n\n".join(context_parts)
    prompt = f"""You are an evidence-grounded clinical statistics assistant for a clinical trial.
Answer in bilingual format: English first, then Chinese in parentheses for key terms and conclusions.
Use project evidence only for project-specific facts. Clearly distinguish project definitions from general clinical/statistical knowledge.
Never invent citations. Every citation must correspond to a supplied SOURCE and use its exact SOURCE_ID.
For each citation, set source_id to the exact string after SOURCE_ID=, set document to the DOCUMENT value, set location to the LOCATION value, set source_class to the CLASS value, and set excerpt to a representative quote from the source text.
If no project evidence is retrieved, state that clearly and provide only general knowledge with confidence "low".

QUESTION: {question}

PROJECT EVIDENCE (use these SOURCE_IDs for citations):
{context or 'No project evidence retrieved.'}
"""
    if settings.provider == "gemini":
        parsed = _gemini_answer(prompt)
    elif settings.provider == "openai":
        client = OpenAI(api_key=settings.api_key)
        response = client.responses.parse(model=settings.model, input=prompt, text_format=EvidenceAnswer)
        parsed = response.output_parsed
        if parsed is None:
            raise ValueError("The model did not return a parseable structured answer.")
    else:
        raise ValueError(f"Unsupported model provider: {settings.provider}")
    by_id = {h["id"]: h for h in hits}
    validated = []
    for citation in parsed.citations:
        if citation.source_id in by_id:
            h = by_id[citation.source_id]
            validated.append({"source_id": h["id"], "document": h["document"], "location": h["location"], "excerpt": h["text"][:260], "source_class": h["source_class"]})
    if not validated and hits:
        for h in hits[:4]:
            validated.append({"source_id": h["id"], "document": h["document"], "location": h["location"], "excerpt": h["text"][:260], "source_class": h["source_class"]})
    parsed.citations = [Citation.model_validate(x) for x in validated]
    return parsed


def _gemini_answer(prompt: str) -> EvidenceAnswer:
    """Call Gemini through the official generateContent REST API with JSON Schema output."""
    model = resolve_gemini_model(settings.gemini_api_key or "", settings.gemini_model)
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{model}:generateContent"
    payload = {
        "contents": [{"role": "user", "parts": [{"text": prompt}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "responseJsonSchema": EvidenceAnswer.model_json_schema(),
        },
    }
    with httpx.Client(timeout=90) as client:
        response = client.post(
            url,
            headers={"x-goog-api-key": settings.gemini_api_key or ""},
            json=payload,
        )
    if response.status_code >= 400:
        try:
            message = response.json().get("error", {}).get("message", "Gemini API request failed")
        except Exception:
            message = "Gemini API request failed"
        raise RuntimeError(f"Gemini API error {response.status_code}: {message}")
    body = response.json()
    try:
        text = body["candidates"][0]["content"]["parts"][0]["text"]
    except (KeyError, IndexError, TypeError) as exc:
        raise ValueError("Gemini returned no structured candidate text.") from exc
    return EvidenceAnswer.model_validate_json(text)


def list_gemini_models(api_key: str) -> list[str]:
    """List model IDs visible to a Gemini API key without exposing the key."""
    if not api_key:
        raise ValueError("GEMINI_API_KEY is not configured.")
    with httpx.Client(timeout=30) as client:
        response = client.get(
            "https://generativelanguage.googleapis.com/v1beta/models",
            headers={"x-goog-api-key": api_key},
            params={"pageSize": 1000},
        )
    if response.status_code >= 400:
        try:
            message = response.json().get("error", {}).get("message", "Unable to list Gemini models")
        except Exception:
            message = "Unable to list Gemini models"
        raise RuntimeError(f"Gemini model-list error {response.status_code}: {message}")
    result = []
    for model in response.json().get("models", []):
        methods = model.get("supportedGenerationMethods", model.get("supportedActions", []))
        if "generateContent" in methods:
            result.append(model.get("name", "").removeprefix("models/"))
    return sorted(x for x in result if x)


def resolve_gemini_model(api_key: str, configured: str = "auto") -> str:
    if configured and configured.lower() != "auto":
        return configured.removeprefix("models/")
    available = list_gemini_models(api_key)
    priorities = [
        "gemini-3.5-flash",
        "gemini-flash-latest",
        "gemini-3.1-flash-lite",
        "gemini-2.5-flash",
        "gemini-2.5-flash-lite",
    ]
    for candidate in priorities:
        if candidate in available:
            return candidate
    flash = [x for x in available if "flash" in x and "image" not in x and "live" not in x]
    if flash:
        return flash[0]
    raise RuntimeError("No generateContent-capable Gemini Flash model is available to this key.")
