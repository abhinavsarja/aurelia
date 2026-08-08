#!/usr/bin/env bash
# Wipe the database, re-apply the schema, reload the CSVs.
# Use after changing db/schema.sql — the container's init script only runs on an empty volume.
set -euo pipefail

ROOT="$(cd "$(dirname "$0")" && pwd)"
cd "$ROOT"

DB="postgresql://aurelia:local@localhost:5432/aurelia"

echo "==> tearing down (this deletes the volume)"
docker compose down -v

echo "==> starting postgres, applying db/schema.sql"
docker compose up -d

echo -n "==> waiting for postgres "
until docker compose exec -T postgres pg_isready -U aurelia -d aurelia >/dev/null 2>&1; do
    echo -n "."; sleep 1
done
echo " ready"

echo "==> loading CSVs"
psql "$DB" -v ON_ERROR_STOP=1 -q -f db/load_csv.sql

echo "==> done"
psql "$DB" -c "SELECT load_id, kind, status, published_at FROM data_load ORDER BY load_id;"
psql "$DB" -c "SELECT (SELECT count(*) FROM v_sales) sales, (SELECT count(*) FROM v_stock) stock, (SELECT count(*) FROM v_targets) targets;"
