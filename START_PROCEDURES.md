# Start procedures

Step-by-step commands to open, run and test B.A.B on this machine. Run each command
in a normal terminal. The folder name has a space, so keep the quotes.

## 1. Open the project

Project folder: `/home/bharat/Bharaths_Personal/BAB APP`

```bash
code "/home/bharat/Bharaths_Personal/BAB APP"
```

## 2. One-time setup

### a) Create the database user and databases (needs your sudo password)

```bash
sudo -u postgres psql -c "CREATE ROLE bab LOGIN PASSWORD 'bab_dev_password';" -c "CREATE DATABASE bab OWNER bab;" -c "CREATE DATABASE bab_test OWNER bab;"
```

### b) Backend packages

The `.venv` folder and `backend/.env` already exist. If `.env` is missing, create it
with `cp .env.example .env` inside `backend/`.

```bash
cd "/home/bharat/Bharaths_Personal/BAB APP/backend" && .venv/bin/pip install -e ".[dev]"
```

### c) Create the database tables

```bash
cd "/home/bharat/Bharaths_Personal/BAB APP/backend" && .venv/bin/alembic upgrade head
```

### d) Frontend packages (Node 24, installed through nvm)

```bash
cd "/home/bharat/Bharaths_Personal/BAB APP/frontend" && source ~/.nvm/nvm.sh && nvm use && npm install
```

## 3. Run it (two terminals, leave both open)

### Terminal 1: backend API

```bash
cd "/home/bharat/Bharaths_Personal/BAB APP/backend" && .venv/bin/uvicorn app.main:app --reload --port 8000
```

Wait for `Application startup complete`, then check:

- Health: http://localhost:8000/api/v1/health (shows `{"status":"ok",...}`)
- API docs: http://localhost:8000/docs

### Terminal 2: frontend

```bash
cd "/home/bharat/Bharaths_Personal/BAB APP/frontend" && source ~/.nvm/nvm.sh && nvm use && npm start
```

Open **http://localhost:4200**.

For the phone view, press F12, then Ctrl+Shift+M (device toolbar) and pick a width of
about 360 px.

## 4. Manual test walkthrough

1. **Register**: any email, a password of 10+ characters, tick both boxes.
2. **Onboarding**: fill in the 3 steps. The 4th step (cut down smoking or drinking) is
   optional.
3. **Today**: line of the day, steps, workout card and food card.
4. **Activity**: "Add today's numbers" with only steps; distance and calories show
   "estimate". Then **Import CSV**: download the template, fill a few rows, upload.
5. **Train**: look at this week's plan, start a workout, tick sets (the rest timer
   starts) and finish.
6. **Eat**: Add food (search "dal"), open **Ideas** and add one, and open "How your
   target is set".
7. **More → Runs**: add a run by hand, or upload a GPX file exported from your watch or
   running app.
8. **More → Check-in**: save one dated a week ago, then one for today. The second shows
   "Your plan was adjusted".
9. **More → Milestones**: unlocks from what you logged.
10. **More → Habits**: start a plan and log one with the button.
11. **More → History**: open the calendar and pick a day.
12. **Account**: edit your profile, **Export my data**, and try **Delete account** (use a
    throwaway account).
13. **Admin**: make yourself an admin, then sign out and back in. More shows **Admin**.

```bash
cd "/home/bharat/Bharaths_Personal/BAB APP/backend" && .venv/bin/python -m app.cli make-admin your@email.com
```

The full checklist for each milestone is in [docs/test-plan.md](docs/test-plan.md).

## 5. Automated tests (optional)

Backend:

```bash
cd "/home/bharat/Bharaths_Personal/BAB APP/backend" && .venv/bin/pytest
```

Frontend:

```bash
cd "/home/bharat/Bharaths_Personal/BAB APP/frontend" && source ~/.nvm/nvm.sh && nvm use && npm run lint && npx ng test --watch=false
```

## Useful extras

Reset a forgotten password (prints a new one):

```bash
cd "/home/bharat/Bharaths_Personal/BAB APP/backend" && .venv/bin/python -m app.cli reset-password your@email.com --generate
```

- **Stop the app:** press Ctrl+C in each terminal.
- **Next time:** skip step 2 and run the two commands in step 3. After pulling changes
  that add tables, run step 2c (`alembic upgrade head`) first.

## Troubleshooting

| Problem | Fix |
| --- | --- |
| `password authentication failed for user "bab"` | Run step 2a. |
| "Cannot reach the server" on the Today page | Terminal 1 (backend) is not running. |
| Node version errors | You skipped `nvm use`; run it in the `frontend` folder. |
| `relation ... does not exist` | Run step 2c (`alembic upgrade head`). |
| Port 8000 or 4200 already in use | Stop the other process, or close the old terminal. |
