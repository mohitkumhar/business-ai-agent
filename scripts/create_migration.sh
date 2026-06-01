#!/usr/bin/env bash
set -euo pipefail

if [ "$#" -eq 0 ]; then
  echo "Usage: scripts/create_migration.sh \"describe schema change\"" >&2
  exit 1
fi

mode="${ALEMBIC_REVISION_MODE:-autogenerate}"
message="$*"

case "$mode" in
  autogenerate)
    alembic revision --autogenerate -m "$message"
    ;;
  manual)
    alembic revision -m "$message"
    ;;
  *)
    echo "ALEMBIC_REVISION_MODE must be 'autogenerate' or 'manual'" >&2
    exit 1
    ;;
esac
