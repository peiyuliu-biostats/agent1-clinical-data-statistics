from pathlib import Path

from clinical_stat_agent.ingestion import file_hash, parse_file


def test_hash_is_stable(tmp_path: Path):
    path = tmp_path / "a.txt"
    path.write_text("clinical evidence", encoding="utf-8")
    assert file_hash(path) == file_hash(path)
    assert len(file_hash(path)) == 64


def test_text_parser_has_locations(tmp_path: Path):
    path = tmp_path / "a.txt"
    path.write_text("Heading\n\nPFS definition here.", encoding="utf-8")
    chunks, details = parse_file(path)
    assert chunks and all("location" in x and "text" in x for x in chunks)
    assert details["characters"] > 0


def test_excel_parser_has_sheet_rows(demo):
    root, *_ = demo
    path = root / "sample_studies" / "NSCLC-DEMO-001" / "specifications" / "SDTM_Spec.xlsx"
    chunks, details = parse_file(path)
    assert chunks
    assert "Sheet1" in details["sheets"]
    assert chunks[0]["location"].startswith("sheet Sheet1, row")
