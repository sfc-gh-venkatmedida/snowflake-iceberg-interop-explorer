-- =============================================================================
-- Feature B+C: AWS Glue IRC Catalog Integration + Catalog-Linked Database
-- Snowflake connects to AWS Glue as an Iceberg REST Catalog (IRC).
-- A catalog-linked database auto-discovers Glue databases as Snowflake schemas.
-- =============================================================================
-- Existing setup on VMEDIDADEMO_AWS1:
--   Catalog Integration : GLUE_ICEBERG_CATALOG_INT
--   Catalog-Linked DB   : ICEBERG_GLUE_DB
--   AWS Account         : 913524911227 (us-east-2)
-- =============================================================================

-- Step 1: Create the AWS Glue Iceberg REST Catalog integration
--   CATALOG_API_TYPE = AWS_GLUE tells Snowflake to use SigV4 auth against Glue
--   CATALOG_NAME = <12-digit AWS account ID>
CREATE OR REPLACE CATALOG INTEGRATION glue_iceberg_catalog_int
    CATALOG_SOURCE    = ICEBERG_REST
    TABLE_FORMAT      = ICEBERG
    CATALOG_NAMESPACE = ''
    REST_CONFIG = (
        CATALOG_URI      = 'https://glue.us-east-2.amazonaws.com/iceberg'
        CATALOG_API_TYPE = AWS_GLUE
        WAREHOUSE        = '913524911227'
        CATALOG_NAME     = '913524911227'
        ACCESS_DELEGATION_MODE = EXTERNAL_VOLUME_CREDENTIALS
    )
    ENABLED = TRUE;

-- Step 2: Retrieve Snowflake's IAM identity for the trust policy
DESC INTEGRATION glue_iceberg_catalog_int;
--   Note: API_AWS_IAM_USER_ARN and API_AWS_EXTERNAL_ID must be added to the
--   IAM trust policy of the role referenced by the external volume.

-- Step 3: Create a catalog-linked database
--   LINKED_CATALOG auto-discovers all Glue databases as Snowflake schemas.
--   EXTERNAL_VOLUME is specified OUTSIDE the LINKED_CATALOG parentheses.
CREATE DATABASE IF NOT EXISTS iceberg_glue_db
    LINKED_CATALOG = (
        CATALOG_INTEGRATION = 'glue_iceberg_catalog_int'
    )
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol';

-- Step 4: Verify catalog sync status
SELECT SYSTEM$GET_CATALOG_INTEGRATION_STATUS('glue_iceberg_catalog_int');

-- Step 5: List auto-discovered Glue databases (as schemas)
SHOW SCHEMAS IN iceberg_glue_db;

-- Step 6: Query Glue-managed Iceberg tables directly from Snowflake SQL
--   NOTE: Glue is case-insensitive — use lowercase identifiers in double quotes
SELECT * FROM iceberg_glue_db."iceberg_insurance_db"."insurance_customers_glue" LIMIT 10;

-- Step 7: Write back to Glue-managed Iceberg from Snowflake
INSERT INTO iceberg_glue_db."iceberg_insurance_db"."insurance_customers_glue"
SELECT * FROM iceberg_insurance_db.insurance.insurance_customers WHERE region = 'us-west';

-- Step 8: Catalog-linked DB auto-refresh (syncs new Glue tables automatically)
ALTER DATABASE iceberg_glue_db REFRESH;
SHOW ICEBERG TABLES IN iceberg_glue_db;
