# B.A.B API guide

The backend is the product contract. Web, Android and iOS clients call the same
endpoints.

- Base path: `/api/v1`
- Interactive docs (development): `http://localhost:8000/docs`
- OpenAPI schema: `http://localhost:8000/openapi.json`
- All stored values are raw units: metres, seconds, steps, kg, cm, kcal.
- Timestamps are UTC (ISO 8601). A `day` is the user's local calendar date
  (`YYYY-MM-DD`) based on the timezone saved on their profile.

## Endpoints

| Method | Path | Auth | Purpose |
| --- | --- | --- | --- |
| GET | `/api/v1/health` | none | Liveness check, returns `{"status": "ok", "version": ...}` |
