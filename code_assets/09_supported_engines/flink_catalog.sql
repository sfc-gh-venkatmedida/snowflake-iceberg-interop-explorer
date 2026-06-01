-- Feature 9: Apache Flink — connect to Snowflake Horizon Catalog
-- Flink 1.18+ supports Iceberg catalogs.  Configure in your Flink application or
-- SQL client using the properties below.
--
-- Maven dependency:
--   org.apache.iceberg:iceberg-flink-runtime-1.18:1.7.0
--   org.apache.iceberg:iceberg-aws-bundle:1.7.0

-- Flink SQL client configuration:
CREATE CATALOG snowflake_horizon WITH (
    'type'             = 'iceberg',
    'catalog-type'     = 'rest',
    'uri'              = 'https://scb47336.snowflakecomputing.com/polaris/api/catalog',
    'token'            = '<SNOWFLAKE_TOKEN>',
    'warehouse'        = 'horizon_demo_db',
    'header.X-Iceberg-Access-Delegation' = 'vended-credentials',
    's3.region'        = 'us-east-2'
);

USE CATALOG snowflake_horizon;
USE public;

-- Read
SELECT * FROM transactions LIMIT 20;

-- Append (streaming insert)
INSERT INTO transactions
SELECT
    CAST(RAND() * 1000 AS VARCHAR) AS transaction_id,
    'cust-stream' AS customer_id,
    RAND() * 500 AS amount,
    'USD' AS currency,
    CURRENT_TIMESTAMP AS transaction_ts,
    'COMPLETED' AS status,
    'us-east' AS region;
