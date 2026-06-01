-- Feature 9: StarRocks — connect to Snowflake Horizon Catalog (Iceberg REST)
-- StarRocks 3.2+ supports the Iceberg REST catalog.
-- Run these commands in the StarRocks SQL client.
--
-- Reference: https://docs.starrocks.io/docs/data_source/catalog/iceberg_catalog/

CREATE EXTERNAL CATALOG snowflake_horizon
COMMENT "Snowflake Horizon Iceberg REST Catalog"
PROPERTIES (
    "type"                         = "iceberg",
    "iceberg.catalog.type"         = "rest",
    "iceberg.catalog.rest.uri"     = "https://scb47336.snowflakecomputing.com/polaris/api/catalog",
    "iceberg.catalog.rest.token"   = "<SNOWFLAKE_TOKEN>",
    "iceberg.catalog.rest.warehouse" = "horizon_demo_db",
    "aws.s3.region"                = "us-east-2",
    "aws.s3.enable_path_style_access" = "false"
);

SET CATALOG snowflake_horizon;

SHOW DATABASES;

USE `public`;

SELECT * FROM transactions LIMIT 20;

SELECT region, COUNT(*) AS cnt, ROUND(SUM(amount), 2) AS total
FROM transactions
GROUP BY region ORDER BY total DESC;
