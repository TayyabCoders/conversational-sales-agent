#!/bin/bash
# PostgreSQL Replica Database Initialization Script

set -e

echo "🚀 Initializing FastAPI PostgreSQL Replica Database..."

# Wait for primary database to be ready
until pg_isready -h fastapi-postgres-primary -p 5432 -U user; do
    echo "⏳ Waiting for primary database to be ready..."
    sleep 2
done

echo "✅ Primary database is ready, setting up replication..."

# Create recovery configuration
cat > /var/lib/postgresql/data/recovery.conf <<EOF
standby_mode = 'on'
primary_conninfo = 'host=fastapi-postgres-primary port=5432 user=replicator password=1234'
trigger_file = '/tmp/promote_trigger'
EOF

echo "🎉 FastAPI PostgreSQL Replica Database initialization completed!"
