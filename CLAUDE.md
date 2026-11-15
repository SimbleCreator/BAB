# B.A.B (Be A Beast)

## What this is
B.A.B is a fitness buddy product. Users get a training and eating plan, log their
daily activity, meals and weekly measurements, see the plan adapt to their
progress, earn milestones, and can follow a plan to reduce smoking or drinking.

The owner is a solo developer who knows Python, FastAPI, Angular and PostgreSQL.

## Current target: Web version 1
A responsive web app (phone browser first) with user accounts. Users enter or
upload their daily numbers (steps, distance, calories burnt, runs) from whatever
watch or phone app they already use, and everything else is computed from that.
All data is stored per user, per day, on the server.

### Roadmap (context only)
- Web version 1 (now): everything in this file
- Android app (after there are users): same accounts and backend, adds automatic
  step capture, wake-up alarm with motivational lines, and a motivating buddy
- iOS app after Android
- LLM features later: meal photo calories, buddy chat, AI-written plans
- Community and subscription later

### Out of scope now (do NOT build, do not add dependencies for these)
- Native mobile code, automatic step capture, alarms, push notifications
- Any LLM or AI API, meal photo recognition, chat
- Community, subscription, payments, ads, third-party analytics
- Email sending (no verification or reset emails in version 1)
- Body photos (removed from the product permanently)

## Hard constraints
- Must run at zero cost in development and fit free hosting tiers for a small
  number of users. No paid services, no paid APIs.
- Adults only: registration requires confirming age 18 or over.
- The backend API is the product's contract. The future mobile apps will call the
  same endpoints, so no business logic lives in the Angular app.
- No copyrighted content: no quotes, names or images from anime, films, games or
  other apps. All text is original.
- Not a medical product. Calorie, plan and habit screens carry a short
  "estimates only, not medical advice" note.

## Tech stack
Backend
- Python, FastAPI, Pydantic v2, SQLAlchemy 2 (async), Alembic, PostgreSQL
- Auth: argon2 password hashing, JWT access token, refresh token in an httpOnly
  cookie
- Tests: pytest, httpx test client
- GPX parsing with defusedxml (never the standard XML parser on uploads)

Frontend
- Angular (latest stable, standalone components, signals), Angular Material
- Leaflet with OpenStreetMap tiles for run maps
- Chart.js for charts
- Installable PWA (manifest and service worker for the app shell only)

Local development
- Docker Compose runs PostgreSQL only. Backend and frontend run natively with
  hot reload.

Use the latest stable versions at install time. Do not pin versions from memory,
and check current docs before using an API that may have changed. Do not add
libraries outside this list without asking.

## Architecture rules
1. Monorepo: `backend/`, `frontend/`, `docs/`.
2. Backend layers: router -> service -> repository -> database. Routers contain no
   logic. Services own transactions.
3. Engines are pure Python with no FastAPI or database imports and full unit
   tests: nutrition_engine, training_engine, adjustment_engine, habit_engine,
   milestone_engine. Inputs and outputs are plain dataclasses or Pydantic models.
   A future LLM will sit beside these engines, not replace them.
4. Every table that holds user data has `user_id`. Every query filters by the
   authenticated user. Add a test per router proving one user cannot read or
   change another user's data.
5. API under `/api/v1`. Keep the generated OpenAPI schema accurate, with response
   models on every route, because the mobile apps will be built from it.
6. Store raw values (metres, seconds, steps, kg, cm, kcal). Format only in the UI.
7. Timestamps are UTC in the database. A "day" is the user's local calendar date,
   stored as a DATE, using the timezone saved on their profile.
8. Built-in content (exercises, foods, motivational lines) lives in JSON files in
   `backend/app/content/`, loaded at startup, versioned in git.
9. Frontend: feature folders, one API service per backend router, typed models
   matching the API, route guards for auth, an HTTP interceptor that refreshes the
   access token once on a 401.
10. Every activity record carries a `source` field ('manual', 'csv', 'gpx', and
    later 'android', 'ios') so automatic data can replace manual data cleanly.

