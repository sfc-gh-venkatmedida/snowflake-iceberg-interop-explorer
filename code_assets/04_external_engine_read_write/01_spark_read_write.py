"""
Feature 4: External Engine Read and Write for Snowflake-managed Iceberg v2/v3
PySpark — full read, update (overwrite), and append to Snowflake Horizon Catalog.

Prerequisites:
  pyspark >= 3.5
  jars: iceberg-spark-runtime-3.5_2.12, iceberg-aws-bundle

Set env vars:
  SNOWFLAKE_TOKEN = <OAuth token>
"""

import os
from pyspark.sql import SparkSession
from pyspark.sql.functions import lit, current_timestamp

HORIZON_URI = "https://scb47336.snowflakecomputing.com/polaris/api/catalog"
WAREHOUSE   = "horizon_demo_db"
TOKEN       = os.getenv("SNOWFLAKE_TOKEN")

spark = (
    SparkSession.builder
    .appName("HorizonReadWrite")
    .config("spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
    .config("spark.sql.catalog.sf",          "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.sf.type",     "rest")
    .config("spark.sql.catalog.sf.uri",      HORIZON_URI)
    .config("spark.sql.catalog.sf.token",    TOKEN)
    .config("spark.sql.catalog.sf.warehouse", WAREHOUSE)
    .config("spark.sql.catalog.sf.header.X-Iceberg-Access-Delegation",
            "vended-credentials")
    .config("spark.sql.catalog.sf.s3.region", "us-east-2")
    .getOrCreate()
)
spark.sparkContext.setLogLevel("WARN")

table_ref = "sf.public.transactions"

# ── READ ──────────────────────────────────────────────────────────────────────
print("=== READ: all rows ===")
df = spark.table(table_ref)
df.show(truncate=False)
print(f"Row count: {df.count()}")

# ── APPEND (write new rows) ───────────────────────────────────────────────────
print("\n=== APPEND: insert two new transactions ===")
new_rows = spark.createDataFrame(
    [
        ("txn-006", "cust-D", 999.99,  "USD", "2024-01-16 08:00:00", "COMPLETED", "us-west"),
        ("txn-007", "cust-E", 450.00,  "EUR", "2024-01-16 09:15:00", "PENDING",   "eu-west"),
    ],
    schema=["transaction_id", "customer_id", "amount", "currency",
            "transaction_ts", "status", "region"],
)
new_rows.writeTo(table_ref).append()
print(f"Row count after append: {spark.table(table_ref).count()}")

# ── MERGE / UPSERT ────────────────────────────────────────────────────────────
print("\n=== MERGE: upsert txn-007 status to COMPLETED ===")
spark.sql(f"""
    MERGE INTO {table_ref} AS t
    USING (SELECT 'txn-007' AS transaction_id, 'COMPLETED' AS status) AS src
    ON t.transaction_id = src.transaction_id
    WHEN MATCHED THEN UPDATE SET t.status = src.status
""")
spark.table(table_ref).filter("transaction_id = 'txn-007'").show()

# ── DELETE ────────────────────────────────────────────────────────────────────
print("\n=== DELETE: remove FAILED transactions ===")
spark.sql(f"DELETE FROM {table_ref} WHERE status = 'FAILED'")
print(f"Row count after delete: {spark.table(table_ref).count()}")

# ── TIME TRAVEL (Iceberg snapshots) ─────────────────────────────────────────
print("\n=== TIME TRAVEL: list snapshots ===")
spark.sql(f"SELECT snapshot_id, committed_at, operation FROM {table_ref}.snapshots ORDER BY committed_at").show()

spark.stop()
