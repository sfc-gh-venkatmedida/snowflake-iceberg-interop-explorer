"""
Feature 21: Snowpark on Iceberg
Use the native Snowflake Python DataFrame API (Snowpark) to read, transform,
and write Iceberg tables — no external engine, no REST token needed.

This is the Python-native path for data engineers already working in Snowflake.

Run inside a Snowflake Notebook or any Python environment with snowflake-snowpark-python.
"""

from snowflake.snowpark.context import get_active_session
from snowflake.snowpark import functions as F
from snowflake.snowpark.types import StringType, DecimalType, TimestampType

session = get_active_session()

DB     = "horizon_demo_db"
SCHEMA = "public"

# ── READ ─────────────────────────────────────────────────────────────────────
print("=== Snowpark read from Iceberg table ===")
df = session.table(f"{DB}.{SCHEMA}.transactions")
df.printSchema()
df.show(5)

# ── FILTER + SELECT ──────────────────────────────────────────────────────────
print("\n=== Filter: COMPLETED transactions in us-* regions ===")
completed_us = (
    df
    .filter((F.col("STATUS") == "COMPLETED") & F.col("REGION").startswith("us-"))
    .select("TRANSACTION_ID", "CUSTOMER_ID", "AMOUNT", "CURRENCY", "REGION")
)
completed_us.show()

# ── AGGREGATION ──────────────────────────────────────────────────────────────
print("\n=== Aggregation: revenue by currency ===")
agg = (
    df
    .filter(F.col("STATUS") == "COMPLETED")
    .group_by("CURRENCY")
    .agg(
        F.count("TRANSACTION_ID").alias("TXN_COUNT"),
        F.sum("AMOUNT").alias("TOTAL_AMOUNT"),
        F.avg("AMOUNT").alias("AVG_AMOUNT"),
    )
    .sort(F.col("TOTAL_AMOUNT").desc())
)
agg.show()

# ── WRITE (append to Iceberg) ─────────────────────────────────────────────────
print("\n=== Write aggregation result to a new Iceberg table ===")
session.sql(f"""
    CREATE OR REPLACE ICEBERG TABLE {DB}.{SCHEMA}.revenue_by_currency (
        currency      VARCHAR(3),
        txn_count     BIGINT,
        total_amount  DECIMAL(18,2),
        avg_amount    DECIMAL(18,2)
    )
    CATALOG='SNOWFLAKE' EXTERNAL_VOLUME='iceberg_demo_ext_vol'
    BASE_LOCATION='horizon_demo/revenue_by_currency/'
""").collect()

agg.write.mode("append").save_as_table(f"{DB}.{SCHEMA}.revenue_by_currency")
session.table(f"{DB}.{SCHEMA}.revenue_by_currency").show()
print("✓ Written to Iceberg table via Snowpark — open for external engines via Horizon")

# ── SNOWPARK ML ON ICEBERG ────────────────────────────────────────────────────
print("\n=== Snowpark ML feature engineering on Iceberg data ===")
from snowflake.snowpark.functions import stddev, mean, col

stats = df.select(
    mean(col("AMOUNT")).alias("MEAN_AMOUNT"),
    stddev(col("AMOUNT")).alias("STDDEV_AMOUNT"),
).collect()[0]
print(f"Mean: {stats['MEAN_AMOUNT']:.2f}  |  StdDev: {stats['STDDEV_AMOUNT']:.2f}")
