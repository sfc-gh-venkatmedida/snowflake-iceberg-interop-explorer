-- =============================================================================
-- Feature 20: Delta Sharing Protocol on Iceberg Tables
-- Snowflake supports Delta Sharing for Iceberg tables — share data with
-- non-Snowflake consumers using an open protocol, no account access needed.
-- Consumers use the Delta Sharing client (Python, Spark, pandas, Power BI).
-- =============================================================================

-- Step 1: Enable Delta Sharing on the account
ALTER ACCOUNT SET DELTA_SHARING_ORGANIZATION_NAME = 'my-snowflake-org';

-- Step 2: Set data retention for sharing
ALTER ACCOUNT SET DELTA_SHARING_REPLICATION_ENABLED = TRUE;

-- Step 3: Create a Delta Share
CREATE SHARE delta_iceberg_share
    COMMENT = 'Open Delta Sharing endpoint for Iceberg transaction data';

-- Step 4: Add Iceberg table to the share
GRANT USAGE ON DATABASE horizon_demo_db        TO SHARE delta_iceberg_share;
GRANT USAGE ON SCHEMA   horizon_demo_db.public  TO SHARE delta_iceberg_share;
GRANT SELECT ON TABLE   horizon_demo_db.public.transactions TO SHARE delta_iceberg_share;

-- Step 5: Create a recipient (a specific external consumer)
CREATE RECIPIENT partner_data_team
    COMMENT = 'Partner analytics team — no Snowflake account needed';

-- Retrieve the activation link / profile JSON for the recipient
DESC RECIPIENT partner_data_team;
-- Gives a profile.share URL that the consumer downloads and uses

-- Step 6: Grant the share to the recipient
ALTER SHARE delta_iceberg_share ADD RECIPIENTS partner_data_team;

-- Step 7: Monitor what consumers accessed
SELECT *
FROM snowflake.account_usage.delta_sharing_usage_history
WHERE share_name = 'DELTA_ICEBERG_SHARE'
  AND request_time >= DATEADD(DAY, -7, CURRENT_TIMESTAMP())
ORDER BY request_time DESC;

-- =============================================================
-- Consumer side (Python — no Snowflake account needed)
-- =============================================================
-- pip install delta-sharing pandas pyarrow
--
-- import delta_sharing
-- client = delta_sharing.SharingClient("profile.share")
-- tables = client.list_all_tables()
-- df = delta_sharing.load_as_pandas("profile.share#delta_iceberg_share.public.transactions")
-- df.head()

-- =============================================================
-- Consumer side (Spark — no Snowflake account needed)
-- =============================================================
-- spark = SparkSession.builder \
--     .config("spark.jars.packages", "io.delta:delta-sharing-spark_2.12:3.0.0") \
--     .getOrCreate()
-- df = spark.read.format("deltaSharing") \
--     .option("responseFormat", "delta") \
--     .load("profile.share#delta_iceberg_share.public.transactions")
-- df.show()
