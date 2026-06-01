-- =============================================================================
-- Feature 1: Open Iceberg REST Access via Snowflake Horizon Catalog
-- Account: SCB47336 (vmedidademo-aws1)
-- Horizon Catalog REST endpoint:
--   https://scb47336.snowflakecomputing.com/polaris/api/catalog
-- =============================================================================

-- Step 1: Verify the external volume exists (pre-created)
DESC EXTERNAL VOLUME iceberg_demo_ext_vol;

-- Step 2: Create a Snowflake-managed Iceberg table
--   CATALOG = SNOWFLAKE means Horizon Catalog is the authoritative catalog
CREATE DATABASE IF NOT EXISTS horizon_demo_db;
CREATE SCHEMA IF NOT EXISTS horizon_demo_db.public;

CREATE OR REPLACE ICEBERG TABLE horizon_demo_db.public.transactions (
    transaction_id   VARCHAR(36),
    customer_id      VARCHAR(36),
    amount           DECIMAL(12, 2),
    currency         VARCHAR(3),
    transaction_ts   TIMESTAMP_NTZ(6),
    status           VARCHAR(20),
    region           VARCHAR(50)
)
    CATALOG           = 'SNOWFLAKE'
    EXTERNAL_VOLUME   = 'iceberg_demo_ext_vol'
    BASE_LOCATION     = 'horizon_demo/transactions/';

-- Step 3: Load sample data
INSERT INTO horizon_demo_db.public.transactions VALUES
    ('txn-001', 'cust-A', 1250.00, 'USD', '2024-01-15 09:30:00'::TIMESTAMP_NTZ(6), 'COMPLETED', 'us-west'),
    ('txn-002', 'cust-B',  320.50, 'USD', '2024-01-15 10:15:00'::TIMESTAMP_NTZ(6), 'PENDING',   'us-east'),
    ('txn-003', 'cust-A',  875.00, 'EUR', '2024-01-15 11:00:00'::TIMESTAMP_NTZ(6), 'COMPLETED', 'eu-west'),
    ('txn-004', 'cust-C', 4200.00, 'USD', '2024-01-15 12:45:00'::TIMESTAMP_NTZ(6), 'FAILED',    'us-west'),
    ('txn-005', 'cust-B',  650.75, 'GBP', '2024-01-15 13:30:00'::TIMESTAMP_NTZ(6), 'COMPLETED', 'eu-west');

-- Step 4: Query through Snowflake to verify data
SELECT * FROM horizon_demo_db.public.transactions ORDER BY transaction_ts;

-- Step 5: Inspect the Iceberg metadata Snowflake exposes
SELECT
    SYSTEM$GET_ICEBERG_TABLE_INFORMATION(
        'horizon_demo_db.public.transactions'
    ) AS iceberg_metadata;

-- Step 6: Retrieve the Horizon Catalog REST endpoint for this account
--   External engines use this URI as their catalog URI
SELECT SYSTEM$GET_ICEBERG_REST_CATALOG_ENDPOINT() AS horizon_endpoint;

-- Step 7: Create a service user + role for external engine access
--   (see 05_security_model for full RBAC setup)
CREATE ROLE IF NOT EXISTS horizon_reader_role;
GRANT USAGE ON DATABASE horizon_demo_db TO ROLE horizon_reader_role;
GRANT USAGE ON SCHEMA horizon_demo_db.public TO ROLE horizon_reader_role;
GRANT SELECT ON TABLE horizon_demo_db.public.transactions TO ROLE horizon_reader_role;
