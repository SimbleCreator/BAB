# B.A.B API guide

The backend is the product contract. Web, Android and iOS clients call the same
endpoints.

- Base path: `/api/v1`
- Interactive docs (development): `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`
- All stored values are raw units: metres, seconds, steps, kg, cm, kcal.
- Timestamps are UTC (ISO 8601). A `day` is the user's local calendar date
  (`YYYY-MM-DD`) based on the timezone saved on their profile.
- Errors: `{"detail": "<message for the user>", "code": "<machine code>"}`.
  Validation errors (422) use FastAPI's list format in `detail`.

## Authentication

1. `POST /auth/register` or `POST /auth/login` returns `{access_token, expires_in, user}`
   and sets the `bab_refresh` cookie (httpOnly, path `/api/v1/auth`).
2. Send `Authorization: Bearer <access_token>` on every other call.
3. On a 401, call `POST /auth/refresh` once (cookie is sent automatically) and retry.
   If refresh also fails, the user must sign in again.
4. Browsers must send credentials (`withCredentials` / `credentials: 'include'`).
   Mobile apps keep the cookie in their HTTP client's cookie store.

## Endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/health` | none | Liveness check |
| POST | `/auth/register` | none | Create account (18+, consent required), returns tokens |
| POST | `/auth/login` | none | Sign in, returns tokens |
| POST | `/auth/refresh` | cookie | Rotate refresh cookie, new access token |
| POST | `/auth/logout` | cookie | Revoke the refresh token, clear cookie |
| GET | `/auth/me` | bearer | Current user, including `has_profile` |
| POST | `/auth/change-password` | bearer | Needs current password; other sessions end |
| GET | `/profile` | bearer | Own profile; 404 `profile_missing` before onboarding |
| PUT | `/profile` | bearer | Create (onboarding) or replace the profile |
| GET | `/today` | bearer | Today screen: local date, name, line of the day, step goal, streak, today's activity |
| GET | `/activity?from=&to=` | bearer | Logged days in a range (at most 366 days), oldest first |
| GET | `/activity/summary?days=30` | bearer | One point per day ending today, totals, current and longest streak |
| GET | `/activity/csv-template` | none | CSV template download |
| POST | `/activity/import/preview` | bearer | Multipart `file`; parse and report row errors, nothing saved |
| POST | `/activity/import` | bearer | Multipart `file` and `overwrite` (true/false); saves valid rows |
| GET | `/activity/{day}` | bearer | One day; 404 `activity_missing` if nothing logged |
| PUT | `/activity/{day}` | bearer | Create or replace a day (`source` becomes `manual`); future days rejected |
| DELETE | `/activity/{day}` | bearer | Remove a day |

| GET | `/runs?limit=50&offset=0` | bearer | Runs newest first, with `total` |
| POST | `/runs` | bearer | Add a run by hand (`day`, `distance_m`, `duration_s`, `note`) |
| POST | `/runs/gpx` | bearer | Multipart `file` (GPX, 5 MB) and optional `note`; file is not kept |
| GET | `/runs/{id}` | bearer | Run with `splits` and `track` (empty for manual runs) |
| PATCH | `/runs/{id}` | bearer | Change any of `day`, `distance_m`, `duration_s`, `note` |
| DELETE | `/runs/{id}` | bearer | Delete the run and its track |

| GET | `/checkins` | bearer | All check-ins, newest first, with change from the previous one |
| GET | `/checkins/status` | bearer | `due`, last check-in day, days since |
| PUT | `/checkins/{day}` | bearer | Create or replace a check-in; the newest one updates profile weight and may run the weekly adjustment (`adjustment`, or `adjustment_note` saying why not) |
| DELETE | `/checkins/{day}` | bearer | Remove a check-in |
| GET | `/checkins/adjustments` | bearer | Weekly adjustments, newest first, with plain summary lines |
| GET | `/milestones` | bearer | Every milestone with progress, `unlocked_at` and `seen` |
| POST | `/milestones/seen` | bearer | Mark unlocked milestones as seen after celebrating |

| GET | `/exercises` | bearer | Exercise library |
| GET | `/exercises/{code}` | bearer | One exercise with easier and harder codes |
| GET | `/training/week?day=` | bearer | The plan for the week containing `day` (default today) with each day's status |
| GET | `/training/workouts/{day}` | bearer | The logged workout with sets and summary; 404 if none |
| PUT | `/training/workouts/{day}` | bearer | Save `{status, sets:[{exercise_code, set_no, actual_reps, actual_seconds}]}` for a planned day |
| DELETE | `/training/workouts/{day}` | bearer | Clear a day's log |

| GET | `/nutrition/targets` | bearer | Current target, how it is calculated, and target history |
| GET | `/nutrition/days/{day}` | bearer | Target, eaten totals, remaining and the four meals with items |
| POST | `/nutrition/days/{day}/items` | bearer | Log `{meal_type, food_code or custom_food_id, servings}`; returns the day |
| PATCH | `/nutrition/items/{id}` | bearer | Change servings; returns the day |
| DELETE | `/nutrition/items/{id}` | bearer | Remove an item; returns the day |
| GET | `/nutrition/days/{day}/suggestions` | bearer | 3 options per meal within each meal's calorie budget |
| GET | `/nutrition/summary?days=7` | bearer | Calories eaten and target per day |
| GET | `/foods?q=&meal_type=` | bearer | Built-in foods for the user's diet and their custom foods, recent first |
| GET/POST | `/foods/custom` | bearer | List or create custom foods |
| PUT/DELETE | `/foods/custom/{id}` | bearer | Edit or delete a custom food |

`/today` also returns `nutrition` (target, eaten, remaining, protein), `workout` (today's planned session, or null on a rest day) `checkin_due` and `new_milestones` (unlocked, not yet seen).

Activity responses return the value to show. When `distance_estimated` or
`active_kcal_estimated` is true, that field was blank and the value is an estimate;
send it back as `null` when editing so it stays estimated.

Most feature endpoints answer 409 `profile_missing` until onboarding is finished.
