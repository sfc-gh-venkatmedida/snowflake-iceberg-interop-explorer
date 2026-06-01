"""
Feature 4: External Engine Read via DuckDB
DuckDB queries a Snowflake-managed Iceberg table through Horizon Catalog using
the built-in iceberg extension (DuckDB >= 1.1.0).

Prerequisites:
  pip install duckdb

Set env vars:
  SNOWFLAKE_TOKEN = <OAuth token>
"""

import os
import duckdb

HORIZON_URI = "https://scb47336.snowflakecomputing.com/polaris/api/catalog"
WAREHOUSE   = "horizon_demo_db"
TOKEN       = os.getenv("SNOWFLAKE_TOKEN")

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
    ATTACH '{HORIZON_URI}' AS horizon (
        TYPE    ICEBERG_REST,
        SECRET  'horizon_secret'
    );
""")

print("=== All tables in Horizon catalog ===")
print(conn.execute("SHOW ALL TABLES").fetchdf().to_string(index=False))

print("\n=== Read: full scan of transactions ===")
df = conn.execute("SELECT * FROM horizon.public.transactions ORDER BY transaction_ts").fetchdf()
print(df.to_string(index=False))

print("\n=== Aggregation: total amount by currency ===")
agg = conn.execute("""
    SELECT currency, COUNT(*) AS txn_count, SUM(amount) AS total_amount
    FROM horizon.public.transactions
    GROUP BY currency ORDER BY total_amount DESC
""").fetchdf()
print(agg.to_string(index=False))

conn.close()
