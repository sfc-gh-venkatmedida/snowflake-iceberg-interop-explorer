-- =============================================================================
-- Feature 6: Credential Vending
-- Horizon Catalog vends short-lived AWS STS credentials to external engines.
-- The engine provides X-Iceberg-Access-Delegation: vended-credentials in its
-- REST catalog config, and Horizon returns temporary S3 credentials with each
-- table metadata response.
-- =============================================================================

-- Step 1: Confirm the external volume is configured for credential vending.
--   Horizon reads the external volume storage locations and assumes the
--   associated IAM role to generate STS credentials for the external engine.
DESC EXTERNAL VOLUME iceberg_demo_ext_vol;

-- Step 2: Grant USAGE on the external volume to the service role.
--   Horizon will only vend credentials for volumes the requesting role can use.
GRANT USAGE ON EXTERNAL VOLUME iceberg_demo_ext_vol TO ROLE iceberg_svc_role;

-- Step 3: Test that Snowflake can verify the external volume
SELECT SYSTEM$VERIFY_EXTERNAL_STAGE_ROLE_BINDING(
    'iceberg_demo_ext_vol',
    's3://vmedida-iceberg-demo/horizon_demo/'
);

-- Step 4 (informational): When an external engine calls the Horizon REST API
--   with the vended-credentials delegation header, the response includes:
--   {
--     "config": {
--       "s3.access-key-id":     "<temporary_access_key>",
--       "s3.secret-access-key": "<temporary_secret>",
--       "s3.session-token":     "<temporary_token>",
--       "s3.region":            "us-east-2"
--     }
--   }
--   The engine uses these credentials to read/write Parquet+Iceberg files
--   in S3 directly — without needing static AWS credentials.

-- Step 5: Verify table access path for vending
SELECT
    SYSTEM$GET_ICEBERG_TABLE_INFORMATION('horizon_demo_db.public.transactions')
    AS table_info;
