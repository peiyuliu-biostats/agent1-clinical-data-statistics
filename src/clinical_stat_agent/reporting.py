from __future__ import annotations

from datetime import datetime, timezone
from io import BytesIO

import pandas as pd
from jinja2 import Template

HTML = Template("""<!doctype html><html><head><meta charset='utf-8'><title>{{ study.id }} Review</title>
<style>body{font:15px Arial;max-width:1100px;margin:32px auto;color:#1f2937}h1,h2{color:#15385b}table{border-collapse:collapse;width:100%;margin:12px 0}th,td{border:1px solid #ccd5df;padding:7px;text-align:left;vertical-align:top}.warn{background:#fff3cd;padding:12px}.small{color:#59636e;font-size:12px}</style></head><body>
<div class='warn'><b>AI-assisted draft — not approved for regulatory use.</b></div>
<h1>{{ study.id }} — {{ study.title }}</h1><p>{{ study.indication }} | {{ study.phase }} | {{ study.design }}</p>
<h2>Disease Context</h2><p>{{ disease.summary }}</p><ul>{% for x in disease.statistical_considerations %}<li>{{ x }}</li>{% endfor %}</ul>
<h2>Terminology</h2>{{ terms|safe }}
<h2>Objective–Endpoint–Dataset</h2>{{ relationships|safe }}
<h2>Specification Issues</h2>{{ issues|safe }}
<h2>Questions for Review</h2>{{ questions|safe }}
<p class='small'>Generated {{ generated }}. Sources and decisions require human verification.</p></body></html>""")


def _table(rows) -> str:
    return pd.DataFrame(rows).to_html(index=False, escape=True) if rows else "<p>None.</p>"


def html_report(study: dict, disease: dict, terms: list[dict], relationships: list[dict], issues: list[dict]) -> bytes:
    questions = [{"Owner": i["owner"], "Question": i["recommendation"], "Status": i["status"]} for i in issues]
    return HTML.render(study=study, disease=disease, terms=_table(terms), relationships=_table(relationships), issues=_table(issues), questions=_table(questions), generated=datetime.now(timezone.utc).isoformat()).encode("utf-8")


def excel_report(study: dict, disease: dict, documents: list[dict], terms: list[dict], relationships: list[dict], issues: list[dict]) -> bytes:
    out = BytesIO()
    with pd.ExcelWriter(out, engine="openpyxl") as writer:
        pd.DataFrame([study]).to_excel(writer, sheet_name="Study_Summary", index=False)
        pd.DataFrame([disease]).to_excel(writer, sheet_name="Disease_Context", index=False)
        pd.DataFrame(documents).to_excel(writer, sheet_name="Documents", index=False)
        pd.DataFrame(terms).to_excel(writer, sheet_name="Terminology", index=False)
        pd.DataFrame(relationships).to_excel(writer, sheet_name="Relationships", index=False)
        pd.DataFrame(issues).to_excel(writer, sheet_name="Issues", index=False)
        pd.DataFrame([{"Disclaimer": "AI-assisted draft; not approved for regulatory use."}]).to_excel(writer, sheet_name="Read_Me", index=False)
    return out.getvalue()
