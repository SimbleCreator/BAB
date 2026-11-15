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
