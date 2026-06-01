"""
Feature 7: Governed Multi-Engine Access — Same query, same result across engines
Demonstrates that Spark, DuckDB, and Snowflake Python connector all return
identical results from the same Snowflake-managed Iceberg table.

Set env vars:
  SNOWFLAKE_TOKEN         = <OAuth token for Spark/DuckDB>
  SNOWFLAKE_ACCOUNT       = scb47336
  SNOWFLAKE_USER          = VMEDIDA
  SNOWFLAKE_PRIVATE_KEY_PATH = rsa_key.p8 (for connector)
"""

import os
import pandas as pd

HORIZON_URI = "https://scb47336.snowflakecomputing.com/polaris/api/catalog"
WAREHOUSE   = "horizon_demo_db"
TOKEN       = os.getenv("SNOWFLAKE_TOKEN")
QUERY       = """
    SELECT currency, COUNT(*) AS txn_count, ROUND(SUM(amount), 2) AS total_amount
    FROM transactions
    WHERE status = 'COMPLETED'
    GROUP BY currency
    ORDER BY total_amount DESC
"""

# ── Engine 1: Snowflake native SQL ───────────────────────────────────────────
import snowflake.connector

sf_conn = snowflake.connector.connect(
    account    = os.getenv("SNOWFLAKE_ACCOUNT", "scb47336"),
    user       = os.getenv("SNOWFLAKE_USER", "VMEDIDA"),
    role       = "ACCOUNTADMIN",
    warehouse  = "COMPUTE_WH",
    database   = "horizon_demo_db",
    schema     = "public",
    authenticator = "externalbrowser",
)
sf_df = pd.read_sql(QUERY.replace("FROM transactions", "FROM horizon_demo_db.public.transactions"), sf_conn)
sf_conn.close()
print("Snowflake native:", sf_df.to_string(index=False))

# ── Engine 2: PySpark via Horizon REST ───────────────────────────────────────
from pyspark.sql import SparkSession

spark = (
    SparkSession.builder.appName("GovernedAccess")
    .config("spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
    .config("spark.sql.catalog.sf",          "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.sf.type",     "rest")
    .config("spark.sql.catalog.sf.uri",      HORIZON_URI)
    .config("spark.sql.catalog.sf.token",    TOKEN)
    .config("spark.sql.catalog.sf.warehouse", WAREHOUSE)
    .config("spark.sql.catalog.sf.header.X-Iceberg-Access-Delegation", "vended-credentials")
    .getOrCreate()
)
spark_df = spark.sql(QUERY.replace("FROM transactions", "FROM sf.public.transactions")).toPandas()
spark.stop()
print("\nSpark via Horizon:", spark_df.to_string(index=False))

# ── Engine 3: DuckDB via Horizon REST ────────────────────────────────────────
import duckdb

conn = duckdb.connect()
conn.execute("INSTALL iceberg; LOAD iceberg;")
conn.execute(f"""
    CREATE OR REPLACE SECRET hs (TYPE ICEBERG_REST, TOKEN '{TOKEN}',
        ENDPOINT '{HORIZON_URI}', WAREHOUSE '{WAREHOUSE}');
""")
conn.execute(f"ATTACH '{HORIZON_URI}' AS h (TYPE ICEBERG_REST, SECRET 'hs');")
duck_df = conn.execute(QUERY.replace("FROM transactions", "FROM h.public.transactions")).fetchdf()
conn.close()
print("\nDuckDB via Horizon:", duck_df.to_string(index=False))

# ── Governance check: all three results match ────────────────────────────────
assert sf_df.equals(spark_df), "Mismatch between Snowflake and Spark!"
assert sf_df.equals(duck_df),  "Mismatch between Snowflake and DuckDB!"
print("\n✓ Governance verified: all three engines return identical results.")
