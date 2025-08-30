# DSC Validator (Flask) — Render Deploy

This is a minimal web app to validate whether a PDF has a Digital Signature (DSC) and display signer names if available.

## Local Run
```bash
pip install -r requirements.txt
python app.py
# open http://127.0.0.1:5000
```

## Deploy on Render (recommended)
1. Push this folder to a GitHub repo.
2. On Render, **New → Web Service** → pick your repo.
3. Render auto-detects `render.yaml`, so you can accept defaults and deploy.
4. After deploy, open your public URL and upload a PDF.

> The app listens on `$PORT` automatically and uses the Flask dev server for simplicity.