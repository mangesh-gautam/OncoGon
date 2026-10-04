# OncoGonDB

PostgreSQL 16 for the OncoGon platform, run with Docker.

```sh
cp .env.example .env     # then set strong passwords (a generated .env is already present)
docker compose up -d
docker compose ps        # wait for "healthy"
```

- Host port: **5433** (`POSTGRES_HOST_PORT`) → container 5432.
- Network: `oncogon-net` — the OncoGonAPI services join it and reach the DB at `oncogon-postgres:5432`.
- One schema per microservice. `init/01-init.sh` creates the `auth` schema and the `oncogon_auth` role
  (owner of that schema only). Tables are created by the auth service's migrations on startup.
- Init scripts run only on an empty volume. To start over: `docker compose down -v` (deletes all data).

Connect from the host:

```sh
psql "postgresql://oncogon_admin:<POSTGRES_PASSWORD>@localhost:5433/oncogon"
```
