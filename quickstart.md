author: Venkat Medida
id: snowflake-iceberg-interop-explorer
summary: A hands-on lab covering all Snowflake Horizon Catalog + Iceberg interoperability capabilities — from open REST access to policy enforcement, time travel, and multi-engine writes.
categories: iceberg,data-engineering,interoperability
environments: web
status: Published
feedback link: https://github.com/YOUR_ORG/snowflake-iceberg-interop-explorer/issues
tags: Iceberg, Horizon Catalog, Spark, DuckDB, PyIceberg, Polaris, Interop

---

# Snowflake Iceberg Interop Explorer
<!-- ============================================================ -->

## Overview
Duration: 5

This quickstart walks through every Snowflake Horizon Catalog + Iceberg interoperability capability with real, runnable code for **18 features**.

### What you'll learn

- How Snowflake exposes Iceberg tables via the open **Horizon Catalog REST** endpoint
- How **Apache Spark, DuckDB, PyIceberg, Trino, Flink** and 4 more engines connect to Snowflake
- How **credential vending** eliminates static AWS credentials for external engines
- How **row access policies and masking policies** are enforced transparently on Spark queries
- How **AWS Glue catalog-linked databases** auto-discover external Iceberg tables
- How **OPTIMIZE, time travel, schema evolution, and Dynamic Iceberg Tables** work
- How Snowflake compares to Databricks, AWS Glue, Google BigLake, and Microsoft Fabric

### What you'll need

- A Snowflake account (any edition)
- An S3 bucket + IAM role for external volume (or use Snowflake Storage for Iceberg)
- Python 3.9+ (for PyIceberg / PySpark examples)
- Snowflake CLI (`pip install snowflake-cli`)

---

## Setup: External Volume + Demo Table
Duration: 5

### Create the external volume (skip if using Snowflake Storage)

```sql
CREATE EXTERNAL VOLUME iceberg_demo_ext_vol
    STORAGE_LOCATIONS = (
        (
            NAME            = 'my-s3-us-east-2'
            STORAGE_PROVIDER = 'S3'
            STORAGE_BASE_URL = 's3://YOUR-BUCKET/iceberg/'
            STORAGE_AWS_ROLE_ARN = 'arn:aws:iam::ACCOUNT_ID:role/snowflake-iceberg-role'
        )
    );
```

### Create demo database and Iceberg table

```sql
CREATE DATABASE IF NOT EXISTS horizon_demo_db;
CREATE SCHEMA IF NOT EXISTS horizon_demo_db.public;

CREATE OR REPLACE ICEBERG TABLE horizon_demo_db.public.transactions (
    transaction_id   VARCHAR(36),
    customer_id      VARCHAR(36),
    amount           DECIMAL(12, 2),
    currency         VARCHAR(3),
    transaction_ts   TIMESTAMP_NTZ(6),
    status           VARCHAR(20),
    region           VARCHAR(50)
)
    CATALOG         = 'SNOWFLAKE'
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol'
    BASE_LOCATION   = 'horizon_demo/transactions/';

INSERT INTO horizon_demo_db.public.transactions VALUES
    ('txn-001', 'cust-A', 1250.00, 'USD', '2024-01-15 09:30:00'::TIMESTAMP_NTZ(6), 'COMPLETED', 'us-west'),
    ('txn-002', 'cust-B',  320.50, 'USD', '2024-01-15 10:15:00'::TIMESTAMP_NTZ(6), 'PENDING',   'us-east'),
    ('txn-003', 'cust-A',  875.00, 'EUR', '2024-01-15 11:00:00'::TIMESTAMP_NTZ(6), 'COMPLETED', 'eu-west'),
    ('txn-004', 'cust-C', 4200.00, 'USD', '2024-01-15 12:45:00'::TIMESTAMP_NTZ(6), 'FAILED',    'us-west'),
    ('txn-005', 'cust-B',  650.75, 'GBP', '2024-01-15 13:30:00'::TIMESTAMP_NTZ(6), 'COMPLETED', 'eu-west');
```

