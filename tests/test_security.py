from pathlib import Path


def test_gitignore_protects_secrets_and_outputs():
    root = Path(__file__).resolve().parents[1]
    text = (root / ".gitignore").read_text(encoding="utf-8")
    assert ".env" in text
    assert "data/*.db" in text
    assert "outputs/" in text


def test_source_does_not_embed_key():
    root = Path(__file__).resolve().parents[1]
    for path in list((root / "src").rglob("*.py")) + [root / "app.py"]:
        text = path.read_text(encoding="utf-8")
        assert "sk-" not in text
