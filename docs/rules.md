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
| training_mode | activity, gym, both (default activity) |

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
| Adjustment | the weekly adjustment may run after saving the newest check-in (see below) |

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

## Nutrition (`app/engines/nutrition_engine.py`, `content/foods.json`)

| Rule | Value |
| --- | --- |
| BMR (Mifflin-St Jeor) | 10 x kg + 6.25 x cm - 5 x age, +5 for men, -161 for women |
| Activity factor | training days 0-2: 1.375; 3-4: 1.55; 5+: 1.725 |
| Maintenance | BMR x activity factor |
| Goal adjustment | lose fat -400 kcal; build muscle +250 kcal; stay fit 0 |
| Calorie floor | never below 1,500 kcal for men or 1,200 kcal for women |
| Protein | 1.8 g per kg for fat loss; 1.6 g per kg otherwise |
| Fat | 25% of calories / 9 |
| Carbs | (calories - protein x 4 - fat x 9) / 4, never below 0 |
| Rounding | calories, grams rounded to whole numbers |
| When targets are set | at the end of onboarding, and when sex, age, height, weight, goal or training days change in the profile; effective from today (a second change on the same day replaces the first). The weekly adjustment then moves calories up or down from there |
| Target for a day | the newest target effective on or before that day; days before the first target use the first |
| Foods | 198 foods with an Indian focus, approximate values per serving, marked "to be verified by the owner"; shown as estimates |
| Diet filter | veg sees veg foods; egg sees veg and egg; non-veg sees all. Applies to search and suggestions |
| Logging | any day up to today; one meal per type per day with any number of items; nutrients are saved as eaten |
| Custom foods | per user; editing or deleting one does not change logged items |
| Search order | foods the user has logged (most recent day, then most times) first, then A-Z; up to 50 |

## Meal suggestions

| Rule | Value |
| --- | --- |
| Meal shares of the day | breakfast 25%, lunch 35%, snack 10%, dinner 30% |
| Budget | min(remaining calories for the day, target x meal share), never below 0 |
| Candidates | foods for the user's diet that list the meal type |
| Servings | 0.5, 1 or 1.5, never over budget; chosen to minimise unused budget + 12.5% for each half serving away from 1 |
| Ranking | lowest cost, then most protein per kcal |
| Options | 3 per meal, picked from the best 9 and rotated by day so ideas change daily |

## Weekly adjustment (`app/engines/adjustment_engine.py`)

When it runs: after saving a check-in, if all of these hold, otherwise the check-in
response explains why not:

| Condition | Value |
| --- | --- |
| Check-ins | at least two |
| Which | only the newest check-in (back-filling an older date never adjusts) |
| Once per check-in | editing a check-in that already adjusted does not run it again |
| Once a week | at least 6 days since the last adjustment's check-in |
| Comparison | the latest check-in at least 6 days before this one |

Nutrition, by weight change per week as a % of the earlier weight
((new - old) x 7 / days between / old x 100):

| Goal | Rule |
| --- | --- |
| Lose fat | loss under 0.25% -> 100 kcal less; loss over 1% -> 150 kcal more; otherwise no change (a gain counts as "under") |
| Build muscle | gain under 0.1% -> 100 kcal more; gain over 0.5% -> 100 kcal less; otherwise no change |
| Stay fit | gain over 0.5% -> 100 kcal less; loss over 0.5% -> 100 kcal more; otherwise no change |
| Floor | never below 1,500 kcal (men) or 1,200 kcal (women) |
| Base | the calorie target in effect on the check-in day |
| New target | effective today; protein, fat and carbs recalculated from the new calories and current weight; the reason is stored |

Training, by the 7 days before the check-in:

| Rule | Value |
| --- | --- |
| Completion | planned workout days done / planned workout days in those 7 days |
| No planned days | no change |
| 80% or more | each exercise where every logged set met its target: +2 reps (or +5 s) up to the top of its range; already at the top -> its harder variation at the start of that range, same sets (skipped if it needs a bar you do not have or is already in the session) |
| Under 50% | one set fewer for every exercise, never below 1 (finisher unchanged) |
| Otherwise | no change |
| Applies | from tomorrow; days up to today keep what they had. The adjusted week becomes the template that following weeks start from |

Plan carry-over: a new week copies the previous week's template when goal, level,
minutes, days and pull-up bar are unchanged, so progress builds week to week. A change
to any of those rebuilds the plan from the rules (progress starts again).

Summary: every adjustment stores plain lines of what changed and why, shown after the
check-in, in the check-in history and on the Train page.

## Habit reduction (`app/engines/habit_engine.py`)

