# OncoGonAPI

Python **FastAPI** microservices for OncoGon, run with Docker. Currently: authentication.

```
Mobile app ──► gateway :8000 ──► auth-service :8001 (internal) ──► PostgreSQL (OncoGonDB, schema "auth")
```

| Service | Folder | Role |
|---|---|---|
| `gateway` | `services/gateway` | Single public entry. Routes `/api/v1/<service>/…`, CORS, `X-Request-ID`, per-IP rate limit on credential endpoints, aggregated `/health`. |
| `auth-service` | `services/auth` | Accounts, login, JWT access tokens, rotating refresh tokens, password reset. Runs Alembic migrations on start. |

## Run

```sh
cd ../OncoGonDB && docker compose up -d      # database + oncogon-net network (first)
cd ../OncoGonAPI && docker compose up -d --build
curl localhost:8000/health                   # {"status":"ok","services":{"auth":"ok"}}
```

`.env` is generated from `.env.example`. `AUTH_DB_PASSWORD` must match `OncoGonDB/.env`; set your own `JWT_SECRET` (`openssl rand -hex 32`).
Interactive docs (development only): http://localhost:8000/docs (gateway) — the auth service's own docs are internal.

## Auth API (via gateway, prefix `/api/v1/auth`)

| Method | Path | Body | Result |
|---|---|---|---|
| POST | `/register` | `full_name, email, password, role?, institution?` | 201 `{user, tokens}` |
| POST | `/login` | `email, password` | 200 `{user, tokens}` · 401 wrong credentials · 423 locked (5 failures → 15 min) |
| POST | `/refresh` | `refresh_token` | 200 new token pair (old token revoked; replaying a used token revokes the whole session) |
| POST | `/logout` | `refresh_token` | 204 |
| GET | `/me` | `Authorization: Bearer <access>` | 200 user |
| POST | `/password/forgot` | `email` | 202 always (no account enumeration). In development the 6-digit code is returned as `debug_code`. |
| POST | `/password/verify` | `email, code` | 200 `{reset_token}` (10 min, single use, 5 attempts) |
| POST | `/password/reset` | `reset_token, new_password` | 204 and signs out every session |

Errors are `{"detail": "<message for the user>"}`. Passwords: ≥ 8 chars with a letter and a number, hashed with Argon2.
Sign-up roles: researcher, principal_investigator, scientific_reviewer, ml_scientist, tto_officer, industry_user
(platform_admin and auditor can only be assigned by an administrator).

## Tests

End-to-end through the gateway against the running stack:

```sh
docker run --rm --network oncogon-net -e GATEWAY_URL=http://oncogon-gateway:8000 \
  -v "$PWD/services/auth/tests:/tests" python:3.12-slim \
  sh -c "pip -q install pytest httpx && pytest -q /tests"
```

## Not yet production-ready

- No email provider: reset codes are only returned in development (`ENVIRONMENT=development`). Set `ENVIRONMENT=production` before deploying.
- The gateway rate limiter is in memory (one replica). Use Redis when scaling out.
- Serve behind HTTPS (TLS terminated at a load balancer / reverse proxy).
