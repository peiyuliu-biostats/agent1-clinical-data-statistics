from __future__ import annotations

import os
from dataclasses import dataclass
from pathlib import Path

from dotenv import load_dotenv

ROOT = Path(__file__).resolve().parents[2]
load_dotenv(ROOT / ".env")


def _value(name: str, default: str | None = None) -> str | None:
    value = os.getenv(name)
    if value:
        return value
    try:
        import streamlit as st
        return str(st.secrets[name]) if name in st.secrets else default
    except Exception:
        return default


@dataclass(frozen=True)
class Settings:
    root: Path = ROOT
    db_path: Path = ROOT / (_value("APP_DB_PATH", "data/clinical_stat_agent.db") or "data/clinical_stat_agent.db")
    mode: str = (_value("AGENT_MODE", "mock") or "mock").lower()
    model: str = _value("OPENAI_MODEL", "gpt-5-mini") or "gpt-5-mini"
    api_key: str | None = _value("OPENAI_API_KEY")
    provider: str = (_value("MODEL_PROVIDER", "gemini") or "gemini").lower()
    gemini_model: str = _value("GEMINI_MODEL", "auto") or "auto"
    gemini_api_key: str | None = _value("GEMINI_API_KEY") or _value("GOOGLE_API_KEY")

    @property
    def live_ready(self) -> bool:
        if self.mode != "live":
            return False
        if self.provider == "gemini":
            return bool(self.gemini_api_key)
        if self.provider == "openai":
            return bool(self.api_key)
        return False

    @property
    def active_model(self) -> str:
        return self.gemini_model if self.provider == "gemini" else self.model


settings = Settings()