### Get your Horizon Catalog endpoint

```sql
SELECT SYSTEM$GET_ICEBERG_REST_CATALOG_ENDPOINT() AS horizon_endpoint;
-- https://<account>.snowflakecomputing.com/polaris/api/catalog
```

---

## Feature 1: Open Iceberg REST Access
Duration: 5

Snowflake exposes every Iceberg table via the open Apache Iceberg REST Catalog API. No proprietary connector needed.

### Connect with PyIceberg

```bash
pip install pyiceberg[rest] pandas
export SNOWFLAKE_TOKEN=<your_session_token>
```

```python
from pyiceberg.catalog.rest import RestCatalog

catalog = RestCatalog(
    name="horizon",
    **{
        "uri":      "https://<account>.snowflakecomputing.com/polaris/api/catalog",
        "token":    "<SNOWFLAKE_TOKEN>",
        "warehouse": "horizon_demo_db",
        "header.X-Iceberg-Access-Delegation": "vended-credentials",
    },
)

print(catalog.list_namespaces())
table = catalog.load_table("public.transactions")
df = table.scan().to_pandas()
print(df)
```

### What just happened?

- The `uri` is the **single Horizon endpoint** for your entire account
- `token` is a standard Snowflake session token (from key-pair JWT or OAuth)
- `vended-credentials` tells Horizon to include temporary S3 credentials in the response — your Python process reads Parquet files directly from S3 without needing AWS keys

---

## Feature 2: External Engine Read + Write
Duration: 8

### PySpark — full read, append, merge, delete

```bash
pip install pyspark
# Submit with: --packages org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.7.0,org.apache.iceberg:iceberg-aws-bundle:1.7.0
```

```python
from pyspark.sql import SparkSession

spark = (
    SparkSession.builder.appName("HorizonDemo")
    .config("spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
    .config("spark.sql.catalog.sf",          "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.sf.type",     "rest")
    .config("spark.sql.catalog.sf.uri",      "https://<account>.snowflakecomputing.com/polaris/api/catalog")
    .config("spark.sql.catalog.sf.token",    "<SNOWFLAKE_TOKEN>")
    .config("spark.sql.catalog.sf.warehouse", "horizon_demo_db")
    .config("spark.sql.catalog.sf.header.X-Iceberg-Access-Delegation", "vended-credentials")
    .getOrCreate()
)

# READ
spark.table("sf.public.transactions").show()

# APPEND
new_rows = spark.createDataFrame([
    ("txn-006", "cust-D", 999.99, "USD", "2024-01-16 08:00:00", "COMPLETED", "us-west"),
], schema=["transaction_id","customer_id","amount","currency","transaction_ts","status","region"])
new_rows.writeTo("sf.public.transactions").append()

# MERGE (upsert)
spark.sql("""
    MERGE INTO sf.public.transactions t
    USING (SELECT 'txn-006' AS transaction_id, 'FAILED' AS status) s
    ON t.transaction_id = s.transaction_id
    WHEN MATCHED THEN UPDATE SET t.status = s.status
""")

# DELETE
spark.sql("DELETE FROM sf.public.transactions WHERE status = 'FAILED'")
```

### DuckDB — analytics read

```python
import duckdb, os
conn = duckdb.connect()
conn.execute("INSTALL iceberg; LOAD iceberg;")
conn.execute(f"""
    CREATE SECRET hs (TYPE ICEBERG_REST,
        TOKEN '{os.environ["SNOWFLAKE_TOKEN"]}',
        ENDPOINT 'https://<account>.snowflakecomputing.com/polaris/api/catalog',
        WAREHOUSE 'horizon_demo_db');
""")
conn.execute("ATTACH 'https://<account>.snowflakecomputing.com/polaris/api/catalog' AS h (TYPE ICEBERG_REST, SECRET 'hs');")
print(conn.execute("SELECT currency, SUM(amount) FROM h.public.transactions GROUP BY 1").fetchdf())
```

---

## Feature 3: Security Model + Credential Vending
Duration: 5

### Create a service role for external engines

