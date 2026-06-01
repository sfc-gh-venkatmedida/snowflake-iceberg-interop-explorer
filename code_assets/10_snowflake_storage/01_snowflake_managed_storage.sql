-- =============================================================================
-- Feature A: Snowflake Storage for Iceberg (Public Preview)
-- Snowflake manages the underlying cloud object storage for Iceberg tables.
-- No external volume provisioning, no IAM role setup, no S3 bucket management.
-- Snowflake owns the storage lifecycle including compaction and maintenance.
-- =============================================================================

-- Step 1: Create an Iceberg table using Snowflake-managed storage
--   STORAGE_SERIALIZATION_POLICY = COMPATIBLE enables Iceberg interop
--   No EXTERNAL_VOLUME or BASE_LOCATION needed
CREATE DATABASE IF NOT EXISTS sf_storage_demo;
CREATE SCHEMA IF NOT EXISTS sf_storage_demo.public;

CREATE OR REPLACE ICEBERG TABLE sf_storage_demo.public.orders (
    order_id        VARCHAR(36),
    customer_id     VARCHAR(36),
    order_date      DATE,
    total_amount    DECIMAL(12, 2),
    status          VARCHAR(20),
    region          VARCHAR(50)
)
    CATALOG                        = 'SNOWFLAKE'
    STORAGE_SERIALIZATION_POLICY   = COMPATIBLE;
--   ^ No EXTERNAL_VOLUME or BASE_LOCATION — Snowflake manages storage

-- Step 2: Insert data — same DML as any Snowflake table
INSERT INTO sf_storage_demo.public.orders VALUES
    ('ord-001', 'cust-A', '2024-01-15', 1250.00, 'SHIPPED',    'us-west'),
    ('ord-002', 'cust-B', '2024-01-16',  320.50, 'PENDING',    'us-east'),
    ('ord-003', 'cust-C', '2024-01-17', 4200.00, 'DELIVERED',  'eu-west'),
    ('ord-004', 'cust-A', '2024-01-18',  875.00, 'PROCESSING', 'us-west'),
    ('ord-005', 'cust-D', '2024-01-19', 2100.00, 'SHIPPED',    'ap-south');

SELECT * FROM sf_storage_demo.public.orders;

-- Step 3: External engines connect via Horizon REST — same as always
--   The Horizon endpoint transparently serves Snowflake-managed storage tables.
--   External engines do NOT need to know whether the storage is customer-managed
--   or Snowflake-managed.
SELECT SYSTEM$GET_ICEBERG_REST_CATALOG_ENDPOINT() AS horizon_endpoint;
SELECT SYSTEM$GET_ICEBERG_TABLE_INFORMATION('sf_storage_demo.public.orders') AS table_info;

-- Step 4: Compare the two storage approaches
-- Customer-managed (External Volume):
--   CREATE ICEBERG TABLE ... EXTERNAL_VOLUME = 'my_ext_vol' BASE_LOCATION = 'prefix/'
--   Requires: S3 bucket, IAM role, external volume object, STORAGE INTEGRATION
--   Customer manages: storage costs, lifecycle policies, bucket permissions
-- Snowflake Storage for Iceberg:
--   CREATE ICEBERG TABLE ... STORAGE_SERIALIZATION_POLICY = COMPATIBLE
--   Requires: nothing extra — just CREATE TABLE
--   Snowflake manages: storage costs billed through Snowflake, lifecycle, compaction

-- Step 5: Grant access for external engines (same as any Iceberg table)
CREATE ROLE IF NOT EXISTS ext_engine_role;
GRANT USAGE ON DATABASE sf_storage_demo    TO ROLE ext_engine_role;
GRANT USAGE ON SCHEMA sf_storage_demo.public TO ROLE ext_engine_role;
GRANT SELECT, INSERT ON TABLE sf_storage_demo.public.orders TO ROLE ext_engine_role;
