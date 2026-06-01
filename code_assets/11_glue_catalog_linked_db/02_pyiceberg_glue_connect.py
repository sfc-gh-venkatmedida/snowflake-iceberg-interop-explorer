"""
Feature B+C: AWS Glue IRC — PyIceberg reading Glue-managed Iceberg tables
Connects PyIceberg to the AWS Glue Iceberg REST Catalog directly
(not via Horizon — this is the Glue→external engine path).

Prerequisites:
  pip install pyiceberg[rest] boto3

Set env vars:
  AWS_ACCESS_KEY_ID     = ...
  AWS_SECRET_ACCESS_KEY = ...
  AWS_DEFAULT_REGION    = us-east-2
  AWS_ACCOUNT_ID        = 913524911227
"""

import os
import boto3
from pyiceberg.catalog.rest import RestCatalog

AWS_REGION     = os.getenv("AWS_DEFAULT_REGION", "us-east-2")
AWS_ACCOUNT_ID = os.getenv("AWS_ACCOUNT_ID", "913524911227")
GLUE_URI       = f"https://glue.{AWS_REGION}.amazonaws.com/iceberg"

session = boto3.Session(region_name=AWS_REGION)
credentials = session.get_credentials().get_frozen_credentials()

catalog = RestCatalog(
    name="glue",
    **{
        "uri":              GLUE_URI,
        "warehouse":        AWS_ACCOUNT_ID,
        "rest.sigv4-enabled": "true",
        "rest.sigv4-region": AWS_REGION,
        "rest.sigv4-service": "glue",
        "s3.access-key-id":     credentials.access_key,
        "s3.secret-access-key": credentials.secret_key,
        "s3.session-token":     credentials.token,
        "s3.region":            AWS_REGION,
    },
)

print("=== Glue namespaces (databases) ===")
for ns in catalog.list_namespaces():
    print(" ", ns)
    for tbl in catalog.list_tables(ns):
        print("    →", tbl)

print("\n=== Read insurance_customers from Glue ===")
table = catalog.load_table(("iceberg_insurance_db", "insurance_customers_glue"))
df = table.scan().to_pandas()
print(df.head(5).to_string(index=False))

print("\n=== Append a row to Glue-managed Iceberg ===")
import pyarrow as pa
new_row = pa.table({
    "customer_id": ["cust-glue-001"],
    "name":        ["Test Customer"],
    "region":      ["us-east"],
})
table.append(new_row)
print(f"Row count after append: {table.scan().to_pandas().shape[0]}")
