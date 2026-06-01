-- =============================================================================
-- Feature D: Iceberg Time Travel in Snowflake
-- Snowflake supports time travel on Iceberg tables using:
--   AT(SNAPSHOT => <snapshot_id>)
--   AT(TIMESTAMP => <timestamp>)
--   BEFORE(STATEMENT => <query_id>)
-- External engines can also access historical snapshots via Iceberg REST.
-- =============================================================================

USE DATABASE horizon_demo_db;
USE SCHEMA public;

-- Step 1: Show current snapshot and history
SELECT SYSTEM$GET_ICEBERG_TABLE_INFORMATION('horizon_demo_db.public.transactions') AS info;

-- Step 2: List all snapshots (Iceberg snapshot log)
SELECT *
FROM TABLE(information_schema.iceberg_table_history(
    TABLE_NAME => 'transactions',
    DATABASE_NAME => 'HORIZON_DEMO_DB',
    SCHEMA_NAME => 'PUBLIC'
))
ORDER BY committed_at DESC;

-- Step 3: Time travel to a specific snapshot ID
--   Replace <snapshot_id> with an ID from the query above
SELECT *
FROM horizon_demo_db.public.transactions
    AT(SNAPSHOT => 1234567890123456789)
ORDER BY transaction_ts;

-- Step 4: Time travel to a timestamp
--   See data as it existed 1 hour ago
SELECT *
FROM horizon_demo_db.public.transactions
    AT(TIMESTAMP => DATEADD(HOUR, -1, CURRENT_TIMESTAMP()))
ORDER BY transaction_ts;

-- Step 5: Time travel BEFORE a specific DML statement
--   Useful for accidental DELETE recovery
SELECT *
FROM horizon_demo_db.public.transactions
    BEFORE(STATEMENT => '<query_id_of_delete>');

-- Step 6: Recover deleted data using time travel
--   Example: accidentally deleted FAILED transactions
BEGIN;
    -- Simulate accidental delete
    DELETE FROM horizon_demo_db.public.transactions WHERE status = 'FAILED';

    -- Recover: insert back from snapshot before the delete
    INSERT INTO horizon_demo_db.public.transactions
        SELECT * FROM horizon_demo_db.public.transactions
            BEFORE(STATEMENT => LAST_QUERY_ID())
        WHERE status = 'FAILED';
COMMIT;

-- Step 7: External engine time travel via Iceberg REST
--   External engines use Iceberg snapshot IDs directly:
--   PyIceberg:  table.scan(snapshot_id=<id>).to_pandas()
--   Spark:      spark.read.option("snapshot-id", "<id>").table("sf.public.transactions")
--   Trino:      SELECT * FROM "sf"."public"."transactions$snapshots"

-- Step 8: UNDROP an Iceberg table (Snowflake-specific)
DROP TABLE horizon_demo_db.public.transactions;
UNDROP TABLE horizon_demo_db.public.transactions;
SELECT COUNT(*) FROM horizon_demo_db.public.transactions;  -- data is back
