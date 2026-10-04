# OncoGonAPI

Backend for the OncoGon platform: **Python FastAPI microservices**, run with **Docker Compose**. Right now it provides **authentication** and a **research** service that serves mock data; new services (projects, evidence, analysis, …) plug into the same gateway.

Part of a three-repo setup:

| Repo | What it is |
|---|---|
| [OncoGon](../OncoGon) | React Native app (the client) |
| **OncoGonAPI** (this repo) | Gateway + microservices |
| [OncoGonDB](../OncoGonDB) | PostgreSQL 16 — **start it first** |

```
 Mobile app
     │  HTTP  /api/v1/<service>/...
     ▼
 ┌────────────────────┐      ┌──────────────────────┐      ┌────────────────────────┐
 │ gateway  :8000     │ ───► │ auth-service  :8001  │ ───► │ oncogon-postgres :5432 │
 │ (only public port) │      │ (internal only)      │      │ schema "auth"          │
 │                    │      └──────────────────────┘      └────────────────────────┘
 │                    │      ┌──────────────────────────┐
 │                    │ ───► │ research-service  :8002  │ ───► app/mock/mock_data.json
 └────────────────────┘      │ (internal only)          │      (until a real data layer)
                             └──────────────────────────┘
          all containers share the Docker network  oncogon-net
```

---

## Quick start

```sh
cd ../OncoGonDB  && docker compose up -d           # database + oncogon-net network
cd ../OncoGonAPI && docker compose up -d --build   # gateway + auth-service
curl localhost:8000/health                         # {"status":"ok","services":{"auth":"ok","research":"ok"}}
```

- API docs: the endpoint tables below. The auth service's own Swagger UI (`/docs`, development only) is internal; to browse it, temporarily add `ports: ["8001:8001"]` to `auth-service` and open http://localhost:8001/docs.
- Logs: `docker compose logs -f gateway auth-service`
- Stop: `docker compose down` (data stays in OncoGonDB)
- After code changes: `docker compose up -d --build`

The auth service runs **Alembic migrations automatically** on start (`alembic upgrade head`), then serves.

---

## Configuration (`.env`)

Copy `.env.example` to `.env`. A development `.env` with generated secrets already exists.

| Variable | Default | Notes |
|---|---|---|
| `ENVIRONMENT` | `development` | `production` hides `/docs` and **never** returns reset codes |
| `GATEWAY_PORT` | `8000` | Host port for the gateway |
| `CORS_ORIGINS` | `*` | Comma-separated list in production |
| `POSTGRES_DB` | `oncogon` | Must match OncoGonDB |
| `AUTH_DB_USER` / `AUTH_DB_PASSWORD` | `oncogon_auth` / — | **Must match `OncoGonDB/.env`** |
| `DB_HOST` | `oncogon-postgres` | Container name on `oncogon-net` |
| `JWT_SECRET` | — | Required. `openssl rand -hex 32` |
| `ACCESS_TOKEN_TTL_MINUTES` | `15` | |
| `REFRESH_TOKEN_TTL_DAYS` | `30` | |
| `AUTH_RATE_LIMIT_PER_MINUTE` | `20` | Per client IP, per credential endpoint |

`.env` is git-ignored — never commit it.

---

## Services

### gateway — `services/gateway`

The single entry point. Routes `/api/v1/<service>/<path>` to the matching service from the `SERVICES` registry in `app/main.py`.

- Forwards method, query, body and headers; strips hop-by-hop headers
- Adds/propagates `X-Request-ID` (returned on every response — quote it when reporting a bug)
- Sets `X-Forwarded-For` so services see the real client IP
- Rate-limits `login`, `register` and `password/*` per IP (`429` + `Retry-After`)
- `GET /health` checks every registered service (`503` if any is down)
- Returns `503 {"detail": "Service temporarily unavailable."}` when a service can't be reached

### auth-service — `services/auth`

