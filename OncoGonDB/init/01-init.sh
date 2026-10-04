#!/bin/sh
# Runs once, on first start of an empty data volume.
# Creates one schema per microservice and a least-privilege role for each.
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
  CREATE EXTENSION IF NOT EXISTS citext;
  CREATE EXTENSION IF NOT EXISTS pgcrypto;

  -- Auth service
  DO \$\$
  BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${AUTH_DB_USER}') THEN
      CREATE ROLE ${AUTH_DB_USER} LOGIN PASSWORD '${AUTH_DB_PASSWORD}';
    END IF;
  END
  \$\$;
  CREATE SCHEMA IF NOT EXISTS auth AUTHORIZATION ${AUTH_DB_USER};
  ALTER ROLE ${AUTH_DB_USER} SET search_path = auth, public;
  REVOKE ALL ON SCHEMA public FROM ${AUTH_DB_USER};
  GRANT USAGE ON SCHEMA public TO ${AUTH_DB_USER};
SQL
