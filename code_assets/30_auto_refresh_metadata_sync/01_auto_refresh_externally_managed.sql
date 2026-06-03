-- =============================================================================
-- Feature 30: Auto-Refresh / Metadata Sync for Externally Managed Iceberg
-- When an external engine (Spark, Flink) writes new snapshots to an
-- externally managed Iceberg table, Snowflake must refresh its metadata
-- to see the new data. This is DIFFERENT from CLD auto-discovery (Feature 28).
--
-- Two scenarios:
-- A) Externally managed table (Spark writes, Snowflake reads)
--    → ALTER ICEBERG TABLE ... REFRESH  or  AUTO_REFRESH = TRUE
-- B) Catalog-Linked Database (external catalog as source)
--    → ALTER DATABASE ... REFRESH  (covered in Feature 28)
-- =============================================================================

-- ── SCENARIO A: Externally managed table — Spark writes, Snowflake reads ──

-- Step 1: Register the externally managed table in Snowflake
CREATE ICEBERG TABLE IF NOT EXISTS horizon_demo_db.public.spark_managed_events
    EXTERNAL_VOLUME    = 'iceberg_demo_ext_vol'
    CATALOG            = 'GLUE_ICEBERG_CATALOG_INT'   -- external catalog
    CATALOG_TABLE_NAME = 'spark_events'               -- name in Glue
    METADATA_FILE_PATH = 'spark_events/metadata/v3.metadata.json';

-- Step 2a: Manual refresh — pull latest Spark snapshots on demand
ALTER ICEBERG TABLE horizon_demo_db.public.spark_managed_events REFRESH;

-- Step 2b: Enable automatic metadata refresh (polls catalog on schedule)
ALTER ICEBERG TABLE horizon_demo_db.public.spark_managed_events
    SET AUTO_REFRESH = TRUE;

-- Check refresh interval on the catalog integration
SHOW CATALOG INTEGRATIONS LIKE 'GLUE_ICEBERG_CATALOG_INT';
-- REFRESH_INTERVAL_SECONDS column shows polling frequency (default: 30s)

-- Step 3: Verify latest snapshot is visible
SELECT snapshot_id, committed_at, operation, summary
FROM TABLE(horizon_demo_db.information_schema.iceberg_table_snapshots(
    table_name => 'HORIZON_DEMO_DB.PUBLIC.SPARK_MANAGED_EVENTS'
))
ORDER BY committed_at DESC
LIMIT 5;

-- Step 4: Query — reflects Spark's latest committed snapshot
SELECT COUNT(*), MAX(event_ts)
FROM horizon_demo_db.public.spark_managed_events;

-- =============================================================================
-- AUTO-REFRESH BEHAVIOR REFERENCE
-- =============================================================================
-- AUTO_REFRESH = TRUE on externally managed table:
--   → Snowflake polls the external catalog for new metadata files
--   → Default interval: 30 seconds (set REFRESH_INTERVAL_SECONDS on catalog int)
--   → New Spark snapshots become visible within one polling interval
--   → No warehouse cost — metadata refresh uses serverless resources
--
-- Manual ALTER ... REFRESH:
--   → Immediate sync — use after a Spark job completes
--   → Combine with Snowflake Tasks for post-job trigger pattern
--
-- CLD (Feature 28) vs externally managed (this feature):
--   CLD           = database-level discovery (new tables auto-appear)
--   Externally managed = table-level metadata sync (new data in known table)
-- =============================================================================

-- ── Monitor auto-refresh events ──────────────────────────────────────────
SELECT event_timestamp, event_type, resource_attributes, record
FROM TABLE(INFORMATION_SCHEMA.AUTO_REFRESH_REGISTRATION_HISTORY(
    DATE_RANGE_START => DATEADD(HOUR, -24, CURRENT_TIMESTAMP()),
    TABLE_NAME       => 'HORIZON_DEMO_DB.PUBLIC.SPARK_MANAGED_EVENTS'
))
ORDER BY event_timestamp DESC
LIMIT 10;

-- ── Task-based refresh trigger (post-Spark-job pattern) ──────────────────
CREATE OR REPLACE TASK refresh_after_spark
    WAREHOUSE   = 'OPENFLOW_INGEST_WAREHOUSE'
    SCHEDULE    = '5 MINUTES'
AS
    ALTER ICEBERG TABLE horizon_demo_db.public.spark_managed_events REFRESH;
