"""
Feature 5: Key-Pair Auth — generate a Snowflake OAuth token for Horizon Catalog
The token is passed as the Bearer token in all Iceberg REST calls.

Prerequisites:
  pip install snowflake-connector-python cryptography

Set env vars:
  SNOWFLAKE_PRIVATE_KEY_PATH = /path/to/rsa_key.p8
  SNOWFLAKE_PRIVATE_KEY_PASSPHRASE = <passphrase or empty>
"""

import os
import snowflake.connector
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import (
    load_pem_private_key, Encoding, PrivateFormat, NoEncryption
)

ACCOUNT    = "scb47336"
USER       = "iceberg_svc_user"
ROLE       = "iceberg_svc_role"
WAREHOUSE  = "COMPUTE_WH"
KEY_PATH   = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH", "rsa_key.p8")
PASSPHRASE = os.getenv("SNOWFLAKE_PRIVATE_KEY_PASSPHRASE", "").encode() or None

with open(KEY_PATH, "rb") as f:
    private_key = load_pem_private_key(f.read(), password=PASSPHRASE, backend=default_backend())

private_key_bytes = private_key.private_bytes(
    encoding=Encoding.DER,
    format=PrivateFormat.PKCS8,
    encryption_algorithm=NoEncryption(),
)

conn = snowflake.connector.connect(
    account    = ACCOUNT,
    user       = USER,
    role       = ROLE,
    warehouse  = WAREHOUSE,
    private_key = private_key_bytes,
    authenticator = "snowflake_jwt",
)

token = conn.rest.token
conn.close()

print("Snowflake session token (use as Bearer in Horizon Catalog calls):")
print(token[:80], "...", sep="")

print("\nUsage with PyIceberg:")
print(f"""
from pyiceberg.catalog.rest import RestCatalog
catalog = RestCatalog(
    name="horizon",
    **{{
        "uri":      "https://scb47336.snowflakecomputing.com/polaris/api/catalog",
        "token":    "{token[:30]}...",
        "warehouse": "horizon_demo_db",
        "header.X-Iceberg-Access-Delegation": "vended-credentials",
    }},
)
""")
