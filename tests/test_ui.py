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
        "Study Overview",
        "Documents",
        "Disease Context",
        "Ask & Evidence",
        "Terminology",
        "Issues & Questions",
    ]
