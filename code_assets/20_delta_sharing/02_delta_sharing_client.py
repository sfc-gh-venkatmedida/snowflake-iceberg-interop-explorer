"""
Feature 20: Delta Sharing — Snowflake as CONSUMER
Snowflake consumes Delta Shares from external providers via Catalog-Linked Databases.
This script validates the connection and queries the shared data from Python
using the Snowflake connector (get_active_session in notebooks).

⚠️  POSITIONING NOTE:
Snowflake supports Delta Sharing as a CONSUMER, not as a provider.
Do NOT position Snowflake as serving data out via Delta Sharing protocol.

Prerequisites:
  - A Delta Sharing endpoint + bearer token from the provider (Databricks etc.)
  - Catalog integration 'delta_share_int' created (see 01_delta_sharing_iceberg.sql)
  - Catalog-linked database 'delta_shared_db' created
"""

import snowflake.connector, os

conn = snowflake.connector.connect(
    account       = os.getenv("SNOWFLAKE_ACCOUNT", "scb47336"),
    user          = os.getenv("SNOWFLAKE_USER", "VMEDIDA"),
    role          = "ACCOUNTADMIN",
    warehouse     = "COMPUTE_WH",
    authenticator = "externalbrowser",
)
cur = conn.cursor()

print("=== Delta Share catalog integration status ===")
cur.execute("SELECT SYSTEM$VERIFY_CATALOG_INTEGRATION('delta_share_int')")
print(cur.fetchone()[0])

print("\n=== Schemas auto-discovered from Delta Share ===")
cur.execute("SHOW SCHEMAS IN delta_shared_db")
for row in cur.fetchall():
    print(f"  {row[1]}")

print("\n=== Tables in Delta Share ===")
cur.execute("SHOW ICEBERG TABLES IN delta_shared_db")
for row in cur.fetchall():
    print(f"  {row[1]}.{row[2]}")

print("\n=== Query Delta Shared data from Snowflake SQL ===")
cur.execute("SELECT * FROM delta_shared_db.public.customer_profiles LIMIT 5")
import pandas as pd
df = pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])
print(df.to_string(index=False))

print("\n=== Join Delta Shared data with Snowflake Iceberg table ===")
cur.execute("""
    SELECT s.transaction_id, s.amount, d.customer_segment
    FROM horizon_demo_db.public.transactions s
    JOIN delta_shared_db.public.customer_profiles d
        ON s.customer_id = d.customer_id
    WHERE s.status = 'COMPLETED'
    LIMIT 10
""")
df_join = pd.DataFrame(cur.fetchall(), columns=[d[0] for d in cur.description])
print(df_join.to_string(index=False))

cur.close()
conn.close()
