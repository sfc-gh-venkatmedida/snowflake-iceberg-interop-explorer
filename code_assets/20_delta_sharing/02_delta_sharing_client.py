"""
Feature 20: Delta Sharing — Consumer-side Python client
Access Snowflake-managed Iceberg data without a Snowflake account.

Prerequisites:
  pip install delta-sharing pandas pyarrow

The profile.share file is provided by the Snowflake data provider.
It contains the endpoint URL + bearer token for authentication.
"""

import delta_sharing
import pandas as pd

PROFILE_FILE = "profile.share"   # downloaded from Snowflake recipient activation link

client = delta_sharing.SharingClient(PROFILE_FILE)

print("=== Available shares ===")
shares = client.list_shares()
for s in shares:
    print(f"  {s.name}")

print("\n=== Tables in delta_iceberg_share ===")
tables = client.list_all_tables()
for t in tables:
    print(f"  {t.share}.{t.schema}.{t.name}")

print("\n=== Load transactions as pandas DataFrame ===")
df = delta_sharing.load_as_pandas(f"{PROFILE_FILE}#delta_iceberg_share.public.transactions")
print(f"Rows: {len(df)}")
print(df.head())

print("\n=== Aggregation: total by currency ===")
summary = df.groupby("currency").agg(
    txn_count=("transaction_id", "count"),
    total_amount=("amount", "sum")
).reset_index()
print(summary)

print("\n=== Load as PyArrow (zero-copy, columnar) ===")
arrow_table = delta_sharing.load_as_arrow(f"{PROFILE_FILE}#delta_iceberg_share.public.transactions")
print(f"Schema: {arrow_table.schema}")
print(f"Rows: {arrow_table.num_rows}")
