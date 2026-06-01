-- =============================================================================
-- Feature 8: Policy Enforcement on Iceberg — Row Access Policy
-- Row-level security is enforced by Horizon Catalog on Iceberg tables
-- queried from Apache Spark and other external engines.
-- =============================================================================

USE DATABASE horizon_demo_db;
USE SCHEMA public;

-- Step 1: Add a region column (already present) and a sensitivity flag
--   The transactions table has: transaction_id, customer_id, amount, currency,
--   transaction_ts, status, region

-- Step 2: Create a row access policy
--   Rule: ANALYST_US role only sees us-* region rows.
--         ANALYST_EU role only sees eu-* region rows.
--         SYSADMIN sees all rows.
CREATE OR REPLACE ROW ACCESS POLICY rap_region_filter AS (region_col VARCHAR) RETURNS BOOLEAN ->
    CASE
        WHEN CURRENT_ROLE() = 'ANALYST_US' THEN region_col LIKE 'us-%'
        WHEN CURRENT_ROLE() = 'ANALYST_EU' THEN region_col LIKE 'eu-%'
        WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN', 'SYSADMIN') THEN TRUE
        ELSE FALSE
    END;

-- Step 3: Apply the policy to the Iceberg table
ALTER TABLE horizon_demo_db.public.transactions
    ADD ROW ACCESS POLICY rap_region_filter ON (region);

-- Step 4: Create the analyst roles and grant access
CREATE ROLE IF NOT EXISTS analyst_us;
CREATE ROLE IF NOT EXISTS analyst_eu;

GRANT USAGE ON DATABASE horizon_demo_db     TO ROLE analyst_us;
GRANT USAGE ON SCHEMA horizon_demo_db.public TO ROLE analyst_us;
GRANT SELECT ON TABLE horizon_demo_db.public.transactions TO ROLE analyst_us;

GRANT USAGE ON DATABASE horizon_demo_db     TO ROLE analyst_eu;
GRANT USAGE ON SCHEMA horizon_demo_db.public TO ROLE analyst_eu;
GRANT SELECT ON TABLE horizon_demo_db.public.transactions TO ROLE analyst_eu;

-- Step 5: Test in Snowflake (simulate roles)
USE ROLE analyst_us;
SELECT * FROM horizon_demo_db.public.transactions;  -- only us-* rows

USE ROLE analyst_eu;
SELECT * FROM horizon_demo_db.public.transactions;  -- only eu-* rows

USE ROLE accountadmin;
SELECT * FROM horizon_demo_db.public.transactions;  -- all rows

-- Step 6: Inspect policy binding
SELECT *
FROM table(information_schema.policy_references(
    policy_name => 'rap_region_filter'
));
