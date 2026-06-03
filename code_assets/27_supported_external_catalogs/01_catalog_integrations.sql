-- =============================================================================
-- Feature 27: Supported External Catalogs (separate from External Engines)
-- Snowflake's Horizon Catalog can connect TO external catalogs to read/write
-- tables managed by those catalogs. This is the CATALOG FEDERATION path.
--
-- External ENGINES (Spark, Trino, DuckDB…) connect to Snowflake Horizon.
-- External CATALOGS (Glue, Unity, OneLake…) are connected FROM Snowflake.
-- These are two different directions with different configurations.
-- =============================================================================

-- =============================================================
-- SUPPORTED EXTERNAL CATALOGS (Snowflake reads FROM these)
-- =============================================================

-- 1. AWS Glue Iceberg REST Catalog
--    CATALOG_SOURCE = ICEBERG_REST, CATALOG_API_TYPE = AWS_GLUE
--    Auth: SigV4 (IAM role via external volume delegation)
--    Data: S3 (external volume credentials)
--    Status: GA

-- 2. Databricks Unity Catalog
--    CATALOG_SOURCE = ICEBERG_REST
--    Auth: OAuth (service principal / PAT)
--    Data: S3/ADLS via UC external locations (NOT Snowflake credential vending)
--    Status: GA

-- 3. Apache Polaris / Snowflake Open Catalog
--    CATALOG_SOURCE = POLARIS
--    Auth: OAuth (client credentials)
--    Data: S3 (vended credentials from Polaris)
--    Status: GA

-- 4. Microsoft OneLake REST Catalog  ← NEW addition
--    CATALOG_SOURCE = ICEBERG_REST (OneLake implements Iceberg REST)
--    Auth: Azure Managed Identity or service principal
--    Data: Azure Data Lake Storage (OneLake-managed paths)
--    Status: GA (connector launched 2025)

-- 5. Apache Gravitino (incubating)
--    CATALOG_SOURCE = ICEBERG_REST
--    Auth: token-based
--    Status: Community / experimental

-- =============================================================
-- Reference: create each catalog integration
-- =============================================================

-- AWS Glue
CREATE CATALOG INTEGRATION glue_cat_int
    CATALOG_SOURCE = ICEBERG_REST
    TABLE_FORMAT   = ICEBERG
    REST_CONFIG = (
        CATALOG_URI      = 'https://glue.us-east-2.amazonaws.com/iceberg'
        CATALOG_API_TYPE = AWS_GLUE
        WAREHOUSE        = '913524911227'
        CATALOG_NAME     = '913524911227'
        ACCESS_DELEGATION_MODE = EXTERNAL_VOLUME_CREDENTIALS
    ) ENABLED = TRUE;

-- Databricks Unity Catalog
CREATE CATALOG INTEGRATION uc_cat_int
    CATALOG_SOURCE = ICEBERG_REST
    TABLE_FORMAT   = ICEBERG
    REST_CONFIG = (
        CATALOG_URI = 'https://<workspace>.azuredatabricks.net/api/2.1/unity-catalog/iceberg'
        WAREHOUSE   = '<uc_name>'
    )
    REST_AUTHENTICATION = (
        TYPE                 = OAUTH
        OAUTH_TOKEN_URI      = 'https://<workspace>.azuredatabricks.net/oidc/v1/token'
        OAUTH_CLIENT_ID      = '<sp_client_id>'
        OAUTH_CLIENT_SECRET  = '<sp_secret>'
        OAUTH_ALLOWED_SCOPES = ('all-apis')
    ) ENABLED = TRUE;

-- Apache Polaris / Open Catalog
CREATE CATALOG INTEGRATION polaris_cat_int
    CATALOG_SOURCE = POLARIS
    TABLE_FORMAT   = ICEBERG
    REST_CONFIG = (
        CATALOG_URI = 'https://<polaris-host>/api/catalog'
        WAREHOUSE   = '<catalog_name>'
    )
    REST_AUTHENTICATION = (
        TYPE                 = OAUTH
        OAUTH_TOKEN_URI      = 'https://<polaris-host>/api/catalog/v1/oauth/tokens'
        OAUTH_CLIENT_ID      = '<client_id>'
        OAUTH_CLIENT_SECRET  = '<secret>'
        OAUTH_ALLOWED_SCOPES = ('PRINCIPAL_ROLE:ALL')
    ) ENABLED = TRUE;

-- Microsoft OneLake REST Catalog
CREATE CATALOG INTEGRATION onelake_cat_int
    CATALOG_SOURCE = ICEBERG_REST
    TABLE_FORMAT   = ICEBERG
    REST_CONFIG = (
        CATALOG_URI  = 'https://onelake.dfs.fabric.microsoft.com/<workspace_id>/api/2.0/catalog'
        WAREHOUSE    = '<lakehouse_name>'
    )
    REST_AUTHENTICATION = (
        TYPE                 = OAUTH
        OAUTH_TOKEN_URI      = 'https://login.microsoftonline.com/<tenant_id>/oauth2/v2.0/token'
        OAUTH_CLIENT_ID      = '<azure_sp_client_id>'
        OAUTH_CLIENT_SECRET  = '<azure_sp_secret>'
        OAUTH_ALLOWED_SCOPES = ('https://storage.azure.com/.default')
    ) ENABLED = TRUE;

-- Verify all integrations
SELECT SYSTEM$VERIFY_CATALOG_INTEGRATION('glue_cat_int');
SELECT SYSTEM$VERIFY_CATALOG_INTEGRATION('uc_cat_int');
SELECT SYSTEM$VERIFY_CATALOG_INTEGRATION('polaris_cat_int');
SELECT SYSTEM$VERIFY_CATALOG_INTEGRATION('onelake_cat_int');

SHOW INTEGRATIONS;
