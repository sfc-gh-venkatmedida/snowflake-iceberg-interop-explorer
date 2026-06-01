"""
Feature 1: Open Iceberg REST Access via Snowflake Horizon Catalog
Connect PyIceberg to Snowflake Horizon Catalog and query a Snowflake-managed Iceberg table.

Prerequisites:
  pip install pyiceberg[rest] pandas

Auth: Snowflake OAuth / keypair. Set env vars:
  SNOWFLAKE_ACCOUNT   = scb47336
  SNOWFLAKE_USER      = VMEDIDA
  SNOWFLAKE_ROLE      = ACCOUNTADMIN (or horizon_reader_role)
  SNOWFLAKE_TOKEN     = <OAuth token> OR use key-pair (see below)
"""

import os
from pyiceberg.catalog.rest import RestCatalog

HORIZON_ENDPOINT = "https://scb47336.snowflakecomputing.com/polaris/api/catalog"
SNOWFLAKE_ACCOUNT = os.getenv("SNOWFLAKE_ACCOUNT", "scb47336")
SNOWFLAKE_USER    = os.getenv("SNOWFLAKE_USER", "VMEDIDA")
SNOWFLAKE_TOKEN   = os.getenv("SNOWFLAKE_TOKEN")

if not SNOWFLAKE_TOKEN:
    raise EnvironmentError("Set SNOWFLAKE_TOKEN to a valid Snowflake OAuth or session token.")

catalog = RestCatalog(
    name="horizon",
    **{
        "uri":             HORIZON_ENDPOINT,
        "token":           SNOWFLAKE_TOKEN,
        "warehouse":       "horizon_demo_db",
        "header.X-Iceberg-Access-Delegation": "vended-credentials",
    },
)

print("=== Namespaces (databases/schemas) ===")
namespaces = catalog.list_namespaces()
for ns in namespaces:
    print(" ", ns)

print("\n=== Tables in horizon_demo_db.public ===")
tables = catalog.list_tables(("public",))
for tbl in tables:
    print(" ", tbl)

print("\n=== Load and scan transactions table ===")
table = catalog.load_table("public.transactions")
print("Schema:", table.schema())

df = table.scan().to_pandas()
print(df.to_string(index=False))

print("\n=== Filter: COMPLETED transactions only ===")
from pyiceberg.expressions import EqualTo

completed = table.scan(row_filter=EqualTo("status", "COMPLETED")).to_pandas()
print(completed[["transaction_id", "customer_id", "amount", "currency", "status"]])
