#!/bin/bash
set -e   # exit immediately on any error

echo "==> Waiting for PostgreSQL..."
until pg_isready -h "$POSTGRES_HOST" -p "$POSTGRES_PORT" -U "$POSTGRES_USER"; do
    sleep 1
done
echo "==> PostgreSQL is ready."

echo "==> Running migrations..."
python manage.py migrate --noinput

echo "==> Collecting static files..."
python manage.py collectstatic --noinput

echo "==> Starting: $@"
exec "$@"   # execute whatever command was passed (daphne or celery)
