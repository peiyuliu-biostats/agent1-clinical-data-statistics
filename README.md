# Clinical Statistics Agent

An evidence-grounded, interactive AI assistant built to support biostatisticians working on CDISC-based clinical trials — especially those new to the industry who face a steep learning curve across therapeutic areas, regulatory frameworks, and statistical programming standards.

> **AI-assisted draft only.** This MVP is not validated for GxP, regulatory submission, medical decision-making, or use with real patient/company data.

## Live Demo

**[Open the live app on Streamlit Cloud](https://clinical-stat-agent.streamlit.app)** — no installation needed.

---

## 1. Motivation — Why Build This Agent?

Biostatisticians entering the pharmaceutical industry face an overwhelming volume of domain knowledge that extends far beyond statistics:

- **Terminology and abbreviations**: Clinical trials use hundreds of specialized abbreviations (PFS, OS, ORR, DOR, ITT, mITT, TEAE, SAE, AESI, RECIST, CR, PR, PD, SD...) that carry different meanings depending on context. "PD" can mean "progressive disease" in efficacy analysis or "protocol deviation" in data quality — confusing these has real consequences for analysis.

- **Specification design**: Creating SDTM and ADaM specifications requires understanding CDISC standards, variable naming conventions, controlled terminology, derivation rules, and traceability requirements. Junior statisticians often inherit templates without understanding why columns exist or how datasets connect.

- **Disease understanding across therapeutic areas**: A biostatistician may rotate across cardiovascular, immunology, oncology, neuroscience, and hematology programs. Each area has its own endpoints, assessment schedules, response criteria, regulatory precedents, and analysis conventions. Understanding the disease context is essential for designing meaningful analyses and catching specification errors.

- **FDA regulations and guidelines**: ICH E9(R1) estimands, FDA guidance documents on specific indications, and evolving expectations around multiplicity, missing data handling, and sensitivity analyses all shape how a statistical analysis plan is written.

- **SAP and protocol design**: The Statistical Analysis Plan translates protocol objectives into concrete analysis methods. Ensuring consistency between the protocol and SAP — and catching conflicts before database lock — is critical but tedious work that benefits from systematic checking.

This agent was built to give junior biostatisticians a structured, evidence-grounded tool where they can ask questions about a study and receive answers that are tied to actual project documents, not just general knowledge. Every project claim must be supported by a locally validated citation, teaching users to think in terms of evidence and source documents.

## 2. How AI Tools Assisted Development

This project was developed collaboratively between a human biostatistician and AI coding assistants (Claude Code). The AI contributed:

- **Architecture design**: Suggesting the modular structure (agent, database, ingestion, knowledge, specs, service, reporting) and the separation between deterministic validation and LLM-powered Q&A.
- **Code generation**: Writing the Streamlit frontend, SQLite FTS5 search engine, document parsers (PDF/DOCX/XLSX), Gemini API integration with structured JSON Schema output, and Pydantic data models.
- **Synthetic data generation**: Creating a realistic 60-subject NSCLC Phase III dataset across RAW, SDTM, and ADaM layers with deliberate quality issues for demonstration.
- **Bug detection and fixing**: Identifying issues like citation validation failures, encoding errors on Windows, API response parsing edge cases, and Streamlit deprecation warnings.
- **Deployment configuration**: Setting up Streamlit Cloud deployment files, environment variable handling, and security practices for API key management.

## 3. Human Decisions and Debugging

While AI generated much of the code, the human made all critical decisions:

- **Domain modeling**: Choosing which clinical concepts to include, how to represent the relationship between Protocol, SAP, SDTM Spec, and ADaM Spec, and what constitutes a meaningful "issue" worth flagging.
- **Validation rules**: Defining which SDTM/ADaM column checks to run, what severity levels to assign, and how the issue state machine (Open → Under Review → Confirmed → Resolved) should work.
- **Evidence architecture**: Deciding that all project-specific claims must have validated citations from parsed documents, and that general medical knowledge should be clearly distinguished from project-defined facts.
- **Bilingual design**: Choosing to use bilingual (English with Chinese annotations) specifically in the Q&A interface to support non-native English speakers, while keeping the rest of the UI in clean English.
- **Quality review**: Manually testing every feature, verifying that mock answers match real clinical knowledge, checking that Gemini API responses meet quality standards, and debugging integration issues.
- **Security**: Ensuring API keys are never committed to version control, configuring `.gitignore` and `.env.example` properly, and reviewing all files before public deployment.

## 4. Features and Usage Guide

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

### Quick Start

```bash
# Install dependencies
pip install -r requirements.txt

# Run in mock mode (no API key needed)
python -m streamlit run app.py

# Or run in live mode with Gemini
cp .env.example .env
# Edit .env: set GEMINI_API_KEY and AGENT_MODE=live
python -m streamlit run app.py
```

On Windows, double-click `start.cmd` instead.

### Deploy to Streamlit Cloud

1. Push this repo to GitHub
2. Sign in at [share.streamlit.io](https://share.streamlit.io) with your GitHub account
3. Select this repo, set `app.py` as the entrypoint
4. In **Advanced settings > Secrets**, add your `GEMINI_API_KEY`, `AGENT_MODE=live`, `MODEL_PROVIDER=gemini`, `GEMINI_MODEL=auto`
5. Deploy — you'll get a public URL

See [DEPLOYMENT.md](DEPLOYMENT.md) for detailed options.

### Generate Synthetic Data

The 60-subject synthetic dataset (14 CSV files) is included. To regenerate:
```bash
pip install numpy
python scripts/generate_demo.py
```

## Test Suite

```bash
pip install pytest numpy
python -m pytest -q
```

## Deliberately Seeded Findings

The synthetic study includes real-world-style issues for demonstration:

- Protocol/SAP conflict for prolonged missing tumor assessments in PFS
- Missing SDTM mapping and source lineage
- Invalid SDTM variable types
- Missing ADaM source/derivation/traceability
- Unresolved erroneous-randomization handling for ITT

## Validation Boundary

This is an engineering MVP. Before regulated use it requires: approved source licensing, organizational privacy review, role-based access, immutable audit controls, risk-based computerized-system validation, professional content validation, change control, backup/recovery, and formal user acceptance testing.
