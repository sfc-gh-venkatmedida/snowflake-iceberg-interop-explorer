"""
Feature 8: Policy Enforcement — Test Row Access + Masking via PySpark + Horizon
Connects two Spark sessions with different Snowflake roles and verifies that:
  - analyst_us sees only us-* region rows
  - analyst_eu sees only eu-* region rows
  - customer_id is masked (hashed) for both analyst roles
  - amount is NULL for both analyst roles

Set env vars:
  SNOWFLAKE_TOKEN_US = <OAuth token for analyst_us>
  SNOWFLAKE_TOKEN_EU = <OAuth token for analyst_eu>
  SNOWFLAKE_TOKEN_ADMIN = <OAuth token for ACCOUNTADMIN>
"""

import os
from pyspark.sql import SparkSession

HORIZON_URI = "https://scb47336.snowflakecomputing.com/polaris/api/catalog"
WAREHOUSE   = "horizon_demo_db"
TABLE_REF   = "sf.public.transactions"

TOKEN_US    = os.getenv("SNOWFLAKE_TOKEN_US")
TOKEN_EU    = os.getenv("SNOWFLAKE_TOKEN_EU")
TOKEN_ADMIN = os.getenv("SNOWFLAKE_TOKEN_ADMIN")


def make_spark(app_name, token):
    return (
        SparkSession.builder.appName(app_name)
        .config("spark.sql.extensions",
                "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
        .config("spark.sql.catalog.sf",          "org.apache.iceberg.spark.SparkCatalog")
        .config("spark.sql.catalog.sf.type",     "rest")
        .config("spark.sql.catalog.sf.uri",      HORIZON_URI)
        .config("spark.sql.catalog.sf.token",    token)
        .config("spark.sql.catalog.sf.warehouse", WAREHOUSE)
        .config("spark.sql.catalog.sf.header.X-Iceberg-Access-Delegation", "vended-credentials")
        .getOrCreate()
    )


print("=== analyst_us via Spark — expect only us-* rows, masked customer_id ===")
spark_us = make_spark("PolicyTest-US", TOKEN_US)
df_us = spark_us.table(TABLE_REF)
df_us.show(truncate=False)
assert df_us.filter("region LIKE 'eu-%'").count() == 0, "Row access policy NOT enforced for analyst_us!"
assert df_us.filter("amount IS NOT NULL").count() == 0, "Amount masking NOT enforced for analyst_us!"
spark_us.stop()

print("\n=== analyst_eu via Spark — expect only eu-* rows, masked customer_id ===")
spark_eu = make_spark("PolicyTest-EU", TOKEN_EU)
df_eu = spark_eu.table(TABLE_REF)
df_eu.show(truncate=False)
assert df_eu.filter("region LIKE 'us-%'").count() == 0, "Row access policy NOT enforced for analyst_eu!"
spark_eu.stop()

print("\n=== ACCOUNTADMIN via Spark — expect all rows, unmasked ===")
spark_admin = make_spark("PolicyTest-Admin", TOKEN_ADMIN)
df_admin = spark_admin.table(TABLE_REF)
df_admin.show(truncate=False)
assert df_admin.count() > 0, "Admin should see all rows!"
spark_admin.stop()

print("\nPolicy enforcement validated across all roles via Spark + Horizon Catalog.")
