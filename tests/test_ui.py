from pathlib import Path

from streamlit.testing.v1 import AppTest


def test_streamlit_app_renders_without_exception(monkeypatch):
    root = Path(__file__).resolve().parents[1]
    monkeypatch.setenv("AGENT_MODE", "mock")
    app = AppTest.from_file(str(root / "app.py"), default_timeout=20)
    app.run()
    assert not app.exception
    assert app.title[0].value == "Clinical Statistics Agent"
    assert len(app.tabs) == 6
    assert [tab.label for tab in app.tabs] == [
        "Study Overview（研究概览）",
        "Documents（文档）",
        "Disease Context（疾病背景）",
        "Ask & Evidence（问答与证据）",
        "Terminology（术语）",
        "Issues & Questions（问题与确认）",
    ]
