-- =============================================================================
-- Feature 5: Use Existing Snowflake Security Model for Iceberg Interop
-- External engines authenticate using Snowflake users, roles, and key-pair auth.
-- =============================================================================

-- Step 1: Create a dedicated service user for external engine access
CREATE USER IF NOT EXISTS iceberg_svc_user
    DEFAULT_ROLE     = iceberg_svc_role
    DEFAULT_WAREHOUSE = COMPUTE_WH
    MUST_CHANGE_PASSWORD = FALSE
    COMMENT = 'Service user for external Iceberg engine access via Horizon Catalog';

-- Step 2: Create a scoped service role
CREATE ROLE IF NOT EXISTS iceberg_svc_role;
GRANT ROLE iceberg_svc_role TO USER iceberg_svc_user;

-- Step 3: Grant Iceberg table privileges (Horizon honors Snowflake RBAC)
GRANT USAGE ON DATABASE horizon_demo_db    TO ROLE iceberg_svc_role;
GRANT USAGE ON SCHEMA horizon_demo_db.public TO ROLE iceberg_svc_role;

GRANT SELECT          ON TABLE horizon_demo_db.public.transactions TO ROLE iceberg_svc_role;
GRANT INSERT          ON TABLE horizon_demo_db.public.transactions TO ROLE iceberg_svc_role;
GRANT UPDATE          ON TABLE horizon_demo_db.public.transactions TO ROLE iceberg_svc_role;
GRANT DELETE          ON TABLE horizon_demo_db.public.transactions TO ROLE iceberg_svc_role;

-- Step 4: Assign key-pair public key to the service user
--   Generate locally:  openssl genrsa -out rsa_key.p8 2048
--                      openssl rsa -in rsa_key.p8 -pubout -out rsa_key.pub
ALTER USER iceberg_svc_user SET RSA_PUBLIC_KEY = '
MIIBIjANBgkqhkiG9w0BAQEFAAOCAQ8AMIIBCgKCAQEA...
<paste your RSA public key here>
';

-- Step 5: Verify the key pair assignment
DESC USER iceberg_svc_user;

-- Step 6: Scope access further — read-only vs read-write roles
CREATE ROLE IF NOT EXISTS iceberg_reader_role;
CREATE ROLE IF NOT EXISTS iceberg_writer_role;

GRANT USAGE ON DATABASE horizon_demo_db    TO ROLE iceberg_reader_role;
GRANT USAGE ON SCHEMA horizon_demo_db.public TO ROLE iceberg_reader_role;
GRANT SELECT ON TABLE horizon_demo_db.public.transactions TO ROLE iceberg_reader_role;

GRANT ROLE iceberg_reader_role TO ROLE iceberg_writer_role;
GRANT INSERT, UPDATE, DELETE ON TABLE horizon_demo_db.public.transactions
    TO ROLE iceberg_writer_role;

-- Step 7: External engine OAuth scope mapping
--   The Horizon Catalog token scope includes the Snowflake role.
--   Clients set the role in the token request:
--     scope = session:role:iceberg_svc_role
