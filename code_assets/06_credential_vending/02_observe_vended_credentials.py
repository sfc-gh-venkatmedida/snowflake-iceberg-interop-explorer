"""
Feature 6: Credential Vending — observe vended S3 credentials via PyIceberg
When the Horizon Catalog vends credentials, the engine receives ephemeral STS
credentials alongside the table location. This script shows the raw config
returned by Horizon and how PySpark uses it to access S3 directly.

Prerequisites:
  pip install pyiceberg[rest] boto3

Set env vars:
  SNOWFLAKE_TOKEN = <OAuth token>
"""

import os
from pyiceberg.catalog.rest import RestCatalog

HORIZON_URI = "https://scb47336.snowflakecomputing.com/polaris/api/catalog"
WAREHOUSE   = "horizon_demo_db"
TOKEN       = os.getenv("SNOWFLAKE_TOKEN")

catalog = RestCatalog(
    name="horizon",
    **{
        "uri":      HORIZON_URI,
        "token":    TOKEN,
        "warehouse": WAREHOUSE,
        "header.X-Iceberg-Access-Delegation": "vended-credentials",
    },
)

table = catalog.load_table("public.transactions")

print("=== Table location (S3 path owned by Snowflake) ===")
print(table.location())

print("\n=== Vended credentials embedded in catalog config ===")
creds = {
    k: (v[:8] + "..." if "secret" in k.lower() or "token" in k.lower() else v)
    for k, v in table.io.properties.items()
    if k.startswith("s3.")
}
for k, v in creds.items():
    print(f"  {k}: {v}")

print("\n=== Use vended credentials via boto3 (direct S3 verify) ===")
import boto3

s3 = boto3.client(
    "s3",
    region_name         = "us-east-2",
    aws_access_key_id   = table.io.properties.get("s3.access-key-id"),
    aws_secret_access_key = table.io.properties.get("s3.secret-access-key"),
    aws_session_token   = table.io.properties.get("s3.session-token"),
)

location = table.location()
bucket, prefix = location.replace("s3://", "").split("/", 1)
response = s3.list_objects_v2(Bucket=bucket, Prefix=prefix, MaxKeys=10)

print(f"\nS3 objects under {location}:")
for obj in response.get("Contents", []):
    print(f"  {obj['Key']}  ({obj['Size']} bytes)")