```sql
CREATE USER IF NOT EXISTS iceberg_svc_user DEFAULT_ROLE = iceberg_svc_role MUST_CHANGE_PASSWORD = FALSE;
CREATE ROLE IF NOT EXISTS iceberg_svc_role;
GRANT ROLE iceberg_svc_role TO USER iceberg_svc_user;

GRANT USAGE ON DATABASE horizon_demo_db     TO ROLE iceberg_svc_role;
GRANT USAGE ON SCHEMA horizon_demo_db.public TO ROLE iceberg_svc_role;
GRANT SELECT, INSERT ON TABLE horizon_demo_db.public.transactions TO ROLE iceberg_svc_role;
GRANT USAGE ON EXTERNAL VOLUME iceberg_demo_ext_vol TO ROLE iceberg_svc_role;
```

### How credential vending works

When an external engine calls Horizon with `X-Iceberg-Access-Delegation: vended-credentials`, the response includes:

```json
{
  "config": {
    "s3.access-key-id":     "<temp_key>",
    "s3.secret-access-key": "<temp_secret>",
    "s3.session-token":     "<temp_token>"
  }
}
```

These are short-lived STS credentials scoped to the table's S3 prefix — no static AWS credentials needed in the external engine.

---

## Feature 4: Policy Enforcement on Iceberg
Duration: 8

Policies applied in Snowflake are enforced on Spark queries through Horizon — transparently.

### Row Access Policy

```sql
CREATE OR REPLACE ROW ACCESS POLICY rap_region AS (region_col VARCHAR) RETURNS BOOLEAN ->
    CASE
        WHEN CURRENT_ROLE() = 'ANALYST_US' THEN region_col LIKE 'us-%'
        WHEN CURRENT_ROLE() = 'ANALYST_EU' THEN region_col LIKE 'eu-%'
        ELSE CURRENT_ROLE() = 'ACCOUNTADMIN'
    END;

ALTER TABLE horizon_demo_db.public.transactions
    ADD ROW ACCESS POLICY rap_region ON (region);
```

### Dynamic Masking Policy

```sql
CREATE OR REPLACE MASKING POLICY mask_customer AS (val VARCHAR) RETURNS VARCHAR ->
    CASE WHEN CURRENT_ROLE() = 'ACCOUNTADMIN' THEN val ELSE SHA2(val, 256) END;

ALTER TABLE horizon_demo_db.public.transactions
    MODIFY COLUMN customer_id SET MASKING POLICY mask_customer;
```

### Test via Spark

```python
# Spark session with token for ANALYST_US role
# External engine sees only us-* rows, customer_id is hashed
df = spark.table("sf.public.transactions")
df.show()  # Only us-west and us-east rows; customer_id is SHA2 hash
```

---

## Feature 5: Iceberg Time Travel
Duration: 5

```sql
-- List all snapshots
SELECT * FROM TABLE(information_schema.iceberg_table_history(
    TABLE_NAME => 'transactions', DATABASE_NAME => 'HORIZON_DEMO_DB', SCHEMA_NAME => 'PUBLIC'
)) ORDER BY committed_at DESC;

-- Time travel to a specific snapshot
SELECT * FROM horizon_demo_db.public.transactions AT(SNAPSHOT => 1234567890);

-- Time travel to 1 hour ago
SELECT * FROM horizon_demo_db.public.transactions
    AT(TIMESTAMP => DATEADD(HOUR, -1, CURRENT_TIMESTAMP()));

-- Recover from accidental delete
INSERT INTO horizon_demo_db.public.transactions
    SELECT * FROM horizon_demo_db.public.transactions BEFORE(STATEMENT => LAST_QUERY_ID())
    WHERE status = 'FAILED';
```

**External engines**: PyIceberg uses `table.scan(snapshot_id=<id>)`, Spark uses `.option("snapshot-id", "<id>")`.

---

## Feature 6: Partitioning + Performance
Duration: 5

