$ErrorActionPreference = "Stop"
$env:PYTHONPATH = Join-Path $PSScriptRoot "src"
python -m streamlit run (Join-Path $PSScriptRoot "app.py") --server.port=8501 --server.headless=true --browser.gatherUsageStats=false
