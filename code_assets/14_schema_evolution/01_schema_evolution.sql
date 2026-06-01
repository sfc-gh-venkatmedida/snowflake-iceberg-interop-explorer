-- =============================================================================
-- Feature F: Schema Evolution on Iceberg Tables
-- Iceberg natively supports schema evolution: add, drop, rename columns,
-- change data types, and update partition specs — without rewriting data.
-- Changes made in Snowflake are immediately visible to external engines.
-- =============================================================================

USE DATABASE horizon_demo_db;
USE SCHEMA public;

-- Show current schema
DESCRIBE TABLE transactions;

-- Step 1: ADD COLUMN — add a new column (no data rewrite)
ALTER TABLE horizon_demo_db.public.transactions
    ADD COLUMN merchant_id VARCHAR(36);

ALTER TABLE horizon_demo_db.public.transactions
    ADD COLUMN fee_amount DECIMAL(8, 2) DEFAULT 0.00;

-- Verify: external engines immediately see the new column
-- Spark: spark.table("sf.public.transactions").printSchema()  -- shows merchant_id

-- Step 2: RENAME COLUMN
ALTER TABLE horizon_demo_db.public.transactions
    RENAME COLUMN merchant_id TO merchant_ref_id;

-- Step 3: DROP COLUMN — column is logically removed; Parquet files unchanged
ALTER TABLE horizon_demo_db.public.transactions
    DROP COLUMN fee_amount;

-- Step 4: CHANGE data type (widening only — e.g., INT → BIGINT, VARCHAR(36) → VARCHAR(100))
ALTER TABLE horizon_demo_db.public.transactions
    MODIFY COLUMN transaction_id VARCHAR(100);

-- Step 5: Reorder columns
ALTER TABLE horizon_demo_db.public.transactions
    MODIFY COLUMN status FIRST;

-- Step 6: Update partition spec (Iceberg partition evolution)
--   Original table has no explicit partition spec.
--   Add a partition transform for query pruning.
ALTER ICEBERG TABLE horizon_demo_db.public.transactions
    SET PARTITION SPEC ( MONTH(transaction_ts), IDENTITY(region) );

-- Step 7: View schema evolution history
SELECT *
FROM TABLE(information_schema.iceberg_table_history(
    TABLE_NAME    => 'transactions',
    DATABASE_NAME => 'HORIZON_DEMO_DB',
    SCHEMA_NAME   => 'PUBLIC'
))
ORDER BY committed_at DESC;

-- Step 8: Schema evolution from external engine (Spark)
-- spark.sql("""
--   ALTER TABLE sf.public.transactions
--   ADD COLUMNS (loyalty_points INT)
-- """)
-- Snowflake picks up this change automatically via Iceberg metadata.

DESCRIBE TABLE transactions;  -- verify all changes
