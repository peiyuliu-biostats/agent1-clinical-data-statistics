from pathlib import Path
import sys
import zipfile

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "src"))

from clinical_stat_agent.config import settings
from clinical_stat_agent.database import connect
from clinical_stat_agent.reporting import excel_report, html_report
from clinical_stat_agent.service import STUDY_ID, snapshot

con = connect()
state = snapshot(con, ROOT)
out = ROOT / "outputs"
out.mkdir(exist_ok=True)
(out / f"{STUDY_ID}_review.html").write_bytes(html_report(state["study"], state["disease"], state["terms"], state["relationships"], state["issues"]))
(out / f"{STUDY_ID}_review.xlsx").write_bytes(excel_report(state["study"], state["disease"], state["documents"], state["terms"], state["relationships"], state["issues"]))
data_root = ROOT / "sample_studies" / STUDY_ID / "data"
with zipfile.ZipFile(out / f"{STUDY_ID}_synthetic_data.zip", "w", zipfile.ZIP_DEFLATED) as archive:
    for path in data_root.rglob("*"):
        if path.is_file():
            archive.write(path, path.relative_to(data_root))
print(f"Built demo outputs in {out}")