| Path | Purpose |
|---|---|
| `app/config.py` | Settings from environment |
| `app/db.py` | Async SQLAlchemy engine; all tables live in schema `auth` |
| `app/models.py` | `User`, `RefreshToken`, `PasswordResetCode` |
| `app/schemas.py` | Request/response models and validation (password rules, allowed roles) |
| `app/security.py` | Argon2 hashing, JWT create/verify, token and code generation |
| `app/service.py` | All auth rules (login, lockout, rotation, reset) |
| `app/api/routes.py` | Thin HTTP layer |
| `migrations/` | Alembic (async); `versions/0001_initial_auth.py` creates the tables |
| `tests/test_auth_e2e.py` | End-to-end tests through the gateway |

### research-service — `services/research`

Serves the app's project, experiment, analysis and memory data. **All data is mock** for now: it comes from one file, and every response carries `X-Data-Mode: SIMULATED`.

| Path | Purpose |
|---|---|
| `app/mock/mock_data.json` | **All mock data** — edit this to change what the app shows |
| `app/repositories/base.py` | `ResearchRepository` — the data-access contract services depend on |
| `app/repositories/mock_repository.py` | Implements the contract by reading `mock_data.json` |
| `app/deps.py` | `get_repository()` (the one place to swap in a real data layer) and `require_user` (verifies the auth service's access token) |
| `app/services/*.py` | Logic per area: workspace, project, experiment, analysis, memory, catalog |
| `app/schemas.py` | Response models — the API contract the app relies on |
| `app/api/routes.py` | Thin HTTP layer |
| `tests/test_research.py` | In-process tests (no Docker or DB needed) |

**Replacing the mock data:** write a class with the same methods as `ResearchRepository` (e.g. backed by PostgreSQL in a `research` schema), return it from `get_repository()` in `app/deps.py`, and set `data_mode` to `RESEARCH` in what `get_meta()` returns. Services, routes and the app stay unchanged.

---

## Auth API

Base URL: `http://<host>:8000/api/v1/auth`. Errors are always `{"detail": "<message safe to show the user>"}`.

| Method | Path | Body | Success | Errors |
|---|---|---|---|---|
| POST | `/register` | `full_name`, `email`, `password`, `role?`, `institution?` | `201 {user, tokens}` | `409` email taken · `422` validation |
| POST | `/login` | `email`, `password` | `200 {user, tokens}` | `401` wrong credentials · `423` locked · `403` deactivated |
| POST | `/refresh` | `refresh_token` | `200 {access_token, refresh_token, token_type, expires_in}` | `401` |
| POST | `/logout` | `refresh_token` | `204` | — |
| GET | `/me` | header `Authorization: Bearer <access_token>` | `200 user` | `401` |
| POST | `/password/forgot` | `email` | `202 {message, debug_code}` | — |
| POST | `/password/verify` | `email`, `code` | `200 {reset_token, expires_in}` | `400` |
| POST | `/password/reset` | `reset_token`, `new_password` | `204` | `400` · `422` |

Example:

```sh
curl -X POST localhost:8000/api/v1/auth/login \
  -H 'Content-Type: application/json' \
  -d '{"email":"nomsa@oncogon.org","password":"Oncology2026"}'
```

### Security behaviour

- **Passwords:** ≥ 8 characters with at least one letter and one number; hashed with **Argon2** (rehashed on login if parameters change). Unknown-email logins still run a hash, so response time doesn't reveal which emails exist.
- **Lockout:** 5 wrong passwords → locked for 15 minutes (`423`).
- **Access tokens:** HS256 JWT, 15 minutes, include `sub`, `role`, `email`, `typ=access`, issuer and audience.
- **Refresh tokens:** random opaque strings, stored only as SHA-256. **Rotated on every refresh.** Presenting an already-used token revokes the whole login family (stolen-token protection). Logout revokes the family.
- **Password reset:** 6-digit code, hashed, valid 10 minutes, 5 attempts, single use; only the newest code works. Verifying returns a 10-minute reset token; resetting the password **signs out every session**. `/password/forgot` always returns `202`, so it never reveals whether an account exists.
- **Roles:** sign-up allows `researcher`, `principal_investigator`, `scientific_reviewer`, `ml_scientist`, `tto_officer`, `industry_user`. `platform_admin` and `auditor` can only be set by an administrator (in the database for now); the DB enforces the full role list with a check constraint.

> **Development only:** there is no email provider yet, so `/password/forgot` returns the code as `debug_code` when `ENVIRONMENT=development`. It is `null` in production.

---

## Research API

Base URL: `http://<host>:8000/api/v1/research`. Every endpoint needs `Authorization: Bearer <access_token>` (`401` otherwise). Unknown IDs return `404 {"detail": "Project not found."}` and similar.

| Method | Path | Returns |
|---|---|---|
| GET | `/workspace` | The user's current `project`, `experiment`, `supervisor` and data `meta` |
| GET | `/projects` · `/projects/{id}` | Projects |
| GET | `/projects/{id}/experiments` · `/files` · `/conversations` · `/tasks` | Project lists |
| GET | `/projects/{id}/instruction` | Latest supervisor instruction (with the supervisor's details) |
| GET | `/projects/{id}/memory?category=&q=` | Research Memory, filtered by category and/or search text |
| GET | `/projects/{id}/meeting-draft` | Pre-filled supervisor meeting request |
| GET | `/experiments/{id}` · `/analysis` · `/next-step` · `/note-draft` · `/uploads/latest` | Experiment data |
| GET | `/catalog/evidence-types` · `/catalog/apps` · `/catalog/voice-commands` | Static lists |

---

## Database tables (schema `auth`)

| Table | Key columns |
|---|---|
| `users` | `id` (uuid), `email` (citext, unique), `full_name`, `password_hash`, `role`, `institution`, `is_active`, `failed_login_attempts`, `locked_until`, `last_login_at`, timestamps |
| `refresh_tokens` | `user_id`, `family_id`, `token_hash` (unique), `user_agent`, `expires_at`, `revoked_at` |
| `password_reset_codes` | `user_id`, `code_hash`, `attempts`, `expires_at`, `consumed_at` |
| `alembic_version` | Migration state |

New migration after changing models:

```sh
docker compose run --rm auth-service alembic revision --autogenerate -m "describe change"
# review the generated file in services/auth/migrations/versions/, then rebuild
docker compose up -d --build auth-service
```

(The migration file is created inside the container; copy it out or mount the folder when doing this regularly.)

---

## Tests

End-to-end, through the gateway, against the running stack (8 tests: register/login/me, duplicates and validation, lockout, refresh rotation and reuse detection, logout, full password reset, no account enumeration, auth required):

```sh
docker run --rm --network oncogon-net -e GATEWAY_URL=http://oncogon-gateway:8000 \
  -v "$PWD/services/auth/tests:/tests" python:3.12-slim \
  sh -c "pip -q install pytest httpx && pytest -q /tests"
```

Tests create throwaway users with `@example.org` addresses.

Research service (in-process, 29 tests):

```sh
docker run --rm -v "$PWD/services/research:/src" -w /src python:3.12-slim \
  sh -c "pip -q install -r requirements-dev.txt && pytest -q -p no:cacheprovider"
```

---

## Adding a new microservice

1. Create `services/<name>/` with a `Dockerfile`, `requirements.txt` and a FastAPI app exposing `GET /health`.
2. Add it to `docker-compose.yml` on network `oncogon-net`, with `expose` (not `ports`) so it stays internal.
3. Give it its own schema and database role in `OncoGonDB/init/` (one schema per service — services don't share tables).
4. Register it in the gateway: add `"<name>": ("http://<container>:<port>", "/<prefix>")` to `SERVICES` in `services/gateway/app/main.py`.
5. To protect endpoints, verify the access token (same `JWT_SECRET`, issuer `oncogon-auth`, audience `oncogon-api`, `typ == "access"`) and read the user id from `sub` and the role from `role`.

---

## Before going to production

- Set `ENVIRONMENT=production`, a strong `JWT_SECRET`, real DB passwords and explicit `CORS_ORIGINS`.
- Add an email provider for reset codes.
- Serve behind HTTPS (TLS at a load balancer or reverse proxy).
- Move the gateway rate limiter to Redis if running more than one gateway replica.
- Add an admin path for assigning `platform_admin` / `auditor` roles and deactivating accounts.
