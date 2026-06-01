-- =============================================================================
-- Feature I: Dynamic Tables as Iceberg
-- CREATE DYNAMIC ICEBERG TABLE incrementally materializes query results
-- into an Iceberg table format — open and accessible via Horizon Catalog.
-- =============================================================================

USE DATABASE horizon_demo_db;
USE SCHEMA public;

-- Step 1: Source table (could be standard or streaming)
CREATE OR REPLACE TABLE horizon_demo_db.public.raw_transactions (
    transaction_id  VARCHAR(36),
    customer_id     VARCHAR(36),
    amount          DECIMAL(12, 2),
    currency        VARCHAR(3),
    transaction_ts  TIMESTAMP_NTZ(6),
    status          VARCHAR(20),
    region          VARCHAR(50),
    raw_payload     VARIANT
);

-- Step 2: Create a Dynamic Iceberg Table
--   TARGET_LAG defines how fresh the data must be
--   CATALOG + EXTERNAL_VOLUME makes it open Iceberg format
CREATE OR REPLACE DYNAMIC ICEBERG TABLE horizon_demo_db.public.transactions_daily_agg
    TARGET_LAG      = '1 hour'
    WAREHOUSE       = COMPUTE_WH
    CATALOG         = 'SNOWFLAKE'
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol'
    BASE_LOCATION   = 'horizon_demo/transactions_daily_agg/'
AS
    SELECT
        DATE_TRUNC('day', transaction_ts)       AS txn_date,
        region,
        currency,
        COUNT(*)                                AS txn_count,
        SUM(amount)                             AS total_amount,
        AVG(amount)                             AS avg_amount,
        COUNT(DISTINCT customer_id)             AS unique_customers,
        SUM(CASE WHEN status = 'COMPLETED' THEN amount ELSE 0 END) AS completed_amount
    FROM horizon_demo_db.public.raw_transactions
    WHERE status != 'CANCELLED'
    GROUP BY 1, 2, 3;

-- Step 3: Check the Dynamic Table status
SHOW DYNAMIC TABLES IN horizon_demo_db.public;

SELECT *
FROM TABLE(information_schema.dynamic_table_refresh_history(
    name => 'horizon_demo_db.public.transactions_daily_agg'
))
ORDER BY refresh_start_time DESC
LIMIT 10;

-- Step 4: Verify it's a valid Iceberg table
SELECT SYSTEM$GET_ICEBERG_TABLE_INFORMATION(
    'horizon_demo_db.public.transactions_daily_agg'
) AS iceberg_info;

-- Step 5: External engines read the Dynamic Iceberg Table via Horizon
-- PyIceberg:
--   table = catalog.load_table("public.transactions_daily_agg")
--   df = table.scan().to_pandas()
-- Spark:
--   spark.table("sf.public.transactions_daily_agg").show()
-- DuckDB:
--   conn.execute("SELECT * FROM h.public.transactions_daily_agg").fetchdf()

-- Step 6: Nested pipeline — Dynamic Iceberg feeding another Dynamic Iceberg
CREATE OR REPLACE DYNAMIC ICEBERG TABLE horizon_demo_db.public.transactions_monthly_agg
    TARGET_LAG      = '6 hours'
    WAREHOUSE       = COMPUTE_WH
    CATALOG         = 'SNOWFLAKE'
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol'
    BASE_LOCATION   = 'horizon_demo/transactions_monthly_agg/'
AS
    SELECT
        DATE_TRUNC('month', txn_date) AS txn_month,
        region,
        SUM(txn_count)     AS total_txns,
        SUM(total_amount)  AS monthly_amount,
        SUM(unique_customers) AS unique_customers
    FROM horizon_demo_db.public.transactions_daily_agg
    GROUP BY 1, 2;

SELECT * FROM horizon_demo_db.public.transactions_monthly_agg;
