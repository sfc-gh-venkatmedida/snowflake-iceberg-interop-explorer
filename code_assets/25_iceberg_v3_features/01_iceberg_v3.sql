-- =============================================================================
-- Feature 25: Iceberg v3 Features
-- Apache Iceberg v3 introduces: row lineage, nanosecond timestamps,
-- default column values, VARIANT type (JSON), and improved delete vectors.
-- Snowflake supports Iceberg v3 tables natively.
-- =============================================================================

-- Step 1: Create an Iceberg v3 table
--   FORMAT_VERSION = 3 is set automatically for tables with v3 features
CREATE OR REPLACE ICEBERG TABLE horizon_demo_db.public.events_v3 (
    event_id        VARCHAR(36),
    user_id         VARCHAR(36),
    event_type      VARCHAR(50),
    event_ts        TIMESTAMP_NTZ(9),           -- nanosecond precision (v3)
    payload         OBJECT,                      -- VARIANT/JSON column (v3)
    tags            ARRAY,                       -- ARRAY type (v3)
    severity        INT    DEFAULT 0,            -- default value (v3)
    is_processed    BOOLEAN DEFAULT FALSE,       -- default value (v3)
    region          VARCHAR(50)
)
    CATALOG         = 'SNOWFLAKE'
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol'
    BASE_LOCATION   = 'horizon_demo/events_v3/';

-- Step 2: Insert with VARIANT/JSON payload and nanosecond timestamp
INSERT INTO horizon_demo_db.public.events_v3
    (event_id, user_id, event_type, event_ts, payload, tags, severity, region)
VALUES
    (
        'evt-001', 'usr-A', 'purchase',
        '2024-01-15 09:30:00.123456789'::TIMESTAMP_NTZ(9),
        OBJECT_CONSTRUCT('product_id','P123','price',99.99,'quantity',2),
        ARRAY_CONSTRUCT('high-value','first-purchase'),
        2, 'us-west'
    ),
    (
        'evt-002', 'usr-B', 'click',
        '2024-01-15 09:30:00.987654321'::TIMESTAMP_NTZ(9),
        OBJECT_CONSTRUCT('page','/product/P456','duration_ms',3200),
        ARRAY_CONSTRUCT('mobile','organic'),
        0, 'eu-west'
    );

-- Step 3: Query semi-structured data in Iceberg v3
SELECT
    event_id,
    event_ts,
    event_ts::TIMESTAMP_NTZ(9)                           AS nanos_precision,
    payload:product_id::VARCHAR                          AS product_id,
    payload:price::DECIMAL(10,2)                         AS price,
    tags[0]::VARCHAR                                     AS first_tag,
    severity,
    is_processed                                         -- default FALSE
FROM horizon_demo_db.public.events_v3
ORDER BY event_ts;

-- Step 4: Iceberg v3 position delete vectors (more efficient than v2 equality deletes)
DELETE FROM horizon_demo_db.public.events_v3 WHERE event_type = 'click';
-- v3 uses position-based delete vectors, reducing write amplification

-- Step 5: Row lineage — track insert/update source (v3 metadata column)
SELECT
    event_id,
    event_type,
    METADATA$FILE_ROW_NUMBER  AS row_num_in_file,
    METADATA$PARTITION_ID     AS partition
FROM horizon_demo_db.public.events_v3;

-- Step 6: Check format version
SELECT
    SYSTEM$GET_ICEBERG_TABLE_INFORMATION('horizon_demo_db.public.events_v3') AS info;
-- Look for "format-version": 3 in the JSON output

-- Step 7: v3 table is accessible via Horizon REST from any engine supporting v3
-- Engines supporting Iceberg v3 (as of 2024):
--   Spark       >= 3.4 with Iceberg 1.5+
--   PyIceberg   >= 0.7
--   Trino       >= 438
--   Flink       >= 1.19
--   DuckDB      >= 1.2 (read-only v3)
SELECT SYSTEM$GET_ICEBERG_REST_CATALOG_ENDPOINT() AS horizon_endpoint;
