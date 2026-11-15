# B.A.B (Be A Beast)

A fitness buddy web app: training and eating plans, daily activity, runs, weekly
check-ins, milestones and an optional smoking or drinking reduction plan.
Product spec and working rules: [CLAUDE.md](CLAUDE.md).
Step-by-step local run and test guide: [START_PROCEDURES.md](START_PROCEDURES.md).

```
backend/    FastAPI + SQLAlchemy (async) + Alembic + PostgreSQL
frontend/   Angular + Angular Material (dark theme, mobile first)
docs/       rules, API guide, test plan, deployment
```

## Prerequisites
- Python 3.10 or newer
- Node 24 (via nvm: `cd frontend && nvm use`). Angular needs Node 22.22+ or 24.
- PostgreSQL: Docker Compose (recommended) or a native PostgreSQL install

## 1. Database

With Docker:
```bash
docker compose up -d db
```
This creates databases `bab` and `bab_test` owned by user `bab`
(password `bab_dev_password`, development only).

Without Docker (native PostgreSQL, one time):
```bash
sudo -u postgres psql -c "CREATE ROLE bab LOGIN PASSWORD 'bab_dev_password';" -c "CREATE DATABASE bab OWNER bab;" -c "CREATE DATABASE bab_test OWNER bab;"
```

## 2. Backend
```bash
cd backend
python3 -m venv .venv
.venv/bin/pip install -e ".[dev]"
cp .env.example .env
.venv/bin/alembic upgrade head
.venv/bin/uvicorn app.main:app --reload --port 8000
```
- Health: http://localhost:8000/api/v1/health
- API docs: http://localhost:8000/docs

Checks:
```bash
.venv/bin/pytest
.venv/bin/ruff check . && .venv/bin/ruff format --check .
```

Bounce (the AI coach) is optional: set `BAB_AI_API_KEY` to a free OpenRouter key
(see START_PROCEDURES.md). Without it Bounce is switched off.

New migration after changing models:
```bash
.venv/bin/alembic revision --autogenerate -m "describe the change"
```

## 3. Frontend
```bash
cd frontend
nvm use
npm install
npm start
```
Open http://localhost:4200.

Checks:
```bash
npm run build
npm run lint
npx ng test --watch=false
```

The service worker is off in development (`npm start`). To try it, serve a production
build on a different port than the dev server (for example 8080). A service worker
registered on port 4200 would keep serving the production app shell there; remove it in
DevTools > Application > Service workers if that happens.

## Production
- Build and run the API container: see [docs/deploy.md](docs/deploy.md).
- Frontend production build with the API address:
  `cd frontend && BAB_API_URL=https://api.example.com/api/v1 npm run build:prod`
- The app is an installable PWA in production builds (service worker caches the app
  shell only).
- Security review: [docs/security-review.md](docs/security-review.md).

## Admin commands
Version 1 sends no email. Run these from `backend/`:
```bash
.venv/bin/python -m app.cli reset-password user@example.com
```
```bash
.venv/bin/python -m app.cli reset-password user@example.com --generate
```
```bash
.venv/bin/python -m app.cli make-admin user@example.com
```

Test the database connection (uses `BAB_DATABASE_URL`):
```bash
.venv/bin/python -m app.cli check-db
```
`reset-password` prompts for the new password (or prints a random one with
`--generate`) and signs the user out everywhere.