| Rule | Value |
| --- | --- |
| Plans | optional; smoking (baseline per day) or drinking (baseline per week); one active plan per type; baseline 1 to 100 |
| Pace | gentle 5% or standard 10% of the baseline per week |
| Allowance | max(0, round(baseline x (1 - pace x step))), rounding halves up |
| Weeks | 7-day weeks counted from the day the plan starts |
| Steps | the first week is step 1. A finished week within its allowance moves to the next step; a week over it repeats the same step |
| Week allowance | smoking: daily allowance x 7; drinking: the weekly allowance |
| Daily goals | step goal met; planned workout done (a rest day counts as met); at least two meals logged |
| Unlocking, smoking | today's unlocked = floor(daily allowance x goals met today / 3) |
| Unlocking, drinking | this week's unlocked = floor(weekly allowance x goals met on all days so far this week / 21) |
| Available now | unlocked - used (never below 0); locked = allowance - unlocked |
| Logging | one tap adds one unit; any day from the plan start to today can be set to a total |
| Week within | shows units avoided = baseline week total - used |
| Week over | the same allowance repeats; no blame wording |
| Ending | a plan can be ended (kept for history) or deleted with its logs |
| Milestone | "Week within plan": one finished week within the allowance, across all plans |
| Wording | it is a reduction plan; use is never called a prize, treat or reward; nothing encourages use; every plan screen says a doctor can help with quitting. All habit wording is in `frontend/src/app/features/habits/wording.ts` |

## History, export and deletion

| Rule | Value |
| --- | --- |
| Month view | one entry per day: activity logged, workout done or skipped, at least one meal item, check-in, number of runs; future months refused |
| Day view | everything for one day (activity, runs, planned and logged workout, meals, check-in, reduction plan units), with edit links in the app |
| Export | one JSON file with every stored record for the user (account, profile, activity, runs with tracks, plans, workouts with sets, targets, custom foods, meals with items, check-ins, adjustments, milestones, plans with logs); no password hash or tokens |
| Delete account | needs the password and an explicit confirmation; rate limited like sign-in; removes the user and, by database cascade, every row they own; signs them out |
| Contact email | from `BAB_CONTACT_EMAIL`, served by `/config/public` for the privacy and terms pages |
| Admin | users with `is_admin` (set with `python -m app.cli make-admin <email>`); aggregates only: total users, active in 7 and 30 days (signed in or refreshed a session), new users per week for 12 weeks, record counts by type |

## Bounce (`app/services/bounce/`)

The model writes the plan; these rules decide what is accepted (`rules.py`).

| Rule | Value |
| --- | --- |
| Plan length | 7 days, Mon to Sun in order, in both the workout days and the meal days |
| Plan states | `none`; `active` while under 7 days old (user's local date); after that `update_ready` if a check-in is newer than `based_on_checkin_day` (or any check-in when that was empty), otherwise `checkin_needed` |
| Rebuild inside the week | only when the profile, the training mode or the gym details changed after the plan was made (409 `plan_current` otherwise) |
| Daily limit | `BAB_AI_DAILY_PLAN_LIMIT` plans per user in the last 24 hours (default 5) |
| Repairs before validation | a list sent as one string is split (by sentence, or by comma for a single sentence); text longer than its limit is cut; numbers outside a range are clamped to it; missing or null counts become 0 and lists empty. Missing days, meals or fields still fail |
| Request | JSON mode on (`BAB_AI_JSON_MODE`); on OpenRouter, reasoning off and `BAB_AI_FALLBACK_MODELS` tried in order when the main model is busy |
| Attempts | 2 per request: a reply that is not valid JSON in the shape, or breaks the diet, is sent back once with the reason |
| veg excludes | meat and fish words (chicken, mutton, lamb, goat, beef, pork, bacon, ham, sausage, salami, turkey, meat, keema, fish, tuna, salmon, sardine, mackerel, prawn(s), shrimp, crab, seafood) and egg, eggs, omelette, omelet |
| egg excludes | the meat and fish words |
| non_veg excludes | nothing |
| Diet scan | whole words in the meal plan and the "eat more" list; skipped after "no", "without", "skip", "avoid", "instead of", or before "-free" |
| Mode activity | gym focus, gym exercises and cardio minutes cleared |
| Mode gym | home exercises, walk and jog minutes cleared |
| Rest day | exercises, jog and cardio cleared (an easy walk may stay) |
| Supplement notes | only for gym or both; lines naming steroids, SARMs, prohormones, anabolic, clenbuterol or DNP dropped; at most 4 model lines; a fat burner warning first when the user takes one; two fixed safety lines last |
| Targets | from the current nutrition target row (rule engines), stored with the plan |
| Immediate suggestions | steps left to goal with a walk of `round(left / 100 / 5) x 5` minutes (at least 5), check-in due, today's part of the plan, then plan tips; at most 4 |
| Gym profile | experience beginner/intermediate/advanced, 1 to 7 days, 20 to 180 minutes, supplements from a fixed list ("none" clears the rest), notes up to 300 characters |

### Bounce notifications (`rules.pick_nudge`)

At most one, in this order. Hours are the user's local time.

| Kind | When | Message |
| --- | --- | --- |
| checkin | the weekly check-in is due (none yet, or the last is more than 7 days old) | weigh in so the plan can adapt |
| meals | the latest meal whose hour has passed is not logged: breakfast 10:00, lunch 15:00, snack 18:00, dinner 21:00 | what did you have for that meal |
| activity | no activity numbers for today from 12:00 | add today's steps |
| activity | steps under the goal from 18:00 | steps left to the goal |

The `id` (for example `meals:2026-11-15:lunch`) is stable for the day and reason. The web
app remembers dismissed ids in browser storage (last 30), so "Later" hides that one
notification until the reason or the day changes.
