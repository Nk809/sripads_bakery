#!/bin/bash
set -e

# Load virtual environment if exists
if [ -f "venv/bin/activate" ]; then
    source venv/bin/activate
fi

echo "=== Step 1: Exporting current SQLite3 data ==="
python manage.py dumpdata --natural-foreign --natural-primary -e contenttypes -e auth.Permission --indent 4 > datadump.json
echo "SQLite3 data dumped to datadump.json successfully."

echo "=== Step 2: Running database migrations on PostgreSQL ==="
export USE_POSTGRES=True
export DB_NAME="sripads_bakery"
export DB_USER="postgres"
export DB_PASSWORD="postgres"
export DB_HOST="localhost"
export DB_PORT="5432"

python manage.py migrate

echo "=== Step 3: Loading data into PostgreSQL ==="
python manage.py loaddata datadump.json
echo "=== Migration to PostgreSQL completed successfully! ==="
