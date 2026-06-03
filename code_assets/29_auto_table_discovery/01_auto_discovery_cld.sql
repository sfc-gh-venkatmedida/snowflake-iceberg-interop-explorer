-- =============================================================================
-- Feature 29: Automatic Table Discovery + Remote Catalog Sync
-- Catalog-Linked Databases (CLDs) auto-discover namespaces and tables
-- from external catalogs and keep them in sync — no manual registration.
-- This is a core part of the Catalog Federation story.
-- =============================================================================

-- =============================================================
-- HOW AUTO-DISCOVERY WORKS
-- =============================================================
-- When you CREATE DATABASE ... LINKED_CATALOG:
--   1. Snowflake connects to the external catalog REST endpoint
--   2. Lists all namespaces → maps to Snowflake schemas
--   3. Lists all tables in each namespace → makes them queryable
--   4. Refreshes on a schedule or on-demand
-- No CREATE TABLE or DESCRIBE TABLE needed — all automatic.

-- =============================================================
-- CREATE + VERIFY a catalog-linked database (Glue example)
-- =============================================================
CREATE DATABASE IF NOT EXISTS iceberg_glue_db
    LINKED_CATALOG = (
        CATALOG_INTEGRATION = 'glue_iceberg_catalog_int'
    )
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol';

-- Auto-discovered schemas (= Glue databases)
SHOW SCHEMAS IN iceberg_glue_db;

-- Auto-discovered tables (= Glue tables)
SHOW ICEBERG TABLES IN iceberg_glue_db;

-- Query without any manual schema definition
-- Glue is case-insensitive: use lowercase + double quotes
SELECT * FROM iceberg_glue_db."iceberg_insurance_db"."insurance_customers_glue" LIMIT 5;

-- =============================================================
-- MANUAL REFRESH — sync new tables added to the external catalog
-- =============================================================
ALTER DATABASE iceberg_glue_db REFRESH;

-- Check sync status
SELECT SYSTEM$GET_CATALOG_INTEGRATION_STATUS('glue_iceberg_catalog_int');

-- =============================================================
-- CATALOG SYNC BEHAVIOR
-- =============================================================
-- New table added in Glue:
--   → After ALTER DATABASE ... REFRESH (or scheduled), immediately queryable in Snowflake
-- Table dropped in Glue:
--   → Disappears from SHOW ICEBERG TABLES after next refresh
-- Schema added in Glue:
--   → New schema appears in Snowflake after refresh
-- Table schema changed in Glue (column add):
--   → Schema evolution propagated at next refresh
--   → Snowflake does NOT buffer old schema — live sync

-- =============================================================
-- REMOTE CATALOG WRITES — write from Snowflake back to external catalog
-- =============================================================
-- INSERT, UPDATE, DELETE from Snowflake into externally-managed tables
INSERT INTO iceberg_glue_db."iceberg_insurance_db"."insurance_customers_glue"
SELECT * FROM horizon_demo_db.public.transactions WHERE region = 'us-west';

-- =============================================================
-- ⚠️  SUPPORTED LIMITATIONS FOR AUTO-DISCOVERY
-- =============================================================
-- Catalog-linked databases support:
--   ✅ Snowflake-managed Iceberg tables (CATALOG = 'SNOWFLAKE')
--   ✅ Externally managed Iceberg tables (via catalog integration)
--   ❌ Regular Snowflake native tables (not Iceberg)
--   ❌ Delta Lake tables (unless exposed via Iceberg REST by the catalog)
--   ❌ Snowflake Data Sharing listings (CLD and listings are separate paths)
