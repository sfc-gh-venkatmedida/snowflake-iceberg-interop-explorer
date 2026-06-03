-- =============================================================================
-- Feature 26: WIF / OIDC Authentication for External Engines (GA with write support)
-- Workload Identity Federation (WIF) lets external engines authenticate to
-- Snowflake Horizon Catalog using their native cloud identity — no static tokens,
-- no key rotation. Added with the external-engine write GA release.
--
-- Supported identity providers:
--   AWS    — IAM role (via AWS STS / OIDC)
--   Azure  — Managed Identity or Entra ID service principal
--   GCP    — Service Account (via GCP OIDC)
-- =============================================================================

-- =============================================================
-- PART 1: AWS WIF — EMR/Glue job authenticates to Horizon
--         using its IAM role, no Snowflake password needed
-- =============================================================

-- Step 1: Create a Snowflake security integration for AWS WIF
CREATE OR REPLACE SECURITY INTEGRATION aws_wif_integration
    TYPE = EXTERNAL_OAUTH
    ENABLED = TRUE
    EXTERNAL_OAUTH_TYPE = CUSTOM
    EXTERNAL_OAUTH_ISSUER = 'https://sts.amazonaws.com'
    EXTERNAL_OAUTH_JWS_KEYS_URL = 'https://www.googleapis.com/oauth2/v3/certs'
    EXTERNAL_OAUTH_TOKEN_USER_MAPPING_CLAIM = 'sub'
    EXTERNAL_OAUTH_SNOWFLAKE_USER_MAPPING_ATTRIBUTE = 'login_name'
    EXTERNAL_OAUTH_AUDIENCE_LIST = ('https://scb47336.snowflakecomputing.com');

-- Step 2: Map the IAM role ARN to a Snowflake user
CREATE USER IF NOT EXISTS emr_wif_user
    LOGIN_NAME = 'arn:aws:iam::913524911227:role/emr-iceberg-role'
    DEFAULT_ROLE = iceberg_ext_role
    MUST_CHANGE_PASSWORD = FALSE
    COMMENT = 'WIF user — IAM role identity maps here, no password needed';

GRANT ROLE iceberg_ext_role TO USER emr_wif_user;

-- Step 3: Grant table access to the role (same as any external engine)
GRANT USAGE ON DATABASE horizon_demo_db          TO ROLE iceberg_ext_role;
GRANT USAGE ON SCHEMA   horizon_demo_db.public    TO ROLE iceberg_ext_role;
GRANT SELECT, INSERT, UPDATE, DELETE ON TABLE
    horizon_demo_db.public.transactions           TO ROLE iceberg_ext_role;
GRANT USAGE ON EXTERNAL VOLUME iceberg_demo_ext_vol TO ROLE iceberg_ext_role;

-- Step 4 (reference — runs on the external engine):
-- EMR/Spark does NOT need to generate a Snowflake session token.
-- The engine uses its AWS IAM role to get an OIDC token from STS,
-- then exchanges it for a Snowflake OAuth token automatically.
--
-- Spark config:
--   spark.sql.catalog.sf.auth-manager  = org.apache.iceberg.aws.AssumeRoleAwsClientFactory
--   spark.sql.catalog.sf.token-refresh = oidc
--   spark.sql.catalog.sf.credential-provider = AWS_WIF
--   (no explicit token= needed — EMR instance profile handles it)

-- =============================================================
-- PART 2: Azure WIF — Databricks / ADF using Managed Identity
-- =============================================================

-- Step 1: Create Entra ID (Azure AD) security integration
CREATE OR REPLACE SECURITY INTEGRATION azure_wif_integration
    TYPE = EXTERNAL_OAUTH
    ENABLED = TRUE
    EXTERNAL_OAUTH_TYPE = AZURE
    EXTERNAL_OAUTH_ISSUER = 'https://sts.windows.net/<tenant_id>/'
    EXTERNAL_OAUTH_JWS_KEYS_URL = 'https://login.windows.net/<tenant_id>/discovery/v2.0/keys'
    EXTERNAL_OAUTH_TOKEN_USER_MAPPING_CLAIM = 'upn'
    EXTERNAL_OAUTH_SNOWFLAKE_USER_MAPPING_ATTRIBUTE = 'login_name'
    EXTERNAL_OAUTH_AUDIENCE_LIST = ('https://scb47336.snowflakecomputing.com');

-- Databricks Spark config (Managed Identity — no client secret needed):
--   spark.sql.catalog.sf.token-provider = azure-managed-identity
--   spark.sql.catalog.sf.auth-type       = OAUTH
--   spark.sql.catalog.sf.oauth-client-id = <azure_app_client_id>
--   spark.sql.catalog.sf.audience        = https://scb47336.snowflakecomputing.com

-- =============================================================
-- PART 3: Why WIF matters vs static token approach
-- =============================================================
-- Static token (previous approach):
--   1. Generate RSA key pair
--   2. Assign public key to Snowflake user
--   3. Write code to sign JWT
--   4. Exchange JWT for session token
--   5. Pass token in Spark config
--   6. Token expires → restart required
--   Complexity: HIGH, rotation risk: HIGH
--
-- WIF (new approach):
--   1. Grant the cloud IAM role/identity USAGE on Snowflake role
--   2. The engine's existing cloud identity authenticates automatically
--   No keys, no rotation, no token management
--   Complexity: LOW, rotation risk: NONE (cloud-managed)

SELECT SYSTEM$GET_ICEBERG_REST_CATALOG_ENDPOINT() AS horizon_endpoint;
