#!/usr/bin/env sh
set -eu

fail() {
  echo "Docker Compose environment validation failed: $1" >&2
  exit 1
}

require_var() {
  name="$1"
  value="$(eval "printf '%s' \"\${$name:-}\"")"
  [ -n "$value" ] || fail "$name must be set in .env"
}

reject_value() {
  name="$1"
  value="$(eval "printf '%s' \"\${$name:-}\"")"
  lower="$(printf '%s' "$value" | tr '[:upper:]' '[:lower:]')"

  case "$lower" in
    admin|root|postgres|password|changeme|change-me|secret|secret-token|replace-with-*|your-*)
      fail "$name uses a default or placeholder value; generate a project-local value before starting Compose"
      ;;
  esac
}

require_min_length() {
  name="$1"
  min="$2"
  value="$(eval "printf '%s' \"\${$name:-}\"")"
  length="$(printf '%s' "$value" | wc -c | tr -d ' ')"
  [ "$length" -ge "$min" ] || fail "$name must be at least $min characters"
}

require_var POSTGRES_USER
require_var POSTGRES_PASSWORD
require_var POSTGRES_DB
require_var DATABASE_URL
require_var PGADMIN_DEFAULT_EMAIL
require_var PGADMIN_DEFAULT_PASSWORD

reject_value POSTGRES_USER
reject_value POSTGRES_PASSWORD
reject_value PGADMIN_DEFAULT_EMAIL
reject_value PGADMIN_DEFAULT_PASSWORD

require_min_length POSTGRES_PASSWORD 16
require_min_length PGADMIN_DEFAULT_PASSWORD 16

case "$DATABASE_URL" in
  *admin:root*|*replace-with-*|*your-*)
    fail "DATABASE_URL still contains default or placeholder credentials"
    ;;
esac

case "$DATABASE_URL" in
  postgresql://*@db:5432/*) ;;
  *)
    fail "DATABASE_URL must use the Docker service host 'db' for Docker Compose, for example postgresql://user:password@db:5432/test_db"
    ;;
esac

case "$PGADMIN_DEFAULT_EMAIL" in
  *@*.*) ;;
  *) fail "PGADMIN_DEFAULT_EMAIL must be a valid email address" ;;
esac

echo "Docker Compose environment validation passed."
