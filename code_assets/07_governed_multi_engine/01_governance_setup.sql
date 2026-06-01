-- =============================================================================
-- Feature 7: Governed Multi-Engine Access
-- Snowflake presents consistent metadata and permissions across all engines.
-- The same RBAC roles, policies, and object definitions visible in Snowflake
-- are enforced on every Iceberg REST request through Horizon Catalog.
-- =============================================================================

-- Step 1: Create roles for different engine personas
CREATE ROLE IF NOT EXISTS spark_analyst_role;
CREATE ROLE IF NOT EXISTS trino_analyst_role;
CREATE ROLE IF NOT EXISTS duckdb_analyst_role;

-- Step 2: Grant the same governed access to all engine roles
FOR ROLE IN (spark_analyst_role, trino_analyst_role, duckdb_analyst_role)
    GRANT USAGE ON DATABASE horizon_demo_db    TO ROLE IDENTIFIER(:role_name);
-- (Use individual GRANT statements below for compatibility)

GRANT USAGE ON DATABASE horizon_demo_db    TO ROLE spark_analyst_role;
GRANT USAGE ON SCHEMA horizon_demo_db.public TO ROLE spark_analyst_role;
GRANT SELECT ON TABLE horizon_demo_db.public.transactions TO ROLE spark_analyst_role;

GRANT USAGE ON DATABASE horizon_demo_db    TO ROLE trino_analyst_role;
GRANT USAGE ON SCHEMA horizon_demo_db.public TO ROLE trino_analyst_role;
GRANT SELECT ON TABLE horizon_demo_db.public.transactions TO ROLE trino_analyst_role;

GRANT USAGE ON DATABASE horizon_demo_db    TO ROLE duckdb_analyst_role;
GRANT USAGE ON SCHEMA horizon_demo_db.public TO ROLE duckdb_analyst_role;
GRANT SELECT ON TABLE horizon_demo_db.public.transactions TO ROLE duckdb_analyst_role;

-- Step 3: Create service users per engine
CREATE USER IF NOT EXISTS spark_svc   DEFAULT_ROLE = spark_analyst_role   MUST_CHANGE_PASSWORD = FALSE;
CREATE USER IF NOT EXISTS trino_svc   DEFAULT_ROLE = trino_analyst_role   MUST_CHANGE_PASSWORD = FALSE;
CREATE USER IF NOT EXISTS duckdb_svc  DEFAULT_ROLE = duckdb_analyst_role  MUST_CHANGE_PASSWORD = FALSE;

GRANT ROLE spark_analyst_role  TO USER spark_svc;
GRANT ROLE trino_analyst_role  TO USER trino_svc;
GRANT ROLE duckdb_analyst_role TO USER duckdb_svc;

-- Step 4: Prove governance — all engines see the same schema
--   (Snowflake maintains a single authoritative metadata view)
DESCRIBE TABLE horizon_demo_db.public.transactions;

-- Step 5: Audit — which engine accessed what data
SELECT
    query_id,
    user_name,
    role_name,
    query_text,
    start_time,
    query_tag
FROM snowflake.account_usage.query_history
WHERE
    query_text ILIKE '%transactions%'
    AND start_time >= DATEADD(DAY, -1, CURRENT_TIMESTAMP())
ORDER BY start_time DESC
LIMIT 20;
