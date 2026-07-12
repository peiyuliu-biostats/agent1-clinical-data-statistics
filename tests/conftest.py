from __future__ import annotations

from pathlib import Path

import pytest

from clinical_stat_agent.service import initialize_demo


@pytest.fixture()
def demo(tmp_path: Path):
    root = Path(__file__).resolve().parents[1]
    con, study, parsed, issues = initialize_demo(root, tmp_path / "test.db")
    yield root, con, study, parsed, issues
    con.close()
