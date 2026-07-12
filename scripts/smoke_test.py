from __future__ import annotations

import os
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from clinical_stat_agent.agent import answer_question
from clinical_stat_agent.config import settings
from clinical_stat_agent.database import connect
from clinical_stat_agent.service import STUDY_ID

if not settings.live_ready:
    raise SystemExit("Set AGENT_MODE=live and OPENAI_API_KEY in .env before live smoke testing.")

con = connect()
answer = answer_question(con, STUDY_ID, "本项目的PFS如何定义，Protocol与SAP是否一致？")
assert answer.answer
assert answer.citations, "Live answer must include validated project citations."
print("LIVE API SMOKE TEST PASSED")
print(f"Provider: {settings.provider}; model: {settings.active_model}; citations: {len(answer.citations)}; confidence: {answer.confidence}")
