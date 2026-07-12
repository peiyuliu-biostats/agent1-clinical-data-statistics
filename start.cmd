@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"
python -m streamlit run "%~dp0app.py" --server.port=8501 --server.headless=true --browser.gatherUsageStats=false
if errorlevel 1 (
  echo.
  echo Failed to start. Verify that Python is available with: python --version
  pause
)
