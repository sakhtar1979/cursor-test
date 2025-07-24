-- MintFlow Database Initialization Script
-- Create databases and users

CREATE DATABASE mintflow;
CREATE USER mintflow WITH PASSWORD 'password';
GRANT ALL PRIVILEGES ON DATABASE mintflow TO mintflow;

-- Connect to mintflow database
\c mintflow;

-- Create extensions
CREATE EXTENSION IF NOT EXISTS "uuid-ossp";
CREATE EXTENSION IF NOT EXISTS "pg_trgm";
CREATE EXTENSION IF NOT EXISTS "btree_gin";

-- Create schemas for data organization
CREATE SCHEMA IF NOT EXISTS auth;
CREATE SCHEMA IF NOT EXISTS banking;
CREATE SCHEMA IF NOT EXISTS finance;
CREATE SCHEMA IF NOT EXISTS analytics;

-- Grant permissions
GRANT USAGE ON SCHEMA auth TO mintflow;
GRANT USAGE ON SCHEMA banking TO mintflow;
GRANT USAGE ON SCHEMA finance TO mintflow;
GRANT USAGE ON SCHEMA analytics TO mintflow;

GRANT CREATE ON SCHEMA auth TO mintflow;
GRANT CREATE ON SCHEMA banking TO mintflow;
GRANT CREATE ON SCHEMA finance TO mintflow;
GRANT CREATE ON SCHEMA analytics TO mintflow;

-- Create indexes for performance optimization

-- Users table indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_email ON users (email);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_created_at ON users (created_at);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_last_login ON users (last_login);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_users_is_active ON users (is_active) WHERE is_active = true;

