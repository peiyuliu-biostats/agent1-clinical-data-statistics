@echo off
setlocal
cd /d "%~dp0"
set "PYTHONPATH=%~dp0src"
echo Starting Clinical Statistics Agent for this local network...
echo Find this computer's IPv4 address with: ipconfig
echo Other computers can open: http://YOUR-IP-ADDRESS:8501
python -m streamlit run "%~dp0app.py" --server.address=0.0.0.0 --server.port=8501 --server.headless=true --browser.gatherUsageStats=false
if errorlevel 1 pause
