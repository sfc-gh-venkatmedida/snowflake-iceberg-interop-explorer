-- =============================================================================
-- Feature J: Iceberg Partitioning + Performance Tuning
-- Proper partitioning is the single biggest performance lever for Iceberg.
-- Snowflake + Iceberg support all standard partition transforms.
-- =============================================================================

USE DATABASE horizon_demo_db;
USE SCHEMA public;

-- =============================================================
-- PART 1: PARTITION TRANSFORMS
-- =============================================================

-- Identity partition — exact value match
CREATE OR REPLACE ICEBERG TABLE horizon_demo_db.public.txn_by_region (
    transaction_id  VARCHAR(36),
    customer_id     VARCHAR(36),
    amount          DECIMAL(12, 2),
    currency        VARCHAR(3),
    transaction_ts  TIMESTAMP_NTZ(6),
    status          VARCHAR(20),
    region          VARCHAR(50)
)
    CATALOG         = 'SNOWFLAKE'
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol'
    BASE_LOCATION   = 'horizon_demo/txn_by_region/'
    PARTITION BY (IDENTITY(region));

-- Date-based transforms — coarser granularity reduces partition count
CREATE OR REPLACE ICEBERG TABLE horizon_demo_db.public.txn_by_day (
    transaction_id  VARCHAR(36),
    customer_id     VARCHAR(36),
    amount          DECIMAL(12, 2),
    currency        VARCHAR(3),
    transaction_ts  TIMESTAMP_NTZ(6),
    status          VARCHAR(20),
    region          VARCHAR(50)
)
    CATALOG         = 'SNOWFLAKE'
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol'
    BASE_LOCATION   = 'horizon_demo/txn_by_day/'
    PARTITION BY ( DAY(transaction_ts) );

-- Multi-level partition: month + region
CREATE OR REPLACE ICEBERG TABLE horizon_demo_db.public.txn_partitioned (
    transaction_id  VARCHAR(36),
    customer_id     VARCHAR(36),
    amount          DECIMAL(12, 2),
    currency        VARCHAR(3),
    transaction_ts  TIMESTAMP_NTZ(6),
    status          VARCHAR(20),
    region          VARCHAR(50)
)
    CATALOG         = 'SNOWFLAKE'
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol'
    BASE_LOCATION   = 'horizon_demo/txn_partitioned/'
    PARTITION BY ( MONTH(transaction_ts), IDENTITY(region) );

-- Bucket transform — hash-based, good for high-cardinality columns
CREATE OR REPLACE ICEBERG TABLE horizon_demo_db.public.txn_bucketed (
    transaction_id  VARCHAR(36),
    customer_id     VARCHAR(36),
    amount          DECIMAL(12, 2),
    currency        VARCHAR(3),
    transaction_ts  TIMESTAMP_NTZ(6),
    status          VARCHAR(20),
    region          VARCHAR(50)
)
    CATALOG         = 'SNOWFLAKE'
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol'
    BASE_LOCATION   = 'horizon_demo/txn_bucketed/'
    PARTITION BY ( BUCKET(16, customer_id) );  -- 16 buckets on customer_id

-- Truncate transform — prefix-based, useful for VARCHAR columns
CREATE OR REPLACE ICEBERG TABLE horizon_demo_db.public.txn_truncated (
    transaction_id  VARCHAR(36),
    customer_id     VARCHAR(36),
    amount          DECIMAL(12, 2),
    currency        VARCHAR(3),
    transaction_ts  TIMESTAMP_NTZ(6),
    status          VARCHAR(20),
    region          VARCHAR(50)
)
    CATALOG         = 'SNOWFLAKE'
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol'
    BASE_LOCATION   = 'horizon_demo/txn_truncated/'
    PARTITION BY ( TRUNCATE(2, currency) );  -- first 2 chars of currency

-- =============================================================
-- PART 2: PARTITION EVOLUTION (change spec without rewriting data)
-- =============================================================
ALTER ICEBERG TABLE horizon_demo_db.public.txn_by_region
    SET PARTITION SPEC ( MONTH(transaction_ts), IDENTITY(region) );
-- Old files keep old partition layout; new files use new spec — zero downtime

-- =============================================================
-- PART 3: SORT ORDER (Z-ordering / clustering)
-- =============================================================
ALTER ICEBERG TABLE horizon_demo_db.public.txn_partitioned
    SET SORT ORDER ( region ASC NULLS LAST, transaction_ts DESC NULLS LAST );
-- New files written with this sort order; OPTIMIZE reorg applies retroactively

-- =============================================================
-- PART 4: VERIFY PARTITION PRUNING
-- =============================================================
-- Enable query profiling
ALTER SESSION SET USE_CACHED_RESULT = FALSE;

-- This query should prune to only 'us-west' region partitions
EXPLAIN
SELECT SUM(amount)
FROM horizon_demo_db.public.txn_partitioned
WHERE region = 'us-west'
  AND transaction_ts >= '2024-01-01'::TIMESTAMP_NTZ
  AND transaction_ts <  '2024-02-01'::TIMESTAMP_NTZ;

-- Check partitions scanned via query profile
SELECT
    query_id,
    partitions_scanned,
    partitions_total,
    ROUND(100 * partitions_scanned / NULLIF(partitions_total, 0), 1) AS pct_scanned
FROM snowflake.account_usage.query_history
WHERE query_text ILIKE '%txn_partitioned%'
ORDER BY start_time DESC LIMIT 5;

-- =============================================================
-- PART 5: FILE SIZE TUNING
-- =============================================================
-- Target file size: 128 MB–512 MB for Parquet
-- After many small-file writes, compact:
ALTER ICEBERG TABLE horizon_demo_db.public.txn_partitioned
    OPTIMIZE WHERE transaction_ts >= DATEADD(MONTH, -1, CURRENT_DATE);

-- Check resulting file stats
SELECT file_count, bytes_on_disk, average_row_count_per_file
FROM TABLE(information_schema.iceberg_table_status(
    TABLE_NAME    => 'txn_partitioned',
    DATABASE_NAME => 'HORIZON_DEMO_DB',
    SCHEMA_NAME   => 'PUBLIC'
));
