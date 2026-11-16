# Test plan

## Automated
- Backend: `cd backend && .venv/bin/pytest` (needs the `bab_test` database) and
  `.venv/bin/ruff check . && .venv/bin/ruff format --check .`
- Frontend: `cd frontend && npm run build`, `npm run lint`, `npx ng test --watch=false`

## Bounce (AI coach)
- The violet Bounce key sits above the middle of the dock on every page; its ball hops and
  now and then flexes into the strong form. Tapping it opens the Bounce page (key pressed).
- Go from any page to Home: the ball bounces in from the left in 2 or 3 arcs, turns strong
  mid-way, turns back and lands in the key. With reduced motion it only flexes in the key.
- With a notification (no check-in this week, a meal not logged after its hour, no steps
  by noon, or under the step goal after 18:00): after landing, Bounce jumps to the right
  holding a letter, with the message. The action opens Check-in, Eat or Activity; "Later"
  sends it back into the key and it stays hidden for that day. The key shows a pink dot
  while a notification is waiting.
- Without `BAB_AI_API_KEY`: the Bounce page shows "switched off" with today's tips;
  notifications still work; nothing else changes.
- With an OpenRouter key: Activity profile, veg diet -> "Build my week" shows a loader,
  then 7 day chips, walking and home exercises only, meals with no meat or eggs, foods to
  eat more and cut down, tips. Pressing again says the week is already set.
- Account > profile: switch to Gym -> Bounce asks for gym details and supplements; after
  saving, the rebuilt plan has gym sessions and supplement notes, no home exercises.
