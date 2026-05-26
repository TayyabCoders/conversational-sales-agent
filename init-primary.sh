#!/bin/bash
# PostgreSQL Primary Database Initialization Script

set -e

echo "🚀 Initializing FastAPI PostgreSQL Primary Database..."

# Create replication user
psql -v ON_ERROR_STOP=1 --username "$POSTGRES_USER" --dbname "$POSTGRES_DB" <<-EOSQL
    CREATE USER replicator REPLICATION LOGIN PASSWORD '$REPLICATION_PASSWORD';
    
    -- Grant replication privileges
    GRANT REPLICATION ON ALL TABLES IN SCHEMA public TO replicator;
    
    -- Create application database if it doesn't exist
    SELECT 'CREATE DATABASE app_db' WHERE NOT EXISTS (SELECT FROM pg_database WHERE datname = 'app_db')\gexec
    
    -- Grant privileges to application user
    GRANT ALL PRIVILEGES ON DATABASE app_db TO user;
    
    -- Create extensions
    CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
    CREATE EXTENSION IF NOT EXISTS "pgcrypto";
    
    echo "✅ Primary database initialized successfully"
EOSQL

echo "🎉 FastAPI PostgreSQL Primary Database initialization completed!"
