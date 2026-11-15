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