- "Both": plan has gym days and walk or home days.
- A week later (or move the plan's `created_at` back 8 days in the database): Bounce asks
  for the weekly check-in; after saving one, "Build next week's plan" appears.
- Export includes `gym_profile` and `bounce_plans`.

## Manual checks by milestone

### M0
- `GET http://localhost:8000/api/v1/health` returns `{"status":"ok"}`.
- `http://localhost:4200` shows the dark theme with a deep orange accent.
- At 360 px width the bottom navigation shows Today, Activity, Train, Eat, More.
- "More" opens a list with Runs, Check-in, Milestones, Habits, History, Account.
- At desktop width the navigation moves to a side rail.

### M1
- Signed out, any app URL goes to Sign in (with `returnUrl`).
- Register: empty submit shows inline errors; unticked 18+ or privacy blocks it;
  a 9-character password is refused; a used email shows "already exists".
- After register you land on onboarding; Next on an empty step shows errors.
- Timezone is pre-filled from the browser. Finish lands on Today with navigation.
- Reload the page: you stay signed in.
- Account: saved values are shown; change a value and save; reload to confirm.
- Change password with a wrong current password shows an error; with the right one
  shows a confirmation. Sign in with the new password works, the old one does not.
- Sign out returns to Sign in; reloading an app URL stays on Sign in.
- 11 quick failed logins show "Too many attempts".
- CLI: `python -m app.cli reset-password <email>` and `make-admin <email>`.

### M2
- Today with nothing logged shows the line of the day and "Add today's numbers".
- Add only steps: Today shows distance and active calories with an "estimate" label.
- Check the estimate: distance = steps x height_cm x 0.415 / 100 m;
  calories = steps x 0.04 x weight_kg / 70.
- Edit the day: estimated fields are blank with the estimate shown as a hint. Enter a
  distance and save: the "estimate" label goes away for distance only.
- Activity: "Add a past day" opens a calendar with future days disabled.
- Delete a day needs a second tap.
- Import: download the template, add rows (include a bad date, a future date and a
  duplicate date), choose it. The preview lists each problem by line. Days already
  logged are kept unless "Replace" is switched on.
- A file over 1 MB is refused before upload.
- Chart: 7 and 30 days, goal days in orange, dashed goal line. Streak and best streak
  match the data.
- Works at 360 px and on desktop.

### M3
- Runs with no runs shows an empty state and "Add run".
- Add by hand: empty submit shows inline errors; 10 km in 1:02:30 shows 6:15 /km and
  calories = weight x 10 x 1.036 with an "estimate" label. Future dates are disabled.
- Upload GPX: export a run from your watch or app. Distance, time, pace and splits
  appear; the map shows the route on OpenStreetMap with start and finish circles.
  The day is the local date the run started.
- Splits add up to the total time. The fastest full km is highlighted.
- A non-GPX file, a GPX without times or a file over 5 MB shows a clear message.
- Edit a run: change the distance; pace, calories and splits update; the map stays.
- Delete needs a second tap.
- The map stays under the top bar and bottom navigation when scrolling.

### M4
- With no check-ins, Today shows "Weekly check-in due"; Check-in explains the first one.
- Save a check-in for an earlier date, then one for today: history shows the
  weight and waist change, the trend chart appears, and Today's banner disappears.
- Profile weight (Account) follows the newest check-in only.
- A check-in 8 or more days old makes it due again; 7 days is not due yet.
- Log 10,000+ steps or a 5 km run: Today shows a milestone banner; Milestones shows a
  short celebration once, then not again after reload.
- Delete the run: the milestone stays unlocked.
- Milestones shows progress bars for locked ones (steps, km, days).

### M5
- After onboarding, Train shows this week: the split matches your days per week and
  rest days are marked. Sessions have warm-up, exercises with sets x reps or seconds,
  a cardio finisher for fat loss, and cool-down.
- 20 minutes gives 4 exercises, 40 gives 6, 60 gives 8.
- Without a pull-up bar no exercise needs a bar; with one, bar exercises appear.
- Start a workout: targets are pre-filled; ticking a set starts the rest timer
  (+15 s and Skip work); timed sets have a countdown; Skip exercise works.
- Finish: the summary shows % done, sets, sets on target and reps. Train shows Done.
- Open the workout again: the saved values come back for editing.
- Past days in this or earlier weeks can be logged; Skip day and Undo skip work.
- Account: change days per week: a confirmation explains the plan changes from
  tomorrow. Past days of this week stay as they were.
- Exercise library: search, group filter, detail with easier and harder links.
- Today shows the workout card or "Rest day"; the first finished workout unlocks
  "First workout".

### M6
- Eat shows today's calories against the target with an "estimate" label, macro bars
  and "How your target is set" (BMR, activity factor, goal adjustment, floor).
- Check the target by hand with the formula in docs/rules.md for your profile.
- Add food: pick a meal, search (for example "dal"), choose servings in half steps,
  add. Foods you have logged before appear first next time.
- Veg users never see egg or meat foods; egg users see eggs but not meat.
- Tap a logged item to change servings or remove it.
- Add your own food; it appears as "mine" and in My foods, where it can be edited or
  deleted without changing past days.
- Ideas under a meal show 3 options that fit that meal's budget; Add puts one in.
- Previous days can be viewed and logged; the next arrow stops at today.
- The 7-day chart shows calories per day against the target.
- Today shows "Food today" with Quick add.
- Logging meals on 7 different days unlocks "A week of meals".

### M7
- First check-in: the page says it sets the starting point; nothing changes.
- A check-in a week later: "Your plan was adjusted" lists the weight trend, the
  calorie decision and the training decision. Eat's target and its "How your target
  is set" reason match; Train shows "Updated after your check-in".
- Check the calorie rule for your goal with the table in docs/rules.md (for fat loss,
  losing less than 0.25% a week takes 100 kcal off).
- Save the same check-in again: it says the adjustment already ran.
- A check-in 3 days later: it says plans adjust once a week.
- Log every planned workout of the week at or above target, then check in: reps go up
  by 2 (or holds by 5 s) from tomorrow; at the top of the range the harder variation
  replaces it.
- Miss most workouts, then check in: one set fewer per exercise from tomorrow.
- Next week's plan keeps the changes. Changing goal or days in Account starts fresh.

### M8
- Onboarding has an optional "Cut down" step; skipping it works; choosing drinking
  with a baseline creates the plan and Today shows it.
- Habits: start a smoking plan (for example 12 a day, standard): this week shows 11 a
  day. Available now, locked and used match the goals ticked (each goal a third).
- Meet the step goal and log two meals: more becomes available.
- "Log a cigarette" adds one; "Edit recent days" changes any day since the start.
- After a finished week within the plan: the next week's allowance is lower and the
  page shows units avoided. After a week over: the same allowance repeats with a
  neutral message.
- Every plan screen shows the doctor line; no wording calls smoking or drinking a
  reward or treat.
- End plan needs a second tap; a new plan of that type can then start.

### M9
- History: the month grid marks activity, workout, meals, check-in and runs; the
  next-month arrow stops at the current month; future days cannot be picked.
- Pick a day: every section shows what was logged with Edit or Add links that open
  the right page for that day.
- Account, Your data: "Export my data" downloads a JSON file with everything you
  logged and no password or token.
- Delete account: without the tick box it asks you to confirm; a wrong password is
  refused; with both it signs you out, and signing in again fails.
- Privacy and Terms open while signed out, show the placeholder notice and the
  contact email from BAB_CONTACT_EMAIL.
- Admin: run `python -m app.cli make-admin <email>`, sign in again; More shows
  Admin with totals, active users, new users per week and record counts only.
  A non-admin opening /admin is sent to Today.

### M10
- `npm run build:prod` (with and without `BAB_API_URL`) succeeds; serve
  `dist/frontend/browser` over http://localhost:8080 (not the dev port 4200; add that
  origin to `BAB_FRONTEND_ORIGIN` for the test): the browser offers to install "B.A.B"
  with the orange B icon; after one visit the app shell opens offline (data pages show
  their error state, since API responses are never cached).
