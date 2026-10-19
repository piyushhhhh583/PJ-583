# MADAM.exe ♡

A responsive birthday and friendship website with a plum/pink aesthetic, birthday countdown for **January 4, 2027 (IST)**, friendship letter, timeline, interactive quiz, Easter egg, and a three-layer photo vault.

## Project files

- `app.py` — Flask app and admin/photo routes
- `templates/index.html` — public-facing birthday website
- `templates/admin.html` — admin login and photo dashboard
- `requirements.txt` — Python dependencies
- `.env.example` — environment-variable template

## Run locally (Windows 10/11)

Install Python 3.11+ from python.org. Open PowerShell in the project folder:

```powershell
py -m venv .venv
.\.venv\Scripts\Activate.ps1
pip install -r requirements.txt
Copy-Item .env.example .env
```

Generate a password hash (replace the example with a strong password you choose):

```powershell
python -c "from werkzeug.security import generate_password_hash; print(generate_password_hash('REPLACE_WITH_A_STRONG_PASSWORD'))"
```

Set environment variables in PowerShell for a quick local run:

```powershell
$env:SECRET_KEY = "replace-with-a-long-random-secret"
$env:ADMIN_PASSWORD_HASH = "paste-the-generated-hash-here"
$env:MADAM_DATA_DIR = ".\private_data"
python app.py
```

Open http://127.0.0.1:5000 and the admin page at http://127.0.0.1:5000/admin.

The app reads environment variables directly. The `.env.example` file is documentation only; it is not automatically loaded. Do not commit real passwords, hashes, or secrets.

## Deploy as a shareable website

Use a Python web host that supports Flask and a **persistent disk/volume**. GitHub Pages alone cannot run the Flask backend.

Suggested service settings:
- Build command: `pip install -r requirements.txt`
- Start command: `gunicorn app:app`
- Environment variables:
  - `SECRET_KEY`: a long random secret
  - `ADMIN_PASSWORD_HASH`: hash generated with Werkzeug as above
  - `COOKIE_SECURE`: `1` when served over HTTPS
  - `MADAM_DATA_DIR`: path on the host's persistent disk, such as `/var/data/madam`
- Mount a persistent disk at the same path as `MADAM_DATA_DIR`.

Before uploading personal photos, confirm the host disk persists across deploys and backups are enabled. Don't use a public static file bucket for private photos.

## Important security notes

- Never commit `.env`, password hashes, uploaded photos, or the `private_data` directory.
- Use HTTPS in production and set `COOKIE_SECURE=1`.
- Use a unique, strong admin password. The silly friendship Easter egg on the homepage is not an admin password.
- This is a starter implementation. Before putting sensitive/private photos online, add CSRF protection, rate limiting, a strict upload policy and backups. A login alone is not a guarantee of confidentiality.
- Secret Collection photos are served only to an authenticated admin in this starter app. Public layers are visible to anyone who can access the site.
- The app currently uses SQLite, so use a persistent disk and avoid running multiple instances that each write to separate local databases.

## Personalization

Replace the sample letter and timeline text in `templates/index.html` with your own words. Photos are optional and can be added later from `/admin`. The countdown targets midnight on January 4, 2027 in India Standard Time.
