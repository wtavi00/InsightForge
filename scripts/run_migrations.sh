#!/bin/bash

# Run database migrations for Analytics Dashboard Service

set -e

echo "Running database migrations..."

# Load environment variables
if [ -f .env ]; then
    export $(cat .env | grep -v '#' | awk '/=/ {print $1}')
fi

# Default values
DB_HOST=${POSTGRES_SERVER:-localhost}
DB_PORT=${POSTGRES_PORT:-5432}
DB_USER=${POSTGRES_USER:-postgres}
DB_PASSWORD=${POSTGRES_PASSWORD:-postgres}
DB_NAME=${POSTGRES_DB:-analytics}

# Function to run a single migration
run_migration() {
    local migration=$1
    echo "Applying migration: $(basename $migration)"
    
    # Check if migration has already been applied
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -t -c \
        "SELECT EXISTS (SELECT 1 FROM migrations WHERE name = '$(basename $migration)');" | grep -q 't'
    
    if [ $? -eq 0 ]; then
        echo "Migration already applied, skipping..."
        return 0
    fi
    
    # Apply migration
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME -f "$migration"
    
    # Record migration
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME <<-EOSQL
        INSERT INTO migrations (name, applied_at) 
        VALUES ('$(basename $migration)', NOW());
EOSQL
    
    echo "Migration applied successfully!"
}

# Create migrations table if it doesn't exist
PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME <<-EOSQL
    CREATE TABLE IF NOT EXISTS migrations (
        id SERIAL PRIMARY KEY,
        name VARCHAR(255) NOT NULL UNIQUE,
        applied_at TIMESTAMP WITH TIME ZONE DEFAULT NOW()
    );
EOSQL

# Run migrations in order
for migration in $(ls app/db/migrations/*.sql | sort); do
    run_migration "$migration"
done

echo "All migrations completed successfully!"

# Refresh continuous aggregates if requested
if [ "$1" == "--refresh" ]; then
    echo "Refreshing continuous aggregates..."
    
    PGPASSWORD=$DB_PASSWORD psql -h $DB_HOST -p $DB_PORT -U $DB_USER -d $DB_NAME <<-EOSQL
        CALL refresh_continuous_aggregate('events_hourly', NULL, NULL);
        CALL refresh_continuous_aggregate('events_daily', NULL, NULL);
        CALL refresh_continuous_aggregate('events_weekly', NULL, NULL);
        CALL refresh_continuous_aggregate('events_monthly', NULL, NULL);
EOSQL
    
    echo "Continuous aggregates refreshed!"
fi

echo "Done!"
