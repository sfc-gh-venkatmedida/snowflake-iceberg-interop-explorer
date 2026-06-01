-- =============================================================================
-- Feature H: Snowpipe Streaming → Iceberg Tables
-- Ingest real-time event data directly into Snowflake-managed Iceberg tables
-- using Snowpipe Streaming (Kafka Connector or SDK).
-- =============================================================================

USE DATABASE horizon_demo_db;
USE SCHEMA public;

-- Step 1: Create the Iceberg target table for streaming
CREATE OR REPLACE ICEBERG TABLE horizon_demo_db.public.clickstream (
    record_metadata VARIANT,
    record_content  VARIANT,
    ingested_at     TIMESTAMP_NTZ(6) DEFAULT CURRENT_TIMESTAMP()::TIMESTAMP_NTZ(6)
)
    CATALOG         = 'SNOWFLAKE'
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol'
    BASE_LOCATION   = 'horizon_demo/clickstream/';

-- Step 2: Alternatively, stream into a typed table
CREATE OR REPLACE ICEBERG TABLE horizon_demo_db.public.events_stream (
    event_id    VARCHAR(36),
    user_id     VARCHAR(36),
    event_type  VARCHAR(50),
    page        VARCHAR(200),
    event_ts    TIMESTAMP_NTZ(6),
    session_id  VARCHAR(36),
    region      VARCHAR(50)
)
    CATALOG         = 'SNOWFLAKE'
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol'
    BASE_LOCATION   = 'horizon_demo/events_stream/';

-- Step 3: Configure Kafka Connector (snowflake.conf snippet)
-- snowflake.url.name=scb47336.snowflakecomputing.com
-- snowflake.user.name=SNOWPIPE_USER
-- snowflake.private.key=<base64_encoded_private_key>
-- snowflake.database.name=HORIZON_DEMO_DB
-- snowflake.schema.name=PUBLIC
-- snowflake.topic2table.map=clickstream_topic:clickstream
-- buffer.flush.time=10
-- buffer.count.records=1000
-- snowflake.ingestion.method=SNOWPIPE_STREAMING   -- <-- enables Snowpipe Streaming
-- snowflake.enable.schematization=TRUE
-- snowflake.output.schema.evolution=TRUE           -- <-- auto schema evolution

-- Step 4: Grant Snowpipe Streaming role access
CREATE ROLE IF NOT EXISTS snowpipe_streaming_role;
GRANT USAGE ON DATABASE horizon_demo_db    TO ROLE snowpipe_streaming_role;
GRANT USAGE ON SCHEMA horizon_demo_db.public TO ROLE snowpipe_streaming_role;
GRANT INSERT ON TABLE horizon_demo_db.public.clickstream    TO ROLE snowpipe_streaming_role;
GRANT INSERT ON TABLE horizon_demo_db.public.events_stream  TO ROLE snowpipe_streaming_role;

-- Step 5: Monitor Snowpipe Streaming ingestion lag
SELECT *
FROM TABLE(information_schema.pipe_usage_history(
    DATE_RANGE_START => DATEADD(HOUR, -1, CURRENT_TIMESTAMP()),
    DATE_RANGE_END   => CURRENT_TIMESTAMP()
))
ORDER BY start_time DESC;

-- Step 6: Verify data arrives as an open Iceberg table
SELECT COUNT(*) FROM horizon_demo_db.public.clickstream;
SELECT SYSTEM$GET_ICEBERG_TABLE_INFORMATION('horizon_demo_db.public.clickstream');

-- External engines immediately see streaming data via Horizon:
-- PyIceberg: table = catalog.load_table("public.clickstream"); table.scan().to_pandas()
-- Spark:     spark.table("sf.public.clickstream").show()
