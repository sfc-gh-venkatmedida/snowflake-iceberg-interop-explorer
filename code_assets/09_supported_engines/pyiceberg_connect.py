"""
Feature 9: PyIceberg — connect to Snowflake Horizon Catalog
Lightweight Python-native Iceberg client; no JVM required.

pip install pyiceberg[rest,pyarrow]

Set env vars:
  SNOWFLAKE_TOKEN = <OAuth token>
"""

import os
from pyiceberg.catalog.rest import RestCatalog

catalog = RestCatalog(
    name="horizon",
    **{
        "uri":      "https://scb47336.snowflakecomputing.com/polaris/api/catalog",
        "token":    os.getenv("SNOWFLAKE_TOKEN"),
        "warehouse": "horizon_demo_db",
        "header.X-Iceberg-Access-Delegation": "vended-credentials",
    },
)

print("Namespaces:", catalog.list_namespaces())
print("Tables:    ", catalog.list_tables(("public",)))

table = catalog.load_table("public.transactions")
print(table.scan().to_pandas())
