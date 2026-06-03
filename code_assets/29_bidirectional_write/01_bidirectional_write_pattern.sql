-- =============================================================================
-- Feature 29: Bidirectional Write / Concurrent Write Pattern
-- Both Snowflake AND external engines (Spark, Flink) write to the same
-- Snowflake-managed Iceberg table concurrently via Horizon REST.
-- This is distinct from simple "read+write" — it is a multi-writer architecture.
--
-- Use case: Spark handles high-throughput appends; Snowflake handles
-- merge/upsert and governance. Both read the latest committed state.
-- =============================================================================

-- ── SETUP: Table for bidirectional writes ────────────────────────────────
CREATE ICEBERG TABLE IF NOT EXISTS horizon_demo_db.public.txn_bidir (
    transaction_id  STRING,
    customer_id     STRING,
    amount          DECIMAL(12,2),
    event_ts        TIMESTAMP_NTZ(6),
    source          STRING,    -- 'spark' | 'snowflake'
    status          STRING
)
    CATALOG = 'SNOWFLAKE'
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol'
    BASE_LOCATION   = 'horizon_demo/txn_bidir/'
    ENABLE_SCHEMA_EVOLUTION = TRUE;

-- ── SNOWFLAKE WRITE: merge/upsert path ───────────────────────────────────
-- Snowflake handles deduplication and SCD logic
MERGE INTO horizon_demo_db.public.txn_bidir AS target
USING (
    SELECT transaction_id, customer_id, amount, event_ts,
           'snowflake' AS source, 'processed' AS status
    FROM horizon_demo_db.public.transactions
    WHERE transaction_ts >= DATEADD(HOUR, -1, CURRENT_TIMESTAMP())
) AS src
ON target.transaction_id = src.transaction_id
WHEN MATCHED THEN UPDATE SET
    target.status  = src.status,
    target.source  = src.source
WHEN NOT MATCHED THEN INSERT
    (transaction_id, customer_id, amount, event_ts, source, status)
    VALUES (src.transaction_id, src.customer_id, src.amount,
            src.event_ts, src.source, src.status);

-- ── SPARK WRITE: append path (reference — runs externally) ───────────────
-- Spark writes new raw events via Iceberg REST; Snowflake reads them immediately
-- spark_code = """
-- df.writeTo("sf.horizon_demo_db.public.txn_bidir") \
--     .option("write.format.default", "parquet") \
--     .option("write.metadata.metrics.default", "full") \
--     .append()
-- """

-- ── VERIFY: both sources visible in single query ─────────────────────────
SELECT
    source,
    COUNT(*)                    AS row_count,
    MAX(event_ts)               AS latest_event,
    SUM(amount)                 AS total_amount
FROM horizon_demo_db.public.txn_bidir
GROUP BY source
ORDER BY source;

-- ── OPTIMIZE after Spark appends (small files from streaming writes) ──────
ALTER ICEBERG TABLE horizon_demo_db.public.txn_bidir
    OPTIMIZE WHERE event_ts >= DATEADD(HOUR, -6, CURRENT_TIMESTAMP());

-- =============================================================================
-- IMPORTANT: Concurrent write coordination
-- Snowflake uses OCC (Optimistic Concurrency Control) on Iceberg metadata.
-- If Spark and Snowflake write simultaneously, one will retry on conflict.
-- Best practice: partition writes by time window OR use separate ingestion
-- tables and merge into the main table from a single writer.
-- =============================================================================

-- Check for any commit conflicts in recent snapshots
SELECT snapshot_id, parent_id, committed_at, summary
FROM TABLE(horizon_demo_db.information_schema.iceberg_table_snapshots(
    table_name => 'HORIZON_DEMO_DB.PUBLIC.TXN_BIDIR'
))
ORDER BY committed_at DESC
LIMIT 10;