- DevTools > Application > Service workers: `ngsw-worker.js` active; Cache storage
  holds only app files, never `/api/` responses.
- Backend in production mode refuses to start without `BAB_JWT_SECRET`,
  `BAB_DATABASE_URL` and an https `BAB_FRONTEND_ORIGIN`.
- `/api/v1/health` response has nosniff, frame DENY, CSP and (production) HSTS headers;
  `/docs` and `/openapi.json` return 404 in production.
- Uploading a file over 6 MB returns 413 before it is parsed.
- Build the container (`docker build -t bab-api backend`) and run it with a real
  database; migrations run on start and the health check passes.

### M11 ("Know me", regional foods, logging by weight)
- New account: onboarding has "Your day" (city, state, work, food source, wake time)
  and "Your plate". With Karnataka picked, the plate list starts with South Indian
  dishes marked "local"; search finds others; at most 12 can be picked; switching diet
  to veg drops any egg or meat dish already picked.
- Eat > Add food: usual dishes appear first (tag "usual"), then "local" dishes; each row
  shows its serving weight. Picking a dish opens Weight entry with one serving's grams
  filled in; quick buttons for 0.5 / 1 / 1.5 / 2 servings; 200 g of a 150 g / 230 kcal
  dish shows 307 kcal. Servings mode still works. Empty or 0 g disables Add.
- The logged item shows "225 g"; tapping it edits the weight.
- Ideas for each meal list local dishes first (tags "your usual" / "local") with
  "about N g".
- My foods: a custom food without grams per serving cannot be logged by weight (the
  Weight toggle is hidden); add grams and it can.
- Account: "Your day", "Your plate" and "More about you" load and save; on a 360 px
  phone the paired fields stack.
- Bounce: a new plan's meals lean on the usual dishes and the region (check by eye).

### M12 (goal projection, then-vs-now cards, wins at check-in)
- Account > Goal and training: set a target weight. More > Progress shows a weeks
  range, a date range and "Based on your calorie target"; Home's weight card shows
  "72 kg in N to M weeks" with "estimate".
- Without a target: Progress says "Set a target weight" with a button to Account.
  A target in the wrong direction for the goal (e.g. higher while losing fat) shows
  "No date yet".
- Check-in: the energy, sleep and stairs buttons toggle (tap again to clear) and show
  in the history ("energy 4/5 · stairs 3/5").
- After 3 check-ins over 14+ days the basis line says "Based on your check-ins".
- 28 days after the first check-in a card appears: highlights, a then/now table and
  4-week stats; Home shows "Your 4-week card is ready" until Progress is opened.

### M13 (Sign in with Google)
- Without `BAB_GOOGLE_CLIENT_ID`: no Google button on sign-in or register; email sign-in
  works as before.
- With a real client id (docs/deploy.md, Step 5b): "Continue with Google" shows under
  both forms. A new Google user sees "Create your B.A.B account for you@gmail.com" with
  the 18+ and privacy boxes; Create account is disabled until both are ticked, then
  onboarding opens. Signing in again goes straight in.
- An existing email account signing in with the same Gmail address lands in the same
  account (data intact); its email sign-in still works.
- Google-only account: Account shows "Set a password" with no current-password field;
  after setting one, email sign-in works. Delete asks for the email instead of a password.
- Email sign-in for a Google-only account says to use the Google button.
- Live site: no CSP errors in the console when the Google button loads or its popup opens.

