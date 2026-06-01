"""
Feature 3: Single Endpoint — connect multiple engines to the same Horizon URI
Demonstrates that Spark, PyIceberg, and DuckDB all use the same single endpoint.

Set env vars:
  SNOWFLAKE_TOKEN = <OAuth token>
"""

import os

HORIZON_URI   = "https://scb47336.snowflakecomputing.com/polaris/api/catalog"
WAREHOUSE     = "horizon_demo_db"
TOKEN         = os.getenv("SNOWFLAKE_TOKEN")
DELEGATION    = "vended-credentials"

# ── Client 1: PyIceberg ────────────────────────────────────────────────────────
from pyiceberg.catalog.rest import RestCatalog

pyiceberg_catalog = RestCatalog(
    name="horizon",
    **{
        "uri":      HORIZON_URI,
        "token":    TOKEN,
        "warehouse": WAREHOUSE,
        "header.X-Iceberg-Access-Delegation": DELEGATION,
    },
)
print("PyIceberg — tables:", pyiceberg_catalog.list_tables(("public",)))

# ── Client 2: PySpark ─────────────────────────────────────────────────────────
from pyspark.sql import SparkSession

spark = (
    SparkSession.builder.appName("HorizonSingleEndpoint")
    .config("spark.sql.extensions",
            "org.apache.iceberg.spark.extensions.IcebergSparkSessionExtensions")
    .config("spark.sql.catalog.snowflake",         "org.apache.iceberg.spark.SparkCatalog")
    .config("spark.sql.catalog.snowflake.type",    "rest")
    .config("spark.sql.catalog.snowflake.uri",     HORIZON_URI)
    .config("spark.sql.catalog.snowflake.token",   TOKEN)
    .config("spark.sql.catalog.snowflake.warehouse", WAREHOUSE)
    .config("spark.sql.catalog.snowflake.header.X-Iceberg-Access-Delegation", DELEGATION)
    .getOrCreate()
)
print("Spark — tables:")
spark.sql("SHOW TABLES IN snowflake.public").show()
spark.stop()

# ── Client 3: DuckDB ──────────────────────────────────────────────────────────
import duckdb

conn = duckdb.connect()
conn.execute("INSTALL iceberg; LOAD iceberg;")
conn.execute(f"""
    CREATE OR REPLACE SECRET horizon_secret (
        TYPE         ICEBERG_REST,
        TOKEN        '{TOKEN}',
        ENDPOINT     '{HORIZON_URI}',
        WAREHOUSE    '{WAREHOUSE}'
    );
""")
conn.execute(f"""
    ATTACH '{HORIZON_URI}' AS horizon_catalog (
        TYPE     ICEBERG_REST,
        SECRET   'horizon_secret'
    );
""")
print("DuckDB — tables:", conn.execute("SHOW ALL TABLES").fetchdf())
conn.close()
