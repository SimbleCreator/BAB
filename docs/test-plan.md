# Test plan

## Automated
- Backend: `cd backend && .venv/bin/pytest` and `.venv/bin/ruff check .`
- Frontend: `cd frontend && npm run build` and `npm run lint`

## Manual checks by milestone

### M0
- `GET http://localhost:8000/api/v1/health` returns `{"status":"ok"}`.
- `http://localhost:4200` shows the dark theme with a deep orange accent.
- At 360 px width the bottom navigation shows Today, Activity, Train, Eat, More.
- "More" opens a list with Runs, Check-in, Milestones, Habits, History, Account.
- At desktop width the navigation moves to a side rail.
