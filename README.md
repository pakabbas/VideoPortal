# Video Portal

Farm GoPro video upload and retrieval portal (Flask + MariaDB).

**Production URL:** https://leadpilotai.spiralloopstechnologies.com/videoportal

## Local setup

1. Copy `.env.example` to `.env` and set `DATABASE_URL`, `FLASK_SECRET_KEY`, admin credentials.
2. Create DB: `mysql -u root < schema.sql` (XAMPP: `/Applications/XAMPP/xamppfiles/bin/mysql -u root < schema.sql`).
3. `python3 -m venv .venv && source .venv/bin/activate && pip install -r requirements.txt`
4. `export FLASK_APP=wsgi:app && flask init-db`
5. `python wsgi.py` → http://127.0.0.1:5055/videoportal/

## Roles

- **Admin** — users, configurations, mark any video ready, all download filters
- **Manager** — farmers under them, upload (after DocuSign), mark own videos ready
- **Farmer** — download ready videos tagged to them (if enabled)

## DocuSign

Free [Developer sandbox](https://developers.docusign.com/choose-the-right-developer-plan/). Set `DOCUSIGN_*` in `.env`. Demo envelopes are not legally binding.

## Deploy

See `gcp-connection.txt` and `deploy/`.
