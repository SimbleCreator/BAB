# Deployment

Written in M10. The plan: the Angular build is served from any free static host,
the backend runs from `backend/Dockerfile` on any free container host, and the
database is any managed PostgreSQL free tier. No provider-specific code.
