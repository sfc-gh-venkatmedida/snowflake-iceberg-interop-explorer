"""
Feature 9: Apache Spark — connect to Snowflake Horizon Catalog
Supports full read, append, merge, and delete on Snowflake-managed Iceberg tables.

Set env vars:
  SNOWFLAKE_TOKEN = <OAuth token>

spark-submit --packages \
  org.apache.iceberg:iceberg-spark-runtime-3.5_2.12:1.7.0,\
  org.apache.iceberg:iceberg-aws-bundle:1.7.0 \
  spark_catalog.py
"""

import os
from pyspark.sql import SparkSession

HORIZON_URI = "https://scb47336.snowflakecomputing.com/polaris/api/catalog"
WAREHOUSE   = "horizon_demo_db"
TOKEN       = os.getenv("SNOWFLAKE_TOKEN")

spark = (
    SparkSession.builder
    .appName("Spark-Horizon")
    .config("spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
    .config("spark.sql.catalog.snowflake",
            "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.snowflake.type",     "rest")
    .config("spark.sql.catalog.snowflake.uri",      HORIZON_URI)
    .config("spark.sql.catalog.snowflake.token",    TOKEN)
    .config("spark.sql.catalog.snowflake.warehouse", WAREHOUSE)
    .config("spark.sql.catalog.snowflake.header.X-Iceberg-Access-Delegation",
            "vended-credentials")
    .config("spark.sql.catalog.snowflake.s3.region", "us-east-2")
    .getOrCreate()
)

spark.sql("SHOW NAMESPACES IN snowflake").show()
spark.sql("SHOW TABLES IN snowflake.public").show()
spark.table("snowflake.public.transactions").show(truncate=False)
spark.stop()
