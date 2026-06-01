-- =============================================================================
-- Feature 23: Unity Catalog → Snowflake Horizon Catalog Integration
-- Configure Databricks Unity Catalog to surface Snowflake-managed Iceberg
-- tables, and configure Snowflake to read Databricks Unity Catalog tables.
-- =============================================================================

-- =============================================================
-- DIRECTION A: Databricks reads Snowflake via Horizon
-- (Spark config is in 01_databricks_spark_horizon.py)
-- SQL validation from Snowflake side:
-- =============================================================

-- Verify the table Databricks will read
SELECT * FROM horizon_demo_db.public.transactions ORDER BY transaction_ts;
SELECT SYSTEM$GET_ICEBERG_REST_CATALOG_ENDPOINT() AS horizon_endpoint;

-- Create a service role for Databricks principal
CREATE ROLE IF NOT EXISTS databricks_reader_role;
GRANT USAGE ON DATABASE horizon_demo_db        TO ROLE databricks_reader_role;
GRANT USAGE ON SCHEMA   horizon_demo_db.public  TO ROLE databricks_reader_role;
GRANT SELECT ON TABLE   horizon_demo_db.public.transactions TO ROLE databricks_reader_role;
GRANT USAGE ON EXTERNAL VOLUME iceberg_demo_ext_vol TO ROLE databricks_reader_role;

-- Create a service user for the Databricks OAuth service principal
CREATE USER IF NOT EXISTS databricks_svc
    DEFAULT_ROLE = databricks_reader_role
    MUST_CHANGE_PASSWORD = FALSE
    COMMENT = 'Service user for Databricks Unity Catalog → Horizon integration';

GRANT ROLE databricks_reader_role TO USER databricks_svc;

-- =============================================================
-- DIRECTION B: Snowflake reads Databricks Unity Catalog via Iceberg REST
-- Unity Catalog exposes an Iceberg REST endpoint for external consumers
-- =============================================================

-- Step 1: Create catalog integration pointing to Unity Catalog
CREATE OR REPLACE CATALOG INTEGRATION unity_catalog_int
    CATALOG_SOURCE  = ICEBERG_REST
    TABLE_FORMAT    = ICEBERG
    REST_CONFIG = (
        CATALOG_URI  = 'https://<workspace>.azuredatabricks.net/api/2.1/unity-catalog/iceberg'
        WAREHOUSE    = '<unity_catalog_name>'
    )
    REST_AUTHENTICATION = (
        TYPE                 = OAUTH
        OAUTH_TOKEN_URI      = 'https://<workspace>.azuredatabricks.net/oidc/v1/token'
        OAUTH_CLIENT_ID      = '<service_principal_client_id>'
        OAUTH_CLIENT_SECRET  = '<service_principal_secret>'
        OAUTH_ALLOWED_SCOPES = ('all-apis')
    )
    ENABLED = TRUE;

-- Step 2: Verify connectivity
SELECT SYSTEM$VERIFY_CATALOG_INTEGRATION('unity_catalog_int');

-- Step 3: Catalog-linked database auto-discovers Unity Catalog namespaces
CREATE DATABASE IF NOT EXISTS databricks_uc_db
    LINKED_CATALOG = (
        CATALOG_INTEGRATION = 'unity_catalog_int'
    )
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol';

-- Step 4: Query Databricks Delta tables exposed as Iceberg
SHOW SCHEMAS IN databricks_uc_db;
SHOW ICEBERG TABLES IN databricks_uc_db;

-- Step 5: Join Snowflake Iceberg + Databricks Iceberg in a single SQL query
SELECT
    s.transaction_id,
    s.amount,
    d.customer_segment,      -- from Databricks
    d.lifetime_value          -- from Databricks
FROM horizon_demo_db.public.transactions s
JOIN databricks_uc_db.main.customer_profiles d
    ON s.customer_id = d.customer_id
WHERE s.status = 'COMPLETED'
ORDER BY s.amount DESC;
