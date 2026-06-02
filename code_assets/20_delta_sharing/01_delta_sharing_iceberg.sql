-- =============================================================================
-- Feature 20: Delta Sharing — Snowflake as CONSUMER
-- Snowflake can CONSUME Delta Shares from external providers
-- (Databricks, other Delta Sharing-compatible systems).
-- This is done via a Catalog-Linked Database (CLD).
-- GA target: 2026-06-01
--
-- ⚠️  POSITIONING NOTE:
-- Snowflake supports Delta Sharing as a CONSUMER, not as a provider.
-- The supported model is: ingest/query incoming Delta Shares via CLD.
-- Do NOT position Snowflake as serving data out via Delta Sharing protocol.
-- =============================================================================

-- Step 1: Create a catalog integration pointing to the Delta Sharing provider
--   The provider supplies a Delta Sharing endpoint + bearer token (profile.share)
CREATE OR REPLACE CATALOG INTEGRATION delta_share_int
    CATALOG_SOURCE    = DELTA_SHARING
    TABLE_FORMAT      = DELTA
    DELTA_SHARING_CONFIG = (
        DELTA_SHARING_ENDPOINT = 'https://<databricks-workspace>.azuredatabricks.net/api/2.0/delta-sharing'
        DELTA_SHARING_TOKEN    = '<bearer_token_from_profile_share>'
        DELTA_SHARING_SHARE    = '<share_name>'
    )
    ENABLED = TRUE;

-- Step 2: Verify connectivity to the Delta Share provider
SELECT SYSTEM$VERIFY_CATALOG_INTEGRATION('delta_share_int');

-- Step 3: Create a catalog-linked database
--   Snowflake auto-discovers all tables in the Delta Share as schemas/tables
CREATE DATABASE IF NOT EXISTS delta_shared_db
    LINKED_CATALOG = (
        CATALOG_INTEGRATION = 'delta_share_int'
    );

-- Step 4: List auto-discovered schemas and tables
SHOW SCHEMAS IN delta_shared_db;
SHOW ICEBERG TABLES IN delta_shared_db;

-- Step 5: Query the Delta Shared data directly from Snowflake SQL
SELECT * FROM delta_shared_db.<schema>.<table> LIMIT 10;

-- Step 6: Join Delta Shared data with Snowflake-native Iceberg tables
SELECT
    s.transaction_id,
    s.amount,
    d.customer_segment      -- from Databricks Delta Share
FROM horizon_demo_db.public.transactions s
JOIN delta_shared_db.public.customer_profiles d
    ON s.customer_id = d.customer_id
WHERE s.status = 'COMPLETED';

-- Step 7: Refresh the catalog-linked database to pick up new tables/schemas
ALTER DATABASE delta_shared_db REFRESH;

-- =============================================================
-- Customer-safe positioning:
-- "Snowflake can consume Delta Shares from Databricks or any
--  Delta Sharing-compatible provider directly in Snowflake SQL
--  via a catalog-linked database — no ETL, no data copy,
--  governed by Snowflake RBAC."
-- =============================================================
