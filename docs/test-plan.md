# Test plan

## Automated
- Backend: `cd backend && .venv/bin/pytest` (needs the `bab_test` database) and
  `.venv/bin/ruff check . && .venv/bin/ruff format --check .`
- Frontend: `cd frontend && npm run build`, `npm run lint`, `npx ng test --watch=false`

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
