-- =============================================================================
-- Feature G: Competitive Positioning — SQL-level comparison
-- Snowflake Iceberg vs Databricks Delta Lake vs AWS Lake Formation vs
-- Google BigLake vs Microsoft Fabric OneLake
-- =============================================================================

-- =============================================================
-- 1. SNOWFLAKE ICEBERG  (the recommended path)
-- =============================================================
-- Snowflake manages Iceberg tables with full DML, governance,
-- time travel, and open access via Horizon Catalog REST.

CREATE OR REPLACE ICEBERG TABLE competitive_demo.public.events (
    event_id    VARCHAR(36),
    user_id     VARCHAR(36),
    event_type  VARCHAR(50),
    event_ts    TIMESTAMP_NTZ(6),
    payload     VARIANT
)
    CATALOG = 'SNOWFLAKE'
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol'
    BASE_LOCATION = 'competitive/events/';

-- Native SQL, governance, policy enforcement — all work out of the box
INSERT INTO competitive_demo.public.events
    SELECT gen_random_uuid(), gen_random_uuid(), 'click',
           CURRENT_TIMESTAMP()::TIMESTAMP_NTZ(6), PARSE_JSON('{"page":"home"}')
    FROM TABLE(GENERATOR(ROWCOUNT => 1000));

-- Time travel — unique to Snowflake for Iceberg
SELECT COUNT(*) FROM competitive_demo.public.events
    AT(TIMESTAMP => DATEADD(MINUTE, -5, CURRENT_TIMESTAMP()));

-- Open access — any Iceberg REST engine reads this
SELECT SYSTEM$GET_ICEBERG_REST_CATALOG_ENDPOINT();

-- =============================================================
-- 2. READING DATABRICKS DELTA TABLES (via Unity Catalog IRC)
-- =============================================================
-- Databricks Unity Catalog now supports Iceberg REST endpoint.
-- Snowflake can read Delta tables exposed as Iceberg via UC.

CREATE OR REPLACE CATALOG INTEGRATION unity_catalog_int
    CATALOG_SOURCE = ICEBERG_REST
    TABLE_FORMAT   = ICEBERG
    REST_CONFIG = (
        CATALOG_URI = 'https://<databricks-workspace>.azuredatabricks.net/api/2.1/unity-catalog/iceberg'
        WAREHOUSE   = '<unity_catalog_name>'
    )
    REST_AUTHENTICATION = (
        TYPE         = OAUTH
        OAUTH_TOKEN_URI = 'https://<databricks-workspace>.azuredatabricks.net/oidc/v1/token'
        OAUTH_CLIENT_ID     = '<service_principal_id>'
        OAUTH_CLIENT_SECRET = '<service_principal_secret>'
        OAUTH_ALLOWED_SCOPES = ('all-apis')
    )
    ENABLED = TRUE;

-- Catalog-linked DB for Unity Catalog
CREATE DATABASE IF NOT EXISTS databricks_uc_db
    LINKED_CATALOG = ( CATALOG_INTEGRATION = 'unity_catalog_int' )
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol';

-- =============================================================
-- 3. POSITIONING SUMMARY QUERY
-- =============================================================
-- This query documents the key differentiation at a glance
SELECT * FROM (VALUES
    ('Snowflake Iceberg + Horizon',     'Full DML',    'Yes (native)',  'Yes (RAP+Masking)', 'Yes',          'Open REST',  'GA'),
    ('Databricks Delta via UC',         'Full DML',    'Partial',       'Unity Catalog only','Conditional',  'Open REST',  'GA with caveats'),
    ('AWS Glue Iceberg',                'Full DML',    'Via IAM',       'Lake Formation',    'Yes',          'Open REST',  'GA'),
    ('Google BigLake Metastore',        'Read-heavy',  'Via IAM',       'BigQuery policies', 'Limited',      'Open REST',  'Evolving'),
    ('Microsoft Fabric OneLake',        'Delta focus',  'Via Entra ID', 'Fabric policies',   'Limited',      'Partial',    'Evolving')
) AS t(platform, dml_support, time_travel, policy_enforcement,
       credential_vending, iceberg_rest, status);
