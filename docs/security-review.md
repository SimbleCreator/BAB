# Security review (M10)

Reviewed against the rules in CLAUDE.md on 2026-11-15. "Test" points to the automated
test that covers the item.

## Accounts and sessions

| Requirement | Status | Where / test |
| --- | --- | --- |
| Passwords hashed with argon2, min 10 chars | done | `core/security.py`; `test_register_password_minimum_is_ten` |
| Same response and similar time for unknown email and wrong password | done | dummy hash; `test_login_ok_and_wrong_password_same_message_as_unknown` |
| Access token in memory only, never in storage | done | `AuthService`; no `localStorage`/`sessionStorage` in the frontend |
| Refresh token httpOnly, Secure, SameSite, path `/api/v1/auth`, stored hashed, rotated | done | `core/cookies.py`; `test_register_returns_token_and_secure_cookie`, `test_refresh_rotates_cookie` |
| Refresh token reuse ends every session | done | `test_refresh_reuse_revokes_all_sessions` |
| Cookie endpoints protected from cross-site use | added in M10 | `X-BAB-Client` header required on refresh and logout; CORS refuses other origins; `test_cookie_endpoints_need_client_header`, `test_preflight_allows_client_header_only_for_frontend` |
| Rate limit login, register (and account deletion) by IP | done | `core/rate_limit.py`; `test_login_rate_limited`, `test_register_rate_limited` |
| Change password needs the current one; other sessions end | done | `test_change_password` |
| JWT algorithm pinned, secret strong in production | done | HS256 only; production refuses weak/dev secret: `test_production_refuses_weak_secret` |
| Adults only, consent recorded | done | `RegisterIn`; `test_register_validation` |

## Data access

| Requirement | Status | Where / test |
| --- | --- | --- |
| Every query filters by the signed-in user | done | repositories take `user_id`; child rows reached through owned parents |
| One isolation test per router | done | `test_*_isolation_between_users` for profile, activity, runs, check-ins, milestones, training, nutrition, adjustments, habits, history, Bounce and export |
| Admin sees aggregates only | done | `/admin/stats`; `test_admin_stats` asserts no emails |
| Account deletion removes every row | done | DB cascades; `test_delete_account_removes_everything` checks every table with `user_id` and child tables for orphans |
| Export contains no secrets | done | `test_export` |

## Input and uploads

| Requirement | Status | Where / test |
| --- | --- | --- |
| Request validation | done | Pydantic models with ranges on every input |
| GPX parsed with defusedxml only | done | `services/gpx.py`; entity expansion and XXE tests |
| Upload size limits (CSV 1 MB, GPX 5 MB) | done | read limits in routers |
| Request body capped before parsing | added in M10 | `core/middleware.py` `BodySizeLimit` (6 MB, Content-Length or streamed); `test_oversized_*` |
| Original GPX file not kept | done | only the downsampled track is stored |
| SQL injection | n/a | SQLAlchemy ORM with bound parameters; no string SQL in `app/` |

## Configuration and transport

| Requirement | Status | Where / test |
| --- | --- | --- |
| Secrets only from environment variables | done | `core/config.py`; no secrets in git (`.env` ignored) |
| Production refuses unsafe settings | added in M10 | dev DB URL, dev/short JWT secret, non-https frontend origin; `test_production_settings_are_strict` |
| CORS restricted to the frontend origin | done | `test_cors_allows_configured_origin_only` |
| Security headers | added in M10 | nosniff, frame DENY, no-referrer, CSP `default-src 'none'`, HSTS in production; `test_security_headers` |
| API docs and schema off in production | added in M10 | `test_production_hides_docs_and_schema` |
| Real client IP behind a proxy (for rate limits) | added in M10 | `--proxy-headers` with `FORWARDED_ALLOW_IPS` in the entrypoint |
| No logging of passwords, tokens or bodies | done | no app logging of requests; access logs show method and path only. The admin CLI prints a generated password on purpose |
| Container runs as non-root | done | `USER bab` in `backend/Dockerfile` |

## Frontend

| Requirement | Status | Notes |
| --- | --- | --- |
| No unsafe HTML | done | no `innerHTML` or `bypassSecurityTrust*`; Angular escapes templates |
| Service worker never caches API responses | done | `ngsw-config.json` has no `dataGroups`; `/api/**` excluded from navigation |
| Content Security Policy | documented | set by the static host; see `docs/deploy.md` |
| Open redirects | done | login `returnUrl` and `back` links accept same-app paths only |

## Known limits and follow-ups

- Rate limiting is per process: run a single API container (documented).
- Bounce sends profile numbers (no name, email or IDs) to the configured AI endpoint
  only when the user asks for a plan; the privacy page says so. The token is read from
  `BAB_AI_API_KEY` and never logged; model replies are validated against a strict
  schema before storage and rendered as plain text (Angular escapes it). Prompt text is
  built from validated enums and numbers, plus the user's own gym notes (300 characters
  at most), which can only affect that user's own plan.
- Fonts load from Google Fonts, which receives the visitor's IP address. The privacy
  policy says so. Self-hosting the fonts would remove this; it needs two font packages,
  which are outside the agreed library list.
- `npm audit` reports moderate issues in build tooling only (`minimatch` in the dev
  toolchain); nothing in the shipped bundle. Re-check before each release.
- Python dependency audit: run `pip-audit` (not installed as a project dependency) in CI
  or before releases.
- No account lockout beyond the IP rate limit; consider per-account limits if abuse shows up.
- Email verification and self-service password reset are out of scope for version 1.
