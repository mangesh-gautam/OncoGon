# OncoGonDB

**PostgreSQL 16** for the OncoGon platform, run with Docker Compose. It is the shared database server for the [OncoGonAPI](../OncoGonAPI) microservices: **each service gets its own schema and its own database role**, so services can't read or change each other's tables.

Part of a three-repo setup:

| Repo | What it is |
|---|---|
| [OncoGon](../OncoGon) | React Native app |
| [OncoGonAPI](../OncoGonAPI) | Gateway + microservices |
| **OncoGonDB** (this repo) | PostgreSQL — **start this first** |

---

## Quick start

```sh
cp .env.example .env          # a development .env with generated passwords already exists
docker compose up -d
docker compose ps             # wait for STATUS "healthy"
```

Starting this stack also creates the Docker network **`oncogon-net`**, which OncoGonAPI joins.

| | Value |
|---|---|
| Container | `oncogon-postgres` |
| Image | `postgres:16-alpine` |
| Host port | **5433** → container 5432 (5432 is often taken on dev machines) |
| Database | `oncogon` |
| Data volume | `oncogon-pgdata` (survives restarts and `docker compose down`) |
| From other containers | `oncogon-postgres:5432` on `oncogon-net` |

---

## Configuration (`.env`)

| Variable | Purpose |
|---|---|
| `POSTGRES_USER` / `POSTGRES_PASSWORD` | Superuser — administration and init scripts only. Services never use it. |
| `POSTGRES_DB` | Database name (`oncogon`) |
| `POSTGRES_HOST_PORT` | Port published on your machine (default `5433`) |
| `AUTH_DB_USER` / `AUTH_DB_PASSWORD` | Role used by the auth service. **Must match `OncoGonAPI/.env`.** |

`.env` is git-ignored — never commit it.

> Passwords are applied **only when the volume is first created**. Changing `.env` later does not change existing roles — see *Changing a password* below.

---

## Schemas and roles

`init/01-init.sh` runs once, on an empty volume. It:

1. Enables the `citext` (case-insensitive email) and `pgcrypto` extensions.
2. Creates the role `oncogon_auth` and the schema **`auth`** owned by it.
3. Sets that role's `search_path` to `auth, public` and removes its rights to create objects in `public`.

| Schema | Owner role | Used by | Tables |
|---|---|---|---|
| `auth` | `oncogon_auth` | auth-service | `users`, `refresh_tokens`, `password_reset_codes`, `alembic_version` |

Tables are **not** created here — each service creates and upgrades its own tables with migrations (the auth service runs Alembic on startup). See the [OncoGonAPI README](../OncoGonAPI/README.md#database-tables-schema-auth) for column details.

### Adding a schema for a new service

Add a script such as `init/02-projects.sh` following the same pattern (role + schema + `search_path`), and add its credentials to `.env` and `.env.example`. Init scripts only run on an **empty** volume, so on an existing database run the SQL once by hand:

```sh
docker exec -it oncogon-postgres psql -U oncogon_admin -d oncogon
```

```sql
CREATE ROLE oncogon_projects LOGIN PASSWORD '...';
CREATE SCHEMA projects AUTHORIZATION oncogon_projects;
ALTER ROLE oncogon_projects SET search_path = projects, public;
```

---

## Everyday commands

```sh
# psql shell as admin
docker exec -it oncogon-postgres psql -U oncogon_admin -d oncogon

# from your machine (any client: psql, TablePlus, DBeaver, pgAdmin)
psql "postgresql://oncogon_admin:<POSTGRES_PASSWORD>@localhost:5433/oncogon"

# list auth tables / users
docker exec oncogon-postgres psql -U oncogon_admin -d oncogon -c '\dt auth.*'
docker exec oncogon-postgres psql -U oncogon_admin -d oncogon -c 'select email, role, created_at from auth.users order by created_at desc limit 20;'

# logs
docker compose logs -f postgres
```

### Backup and restore

```sh
# backup
docker exec oncogon-postgres pg_dump -U oncogon_admin -d oncogon -Fc > oncogon_$(date +%F).dump

# restore into the running container
docker exec -i oncogon-postgres pg_restore -U oncogon_admin -d oncogon --clean --if-exists < oncogon_2026-10-04.dump
```

### Changing a password

```sh
docker exec -it oncogon-postgres psql -U oncogon_admin -d oncogon \
  -c "ALTER ROLE oncogon_auth PASSWORD 'new-password';"
```

Then update `AUTH_DB_PASSWORD` in **both** `OncoGonDB/.env` and `OncoGonAPI/.env`, and restart the API (`docker compose up -d` in OncoGonAPI).

### Admin tasks (until there's an admin screen)

```sql
-- give someone an administrator role
UPDATE auth.users SET role = 'platform_admin' WHERE email = 'person@institution.org';

-- unlock an account
UPDATE auth.users SET failed_login_attempts = 0, locked_until = NULL WHERE email = 'person@institution.org';

-- deactivate an account (they can no longer sign in or refresh)
UPDATE auth.users SET is_active = false WHERE email = 'person@institution.org';
```

### Start over (deletes all data)

```sh
docker compose down -v      # removes the oncogon-pgdata volume
docker compose up -d        # init scripts run again; restart OncoGonAPI to re-run migrations
```

---

## Troubleshooting

| Problem | Fix |
|---|---|
| `port is already allocated` | Another Postgres is on that port — set `POSTGRES_HOST_PORT` in `.env`. |
| API logs `password authentication failed for user "oncogon_auth"` | `AUTH_DB_PASSWORD` differs between the two `.env` files, or was changed after the volume was created — see *Changing a password*. |
| API can't resolve `oncogon-postgres` | Start OncoGonDB first; check `docker network inspect oncogon-net`. |
| Init script changes had no effect | They only run on an empty volume — apply the SQL by hand or start over. |

## Before going to production

- Use a managed PostgreSQL service or a hardened server with TLS, automated backups and point-in-time recovery.
- Don't publish the database port publicly — only the API should reach it.
- Rotate the generated development passwords.
