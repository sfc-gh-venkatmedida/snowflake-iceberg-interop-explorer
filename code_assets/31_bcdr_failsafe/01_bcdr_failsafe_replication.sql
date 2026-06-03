-- =============================================================================
-- Feature 31: BCDR / Fail-Safe / Replication for Snowflake-managed Iceberg
-- Snowflake-managed Iceberg tables get enterprise-grade data protection:
--   Fail-safe  : 7-day non-configurable recovery window (ops use only)
--   Time Travel: 0–90 day configurable recovery window
--   Replication: Cross-region / cross-cloud replication via Replication Groups
--
-- This is a key differentiator vs self-managed Iceberg (no fail-safe/replication).
-- External engines only get what they implement themselves. Snowflake provides
-- these automatically for CATALOG='SNOWFLAKE' tables.
-- =============================================================================

-- ── FAIL-SAFE ─────────────────────────────────────────────────────────────
-- Fail-safe is automatic — nothing to configure.
-- 7-day non-configurable window, managed by Snowflake internally.
-- Accessible ONLY by Snowflake Support (not via SQL).
-- Check fail-safe storage cost:
SELECT
    table_schema,
    table_name,
    ROUND(failsafe_bytes / POWER(1024,3), 2)     AS failsafe_gb,
    ROUND(active_bytes   / POWER(1024,3), 2)     AS active_gb
FROM horizon_demo_db.information_schema.table_storage_metrics
WHERE table_schema = 'PUBLIC'
ORDER BY failsafe_gb DESC;

-- ── TIME TRAVEL ──────────────────────────────────────────────────────────
-- Configurable 0–90 days (Enterprise edition) for Snowflake-managed Iceberg
ALTER ICEBERG TABLE horizon_demo_db.public.transactions
    SET DATA_RETENTION_TIME_IN_DAYS = 14;

-- Recover from accidental DELETE
BEGIN;
  DELETE FROM horizon_demo_db.public.transactions WHERE status = 'test';
ROLLBACK;  -- or use Time Travel to recover

-- Query data as-of 24 hours ago
SELECT COUNT(*) AS row_count_yesterday
FROM horizon_demo_db.public.transactions
    AT (OFFSET => -86400);

-- Clone table at a point in time (zero-copy)
CREATE ICEBERG TABLE horizon_demo_db.public.transactions_backup
    CLONE horizon_demo_db.public.transactions
    AT (TIMESTAMP => DATEADD(HOUR, -1, CURRENT_TIMESTAMP()));

-- ── REPLICATION: cross-region / cross-cloud ───────────────────────────────
-- Replicate Snowflake-managed Iceberg tables to another region/cloud.
-- External engines on the secondary can read from the replica via Horizon REST.

-- Step 1: Enable replication on the source database
ALTER DATABASE horizon_demo_db
    ENABLE REPLICATION TO ACCOUNTS aws_eu_west_1.my_org;

-- Step 2: Create replication group (includes Iceberg tables + external volume mapping)
CREATE REPLICATION GROUP iceberg_bcdr_group
    OBJECT_TYPES = DATABASES
    ALLOWED_DATABASES = horizon_demo_db
    ALLOWED_ACCOUNTS  = aws_eu_west_1.my_org
    REPLICATION_SCHEDULE = '10 MINUTES';

-- Step 3: On the secondary account — create failover group and start replication
-- (run on secondary account)
-- CREATE FAILOVER GROUP iceberg_bcdr_group
--     AS REPLICA OF aws_us_east_1.my_org.iceberg_bcdr_group;
-- ALTER FAILOVER GROUP iceberg_bcdr_group REFRESH;

-- Check replication lag
SELECT phase_name, job_uuid, start_time, end_time,
       objects_replicated, bytes_transferred
FROM TABLE(INFORMATION_SCHEMA.REPLICATION_GROUP_REFRESH_HISTORY(
    REPLICATION_GROUP_NAME => 'iceberg_bcdr_group'
))
ORDER BY start_time DESC
LIMIT 5;

-- ── BCDR COMPARISON: Snowflake-managed vs self-managed ───────────────────
-- | Capability       | Snowflake-managed Iceberg | Self-managed / External |
-- |------------------|--------------------------|-------------------------|
-- | Fail-safe        | ✅ 7 days automatic       | ❌ Manual backup only   |
-- | Time Travel      | ✅ 0–90 days (Enterprise) | ⚠️  Iceberg snapshots only |
-- | Cross-region rep | ✅ Built-in Replication   | ❌ Must build own        |
-- | Zero-copy clone  | ✅ CREATE ICEBERG TABLE CLONE | ❌ Not available    |
-- | Horizon access   | ✅ Replicated tables      | ❌ No replication        |
