-- Feature 9: Apache Doris — connect to Snowflake Horizon Catalog (Iceberg REST)
-- Doris 2.1+ supports the Iceberg REST catalog natively.
-- Run these commands in the Doris SQL client.
--
-- Reference: https://doris.apache.org/docs/lakehouse/catalogs/iceberg-catalog

CREATE CATALOG snowflake_horizon PROPERTIES (
    'type'             = 'iceberg',
    'iceberg.catalog.type' = 'rest',
    'uri'              = 'https://scb47336.snowflakecomputing.com/polaris/api/catalog',
    'token'            = '<SNOWFLAKE_TOKEN>',
    'warehouse'        = 'horizon_demo_db',
    'credential_type'  = 'bearer_token',
    'header.X-Iceberg-Access-Delegation' = 'vended-credentials',
    's3.region'        = 'us-east-2'
);

SWITCH snowflake_horizon;

SHOW DATABASES;

USE `public`;

SELECT * FROM transactions LIMIT 20;

SELECT currency, COUNT(*) AS cnt, SUM(amount) AS total
FROM transactions
GROUP BY currency
ORDER BY total DESC;
