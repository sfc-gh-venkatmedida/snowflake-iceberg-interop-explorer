-- =============================================================================
-- Feature 8: Apply + Verify all policies on the Iceberg table
-- =============================================================================

-- Confirm all applied policies
SELECT
    policy_name,
    policy_kind,
    ref_column_name,
    ref_entity_name
FROM table(information_schema.policy_references(
    ref_entity_name  => 'horizon_demo_db.public.transactions',
    ref_entity_domain => 'TABLE'
));

-- Full view of active row-access and masking policies on this account's Iceberg tables
SELECT p.policy_name, p.policy_kind, p.policy_body
FROM snowflake.account_usage.policies p
WHERE p.policy_kind IN ('ROW_ACCESS_POLICY', 'MASKING_POLICY')
  AND p.deleted IS NULL
ORDER BY p.policy_kind, p.policy_name;
