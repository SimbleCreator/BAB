# B.A.B rules

Every formula and threshold used by the backend. This file changes together with
the code. Values marked "estimate" are shown to users with an "estimates only, not
medical advice" note.

## Accounts (`app/core`, `app/services/auth_service.py`)

| Rule | Value |
| --- | --- |
| Password length | 10 to 128 characters |
| Password hashing | argon2id (argon2-cffi defaults), rehashed on login if parameters change |
| Access token | JWT HS256, 15 minutes (`BAB_ACCESS_TOKEN_MINUTES`) |
| Refresh token | 48 random bytes, stored as SHA-256, 30 days (`BAB_REFRESH_TOKEN_DAYS`) |
| Refresh rotation | every refresh revokes the used token and issues a new one |
| Refresh reuse | a revoked token presented again revokes every session of that user |
| Change password | requires current password; signs out all other sessions |
| Admin reset | `python -m app.cli reset-password <email>` signs out all sessions |
| Login rate limit | 10 attempts per IP per 5 minutes |
| Register rate limit | 5 attempts per IP per hour |
| Refresh cookie | `bab_refresh`, httpOnly, Secure, SameSite `lax` (configurable), path `/api/v1/auth` |
| Production secret | `BAB_JWT_SECRET` must be 32+ characters and not the dev default |
| Age | registration requires `is_adult = true`; profile age 18 to 100 |

## Profile ranges (`app/schemas/profile.py`)

| Field | Allowed |
| --- | --- |
| age | 18 to 100 |
| sex | male, female (used by the BMR formula) |
| height_cm | 120 to 230, one decimal |
| weight_kg | 30 to 300, one decimal |
| goal | lose_fat, build_muscle, stay_fit |
| level | beginner, intermediate, advanced |
| minutes_per_day | 15 to 120 (UI offers 20, 30, 40, 50, 60, 90) |
| days_per_week | 2 to 6 |
| daily_step_goal | 1,000 to 50,000, default 8,000 |
| diet_type | veg, egg, non_veg |
| timezone | any IANA name known to the server |

## Daily activity (`app/engines/activity_engine.py`)

| Rule | Value |
| --- | --- |
| Records | one per user per local day; any field may be blank |
| Future days | rejected (compared with today in the profile timezone) |
| Stride length | height_cm x 0.415 / 100 metres |
| Distance estimate (blank distance) | steps x stride, rounded to whole metres, flagged `distance_estimated` |
| Calorie estimate (blank calories) | steps x 0.04 x (weight_kg / 70), rounded, flagged `active_kcal_estimated` |
| Estimate inputs | the current profile height and weight (estimates are computed when read, not stored) |
| No steps | nothing is estimated |
| Step goal met | steps >= daily_step_goal (current profile value) |
| Current streak | consecutive goal-met days ending today; if today is not met yet, ending yesterday |
| Longest streak | longest run of consecutive goal-met days ever |
| Limits | steps 0 to 200,000; distance 0 to 300 km; active calories 0 to 20,000; note 500 chars |
| List range | at most 366 days per request; summary 1 to 90 days |

## CSV import (`app/services/activity_csv.py`)

| Rule | Value |
| --- | --- |
| Columns | `date, steps, distance_km, active_kcal` (header required, any order, case-insensitive, extra columns ignored) |
| Format | UTF-8 (BOM allowed), comma or semicolon separated, dates `YYYY-MM-DD` |
| Size | at most 1 MB and 2,000 rows |
| Row errors | bad date, future date, date repeated in the file, non-number, out of range, no numbers |
| Import | rows with errors are skipped; existing days are kept unless overwrite is chosen |
| Overwrite | replaces steps, distance and calories; keeps the existing note; source becomes `csv` |

## Motivational line of the day (`app/engines/lines_engine.py`)

Index = (date ordinal x 7 + user id) mod number of lines in `content/lines.json`.
Same line all day for a user; changes every day.
