-- =============================================================================
-- Feature 2: Apache Polaris Integration with Snowflake Horizon
-- Apache Polaris (open-source or Snowflake Open Catalog) is integrated into
-- Horizon Catalog to enable interoperability with external engines.
-- =============================================================================

-- Option A: Connect Snowflake to an EXTERNAL Apache Polaris instance
--   (running locally, in Docker, or on any cloud)
--   Snowflake reads Polaris-managed Iceberg tables through a catalog integration.

CREATE OR REPLACE CATALOG INTEGRATION polaris_catalog_int
    CATALOG_SOURCE    = POLARIS
    TABLE_FORMAT      = ICEBERG
    CATALOG_NAMESPACE = 'insurance.public'
    REST_CONFIG = (
        CATALOG_URI   = 'http://<your-polaris-host>:8181/api/catalog'
        WAREHOUSE     = 'insurance_catalog'
    )
    REST_AUTHENTICATION = (
        TYPE         = OAUTH
        OAUTH_TOKEN_URI = 'http://<your-polaris-host>:8181/api/catalog/v1/oauth/tokens'
        OAUTH_CLIENT_ID     = '<snowflake_reader_client_id>'
        OAUTH_CLIENT_SECRET = '<snowflake_reader_client_secret>'
        OAUTH_ALLOWED_SCOPES = ('PRINCIPAL_ROLE:ALL')
    )
    ENABLED = TRUE;

-- Verify the integration can reach Polaris
SELECT SYSTEM$VERIFY_CATALOG_INTEGRATION('polaris_catalog_int');

-- Create a catalog-linked database to auto-discover Polaris namespaces as schemas
CREATE DATABASE IF NOT EXISTS polaris_db
    LINKED_CATALOG = (
        CATALOG_INTEGRATION = 'polaris_catalog_int'
    )
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol';

-- List tables auto-discovered from Polaris
SHOW ICEBERG TABLES IN polaris_db;

-- Query a Polaris-managed table directly from Snowflake SQL
SELECT COUNT(*) FROM polaris_db.public.insurance_customers;

-- =============================================================================
-- Option B: Snowflake AS the Horizon catalog — Polaris is the protocol
--   External engines connect TO Snowflake's Horizon endpoint using the same
--   Apache Iceberg REST protocol that Polaris implements.
-- =============================================================================

-- No additional SQL needed — any Snowflake-managed Iceberg table is automatically
-- accessible via Horizon Catalog at:
--   https://scb47336.snowflakecomputing.com/polaris/api/catalog

-- Grant an external Polaris principal access (role-based in Snowflake):
CREATE ROLE IF NOT EXISTS polaris_writer_role;
GRANT USAGE ON DATABASE horizon_demo_db TO ROLE polaris_writer_role;
GRANT USAGE ON SCHEMA horizon_demo_db.public TO ROLE polaris_writer_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE horizon_demo_db.public.transactions
    TO ROLE polaris_writer_role;
