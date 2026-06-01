"""
Feature 2: Apache Polaris Integration — PySpark reading/writing through Horizon
Uses the open Apache Iceberg REST protocol that Polaris implements, pointed at
Snowflake's Horizon Catalog endpoint.

Prerequisites:
  spark-submit with:
    org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.7.0
    org.apache.iceberg:iceberg-aws-bundle:1.7.0

Set env vars:
  SNOWFLAKE_ACCOUNT = scb47336
  SNOWFLAKE_USER    = VMEDIDA
  SNOWFLAKE_TOKEN   = <OAuth token>
"""

import os
from pyspark.sql import SparkSession

HORIZON_URI  = "https://scb47336.snowflakecomputing.com/polaris/api/catalog"
WAREHOUSE    = "horizon_demo_db"
TOKEN        = os.getenv("SNOWFLAKE_TOKEN")

spark = (
    SparkSession.builder
    .appName("Polaris-Horizon-Spark")
    .config("spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
    .config("spark.sql.catalog.snowflake",
            "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.snowflake.type",           "rest")
    .config("spark.sql.catalog.snowflake.uri",            HORIZON_URI)
    .config("spark.sql.catalog.snowflake.token",          TOKEN)
    .config("spark.sql.catalog.snowflake.warehouse",      WAREHOUSE)
    .config("spark.sql.catalog.snowflake.header.X-Iceberg-Access-Delegation",
            "vended-credentials")
    .config("spark.sql.catalog.snowflake.s3.region",      "us-east-2")
    .getOrCreate()
)

spark.sparkContext.setLogLevel("WARN")

print("=== Namespaces (Snowflake schemas) ===")
spark.sql("SHOW NAMESPACES IN snowflake").show(truncate=False)

print("=== Tables in public namespace ===")
spark.sql("SHOW TABLES IN snowflake.public").show(truncate=False)

print("=== Read transactions from Horizon ===")
df = spark.table("snowflake.public.transactions")
df.show(truncate=False)
df.printSchema()

print("=== Write new rows to Snowflake-managed Iceberg via Polaris REST ===")
from pyspark.sql.types import StructType, StructField, StringType, DecimalType, TimestampNTZType

new_rows = spark.createDataFrame(
    [
        ("txn-006", "cust-D", 999.99, "USD", "2024-01-16 08:00:00", "COMPLETED", "us-west"),
        ("txn-007", "cust-E", 450.00, "EUR", "2024-01-16 09:15:00", "PENDING",   "eu-west"),
    ],
    schema=["transaction_id", "customer_id", "amount", "currency",
            "transaction_ts", "status", "region"],
)

new_rows.writeTo("snowflake.public.transactions").append()
print("Write complete. Verifying in Spark:")
spark.table("snowflake.public.transactions").count()

spark.stop()
