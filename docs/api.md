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
