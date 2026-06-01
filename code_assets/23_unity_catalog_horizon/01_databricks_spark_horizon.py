"""
Feature 23: Unity Catalog → Horizon Catalog (Databricks reading Snowflake Iceberg)
Configure Databricks Spark to read Snowflake-managed Iceberg tables
through Snowflake Horizon Catalog using the Iceberg REST protocol.

Prerequisites on Databricks:
  Cluster libraries: org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.7.0
                     org.apache.iceberg:iceberg-aws-bundle:1.7.0

Set env vars on Databricks cluster:
  SNOWFLAKE_ACCOUNT = <account_identifier>
  SNOWFLAKE_TOKEN   = <service_principal_oauth_token>
"""

import os
from pyspark.sql import SparkSession

SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT", "<your_account>")
SNOWFLAKE_TOKEN   = os.getenv("SNOWFLAKE_TOKEN")
HORIZON_URI       = f"https://{SNOWFLAKE_ACCOUNT}.snowflakecomputing.com/polaris/api/catalog"
WAREHOUSE         = "horizon_demo_db"

# Configure Spark to use Snowflake Horizon as an Iceberg REST catalog
spark = (
    SparkSession.builder
    .appName("Databricks-Reads-Snowflake-Iceberg")
    .config("spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
    .config("spark.sql.catalog.snowflake",           "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.snowflake.type",      "rest")
    .config("spark.sql.catalog.snowflake.uri",       HORIZON_URI)
    .config("spark.sql.catalog.snowflake.token",     SNOWFLAKE_TOKEN)
    .config("spark.sql.catalog.snowflake.warehouse", WAREHOUSE)
    .config("spark.sql.catalog.snowflake.header.X-Iceberg-Access-Delegation",
            "vended-credentials")
    .config("spark.sql.catalog.snowflake.s3.region", "us-east-2")
    .getOrCreate()
)

print("=== Databricks Spark reading Snowflake Horizon ===")
print(f"Catalog URI: {HORIZON_URI}")

print("\n=== Namespaces (Snowflake schemas) ===")
spark.sql("SHOW NAMESPACES IN snowflake").show()

print("\n=== Tables ===")
spark.sql("SHOW TABLES IN snowflake.public").show()

print("\n=== Full scan of transactions (Snowflake-managed Iceberg) ===")
df = spark.table("snowflake.public.transactions")
df.printSchema()
df.show(truncate=False)

print("\n=== Databricks writes back to Snowflake Iceberg ===")
new_rows = spark.createDataFrame(
    [("txn-dbx-01", "cust-databricks", 1500.00, "USD",
      "2024-01-20 10:00:00", "COMPLETED", "us-west")],
    schema=["transaction_id","customer_id","amount","currency",
            "transaction_ts","status","region"],
)
new_rows.writeTo("snowflake.public.transactions").append()
print(f"Row count after Databricks write: {spark.table('snowflake.public.transactions').count()}")

spark.stop()