## Directory structure
```
bab/
├─ CLAUDE.md
├─ README.md
├─ docker-compose.yml             # PostgreSQL for local development
├─ docs/
│  ├─ rules.md                    # every formula and threshold, kept in sync
│  ├─ api.md                      # short guide to the API for future mobile work
│  ├─ deploy.md
│  └─ test-plan.md
├─ backend/
│  ├─ pyproject.toml
│  ├─ Dockerfile
│  ├─ .env.example
│  ├─ alembic/
│  ├─ app/
│  │  ├─ main.py
│  │  ├─ core/                    # settings, security, dependencies, errors
│  │  ├─ models/                  # SQLAlchemy tables
│  │  ├─ schemas/                 # Pydantic request and response models
│  │  ├─ repositories/
│  │  ├─ services/
│  │  ├─ engines/                 # pure Python rules
│  │  ├─ routers/
│  │  └─ content/                 # exercises.json, foods.json, lines.json
│  └─ tests/
└─ frontend/
   ├─ package.json
   └─ src/app/
      ├─ core/                    # auth, interceptors, guards, api base
      ├─ shared/                  # reusable components, pipes, formatters
      └─ features/
         ├─ auth/
         ├─ onboarding/
         ├─ today/
         ├─ activity/
         ├─ runs/
         ├─ training/
         ├─ nutrition/
         ├─ checkin/
         ├─ milestones/
         ├─ habits/
         ├─ history/
         ├─ account/
         └─ admin/
```

## Data model (PostgreSQL)
```
users              id PK, email UNIQUE, password_hash, is_admin, is_active,
                   consent_at, created_at, last_login_at
refresh_tokens     id PK, user_id FK, token_hash, expires_at, revoked_at, created_at
profiles           user_id PK FK, name, age, sex, height_cm, weight_kg, goal,
                   level, minutes_per_day, days_per_week, has_pullup_bar, diet_type,
                   daily_step_goal, timezone, updated_at
daily_activity     id PK, user_id FK, day, steps, distance_m, active_kcal, source,
                   note, updated_at          UNIQUE (user_id, day)
runs               id PK, user_id FK, day, started_at, distance_m, duration_s,
                   calories_kcal, source, note, created_at
run_points         id PK, run_id FK, seq, lat, lng, ele_m, recorded_at
training_plans     id PK, user_id FK, week_start, plan_json, created_at
workout_sessions   id PK, user_id FK, plan_id FK, day, status, finished_at
                   UNIQUE (user_id, day)
workout_sets       id PK, session_id FK, exercise_code, set_no, target_reps,
                   actual_reps, target_seconds, actual_seconds
nutrition_targets  id PK, user_id FK, effective_from, calories_kcal, protein_g,
                   carbs_g, fat_g, reason
meals              id PK, user_id FK, day, meal_type, created_at
meal_items         id PK, meal_id FK, food_code, custom_food_id, servings,
                   calories_kcal, protein_g, carbs_g, fat_g
custom_foods       id PK, user_id FK, name, serving_label, calories_kcal, protein_g,
                   carbs_g, fat_g
checkins           id PK, user_id FK, day, weight_kg, waist_cm, chest_cm, arms_cm,
                   thighs_cm, note           UNIQUE (user_id, day)
milestones         user_id FK, code, unlocked_at, seen_at   PK (user_id, code)
habits             id PK, user_id FK, type, baseline, period, pace_pct, started_on,
                   active
habit_logs         id PK, habit_id FK, day, units, logged_at
```
All schema changes go through Alembic migrations. Deleting a user cascades to all
of their rows.

## Feature specifications

### Accounts and security
- Register with email, password (minimum 10 characters), a required "I am 18 or
  older" checkbox and a required consent checkbox linking to the privacy policy.
- Login, logout, refresh. Access token lives in memory in the frontend, refresh
  token in an httpOnly, Secure, SameSite cookie. Refresh tokens are stored hashed
  and rotated on use.
- Rate-limit login and register by IP with a simple in-process limiter.
- No email is sent in version 1. Password reset is a documented admin CLI command
  (`python -m app.cli reset-password <email>`). Say this clearly on the login page
  as "contact the admin to reset".
- Change password (requires the current one).
- CORS restricted to the configured frontend origin. Secrets only from environment
  variables. Never log passwords, tokens or request bodies with personal data.

### Onboarding and profile
- After first login: name, age, sex, height, weight, goal (lose fat / build
  muscle / stay fit), level, minutes per day, training days per week, pull-up bar
  yes/no, diet type (veg / egg / non-veg), timezone (default from the browser), and
  an optional smoking or drinking reduction plan.
- Finishing onboarding generates the first nutrition targets and training plan.
- Editable later. Changing goal, level, time or days regenerates the plan from the
  next day after confirmation.

### Today
- One screen for "what do I do today": an original motivational line of the day,
  today's activity with a prominent "Add today's numbers" button if empty, today's
  workout, calories eaten versus target with quick add, habit allowance if active,
  and banners for check-in due and new milestones.

