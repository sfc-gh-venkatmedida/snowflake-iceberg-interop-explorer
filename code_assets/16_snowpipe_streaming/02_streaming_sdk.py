"""
Feature H: Snowpipe Streaming SDK → Iceberg
Uses the Snowflake Ingest SDK to stream rows into an Iceberg table in near real-time.

Prerequisites:
  pip install snowflake-ingest

Set env vars:
  SNOWFLAKE_PRIVATE_KEY_PATH = rsa_key.p8
"""

import os, time, json, uuid
from datetime import datetime, timezone
from snowflake.ingest import SimpleIngestManager
from cryptography.hazmat.backends import default_backend
from cryptography.hazmat.primitives.serialization import load_pem_private_key, \
    Encoding, PrivateFormat, NoEncryption

ACCOUNT   = "scb47336"
USER      = "SNOWPIPE_USER"
PIPE_NAME = "horizon_demo_db.public.events_stream_pipe"
KEY_PATH  = os.getenv("SNOWFLAKE_PRIVATE_KEY_PATH", "rsa_key.p8")

with open(KEY_PATH, "rb") as f:
    private_key = load_pem_private_key(f.read(), password=None, backend=default_backend())
private_key_bytes = private_key.private_bytes(
    encoding=Encoding.DER, format=PrivateFormat.PKCS8, encryption_algorithm=NoEncryption()
)

manager = SimpleIngestManager(
    account      = ACCOUNT,
    host         = f"{ACCOUNT}.snowflakecomputing.com",
    user         = USER,
    pipe         = PIPE_NAME,
    private_key  = private_key_bytes,
)

def generate_event_batch(n=50):
    events = []
    for _ in range(n):
        events.append({
            "event_id":   str(uuid.uuid4()),
            "user_id":    str(uuid.uuid4()),
            "event_type": "click",
            "page":       f"/product/{uuid.uuid4().hex[:8]}",
            "event_ts":   datetime.now(timezone.utc).isoformat(),
            "session_id": str(uuid.uuid4()),
            "region":     "us-west",
        })
    return events

print("Streaming 5 batches of 50 events into Iceberg table...")
for i in range(5):
    batch = generate_event_batch(50)
    staged = manager.ingest_many([json.dumps(e) for e in batch])
    print(f"  Batch {i+1}: {staged}")
    time.sleep(2)

print("Done. Data is now available as an open Iceberg table via Horizon Catalog.")
