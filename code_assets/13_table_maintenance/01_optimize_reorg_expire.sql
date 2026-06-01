-- =============================================================================
-- Feature E: Iceberg Table Maintenance
-- Snowflake provides native maintenance operations for Iceberg tables:
--   OPTIMIZE  — file compaction (merges small Parquet files)
--   REORG     — reorganizes files for better partition pruning
--   ALTER TABLE ... EXPIRE SNAPSHOTS  — removes old snapshot metadata
-- External engines (Spark) create small files; Snowflake cleans them up.
-- =============================================================================

USE DATABASE horizon_demo_db;
USE SCHEMA public;

-- Step 1: Check current file statistics before maintenance
SELECT
    active_row_count,
    average_row_count_per_file,
    file_count,
    bytes_on_disk
FROM TABLE(information_schema.iceberg_table_status(
    TABLE_NAME    => 'transactions',
    DATABASE_NAME => 'HORIZON_DEMO_DB',
    SCHEMA_NAME   => 'PUBLIC'
));

-- Step 2: OPTIMIZE — compact small Parquet files into larger ones
--   Run this after bulk Spark/Flink appends that create many small files
ALTER ICEBERG TABLE horizon_demo_db.public.transactions OPTIMIZE;

-- Step 3: OPTIMIZE with WHERE clause — target a specific partition range
ALTER ICEBERG TABLE horizon_demo_db.public.transactions
    OPTIMIZE WHERE transaction_ts >= DATEADD(DAY, -7, CURRENT_DATE);

-- Step 4: REORG — rewrites files sorted by a column for better pruning
ALTER ICEBERG TABLE horizon_demo_db.public.transactions
    REORG (REWRITE_DATA_FILES = TRUE);

-- Step 5: EXPIRE SNAPSHOTS — remove old snapshot metadata to save storage
--   Keep only snapshots newer than 7 days
ALTER ICEBERG TABLE horizon_demo_db.public.transactions
    EXPIRE SNAPSHOTS OLDER_THAN = DATEADD(DAY, -7, CURRENT_TIMESTAMP());

-- Step 6: Check stats after maintenance
SELECT
    active_row_count,
    average_row_count_per_file,
    file_count,
    bytes_on_disk
FROM TABLE(information_schema.iceberg_table_status(
    TABLE_NAME    => 'transactions',
    DATABASE_NAME => 'HORIZON_DEMO_DB',
    SCHEMA_NAME   => 'PUBLIC'
));

-- Step 7: AUTO maintenance — Snowflake can schedule this automatically
--   Set AUTO_REFRESH_ENABLED in EXTERNAL VOLUME for background compaction
ALTER ICEBERG TABLE horizon_demo_db.public.transactions
    SET AUTO_REFRESH = TRUE;

-- Step 8: Monitor maintenance operations
SELECT
    query_id,
    query_text,
    start_time,
    total_elapsed_time / 1000 AS seconds
FROM snowflake.account_usage.query_history
WHERE query_text ILIKE '%ALTER ICEBERG TABLE%OPTIMIZE%'
  AND start_time >= DATEADD(DAY, -7, CURRENT_TIMESTAMP())
ORDER BY start_time DESC;