-- Bank connections indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bank_connections_user_id ON bank_connections (user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bank_connections_provider ON bank_connections (provider);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bank_connections_institution_id ON bank_connections (institution_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bank_connections_is_active ON bank_connections (is_active) WHERE is_active = true;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bank_connections_last_sync ON bank_connections (last_sync);

-- Bank accounts indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bank_accounts_user_id ON bank_accounts (user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bank_accounts_connection_id ON bank_accounts (connection_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bank_accounts_account_id ON bank_accounts (account_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bank_accounts_type ON bank_accounts (type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_bank_accounts_is_active ON bank_accounts (is_active) WHERE is_active = true;

-- Transactions indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_user_id ON transactions (user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_account_id ON transactions (account_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_date ON transactions (date DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_amount ON transactions (amount);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_category ON transactions (category);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_merchant_name ON transactions (merchant_name);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_pending ON transactions (pending) WHERE pending = true;
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_user_date ON transactions (user_id, date DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_description_gin ON transactions USING gin (description gin_trgm_ops);

-- Composite indexes for common queries
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_user_account_date ON transactions (user_id, account_id, date DESC);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_user_category_date ON transactions (user_id, category, date DESC);

-- Login attempts indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_login_attempts_email ON login_attempts (email);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_login_attempts_ip_address ON login_attempts (ip_address);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_login_attempts_attempted_at ON login_attempts (attempted_at DESC);

-- Password resets indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_password_resets_user_id ON password_resets (user_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_password_resets_token ON password_resets (token);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_password_resets_expires_at ON password_resets (expires_at);

-- Sync logs indexes
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sync_logs_connection_id ON sync_logs (connection_id);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sync_logs_sync_type ON sync_logs (sync_type);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sync_logs_status ON sync_logs (status);
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_sync_logs_started_at ON sync_logs (started_at DESC);

-- Create partitioning for large tables (transactions)
-- Partition by month for better performance with large datasets

-- Create partition function
CREATE OR REPLACE FUNCTION create_monthly_partition(table_name text, start_date date)
RETURNS void AS $$
DECLARE
    partition_name text;
    start_month text;
    end_date date;
BEGIN
    start_month := to_char(start_date, 'YYYY_MM');
    partition_name := table_name || '_' || start_month;
    end_date := start_date + interval '1 month';
    
    EXECUTE format('CREATE TABLE IF NOT EXISTS %I PARTITION OF %I 
                    FOR VALUES FROM (%L) TO (%L)',
                   partition_name, table_name, start_date, end_date);
    
    -- Create indexes on partition
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %I (user_id, date DESC)',
                   'idx_' || partition_name || '_user_date', partition_name);
    EXECUTE format('CREATE INDEX IF NOT EXISTS %I ON %I (account_id, date DESC)',
                   'idx_' || partition_name || '_account_date', partition_name);
END;
$$ LANGUAGE plpgsql;

-- Create triggers for automatic cleanup of old data
CREATE OR REPLACE FUNCTION cleanup_old_login_attempts()
RETURNS trigger AS $$
BEGIN
    DELETE FROM login_attempts WHERE attempted_at < NOW() - INTERVAL '30 days';
    RETURN NULL;
END;
$$ LANGUAGE plpgsql;

CREATE TRIGGER trigger_cleanup_login_attempts
    AFTER INSERT ON login_attempts
    EXECUTE FUNCTION cleanup_old_login_attempts();

-- Create function for transaction categorization
CREATE OR REPLACE FUNCTION update_transaction_search_vector()
RETURNS trigger AS $$
BEGIN
    -- This could be used for full-text search on transactions
    NEW.search_vector := to_tsvector('english', 
        COALESCE(NEW.description, '') || ' ' || 
        COALESCE(NEW.merchant_name, '') || ' ' ||
        COALESCE(NEW.category, '')
    );
    RETURN NEW;
END;
$$ LANGUAGE plpgsql;

-- Add search vector column if it doesn't exist
ALTER TABLE transactions ADD COLUMN IF NOT EXISTS search_vector tsvector;

-- Create trigger for search vector
CREATE TRIGGER trigger_transactions_search_vector
    BEFORE INSERT OR UPDATE ON transactions
    FOR EACH ROW EXECUTE FUNCTION update_transaction_search_vector();

-- Create GIN index for full-text search
CREATE INDEX CONCURRENTLY IF NOT EXISTS idx_transactions_search_vector 
    ON transactions USING gin (search_vector);

-- Create materialized views for analytics
CREATE MATERIALIZED VIEW IF NOT EXISTS monthly_spending_summary AS
SELECT 
    user_id,
    DATE_TRUNC('month', date) as month,
    category,
    SUM(CASE WHEN amount > 0 THEN amount ELSE 0 END) as total_spent,
    SUM(CASE WHEN amount < 0 THEN ABS(amount) ELSE 0 END) as total_income,
    COUNT(*) as transaction_count
FROM transactions
WHERE NOT pending
GROUP BY user_id, DATE_TRUNC('month', date), category;

CREATE UNIQUE INDEX IF NOT EXISTS idx_monthly_spending_summary_unique
    ON monthly_spending_summary (user_id, month, category);

-- Create view for account balances
CREATE OR REPLACE VIEW account_balances_view AS
SELECT 
    ba.id,
    ba.user_id,
    ba.name,
    ba.type,
    ba.current_balance,
    ba.available_balance,
    ba.credit_limit,
    bc.institution_name,
    bc.last_sync,
    CASE 
        WHEN ba.type = 'credit' THEN ba.credit_limit - ba.current_balance
        ELSE ba.available_balance
    END as available_to_spend
FROM bank_accounts ba
JOIN bank_connections bc ON ba.connection_id = bc.id
WHERE ba.is_active = true AND bc.is_active = true;

-- Create function to refresh materialized views
CREATE OR REPLACE FUNCTION refresh_analytics_views()
RETURNS void AS $$
BEGIN
    REFRESH MATERIALIZED VIEW CONCURRENTLY monthly_spending_summary;
END;
$$ LANGUAGE plpgsql;

-- Create stored procedure for user data deletion (GDPR compliance)
CREATE OR REPLACE FUNCTION delete_user_data(user_id_param text)
RETURNS void AS $$
BEGIN
    -- Delete transactions
    DELETE FROM transactions WHERE user_id = user_id_param;
    
    -- Delete bank accounts
    DELETE FROM bank_accounts WHERE user_id = user_id_param;
    
    -- Delete bank connections
    DELETE FROM bank_connections WHERE user_id = user_id_param;
    
    -- Delete password resets
    DELETE FROM password_resets WHERE user_id = user_id_param;
    
    -- Delete login attempts
    DELETE FROM login_attempts WHERE email = (SELECT email FROM users WHERE id = user_id_param);
    
    -- Finally delete user
    DELETE FROM users WHERE id = user_id_param;
    
    -- Log the deletion
    INSERT INTO data_deletion_log (user_id, deleted_at) VALUES (user_id_param, NOW());
END;
$$ LANGUAGE plpgsql;

-- Create data deletion log table
CREATE TABLE IF NOT EXISTS data_deletion_log (
    id SERIAL PRIMARY KEY,
    user_id text NOT NULL,
    deleted_at timestamp DEFAULT NOW()
);

-- Create function for database health check
CREATE OR REPLACE FUNCTION database_health_check()
RETURNS json AS $$
DECLARE
    result json;
    db_size bigint;
    connection_count int;
    slow_queries int;
BEGIN
    -- Get database size
    SELECT pg_database_size(current_database()) INTO db_size;
    
    -- Get active connections
    SELECT count(*) FROM pg_stat_activity WHERE state = 'active' INTO connection_count;
    
    -- Check for slow queries (running > 5 minutes)
    SELECT count(*) FROM pg_stat_activity 
    WHERE state = 'active' AND now() - query_start > interval '5 minutes' INTO slow_queries;
    
    result := json_build_object(
        'database_size_bytes', db_size,
        'active_connections', connection_count,
        'slow_queries', slow_queries,
        'timestamp', now()
    );
    
    RETURN result;
END;
$$ LANGUAGE plpgsql;

-- Grant execute permissions on functions
GRANT EXECUTE ON FUNCTION create_monthly_partition(text, date) TO mintflow;
GRANT EXECUTE ON FUNCTION refresh_analytics_views() TO mintflow;
GRANT EXECUTE ON FUNCTION delete_user_data(text) TO mintflow;
GRANT EXECUTE ON FUNCTION database_health_check() TO mintflow;

-- Create job for automatic partition creation (requires pg_cron extension)
-- This would typically be set up separately in production

-- Final optimization settings
-- These would be set in postgresql.conf in production
-- ALTER SYSTEM SET shared_preload_libraries = 'pg_stat_statements';
-- ALTER SYSTEM SET track_activity_query_size = 2048;
-- ALTER SYSTEM SET log_min_duration_statement = 1000;