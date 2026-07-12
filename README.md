# Clinical Statistics Agent

An evidence-grounded assistant for clinical statisticians working with CDISC-based trials. Every project-specific answer must carry a citation that resolves to a parsed source document — general medical knowledge is labeled as such and kept separate.

> **Engineering MVP.** Not validated for GxP, regulatory submission, medical decision-making, or use with real patient or company data.

**[Live demo](URL)** · Streamlit Cloud, no installation needed. Runs in mock mode by default.

---

## Why

Statisticians rotating into a new therapeutic area face a knowledge load that has little to do with statistics:

- **Context-dependent abbreviations.** `PD` is progressive disease in an efficacy analysis and protocol deviation in data quality. Hundreds of these, and the context decides.
- **Specifications inherited without rationale.** SDTM and ADaM specs get passed down as templates. Why a variable exists, how datasets link, what the derivation traces back to — often undocumented.
- **Protocol–SAP drift.** Conflicts between the two are cheap to catch before database lock and expensive after.

The tool exists so that these questions can be asked against *the actual study documents*, and so that the answer arrives with its evidence attached.

---

## Design

The starting question was not "what can an LLM do here" but **"in a regulated setting, what must an LLM not be allowed to do."** The architecture is derived backwards from that line.

```
Documents (PDF/DOCX/XLSX)
        │
        ▼
   Parse & index ──────────► SQLite FTS5
        │                         │
        │                         ▼
        │                    Retrieval (BM25)
        │                         │
        ├──► Deterministic ◄──────┤
        │    spec checks          │
        │    (no LLM)             ▼
        │                    LLM (structured JSON)
        │                         │
        ▼                         ▼
   Issue log            ┌─ Citation validation ─┐
   (state machine,      │  resolves against     │
    human rationale)    │  local parsed docs    │
                        └───────────┬───────────┘
                                    ▼
                                 Answer
```

### Three decisions, and what they cost

**Spec validation runs on deterministic rules, not the LLM.**
The alternative — letting the model read the spec and flag issues — covers far more ground and is much faster to build. It was rejected because validation output has to be reproducible and traceable: identical input must yield identical output, and every flag must point at the rule that raised it. An LLM cannot offer that.
*Cost:* rules are hand-maintained and cover a narrow set of checks. Worth it — a validation result that cannot be reproduced is worth nothing in a regulated context, however broad its coverage.

**Retrieval is BM25 over SQLite FTS5, not embeddings.**
A vector store would generalize better across paraphrase and synonym. It was rejected because retrieval here has to be explainable: a lexical hit can be pointed at — *this passage matched these terms*. A cosine similarity cannot be defended the same way, and every downstream claim has to hang off a citation someone can check.
*Cost:* weak semantic generalization; synonyms are handled by the terminology layer instead.

**Citations are validated locally before an answer is returned.**
The model returns structured JSON with claims and citations. Each citation is checked against the parsed-document store; a claim whose citation does not resolve is not surfaced as a project fact. General medical knowledge is permitted, but explicitly marked as not project-derived.
*Cost:* the assistant refuses more often, and answers are narrower. That is the intended failure mode — a plausible-sounding claim with no source is the failure this system is built to prevent.

The issue log follows `Open → Under Review → Confirmed → Resolved`, with the reviewer's rationale recorded at each transition. This is an audit trail, not a product feature.

---

## What's in the demo

### Tabs

| Tab | What It Does |
|-----|-------------|
| **Study Overview** | View the synthetic NSCLC Phase III study (60 subjects, 14 datasets across RAW/SDTM/ADaM), download the complete data package |
| **Documents** | Upload and parse Protocol, SAP, SDTM Spec, ADaM Spec (PDF/DOCX/XLSX); parsed content becomes searchable evidence |
| **Disease Context** | Curated NSCLC knowledge card covering endpoints, statistical considerations, common SDTM domains and ADaM datasets |
| **Ask & Evidence** | Interactive bilingual Q&A — ask in English or Chinese, get evidence-grounded answers with validated citations from project documents |
| **Terminology** | Searchable dictionary of clinical abbreviations with context-dependent definitions (e.g., PD = progressive disease vs. protocol deviation) |
| **Issues & Questions** | Review specification issues detected by deterministic checks; record human decisions with rationale and full audit trail |

### Sidebar

- **Quick Upload**: Upload documents directly without switching tabs
- **Mode indicator**: Shows whether the agent is running in Live API mode (Gemini-powered) or Mock/Offline mode
- **Export**: Download HTML or Excel reports of the current study review
- **Reset**: Reinitialize the demo study to its original state

### Two Operating Modes

- **Mock mode** (default, no API key needed): Returns curated bilingual answers for common clinical questions. Fully functional for demonstration.
- **Live mode** (requires Gemini API key): Sends questions to Google Gemini with structured JSON output, retrieves evidence from parsed documents, and validates citations against the local database.

## Validation Boundary

This is an engineering MVP now. Synthetic data only. One therapeutic area. Sixty subjects. Hallucination rate is not quantified and the system has not been red-teamed. No IQ/OQ/PQ at this stage.
