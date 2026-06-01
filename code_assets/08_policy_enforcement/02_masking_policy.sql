-- =============================================================================
-- Feature 8: Policy Enforcement — Dynamic Data Masking on Iceberg
-- Masking policies applied to Snowflake-managed Iceberg tables are enforced
-- when the table is queried via Horizon Catalog from external engines.
-- =============================================================================

USE DATABASE horizon_demo_db;
USE SCHEMA public;

-- Step 1: Create a masking policy on the customer_id column
--   ACCOUNTADMIN sees the full value; analysts see a SHA2 hash.
CREATE OR REPLACE MASKING POLICY mask_customer_id AS (val VARCHAR) RETURNS VARCHAR ->
    CASE
        WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN', 'SYSADMIN') THEN val
        ELSE SHA2(val, 256)
    END;

-- Step 2: Create a masking policy on the amount column
--   Finance role sees the full amount; others see NULL.
CREATE OR REPLACE MASKING POLICY mask_amount AS (val DECIMAL(12, 2)) RETURNS DECIMAL(12, 2) ->
    CASE
        WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN', 'FINANCE_ROLE') THEN val
        ELSE NULL
    END;

-- Step 3: Apply masking policies to the Iceberg table columns
ALTER TABLE horizon_demo_db.public.transactions
    MODIFY COLUMN customer_id SET MASKING POLICY mask_customer_id;

ALTER TABLE horizon_demo_db.public.transactions
    MODIFY COLUMN amount SET MASKING POLICY mask_amount;

-- Step 4: Test in Snowflake native SQL
USE ROLE analyst_us;
SELECT transaction_id, customer_id, amount, currency, status
FROM horizon_demo_db.public.transactions;
-- customer_id: SHA2 hash; amount: NULL

USE ROLE accountadmin;
SELECT transaction_id, customer_id, amount, currency, status
FROM horizon_demo_db.public.transactions;
-- customer_id: plain; amount: full value

-- Step 5: Verify policy references
SELECT *
FROM table(information_schema.policy_references(
    policy_name => 'mask_customer_id'
));