### Daily activity (the "upload" feature)
- One record per user per day: steps, distance, active calories, note. Any field
  may be left blank. Users copy these from their watch or phone health app.
- Add or edit any day, including past days, from a calendar or list. Future dates
  are rejected.
- If distance is blank it is estimated from steps (stride = height_cm x 0.415 /
  100 m); if active calories are blank they are estimated as steps x 0.04 x
  (weight_kg / 70). Estimated values are flagged and labelled "estimate".
- CSV import: a downloadable template with columns date, steps, distance_km,
  active_kcal. Upload shows a preview with row-level errors before saving, and
  asks whether to overwrite days that already have data. Maximum 1 MB.
- Activity screen: today, 7-day and 30-day charts, streak of days meeting the
  step goal.

### Runs
- Add a run manually: date, distance, duration, optional note.
- Or upload a GPX file exported from a watch or running app (maximum 5 MB). Parse
  it safely, compute distance, duration and per-km splits, and store the track
  downsampled to at most 2,000 points. Do not keep the original file.
- Calories = weight_kg x distance_km x 1.036, labelled "estimate".
- Run list newest first; detail page with the route on a Leaflet map (when a track
  exists), pace and splits. Edit and delete.

### Training plan (rule-based)
- `content/exercises.json`: at least 40 bodyweight exercises with code, name,
  muscle group (push / pull / legs / core / cardio), difficulty 1-5, type
  (reps / timed), short original instructions, easier and harder variation codes,
  and whether a pull-up bar is needed.
- `training_engine` builds a weekly plan from the profile:
  - 2-3 days per week: full-body sessions
  - 4 days: upper / lower split
  - 5-6 days: push / pull / legs
  - session size fits minutes per day (about 4 exercises for 20 minutes, 6 for
    40, 8 for 60) plus warm-up and cool-down
  - starting difficulty from level; without a pull-up bar, substitute a pull
    alternative
  - fat-loss goal adds a short cardio finisher; muscle goal favours lower reps on
    harder variations
- Workout page: exercises with target sets and reps or time, a rest timer, entry
  of actual reps, skip, and a finish summary. Sessions can be logged for past days.

### Eating plan and meal logging (formula-based)
- `nutrition_engine` targets:
  - BMR (Mifflin-St Jeor): 10 x kg + 6.25 x cm - 5 x age + 5 for men, - 161 for women
  - activity factor by training days per week: 0-2 -> 1.375, 3-4 -> 1.55, 5+ -> 1.725
  - goal adjustment: lose fat -400 kcal, build muscle +250 kcal, stay fit 0
  - never below 1500 kcal for men or 1200 kcal for women
  - protein 1.8 g/kg for fat loss, 1.6 g/kg otherwise; fat 25% of calories; carbs
    the remainder
- `content/foods.json`: at least 150 common foods with an Indian focus: code, name,
  serving label, calories, protein, carbs, fat, diet type, suitable meal types.
  These values are approximate: mark the file "approximate, to be verified by the
  owner" and show "estimate" beside calories in the UI.
- Meal suggestions: 3 options per meal type matching diet type and the remaining
  calories for the day.
- Meal logging: meal type, search foods, servings, or a custom food with its own
  values saved for reuse. Recent and frequent foods first. Any day can be edited.
- Eat page: calories and macros versus target, meals of the day, 7-day chart.

### Weekly check-in
- Weight (required), waist, chest, arms, thighs (optional), note.
- History with change from the previous check-in and a weight trend chart.
- "Check-in due" when the last one is more than 7 days old or missing.
- Saving updates profile weight and runs the adjustment engine.

### Weekly adjustment (rule-based)
`adjustment_engine` runs after a check-in when at least two exist:
- Nutrition, by weight change per week as a percentage of body weight:
  - lose fat: loss under 0.25% -> -100 kcal; loss over 1% -> +150 kcal
  - build muscle: gain under 0.1% -> +100 kcal; gain over 0.5% -> -100 kcal
  - stay fit: change beyond 0.5% either way -> 100 kcal toward stable
  - always respect the calorie floors
- Training, by last week's sessions:
  - 80% or more done with target reps met -> add reps up to the range top, then
    move to the harder variation
  - under 50% done -> remove one set per exercise
  - otherwise unchanged
- Show a plain summary of what changed and why, and store the reason.

