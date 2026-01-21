# QR Generator - Backend (FastAPI)

Quick start:

1. Create a python venv and install requirements:

```bash
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
```

2. Copy `.env.example` to `.env` and set your environment variables (SECRET_KEY, SMTP, DROPBOX_TOKEN)

3. Run the app:

```bash
uvicorn app.main:app --reload
```

Notes:
- Email verification will print an example verification link in server logs if SMTP is not configured.
- Dropbox: create an App at https://www.dropbox.com/developers/apps and generate an access token; place it in `DROPBOX_TOKEN` in `.env`.