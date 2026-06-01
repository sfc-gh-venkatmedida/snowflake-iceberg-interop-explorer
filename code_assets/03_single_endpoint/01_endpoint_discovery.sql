-- =============================================================================
-- Feature 3: Single Endpoint
-- Snowflake exposes ONE Horizon Catalog endpoint per account.
-- External engines do not need per-database or per-schema URIs.
-- Endpoint format:
--   https://<account_identifier>.snowflakecomputing.com/polaris/api/catalog
-- =============================================================================

-- Retrieve the endpoint for this account programmatically
SELECT SYSTEM$GET_ICEBERG_REST_CATALOG_ENDPOINT() AS horizon_endpoint;

-- The warehouse parameter in the catalog config selects which Snowflake database
-- to operate in.  All schemas/tables within are discoverable from the same URI.

-- Show what a single endpoint surfaces across multiple databases:
SHOW ICEBERG TABLES IN horizon_demo_db.public;
SHOW ICEBERG TABLES IN fgac_iceberg_db.fgac_schema;

-- Demonstrate: a single REST client call lists tables from ALL namespaces
--   GET https://scb47336.snowflakecomputing.com/polaris/api/catalog/v1/namespaces
--   GET https://scb47336.snowflakecomputing.com/polaris/api/catalog/v1/namespaces/public/tables
