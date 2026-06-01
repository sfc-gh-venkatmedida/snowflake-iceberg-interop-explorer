-- =============================================================================
-- Feature 22: Object Tags + Data Classification on Iceberg Tables
-- Apply governance tags, classify PII columns, and enforce masking
-- policies based on classification — all on Iceberg tables.
-- =============================================================================

USE DATABASE horizon_demo_db;
USE SCHEMA public;

-- =============================================================
-- PART 1: Object Tags
-- =============================================================

-- Step 1: Create governance tags
CREATE TAG IF NOT EXISTS data_sensitivity
    ALLOWED_VALUES 'PUBLIC', 'INTERNAL', 'CONFIDENTIAL', 'RESTRICTED';

CREATE TAG IF NOT EXISTS data_domain
    ALLOWED_VALUES 'FINANCIAL', 'PII', 'OPERATIONAL', 'REFERENCE';

CREATE TAG IF NOT EXISTS data_owner
    COMMENT 'Team or person responsible for this data';

-- Step 2: Apply tags to the Iceberg table
ALTER TABLE horizon_demo_db.public.transactions
    SET TAG data_sensitivity = 'CONFIDENTIAL',
            data_domain      = 'FINANCIAL',
            data_owner       = 'data-engineering@company.com';

-- Step 3: Apply column-level tags for PII
ALTER TABLE horizon_demo_db.public.transactions
    MODIFY COLUMN customer_id SET TAG data_sensitivity = 'RESTRICTED', data_domain = 'PII';

ALTER TABLE horizon_demo_db.public.transactions
    MODIFY COLUMN amount SET TAG data_sensitivity = 'CONFIDENTIAL', data_domain = 'FINANCIAL';

-- Step 4: Verify tags
SELECT *
FROM TABLE(information_schema.tag_references(
    'horizon_demo_db.public.transactions', 'TABLE'
));

SELECT *
FROM TABLE(information_schema.tag_references(
    'horizon_demo_db.public.transactions', 'COLUMN'
));

-- =============================================================
-- PART 2: Auto Data Classification
-- =============================================================

-- Step 5: Auto-classify the Iceberg schema for PII detection
SELECT SYSTEM$CLASSIFY('horizon_demo_db.public.transactions',
    {'auto_tag': true}
);

-- Step 6: Check classification results
SELECT column_name, tag_name, tag_value
FROM TABLE(information_schema.tag_references_all_columns(
    'horizon_demo_db.public.transactions', 'table'
));

-- =============================================================
-- PART 3: Tag-Based Masking Policy (governance via tags)
-- =============================================================

-- Step 7: Assign masking policy to all columns tagged as PII
CREATE OR REPLACE MASKING POLICY mask_pii_tagged
    AS (val VARCHAR) RETURNS VARCHAR ->
    CASE
        WHEN CURRENT_ROLE() IN ('ACCOUNTADMIN', 'DATA_STEWARD') THEN val
        WHEN SYSTEM$GET_TAG_ON_CURRENT_COLUMN(
             'horizon_demo_db.public.data_sensitivity') = 'RESTRICTED'
             THEN '*** RESTRICTED ***'
        ELSE val
    END;

-- Step 8: Tag-based masking applies to ALL columns with data_sensitivity = RESTRICTED
-- (customer_id gets masked automatically based on its tag)
SELECT * FROM horizon_demo_db.public.transactions LIMIT 5;

-- Step 9: Monitor tag usage in access history
SELECT
    query_id,
    user_name,
    objects_accessed,
    query_start_time
FROM snowflake.account_usage.access_history
WHERE ARRAY_CONTAINS(
    'TRANSACTIONS'::VARIANT,
    objects_accessed::VARIANT
)
  AND query_start_time >= DATEADD(DAY, -1, CURRENT_TIMESTAMP())
ORDER BY query_start_time DESC;
