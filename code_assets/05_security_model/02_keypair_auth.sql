-- =============================================================================
-- Feature 5: Key-Pair Authentication for External Engines
-- Snowflake supports key-pair auth for service accounts connecting via
-- Horizon Catalog.  The access token is obtained using the JWT flow.
-- =============================================================================

-- Verify the assigned RSA key for the service user
DESC USER iceberg_svc_user;

-- Test connectivity: generate a session token programmatically via
--   the Snowflake REST API /api/v2/sessions/token-request (KEYPAIR_JWT flow)
--   and then pass it as the Bearer token to the Horizon Catalog endpoint.

-- Confirm the role grants are correct:
SHOW GRANTS TO ROLE iceberg_svc_role;
SHOW GRANTS TO USER iceberg_svc_user;
