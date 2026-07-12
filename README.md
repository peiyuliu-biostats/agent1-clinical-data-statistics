# Clinical Statistics Agent (临床统计Agent)

An evidence-grounded, interactive assistant for clinical statisticians working on CDISC-based clinical trials. Built with Streamlit and powered by Gemini API.

> **AI-assisted draft only (仅为AI辅助草稿).** This MVP is not validated for GxP, regulatory submission, medical decision-making, or use with real patient/company data.

## Live Demo (在线演示)

**[Open the live app on Streamlit Cloud](https://clinical-stat-agent.streamlit.app)** — no installation needed.

## Features (功能)

| Tab | Description |
|-----|-------------|
| **Study Overview (研究概览)** | Synthetic NSCLC Phase III study with 60-subject data package across RAW/SDTM/ADaM layers |
| **Documents (文档)** | Upload and parse Protocol, SAP, SDTM Spec, ADaM Spec (PDF/DOCX/XLSX) |
| **Disease Context (疾病背景)** | Curated NSCLC knowledge card with endpoints, domains, and statistical considerations |
| **Ask & Evidence (问答与证据)** | Interactive Q&A with citation-validated answers — bilingual (English/中文) |
| **Terminology (术语)** | Merged project terms + curated clinical-statistics dictionary |
| **Issues & Questions (问题与确认)** | Deterministic spec checks + human-reviewed state transitions with audit trail |

## Architecture (架构)

- **Frontend:** Streamlit with bilingual UI
- **LLM Provider:** Google Gemini API (auto-selects best available Flash model)
- **Evidence Retrieval:** SQLite FTS5 full-text search over parsed document chunks
- **Spec Validation:** Deterministic column/rule checks against CDISC SDTM/ADaM requirements
- **Mock Mode:** Full offline demo with no API key required

## Quick Start (快速开始)

### Prerequisites (前提条件)

- Python >= 3.11
- (Optional) Gemini API key from [Google AI Studio](https://aistudio.google.com/apikey) — free tier available

### Install and Run (安装与运行)

```bash
pip install -r requirements.txt
```

**Option A — Mock mode (offline, no API key needed):**
```bash
python -m streamlit run app.py
```

**Option B — Live mode (interactive Gemini-powered answers):**
```bash
cp .env.example .env
# Edit .env: set GEMINI_API_KEY=your-key and AGENT_MODE=live
python -m streamlit run app.py
```

On Windows, double-click `start.cmd` instead.

### Generate Synthetic Data (生成合成数据)

The 60-subject synthetic dataset (14 CSV files across RAW/SDTM/ADaM) is included. To regenerate:
```bash
pip install numpy
python scripts/generate_demo.py
```

## API Configuration (API配置)

Copy `.env.example` to `.env` and fill in:

| Variable | Default | Description |
|----------|---------|-------------|
| `MODEL_PROVIDER` | `gemini` | LLM provider (`gemini` or `openai`) |
| `GEMINI_API_KEY` | — | Your Gemini API key (never commit this) |
| `GEMINI_MODEL` | `auto` | Auto-selects best available Flash model |
| `AGENT_MODE` | `mock` | `mock` for offline demo, `live` for API calls |

## Deployment to Streamlit Cloud (部署到Streamlit Cloud)

1. Push this repo to GitHub (public or private)
2. Sign in at [share.streamlit.io](https://share.streamlit.io) with your GitHub account
3. Select this repo, set `app.py` as the entrypoint
4. In **Advanced settings > Secrets**, add:
   ```toml
   GEMINI_API_KEY = "your-key"
   AGENT_MODE = "live"
   MODEL_PROVIDER = "gemini"
   GEMINI_MODEL = "auto"
   ```
5. Deploy — you'll get a public `https://xxx.streamlit.app` URL

For detailed options see [DEPLOYMENT.md](DEPLOYMENT.md).

## Deliberately Seeded Findings (故意植入的发现)

The synthetic study includes real-world-style issues for demonstration:

- Protocol/SAP conflict for prolonged missing tumor assessments in PFS (PFS连续缺失评估处理的Protocol/SAP冲突)
- Missing SDTM mapping and source lineage (缺失SDTM映射和源数据追溯)
- Invalid SDTM variable types (无效的SDTM变量类型)
- Missing ADaM source/derivation/traceability (缺失ADaM源/推导/追溯)
- Unresolved erroneous-randomization handling for ITT (ITT错误随机化处理未解决)

## Test Suite (测试)

```bash
pip install pytest numpy
python -m pytest -q
```

## Validation Boundary (验证边界)

This is an engineering MVP. Before regulated use it requires: approved source licensing, organizational privacy review, role-based access, immutable audit controls, risk-based computerized-system validation, professional content validation, change control, backup/recovery, and formal user acceptance testing.