```sql
-- Multi-level partition: month + region
CREATE OR REPLACE ICEBERG TABLE horizon_demo_db.public.txn_partitioned (...)
    CATALOG = 'SNOWFLAKE'
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol'
    BASE_LOCATION = 'horizon_demo/txn_partitioned/'
    PARTITION BY ( MONTH(transaction_ts), IDENTITY(region) );

-- High-cardinality bucket partition
CREATE OR REPLACE ICEBERG TABLE horizon_demo_db.public.txn_bucketed (...)
    PARTITION BY ( BUCKET(16, customer_id) );

-- Compact small files after Spark writes
ALTER ICEBERG TABLE horizon_demo_db.public.txn_partitioned OPTIMIZE;

-- Partition evolution (zero downtime)
ALTER ICEBERG TABLE horizon_demo_db.public.txn_partitioned
    SET PARTITION SPEC ( YEAR(transaction_ts), IDENTITY(region) );
```

---

## Feature 7: Dynamic Iceberg Tables
Duration: 5

```sql
CREATE OR REPLACE DYNAMIC ICEBERG TABLE horizon_demo_db.public.txn_daily_agg
    TARGET_LAG      = '1 hour'
    WAREHOUSE       = COMPUTE_WH
    CATALOG         = 'SNOWFLAKE'
    EXTERNAL_VOLUME = 'iceberg_demo_ext_vol'
    BASE_LOCATION   = 'horizon_demo/txn_daily_agg/'
AS
    SELECT DATE_TRUNC('day', transaction_ts) AS txn_date, region, currency,
           COUNT(*) AS txn_count, SUM(amount) AS total_amount
    FROM horizon_demo_db.public.transactions
    GROUP BY 1, 2, 3;
```

The result is an **open Iceberg table** refreshed incrementally — any external engine reads it via Horizon.

---

## Feature 8: Supported Engines Quick Reference
Duration: 3

| Engine | Config key | Notes |
|--------|-----------|-------|
| **Spark** | `spark.sql.catalog.X.type=rest` | Full DML; best reference path |
| **Flink** | `'catalog-type'='rest'` | Streaming inserts |
| **Trino** | `iceberg.catalog.type=rest` | `vended-credentials-enabled=true` |
| **DuckDB** | `TYPE ICEBERG_REST` | Read-only via REST |
| **PyIceberg** | `RestCatalog(uri=..., token=...)` | No JVM; Python-native |
| **Dremio** | `"type":"ICEBERG_REST"` | JSON catalog config |
| **Doris** | `'iceberg.catalog.type'='rest'` | `CREATE CATALOG` DDL |
| **StarRocks** | `"iceberg.catalog.rest.uri"` | `CREATE EXTERNAL CATALOG` |

All engines use the **same single URI**: `https://<account>.snowflakecomputing.com/polaris/api/catalog`

---

## Deploy the Interactive App
Duration: 3

Run the full Streamlit app locally or deploy to Snowflake:

```bash
# Clone
git clone https://github.com/YOUR_ORG/snowflake-iceberg-interop-explorer.git
cd snowflake-iceberg-interop-explorer

# Local run
pip install streamlit pandas
streamlit run streamlit_app.py

# Deploy to Snowflake (edit snowflake.yml first)
pip install snowflake-cli
snow streamlit deploy --replace
```

---

## Conclusion
Duration: 2

### What you covered

- **18 Iceberg capabilities** from a single Snowflake Horizon Catalog endpoint
- Open REST access for Spark, DuckDB, Trino, Flink, PyIceberg, Dremio, Doris, StarRocks
- Credential vending, RBAC governance, row-level and column-level policy enforcement
- Time travel, schema evolution, table maintenance, streaming, and Dynamic Iceberg Tables
- Partitioning strategies and performance tuning

### Next steps

- Deploy the Streamlit app to your Snowflake account
- Run the `notebooks/horizon_iceberg_demo.ipynb` end-to-end
- Try connecting your own Spark or Trino cluster using the engine configs in `code_assets/09_supported_engines/`
- Explore [Snowflake Iceberg docs](https://docs.snowflake.com/en/user-guide/tables-iceberg)
