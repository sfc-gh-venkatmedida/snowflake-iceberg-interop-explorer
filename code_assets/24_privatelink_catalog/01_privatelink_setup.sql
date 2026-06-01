-- =============================================================================
-- Feature 24: PrivateLink for Catalog Integrations
-- Secure private network connectivity between Snowflake and external catalogs
-- (AWS Glue, Apache Polaris, Unity Catalog) — no traffic over the public internet.
-- =============================================================================

-- =============================================================
-- OPTION A: AWS PrivateLink for Glue IRC
-- =============================================================

-- Step 1: Create the catalog integration pointing to a PrivateLink VPC endpoint
--   The CATALOG_URI uses the private DNS name of your AWS VPC Endpoint
--   for Glue (not the public glue.us-east-2.amazonaws.com URL)
CREATE OR REPLACE CATALOG INTEGRATION glue_private_catalog_int
    CATALOG_SOURCE    = ICEBERG_REST
    TABLE_FORMAT      = ICEBERG
    REST_CONFIG = (
        CATALOG_URI      = 'https://glue.us-east-2.vpce.amazonaws.com/iceberg'
        CATALOG_API_TYPE = AWS_GLUE
        WAREHOUSE        = '913524911227'
        CATALOG_NAME     = '913524911227'
        ACCESS_DELEGATION_MODE = EXTERNAL_VOLUME_CREDENTIALS
    )
    ENABLED = TRUE;

-- Step 2: AWS-side setup (for reference — done in AWS Console/CLI)
-- aws ec2 create-vpc-endpoint \
--   --vpc-id vpc-xxx \
--   --service-name com.amazonaws.us-east-2.glue \
--   --vpc-endpoint-type Interface \
--   --subnet-ids subnet-xxx \
--   --security-group-ids sg-xxx \
--   --private-dns-enabled

-- Step 3: Snowflake network rule restricting outbound to private endpoint
CREATE NETWORK RULE glue_private_endpoint_rule
    TYPE = HOST_PORT
    MODE = EGRESS
    VALUE_LIST = ('glue.us-east-2.vpce.amazonaws.com:443');

CREATE EXTERNAL ACCESS INTEGRATION glue_private_eai
    ALLOWED_NETWORK_RULES = (glue_private_endpoint_rule)
    ENABLED = TRUE;

-- Step 4: Verify
SELECT SYSTEM$VERIFY_CATALOG_INTEGRATION('glue_private_catalog_int');

-- =============================================================
-- OPTION B: PrivateLink for Snowflake Horizon Catalog (inbound)
-- External engines connect to Horizon via PrivateLink instead of public internet
-- =============================================================

-- In Snowflake (provider side): enable PrivateLink for the account
-- (done via Snowflake Support or account admin)
-- After activation, the Horizon endpoint is reachable at the private IP:
--   https://<account_id>.privatelink.snowflakecomputing.com/polaris/api/catalog

-- External engine config (Spark example using PrivateLink endpoint):
-- spark.sql.catalog.sf.uri =
--   https://scb47336.privatelink.snowflakecomputing.com/polaris/api/catalog

-- =============================================================
-- OPTION C: AWS PrivateLink for Snowflake → Polaris
-- =============================================================
CREATE OR REPLACE CATALOG INTEGRATION polaris_private_int
    CATALOG_SOURCE = POLARIS
    TABLE_FORMAT   = ICEBERG
    REST_CONFIG = (
        CATALOG_URI = 'https://polaris.privatelink.snowflakecomputing.com/api/catalog'
        WAREHOUSE   = 'my_catalog'
    )
    REST_AUTHENTICATION = (
        TYPE                 = OAUTH
        OAUTH_TOKEN_URI      = 'https://polaris.privatelink.snowflakecomputing.com/api/catalog/v1/oauth/tokens'
        OAUTH_CLIENT_ID      = '<client_id>'
        OAUTH_CLIENT_SECRET  = '<client_secret>'
        OAUTH_ALLOWED_SCOPES = ('PRINCIPAL_ROLE:ALL')
    )
    ENABLED = TRUE;

-- Validate private connectivity
SELECT SYSTEM$VERIFY_CATALOG_INTEGRATION('polaris_private_int');

-- =============================================================
-- Network Policy: restrict Horizon access to specific IP ranges
-- (for customers who want only internal network access to Horizon)
-- =============================================================
CREATE NETWORK POLICY horizon_access_policy
    ALLOWED_IP_LIST = (
        '10.0.0.0/8',       -- internal VPC range
        '172.16.0.0/12',    -- private network
        '192.168.0.0/16'    -- private network
    )
    COMMENT = 'Restrict Horizon Catalog access to private network only';

ALTER ACCOUNT SET NETWORK_POLICY = horizon_access_policy;
