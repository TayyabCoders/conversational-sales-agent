#!/bin/bash
set -e

# Load environment variables if needed
# source .env

echo "Running migrations..."

# Wait for DB to be ready (optional but recommended in Docker)
# You could use pg_isready or a custom python wait script
# python scripts/wait_for_db.py

# Run migrations
python -m alembic upgrade head

echo "Migrations completed successfully."
