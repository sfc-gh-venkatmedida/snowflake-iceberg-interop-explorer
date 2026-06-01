"""
Feature 4: External Engine Read+Write via PyIceberg
Demonstrates full read, append, and positional delete (v2 row-level deletes)
using PyIceberg against Snowflake Horizon Catalog.

Prerequisites:
  pip install pyiceberg[rest,pyarrow] pandas

Set env vars:
  SNOWFLAKE_TOKEN = <OAuth token>
"""

import os
import pyarrow as pa
from pyiceberg.catalog.rest import RestCatalog
from pyiceberg.expressions import EqualTo, GreaterThan

HORIZON_URI = "https://scb47336.snowflakecomputing.com/polaris/api/catalog"
WAREHOUSE   = "horizon_demo_db"
TOKEN       = os.getenv("SNOWFLAKE_TOKEN")

catalog = RestCatalog(
    name="horizon",
    **{
        "uri":       HORIZON_URI,
        "token":     TOKEN,
        "warehouse": WAREHOUSE,
        "header.X-Iceberg-Access-Delegation": "vended-credentials",
    },
)

table = catalog.load_table("public.transactions")
print("Schema:", table.schema())
print("Current snapshot:", table.current_snapshot())

# ── READ all rows ─────────────────────────────────────────────────────────────
print("\n=== Full scan ===")
df_all = table.scan().to_pandas()
print(df_all.to_string(index=False))

# ── READ with predicate pushdown ──────────────────────────────────────────────
print("\n=== Filter: amount > 500 ===")
df_filtered = table.scan(row_filter=GreaterThan("amount", 500)).to_pandas()
print(df_filtered[["transaction_id", "amount", "currency", "status"]])

# ── APPEND new rows ───────────────────────────────────────────────────────────
print("\n=== Append new rows via PyArrow ===")
schema = table.schema().as_arrow()
new_data = pa.table(
    {
        "transaction_id": ["txn-008", "txn-009"],
        "customer_id":    ["cust-F",  "cust-G"],
        "amount":         [1100.00,    220.50],
        "currency":       ["USD",      "GBP"],
        "transaction_ts": [
            pa.scalar(1705392000000000, type=pa.timestamp("us")),
            pa.scalar(1705395600000000, type=pa.timestamp("us")),
        ],
        "status":         ["COMPLETED", "PENDING"],
        "region":         ["us-east",   "eu-west"],
    }
)
table.append(new_data)
print(f"Row count after append: {table.scan().to_pandas().shape[0]}")

# ── DELETE rows (Iceberg v2 row-level delete) ─────────────────────────────────
print("\n=== Delete PENDING transactions ===")
table.delete(EqualTo("status", "PENDING"))
print(f"Row count after delete: {table.scan().to_pandas().shape[0]}")

# ── SNAPSHOT HISTORY ─────────────────────────────────────────────────────────
print("\n=== Snapshot history ===")
for snap in table.history():
    print(f"  snapshot_id={snap.snapshot_id}  ts={snap.timestamp_ms}  op={snap.summary.get('operation')}")