### Milestones
- Defined in code: code, title, description, target, progress function.
- Initial set: 5,000 and 10,000 steps in a day; 100,000 total steps; first run;
  5 km and 10 km in one run; 25 km and 50 km total; first workout; 10 and 50
  workouts; 7-day and 30-day step-goal streaks; 7 days of logged meals; 4 and 12
  weekly check-ins; first full week inside a habit allowance.
- Re-evaluated server-side after any change to activity, runs, workouts, meals,
  check-ins or habit logs. `unlocked_at` is set once and never cleared.
- Milestones page with progress bars and a short celebration on unlock.

### Habit reduction (smoking and drinking)
- Optional. Setup: type, baseline (per day for smoking, per week for drinking),
  pace: gentle 5% or standard 10% of baseline per week.
- `habit_engine`: allowance for week n = max(0, round(baseline x (1 - pace x n))).
- Daily goals unlock the allowance: step goal met, planned workout done, meals
  logged each unlock a third. Show "available now" versus "locked".
- One-tap logging of each cigarette or drink, editable for past days.
- A week ending over the allowance repeats the same allowance next week. No blame
  wording. A week within the allowance shows units avoided versus baseline.
- Wording rule: this is a reduction plan. Never call smoking or drinking a prize,
  treat or reward, never encourage use, and include one line that a doctor can
  help with quitting.

### History
- Calendar view of any month: each day shows whether activity, workout, meals and
  check-in were logged. Selecting a day shows everything recorded for it, with
  edit links.

### Account, privacy and admin
- Export my data: one JSON download with everything stored for the user.
- Delete my account: password confirmation, then permanent removal of all rows.
- Static privacy policy and terms pages with clearly marked placeholder text for
  the owner to review; they must state what is stored, why, that it is not shared,
  how to export and delete, and a contact email from configuration.
- Admin page for users with `is_admin`: total users, new users per week, users
  active in the last 7 and 30 days, counts of records by type. Aggregates only; no
  admin view of an individual's health data. First admin is set by a CLI command.

### PWA
- Web manifest with app name "B.A.B", icons and theme colour so it can be added to
  the home screen. Service worker caches the app shell only, never API responses.

## UI guidelines
- Mobile-first, works from 360 px width, also usable on desktop.
- Dark theme, one accent colour (deep orange), large readable numbers.
- Bottom navigation on phones: Today, Activity, Train, Eat, More. More holds Runs,
  Check-in, Milestones, Habits, History, Account.
- Every page handles loading, empty and error states. Forms validate inline.
- Text tone: short, direct, encouraging, original.

## Quality rules
- Backend: ruff clean, pytest passing. Unit tests for every engine covering each
  threshold in this file, plus API tests for auth and cross-user isolation.
- Frontend: `ng build` and lint pass with no errors.
- `docs/rules.md` lists every formula and threshold and changes with the code.
- No TODO placeholders in shipped pages. If something is deferred, say so in the
  milestone report.
- Commit after each milestone with a clear message.

## How to work
Build in milestones, in order. After each milestone:
1. run backend tests and the frontend build
2. give me the exact commands to start everything locally
3. list what to check by hand in the browser
4. stop and wait for my confirmation before starting the next milestone

Milestones:
- M0: repo scaffold, docker-compose for PostgreSQL, backend skeleton with health
  endpoint and Alembic, Angular skeleton with theme and navigation, README,
  .gitignore, git init
- M1: accounts (register, login, refresh, logout, change password, guards, CLI
  commands), onboarding and profile
- M2: daily activity entry, past-day editing, CSV import, charts, Today screen
- M3: runs with manual entry, GPX upload and map
- M4: weekly check-in and milestones
- M5: training plan engine, exercise library, workout logging
- M6: nutrition targets, food list, suggestions, meal logging
- M7: weekly adjustment engine and summary
- M8: habit reduction
- M9: history calendar, export, delete account, privacy and terms pages, admin page
- M10: PWA setup, security review against this file, production Dockerfile,
  `docs/deploy.md` describing deployment to a free static host for the frontend
  and a free container host and managed PostgreSQL for the backend, without
  locking the code to any one provider

If a requirement is unclear or conflicts with what a library can do, ask before
choosing.

## Local environment notes
- Node: the frontend needs Node 22.22+ or 24 (latest Angular). Run `nvm use` in
  `frontend/` (an `.nvmrc` is provided).
- Python: backend targets the system Python 3.10+ in a venv at `backend/.venv`.
- Docker may not be installed on the dev machine; a native PostgreSQL works too
  (see README).
