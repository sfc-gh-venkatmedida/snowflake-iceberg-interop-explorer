-- =============================================================================
-- Feature 28: Microsoft OneLake REST Catalog Integration
-- Snowflake connects to Microsoft OneLake as an Iceberg REST catalog source.
-- Read OneLake-managed tables in Snowflake SQL via a catalog-linked database.
-- This is separate from the JDBC/warehouse path used by Fabric.
--
-- ⚠️  TWO DIFFERENT PATHS for Snowflake ↔ Microsoft Fabric/OneLake:
--
-- Path A (this feature): Snowflake reads OneLake Iceberg tables via REST
--   Direction : Snowflake → OneLake
--   Protocol  : Iceberg REST Catalog
--   Auth      : Azure OAuth (service principal)
--   Warehouse : NOT needed — Snowflake reads Parquet files via CLD
--   Status    : GA
--
-- Path B (JDBC): Fabric reads Snowflake tables via standard connector
--   Direction : Fabric → Snowflake
--   Protocol  : JDBC/ODBC (standard SQL)
--   Auth      : username + password
--   Warehouse : REQUIRED — Snowflake executes the query
--   Docs      : docs.snowflake.com/.../tables-iceberg-query-using-microsoft-fabric
-- =============================================================================

-- Step 1: Create external volume pointing to OneLake ADLS storage
--   OneLake storage follows ABFS path: abfss://<workspace>@onelake.dfs.fabric.microsoft.com/
CREATE EXTERNAL VOLUME onelake_ext_vol
    STORAGE_LOCATIONS = (
        (
            NAME                = 'onelake-fabric-workspace'
            STORAGE_PROVIDER    = 'AZURE'
            STORAGE_BASE_URL    = 'azure://onelake.blob.fabric.microsoft.com/<workspace_id>/'
            AZURE_TENANT_ID     = '<azure_tenant_id>'
        )
    );

-- Step 2: Create catalog integration for OneLake Iceberg REST
CREATE OR REPLACE CATALOG INTEGRATION onelake_iceberg_int
    CATALOG_SOURCE = ICEBERG_REST
    TABLE_FORMAT   = ICEBERG
    REST_CONFIG = (
        CATALOG_URI  = 'https://api.fabric.microsoft.com/v1/workspaces/<workspace_id>/lakehouses/<lakehouse_id>/livyapi/versions/2023-12-01/spark/icebergcatalog'
        WAREHOUSE    = '<lakehouse_name>'
    )
    REST_AUTHENTICATION = (
        TYPE                 = OAUTH
        OAUTH_TOKEN_URI      = 'https://login.microsoftonline.com/<tenant_id>/oauth2/v2.0/token'
        OAUTH_CLIENT_ID      = '<azure_app_client_id>'
        OAUTH_CLIENT_SECRET  = '<azure_app_client_secret>'
        OAUTH_ALLOWED_SCOPES = ('https://analysis.windows.net/powerbi/api/.default')
    )
    ENABLED = TRUE;

-- Step 3: Verify connectivity
SELECT SYSTEM$VERIFY_CATALOG_INTEGRATION('onelake_iceberg_int');

-- Step 4: Create catalog-linked database — auto-discovers OneLake lakehouses
CREATE DATABASE IF NOT EXISTS onelake_db
    LINKED_CATALOG = (
        CATALOG_INTEGRATION = 'onelake_iceberg_int'
    )
    EXTERNAL_VOLUME = 'onelake_ext_vol';

-- Step 5: List auto-discovered tables
SHOW SCHEMAS IN onelake_db;
SHOW ICEBERG TABLES IN onelake_db;

-- Step 6: Query OneLake-managed Iceberg tables from Snowflake SQL
SELECT * FROM onelake_db.<lakehouse_name>.<table_name> LIMIT 10;

-- Step 7: Join OneLake data with Snowflake-native Iceberg
SELECT
    s.transaction_id,
    s.amount,
    o.customer_segment       -- from OneLake Lakehouse
FROM horizon_demo_db.public.transactions s
JOIN onelake_db.<lakehouse_name>.customers o
    ON s.customer_id = o.customer_id;

-- =============================================================
-- ⚠️  PRIVATE CONNECTIVITY CAVEAT (applies to ALL catalog integrations)
-- For catalog integrations using private connectivity (PrivateLink):
--   Catalog-VENDED CREDENTIALS are NOT supported.
--   You must configure the external volume separately for data access.
--   The catalog integration handles metadata only over the private link.
-- =============================================================
