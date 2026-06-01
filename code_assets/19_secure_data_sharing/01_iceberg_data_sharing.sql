-- =============================================================================
-- Feature 19: Secure Data Sharing for Iceberg
-- Share Snowflake-managed Iceberg tables across accounts.
-- Pattern A: Cross-account share (provider → consumer)
-- Pattern B: Multi-tenant row isolation via SYSTEM$CURRENT_ACCOUNT()
-- Pattern C: Reader accounts for external parties
-- =============================================================================

-- =============================================================
-- PATTERN A: Cross-Account Iceberg Share
-- =============================================================

-- Provider account: create share and grant access
CREATE SHARE iceberg_data_share
    COMMENT = 'Shared Iceberg transaction data for partner accounts';

GRANT USAGE ON DATABASE horizon_demo_db       TO SHARE iceberg_data_share;
GRANT USAGE ON SCHEMA   horizon_demo_db.public TO SHARE iceberg_data_share;
GRANT SELECT ON TABLE   horizon_demo_db.public.transactions TO SHARE iceberg_data_share;

-- Add consumer accounts
ALTER SHARE iceberg_data_share ADD ACCOUNTS = consumer_account_id_1, consumer_account_id_2;

-- Consumer account: create a database from the share
CREATE DATABASE shared_iceberg_db FROM SHARE provider_account.iceberg_data_share;

-- Consumer queries — same SQL, policies from PROVIDER still enforced
SELECT * FROM shared_iceberg_db.public.transactions WHERE region = 'us-west';

-- Consumer can ALSO access via Horizon REST (same Iceberg data, provider's governance)
SELECT SYSTEM$GET_ICEBERG_REST_CATALOG_ENDPOINT() AS consumer_horizon_endpoint;

-- =============================================================
-- PATTERN B: Multi-Tenant Row Isolation
-- Each tenant (account) only sees its own rows — enforced at Horizon level
-- =============================================================

-- Step 1: Add a tenant_account column to the Iceberg table
ALTER TABLE horizon_demo_db.public.transactions
    ADD COLUMN tenant_account VARCHAR(50);

UPDATE horizon_demo_db.public.transactions
    SET tenant_account = 'CONSUMER_ACCOUNT_A' WHERE region LIKE 'us-%';
UPDATE horizon_demo_db.public.transactions
    SET tenant_account = 'CONSUMER_ACCOUNT_B' WHERE region LIKE 'eu-%';

-- Step 2: Create a multi-tenant row access policy
CREATE OR REPLACE ROW ACCESS POLICY rap_multitenant
    AS (tenant_col VARCHAR) RETURNS BOOLEAN ->
    CASE
        WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN', 'SYSADMIN') THEN TRUE
        ELSE tenant_col = SYSTEM$CURRENT_ACCOUNT()
    END;

ALTER TABLE horizon_demo_db.public.transactions
    ADD ROW ACCESS POLICY rap_multitenant ON (tenant_account);

-- Step 3: Share the table — each consumer automatically sees only their rows
CREATE SHARE multitenant_share;
GRANT USAGE ON DATABASE horizon_demo_db       TO SHARE multitenant_share;
GRANT USAGE ON SCHEMA horizon_demo_db.public   TO SHARE multitenant_share;
GRANT SELECT ON TABLE horizon_demo_db.public.transactions TO SHARE multitenant_share;

ALTER SHARE multitenant_share
    ADD ACCOUNTS = CONSUMER_ACCOUNT_A, CONSUMER_ACCOUNT_B;

-- CONSUMER_ACCOUNT_A only sees us-* rows even via Horizon REST
-- CONSUMER_ACCOUNT_B only sees eu-* rows even via Horizon REST

-- =============================================================
-- PATTERN C: Reader Account (for external parties without Snowflake)
-- =============================================================

-- Create a managed reader account
CREATE MANAGED ACCOUNT iceberg_reader_1
    ADMIN_NAME    = reader_admin
    ADMIN_PASSWORD = 'SecurePass123!'
    TYPE          = READER;

-- Grant share access to reader account
ALTER SHARE iceberg_data_share ADD ACCOUNTS = iceberg_reader_1;

-- Monitor sharing activity
SELECT *
FROM snowflake.account_usage.access_history
WHERE object_name = 'TRANSACTIONS'
  AND query_start_time >= DATEADD(DAY, -1, CURRENT_TIMESTAMP())
ORDER BY query_start_time DESC
LIMIT 20;
