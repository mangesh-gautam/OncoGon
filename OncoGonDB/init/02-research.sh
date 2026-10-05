#!/bin/sh
# Runs once, on first start of an empty data volume (after 01-init.sh).
# Research service (OncoGonResearchAPI): its own schema and least-privilege role.
# On an existing database, run the same SQL by hand (see README "Adding a schema for a new service").
set -eu

psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-SQL
  DO \$\$
  BEGIN
    IF NOT EXISTS (SELECT FROM pg_roles WHERE rolname = '${RESEARCH_DB_USER}') THEN
      CREATE ROLE ${RESEARCH_DB_USER} LOGIN PASSWORD '${RESEARCH_DB_PASSWORD}';
    END IF;
  END
  \$\$;
  CREATE SCHEMA IF NOT EXISTS research AUTHORIZATION ${RESEARCH_DB_USER};
  ALTER ROLE ${RESEARCH_DB_USER} SET search_path = research, public;
  REVOKE ALL ON SCHEMA public FROM ${RESEARCH_DB_USER};
  GRANT USAGE ON SCHEMA public TO ${RESEARCH_DB_USER};
SQL
