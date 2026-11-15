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

## Runs (`app/engines/run_engine.py`, `app/services/gpx.py`)

| Rule | Value |
| --- | --- |
| Calories | weight_kg x distance_km x 1.036, rounded; always labelled "estimate"; uses profile weight when the run is saved or its distance edited |
| Pace | duration_s / (distance_m / 1000), seconds per km |
| Manual limits | distance 10 m to 300 km; duration 30 s to 48 h; note 500 chars; no future days |
| GPX file | at most 5 MB; parsed with defusedxml (DTDs and entities refused); GPX 1.0 and 1.1; not stored |
| GPX points | `trk/trkseg/trkpt`; points outside valid lat/lon skipped; at most 200,000 read |
| GPX needs | at least two points with times; at least 10 m and 30 s |
| Track distance | sum of great-circle (haversine, R = 6,371 km) distances between consecutive points; not counted across segment breaks |
| Duration | elapsed time from first to last timestamp |
| Day | local date of the first timestamp in the profile timezone |
| Stored track | downsampled to at most 2,000 evenly spaced points, first and last always kept; distance is measured on the full track first |
| Splits | per km; the time at each km mark is interpolated between points; a last partial split is shown if 10 m or more |
| Splits after edits | track distances are scaled to the run's stored distance, so splits always add up to the distance and time shown |

## Weekly check-in (`app/engines/checkin_engine.py`)

| Rule | Value |
| --- | --- |
| Fields | weight 30 to 300 kg (required); waist, chest, arm, thigh 20 to 250 cm (optional); note 500 chars |
| One per day | saving the same day again replaces it; future days rejected |
| Due | no check-in yet, or the newest one is more than 7 days old (day 8 onward) |
| Change | value minus the previous check-in's value (by date), rounded to 0.1 |
| Profile weight | saving the newest check-in (latest date) sets the profile weight; back-filling an older date does not |
| Deleting | does not change the profile weight |
| Adjustment | the weekly adjustment engine runs after a check-in from M7 |

## Milestones (`app/engines/milestone_engine.py`)

| Code | Title | Unlocks when |
| --- | --- | --- |
| steps_5k_day | 5K step day | best single day >= 5,000 steps |
| steps_10k_day | 10K step day | best single day >= 10,000 steps |
| steps_100k_total | 100K club | total steps >= 100,000 |
| streak_7 | One solid week | longest step-goal streak >= 7 days |
| streak_30 | Month of momentum | longest step-goal streak >= 30 days |
| run_first | First run | runs >= 1 |
| run_5k | 5 km run | longest single run >= 5,000 m |
| run_10k | 10 km run | longest single run >= 10,000 m |
| run_25k_total | 25 km on the clock | total run distance >= 25,000 m |
| run_50k_total | 50 km on the clock | total run distance >= 50,000 m |
| workout_first | First workout | finished workouts >= 1 (counted from M5) |
| workout_10 | 10 workouts | finished workouts >= 10 |
| workout_50 | 50 workouts | finished workouts >= 50 |
| meals_7_days | A week of meals | different days with a logged meal >= 7 (counted from M6) |
| checkins_4 | Four check-ins | check-ins >= 4 |
| checkins_12 | Twelve check-ins | check-ins >= 12 |
| habit_week_within | Week within plan | full weeks inside the habit allowance >= 1 (counted from M8) |

- Evaluated on the server after every change to activity (including CSV import),
  runs, check-ins (and, as they are built, workouts, meals and habit logs), and
  when the milestones list or Today is read, to catch up on older data.
- Streak milestones use the longest streak ever against the current step goal.
- `unlocked_at` is set once and never cleared, even if the data is deleted later.
- `seen_at` is set when the user has seen the celebration (`POST /milestones/seen`).

## Training plan (`app/engines/training_engine.py`, `content/exercises.json`)

| Rule | Value |
| --- | --- |
| Library | 71 bodyweight exercises (push, pull, legs, core, cardio), difficulty 1 to 5, reps or timed, easier/harder links, pull-up bar flag; 6 warm-up and 5 cool-down drills |
| Split | 2-3 days: full body; 4 days: upper / lower / upper / lower; 5 days: push, pull, legs, push, pull; 6 days: push, pull, legs x 2 |
| Training days | 2: Mon, Thu; 3: Mon, Wed, Fri; 4: Mon, Tue, Thu, Fri; 5: Mon, Tue, Wed, Fri, Sat; 6: Mon to Sat |
| Session size | exercises = clamp(floor(minutes / 10 + 0.5) + 2, 4, 8): 20 min 4, 30 min 5, 40 min 6, 50 min 7, 60+ min 8 |
| Slots | full body cycles push, pull, legs, core; upper: push, pull, push, pull, core; lower: legs, legs, core, legs, core; push/pull/legs days: main group twice, core, main group |
| Difficulty | beginner 2, intermediate 3, advanced 4; build muscle +1 (max 5). Exercises are chosen from target-1 to target, nearest first |
| Variety | no exercise repeats in a session; repeated session types in a week rotate through the choices |
| No pull-up bar | exercises that need a bar are never chosen; pull slots use door, table and floor rows |
| Reps | lose fat 3 x 12-15, rest 45 s; stay fit 3 x 10-12, rest 60 s; build muscle 4 x 6-10, rest 90 s. Beginners do one set fewer (min 2). Target starts at the bottom of the range |
| Timed | beginner 20-40 s, intermediate 30-50 s, advanced 40-60 s; target starts at the bottom |
| Fat-loss finisher | one cardio exercise, 3 rounds, rest 30 s (timed by level, or 8-15 reps) |
| Warm-up / cool-down | 3 drills each, rotating per session |
| Estimate | minutes = (sets x (work + rest) for every exercise + warm-up + cool-down) / 60; a rep counts as 3 s |
| Weeks | a week starts Monday (profile timezone). Each week's plan is generated the first time it is needed; future weeks are not shown |
| Plan changes | changing goal, level, minutes, days or pull-up bar (after confirming) keeps this week's sessions up to today and uses the new plan from tomorrow |

## Workouts

| Rule | Value |
| --- | --- |
| Logging | only on a planned day, today or earlier (including past weeks); one log per day, saving again replaces it |
| Targets | taken from the plan, never from the client |
| Status | done or skipped; a skipped day stores no sets |
| Sets not sent | stored as not done |
| Target met | actual reps >= target reps, or actual seconds >= target seconds |
| Completion | sets done / sets planned (including the finisher), as a percentage |
| Milestones | a "done" workout counts toward workout milestones; skipped days do not |
