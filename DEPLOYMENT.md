# Deployment and sharing

## 1. Same computer

Run `start.cmd`, then open `http://localhost:8501`.

## 2. Other computers on the same trusted network

1. Run `start_lan.cmd` and keep the terminal open.
2. Run `ipconfig` and find this computer's IPv4 address.
3. A viewer on the same network opens `http://<IPv4-address>:8501`.
4. Windows Firewall may ask whether Python can accept private-network connections. Do not enable public-network access unless that is intentionally approved.

This mode is for synthetic demonstration data only. It has no authentication.

## 3. Shareable internet link with Streamlit Community Cloud

1. Commit the project to a GitHub repository. Never commit `.env`, `.streamlit/secrets.toml`, databases, logs, uploads, or real study data.
2. Sign in at `https://share.streamlit.io` and connect the repository.
3. Create an app with entrypoint `app.py` and select a supported Python version.
4. In Advanced settings → Secrets, set values without committing them:

```toml
GEMINI_API_KEY = "rotated-key"
GEMINI_MODEL = "auto"
MODEL_PROVIDER = "gemini"
AGENT_MODE = "live"
APP_DB_PATH = "data/clinical_stat_agent.db"
```

5. Deploy and share the resulting `https://...streamlit.app` URL.

For a stable no-cost demonstration, set `AGENT_MODE = "mock"` and omit the API key. For a private or regulated company deployment, do not use this prototype hosting path without organizational security, privacy, authentication, persistence and validation review.

## Persistence boundary

SQLite is adequate for this single-instance MVP. Public cloud filesystems may be ephemeral, so Q&A history and issue decisions are demonstration state, not a regulated system of record. Phase 2 multi-user deployment should use authenticated users plus a managed persistent database and immutable audit controls.
