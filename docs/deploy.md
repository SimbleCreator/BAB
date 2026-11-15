# Deploying B.A.B

Three pieces, each on any provider's free tier:

| Piece | What it is | Needs |
| --- | --- | --- |
| Frontend | static files from `frontend/dist/frontend/browser` | any static host with a "single-page app" fallback to `index.html` |
| API | the container from `backend/Dockerfile` | any container host that runs a Docker image and gives HTTPS |
| Database | PostgreSQL 14 or newer | any managed PostgreSQL with a connection string |

Nothing in the code is tied to a provider. Examples of free tiers people commonly use
change often, so check current limits before choosing: static hosts (Cloudflare Pages,
Netlify, GitHub Pages, Vercel), container hosts (Render, Fly.io, Koyeb, Google Cloud Run),
managed PostgreSQL (Neon, Supabase, Aiven).

## 1. Choose the domain layout first (important)

The refresh token is an httpOnly cookie. Browsers increasingly block cookies between
different sites, so **put the frontend and the API on the same site**:

- **Recommended:** one domain you own, two subdomains, for example
  `app.example.com` (frontend) and `api.example.com` (API). Same site, so use
  `BAB_COOKIE_SAMESITE=lax`.
- **Also fine:** the static host proxies `/api/*` to the API (many static hosts support
  rewrites/proxies). The browser sees one origin. Build the frontend without
  `BAB_API_URL` and use `BAB_COOKIE_SAMESITE=lax`.
- **Avoid:** two unrelated provider subdomains (for example `myapp.pages.dev` and
  `myapi.onrender.com`). That needs `BAB_COOKIE_SAMESITE=none`, and Safari and other
  browsers may block the cookie, which signs users out on every reload.

## 2. Database

1. Create a PostgreSQL database and copy its connection string.
2. Change the scheme to the async driver: `postgresql+asyncpg://user:password@host:5432/dbname`.
   If the provider requires TLS, add `?ssl=require`.
3. Turn on the provider's automatic backups if the free tier has them; otherwise
   schedule a `pg_dump` (see "Backups").

## 3. API container

Build and run anywhere Docker runs:

```bash
docker build -t bab-api backend
```
```bash
docker run -p 8000:8000 --env-file prod.env bab-api
```

On a container host, point it at the repository's `backend/` folder (Dockerfile build)
or push the image to a registry it can pull from.

Environment variables (secrets go in the host's secret settings, never in git):

| Variable | Required | Example / notes |
| --- | --- | --- |
| `BAB_DATABASE_URL` | yes | `postgresql+asyncpg://user:pass@host:5432/bab?ssl=require` |
| `BAB_JWT_SECRET` | yes | 32+ random characters: `python -c "import secrets; print(secrets.token_urlsafe(48))"` |
| `BAB_FRONTEND_ORIGIN` | yes | `https://app.example.com` (exact origin, https, no trailing slash) |
| `BAB_CONTACT_EMAIL` | yes | shown on the privacy and terms pages |
| `BAB_COOKIE_SAMESITE` | no | `lax` (default) or `none` (see section 1) |
| `BAB_ENV` | set by the image | `production`: hides API docs, adds HSTS, refuses weak settings |
| `PORT` | no | most hosts set this; default 8000 |
| `RUN_MIGRATIONS` | no | `1` (default) runs `alembic upgrade head` on start; set `0` to run them yourself |
| `FORWARDED_ALLOW_IPS` | depends | IP(s) of the host's proxy so rate limits see real client IPs; `*` only if the container is reachable solely through that proxy |
| `BAB_ACCESS_TOKEN_MINUTES`, `BAB_REFRESH_TOKEN_DAYS` | no | defaults 15 and 30 |

The container refuses to start in production with the development secret, the
development database URL, or a non-https frontend origin.

Health check: `GET /api/v1/health` (also built into the image).

Run one container. Login and registration rate limits are kept in memory, so they only
work as intended with a single instance.

First admin (after the first sign-up), using the host's one-off command or shell:

```bash
python -m app.cli make-admin you@example.com
```

Password reset (no email in version 1):

```bash
python -m app.cli reset-password user@example.com --generate
```

## 4. Frontend

Build with the API address (skip `BAB_API_URL` when the static host proxies `/api`):

```bash
cd frontend && npm ci && BAB_API_URL=https://api.example.com/api/v1 npm run build:prod
```

Upload `frontend/dist/frontend/browser/`. On the static host:

- **SPA fallback:** serve `index.html` for unknown paths (so `/today` works on reload).
- **No caching for these files:** `index.html`, `ngsw.json`, `ngsw-worker.js`,
  `manifest.webmanifest` (`Cache-Control: no-cache`). Hashed `*.js`/`*.css` can be cached
  for a year.
- **Headers** (adjust the API origin):

```
Content-Security-Policy: default-src 'self'; script-src 'self'; style-src 'self' 'unsafe-inline' https://fonts.googleapis.com; font-src https://fonts.gstatic.com; img-src 'self' data: https://tile.openstreetmap.org; connect-src 'self' https://api.example.com; manifest-src 'self'; worker-src 'self'; frame-ancestors 'none'; base-uri 'self'; form-action 'self'
X-Content-Type-Options: nosniff
Referrer-Policy: strict-origin-when-cross-origin
Permissions-Policy: geolocation=(), camera=(), microphone=()
Strict-Transport-Security: max-age=31536000; includeSubDomains
```

`'unsafe-inline'` for styles is needed by Angular's component styles; scripts stay
`'self'` only.

The service worker caches the app shell only. API responses are never cached. After a
new deploy, users get the new version on their next visit (the old one is replaced in
the background).

## 5. After the first deploy

1. Open `https://app.example.com`, register, finish onboarding.
2. Make yourself admin (above) and check the Admin page.
3. Install to the home screen from the browser menu and open it.
4. Check `https://api.example.com/docs` returns 404 (docs are development-only).
5. Review the privacy policy and terms placeholders, and the food values in
   `backend/app/content/foods.json`.

## Free tier caveats

- Free containers often sleep when idle; the first request after sleeping can take
  several seconds. The app shows its loading state meanwhile.
- Free databases have small storage limits. GPS tracks are capped at 2,000 points per
  run to keep rows small.
- OpenStreetMap tiles are free under the OSM tile usage policy (attribution is shown on
  every map). Heavy traffic needs a tile provider of your own.

## Backups

If the database provider has no automatic backups:

```bash
pg_dump --format=custom --no-owner "$DATABASE_URL_WITHOUT_ASYNCPG" > bab-$(date +%F).dump
```

Restore with `pg_restore --no-owner --dbname "$URL" bab-YYYY-MM-DD.dump`.
