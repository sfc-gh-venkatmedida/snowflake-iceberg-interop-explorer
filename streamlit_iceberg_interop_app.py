import streamlit as st
import pandas as pd
import subprocess
import sys
from pathlib import Path

st.set_page_config(
    page_title="Snowflake Iceberg Interop Explorer",
    layout="wide",
    initial_sidebar_state="expanded",
)

ASSETS_ROOT = Path(__file__).parent / "code_assets"
HORIZON_URI = "https://scb47336.snowflakecomputing.com/polaris/api/catalog"
ACCOUNT_ID  = "SCB47336"

CAPABILITIES = [
    {
        "id":     "01_horizon_rest_access",
        "title":  "1. Open Iceberg REST Access",
        "status": "GA",
        "icon":   "🌐",
        "summary": (
            "Snowflake Horizon Catalog exposes the Apache Iceberg REST Catalog API. "
            "Any engine that speaks the open Iceberg REST protocol can query Snowflake-managed tables "
            "without proprietary connectors."
        ),
        "arch": """
External Engine (Spark / DuckDB / PyIceberg / Trino / ...)
        │
        │  HTTP/S  –  Apache Iceberg REST Catalog Protocol
        ▼
┌─────────────────────────────────────────────────────────┐
│       Snowflake Horizon Catalog (REST endpoint)         │
│  https://scb47336.snowflakecomputing.com/polaris/api/catalog │
└──────────────────────┬──────────────────────────────────┘
                       │
        ┌──────────────┴──────────────┐
        ▼                             ▼
  Iceberg Metadata              Snowflake RBAC
  (table location,              (roles, policies,
   schema, snapshots)            credential vending)
""",
        "files": {
            "SQL — Setup": ("01_horizon_rest_access/01_setup_horizon_catalog.sql", "sql"),
            "Python — PyIceberg": ("01_horizon_rest_access/02_pyiceberg_rest_connect.py", "python"),
        },
        "key_facts": [
            f"Single endpoint per account: `{HORIZON_URI}`",
            "No proprietary connector needed — standard Iceberg REST client",
            "Snowflake-managed Iceberg tables are immediately accessible",
            "GA as of 2024",
        ],
    },
    {
        "id":     "02_polaris_integration",
        "title":  "2. Apache Polaris Integration",
        "status": "GA",
        "icon":   "🐻‍❄️",
        "summary": (
            "Apache Polaris (the open-source catalog that Snowflake Open Catalog is built on) is "
            "integrated into Horizon Catalog. Snowflake can both serve as a Polaris-compatible REST "
            "endpoint AND read tables managed by an external Polaris instance."
        ),
        "arch": """
Direction A — Snowflake as Horizon (Polaris protocol):
  External Spark / Flink  →  Horizon REST endpoint  →  Snowflake Iceberg tables

Direction B — Snowflake reads an external Polaris:
  External Apache Polaris (Docker / any host)
        │  Iceberg REST
        ▼
  Snowflake CATALOG INTEGRATION (CATALOG_SOURCE = POLARIS)
        │
        ▼
  Catalog-Linked Database  →  Snowflake SQL queries
""",
        "files": {
            "SQL — Catalog Integration": ("02_polaris_integration/01_polaris_catalog_integration.sql", "sql"),
            "Python — PySpark config": ("02_polaris_integration/02_spark_polaris_config.py", "python"),
        },
        "key_facts": [
            "CATALOG_SOURCE = POLARIS in CREATE CATALOG INTEGRATION",
            "Catalog-linked database auto-discovers Polaris namespaces as schemas",
            "Same IAM external volume for credential vending",
            "Both directions (read Polaris OR serve as Polaris endpoint) supported",
        ],
    },
    {
        "id":     "03_single_endpoint",
        "title":  "3. Single Endpoint",
        "status": "GA",
        "icon":   "🔗",
        "summary": (
            "External engines connect to a single Horizon Catalog endpoint per Snowflake account. "
            "No per-database URIs. The `warehouse` parameter in the catalog config selects the database."
        ),
        "arch": f"""
One URI:  {HORIZON_URI}
           │
           ├── warehouse=horizon_demo_db  →  SELECT * FROM public.transactions
           ├── warehouse=fgac_iceberg_db  →  SELECT * FROM fgac_schema.patients
           └── warehouse=iceberg_glue_db →  SELECT * FROM iceberg_insurance_db.insurance_customers_glue
""",
        "files": {
            "SQL — Endpoint discovery": ("03_single_endpoint/01_endpoint_discovery.sql", "sql"),
            "Python — Multi-engine connect": ("03_single_endpoint/02_multi_engine_connect.py", "python"),
        },
        "key_facts": [
            "SYSTEM$GET_ICEBERG_REST_CATALOG_ENDPOINT() returns the endpoint URL",
            "All Snowflake databases/schemas/tables discoverable from one URI",
            "Engine switches datasets by changing the `warehouse` config value",
        ],
    },
    {
        "id":     "04_external_engine_read_write",
        "title":  "4. External Engine Read + Write",
        "status": "GA",
        "icon":   "✏️",
        "summary": (
            "External engines can read AND write Snowflake-managed Iceberg v2 and v3 tables through "
            "Horizon Catalog. This includes INSERT, MERGE/UPSERT, and row-level DELETE (Iceberg v2 "
            "positional deletes)."
        ),
        "arch": """
External Engine (Spark / DuckDB / PyIceberg)
    │                │
    │ READ           │ WRITE (append / merge / delete)
    ▼                ▼
  Horizon Catalog REST  →  Snowflake-managed Iceberg table
                              (Parquet files in S3 via vended credentials)
""",
        "files": {
            "Python — PySpark read+write": ("04_external_engine_read_write/01_spark_read_write.py", "python"),
            "Python — DuckDB read": ("04_external_engine_read_write/02_duckdb_read.py", "python"),
            "Python — PyIceberg read+write": ("04_external_engine_read_write/03_pyiceberg_read_write.py", "python"),
        },
        "key_facts": [
            "Full DML: INSERT (append), MERGE, DELETE via external engines",
            "Supports Iceberg format v2 (row-level deletes) and v3",
            "Spark uses `writeTo().append()` and `MERGE INTO` syntax",
            "PyIceberg uses `table.append(arrow_table)` and `table.delete(expr)`",
        ],
    },
    {
        "id":     "05_security_model",
        "title":  "5. Existing Snowflake Security Model",
        "status": "GA",
        "icon":   "🔐",
        "summary": (
            "External engines authenticate using existing Snowflake users, roles, and key-pair JWT auth. "
            "No separate identity system. Horizon enforces the caller's Snowflake role when evaluating "
            "object privileges and data policies."
        ),
        "arch": """
External Engine
    │  JWT (key-pair) or OAuth bearer token
    ▼
Snowflake Horizon Catalog
    │  Role: iceberg_svc_role
    ▼
Enforce:  GRANT SELECT ON TABLE ...
          ROW ACCESS POLICY ...
          MASKING POLICY ...
""",
        "files": {
            "SQL — Service role setup": ("05_security_model/01_setup_service_role.sql", "sql"),
            "SQL — Key-pair auth": ("05_security_model/02_keypair_auth.sql", "sql"),
            "Python — Get session token": ("05_security_model/03_get_session_token.py", "python"),
        },
        "key_facts": [
            "Snowflake users + roles = authorization plane for Horizon",
            "Key-pair JWT: generate RSA key, set public key on user, use private key for JWT",
            "Token scope carries the Snowflake role: `session:role:<role_name>`",
            "No new identity system required",
        ],
    },
    {
        "id":     "06_credential_vending",
        "title":  "6. Credential Vending",
        "status": "GA",
        "icon":   "🎟️",
        "summary": (
            "Horizon Catalog vends short-lived AWS STS credentials to external engines alongside the "
            "table location. Engines access S3 directly without needing permanent AWS credentials."
        ),
        "arch": """
External Engine → Horizon REST (with X-Iceberg-Access-Delegation: vended-credentials)
                        │
                        │  AssumeRole (IAM)
                        ▼
               Snowflake IAM role on S3
                        │  STS credentials (15-minute TTL)
                        ▼
                  Response includes:
                    s3.access-key-id
                    s3.secret-access-key
                    s3.session-token
                        │
                        ▼
              Engine reads/writes S3 directly
""",
        "files": {
            "SQL — Enable vending": ("06_credential_vending/01_enable_vending.sql", "sql"),
            "Python — Observe credentials": ("06_credential_vending/02_observe_vended_credentials.py", "python"),
        },
        "key_facts": [
            "Header: `X-Iceberg-Access-Delegation: vended-credentials`",
            "Credentials scoped to the table's S3 prefix, not the whole bucket",
            "Short TTL (minutes) — engines refresh automatically",
            "External volume IAM role must allow `sts:AssumeRole` from Snowflake",
        ],
    },
    {
        "id":     "07_governed_multi_engine",
        "title":  "7. Governed Multi-Engine Access",
        "status": "GA",
        "icon":   "🏛️",
        "summary": (
            "Snowflake presents consistent metadata and permissions across all engines. "
            "The same RBAC grants and object definitions visible in native Snowflake SQL "
            "are enforced for every Iceberg REST request through Horizon."
        ),
        "arch": """
Snowflake SQL ──┐
                │
Spark ──────────┤── Horizon Catalog ──► Single authoritative metadata
                │                       + consistent RBAC enforcement
DuckDB ─────────┤
                │
Trino ──────────┘
""",
        "files": {
            "SQL — Governance setup": ("07_governed_multi_engine/01_governance_setup.sql", "sql"),
            "Python — Cross-engine query": ("07_governed_multi_engine/02_cross_engine_query.py", "python"),
        },
        "key_facts": [
            "All engines see the same schema (no schema drift)",
            "Query history in ACCOUNT_USAGE shows external engine accesses",
            "Revoke a Snowflake role → instantly revoked in all engines",
            "Audit trail for compliance across Spark, DuckDB, Trino",
        ],
    },
    {
        "id":     "08_policy_enforcement",
        "title":  "8. Policy Enforcement on Iceberg",
        "status": "GA",
        "icon":   "🛡️",
        "summary": (
            "Row Access Policies and Dynamic Data Masking Policies applied to Iceberg tables in "
            "Snowflake are enforced when those tables are queried through Horizon Catalog from "
            "Apache Spark, DuckDB, and other external engines."
        ),
        "arch": """
Spark query → Horizon REST (role=analyst_us)
    │
    ▼  Snowflake evaluates:
    │  ROW ACCESS POLICY  →  filter rows by region='us-%'
    │  MASKING POLICY     →  hash(customer_id), NULL(amount)
    ▼
Spark receives only the filtered, masked result set
""",
        "files": {
            "SQL — Row access policy": ("08_policy_enforcement/01_row_access_policy.sql", "sql"),
            "SQL — Masking policy": ("08_policy_enforcement/02_masking_policy.sql", "sql"),
            "SQL — Apply + verify": ("08_policy_enforcement/03_apply_policies.sql", "sql"),
            "Python — Spark policy test": ("08_policy_enforcement/04_spark_policy_test.py", "python"),
        },
        "key_facts": [
            "Row access policies filter rows based on CURRENT_ROLE()",
            "Masking policies can hash, NULL, or partially mask columns",
            "Enforced transparently — Spark does not know a policy exists",
            "Same policies apply to Snowflake SQL and all external engines",
        ],
    },
    {
        "id":     "09_supported_engines",
        "title":  "9. Supported External Engines",
        "status": "GA",
        "icon":   "⚙️",
        "summary": (
            "Snowflake Horizon Catalog is compatible with any engine that implements the "
            "Apache Iceberg REST Catalog spec. Validated engines include Spark, Flink, Trino, "
            "DuckDB, Dremio, Doris, PyIceberg, and StarRocks."
        ),
        "arch": """
┌──────────────────────────────────────────────────────────────┐
│           Apache Iceberg REST Catalog Protocol               │
│  https://scb47336.snowflakecomputing.com/polaris/api/catalog │
└──────┬──────┬──────┬──────┬──────┬──────┬──────┬────────────┘
       │      │      │      │      │      │      │
     Spark  Flink  Trino DuckDB Dremio Doris PyIceberg StarRocks
""",
        "files": {
            "Python — Spark": ("09_supported_engines/spark_catalog.py", "python"),
            "SQL — Flink": ("09_supported_engines/flink_catalog.sql", "sql"),
            "Config — Trino": ("09_supported_engines/trino_catalog.properties", "properties"),
            "Python — DuckDB": ("09_supported_engines/duckdb_query.py", "python"),
            "JSON — Dremio": ("09_supported_engines/dremio_catalog.json", "json"),
            "SQL — Doris": ("09_supported_engines/doris_catalog.sql", "sql"),
            "Python — PyIceberg": ("09_supported_engines/pyiceberg_connect.py", "python"),
            "SQL — StarRocks": ("09_supported_engines/starrocks_catalog.sql", "sql"),
        },
        "key_facts": [
            "All engines use the same single Horizon Catalog URI",
            "Bearer token (Snowflake session token) is the auth mechanism",
            "Credential vending header enables direct S3 access",
            "Engine-specific jar/extension may be needed — see each config",
        ],
    },
    {
        "id":     "10_snowflake_storage",
        "title":  "10. Snowflake Storage for Iceberg",
        "status": "Preview",
        "icon":   "🗄️",
        "summary": (
            "Snowflake manages the underlying cloud object storage for Iceberg tables. "
            "No external volume provisioning, no IAM role setup, no S3 bucket management. "
            "The table is still open Iceberg — accessible via Horizon Catalog REST."
        ),
        "arch": """
Customer-managed (traditional):
  You → provision S3 bucket + IAM role + External Volume → CREATE ICEBERG TABLE

Snowflake Storage for Iceberg (new):
  You → CREATE ICEBERG TABLE ... STORAGE_SERIALIZATION_POLICY = COMPATIBLE
  Snowflake manages: storage location, lifecycle, IAM, compaction

Both paths → same Horizon REST endpoint for external engines
""",
        "files": {
            "SQL — Snowflake Storage setup": ("10_snowflake_storage/01_snowflake_managed_storage.sql", "sql"),
        },
        "key_facts": [
            "STORAGE_SERIALIZATION_POLICY = COMPATIBLE is the only extra DDL needed",
            "No EXTERNAL_VOLUME or BASE_LOCATION — Snowflake manages the path",
            "Table is fully open Iceberg — accessible via Horizon REST",
            "Public Preview as of 2024; storage costs billed through Snowflake",
        ],
    },
    {
        "id":     "11_glue_catalog_linked_db",
        "title":  "11. AWS Glue + Catalog-Linked Databases",
        "status": "GA",
        "icon":   "🔌",
        "summary": (
            "Snowflake connects to AWS Glue as an Iceberg REST Catalog. "
            "A catalog-linked database auto-discovers all Glue databases as Snowflake schemas — "
            "no manual table registration. Full DML from Snowflake SQL."
        ),
        "arch": """
AWS Glue Iceberg REST Catalog (us-east-2)
    │  CATALOG_SOURCE = ICEBERG_REST, CATALOG_API_TYPE = AWS_GLUE
    ▼
CREATE CATALOG INTEGRATION glue_iceberg_catalog_int
    │
    ▼
CREATE DATABASE iceberg_glue_db LINKED_CATALOG = (...)
    │  auto-discovers Glue DBs as schemas
    ▼
SELECT * FROM iceberg_glue_db."iceberg_insurance_db"."insurance_customers"
""",
        "files": {
            "SQL — Glue integration + CLD": ("11_glue_catalog_linked_db/01_glue_catalog_integration.sql", "sql"),
            "Python — PyIceberg via Glue": ("11_glue_catalog_linked_db/02_pyiceberg_glue_connect.py", "python"),
        },
        "key_facts": [
            "CATALOG_API_TYPE = AWS_GLUE; CATALOG_NAME = <12-digit AWS account ID>",
            "CATALOG_SOURCE = ICEBERG_REST (not GLUE — Glue speaks Iceberg REST)",
            "ACCESS_DELEGATION_MODE = EXTERNAL_VOLUME_CREDENTIALS reuses IAM role",
            "Glue is case-insensitive — use lowercase + double quotes in SQL",
        ],
    },
    {
        "id":     "12_time_travel",
        "title":  "12. Iceberg Time Travel",
        "status": "GA",
        "icon":   "⏱️",
        "summary": (
            "Snowflake supports time travel on Iceberg tables using snapshot IDs or timestamps. "
            "AT(SNAPSHOT =>) and BEFORE(STATEMENT =>) are Snowflake-native. "
            "External engines access historical snapshots via Iceberg REST snapshot metadata."
        ),
        "arch": """
Iceberg snapshot log:
  snap-001 (t=09:00) → snap-002 (t=09:30) → snap-003 (t=10:00) [current]

Snowflake SQL:
  SELECT * FROM transactions AT(SNAPSHOT => <snap-002-id>)
  SELECT * FROM transactions AT(TIMESTAMP => '2024-01-15 09:15:00')
  SELECT * FROM transactions BEFORE(STATEMENT => <delete_query_id>)

External engines:
  PyIceberg: table.scan(snapshot_id=<id>).to_pandas()
  Spark:     spark.read.option("snapshot-id","<id>").table("sf.public.t")
""",
        "files": {
            "SQL — Time travel queries": ("12_time_travel/01_iceberg_time_travel.sql", "sql"),
        },
        "key_facts": [
            "AT(SNAPSHOT => id) — pinpoint any historical snapshot",
            "AT(TIMESTAMP => ts) — closest snapshot before timestamp",
            "BEFORE(STATEMENT => query_id) — recover from accidental DML",
            "UNDROP TABLE works on Iceberg tables just like regular tables",
        ],
    },
    {
        "id":     "13_table_maintenance",
        "title":  "13. Table Maintenance (OPTIMIZE / REORG)",
        "status": "GA",
        "icon":   "🔧",
        "summary": (
            "External engines (Spark, Flink) create many small Parquet files. "
            "Snowflake's OPTIMIZE compacts them, REORG rewrites with sort order, "
            "and EXPIRE SNAPSHOTS clears old metadata — without downtime."
        ),
        "arch": """
After Spark writes 1000 small files:
  ALTER ICEBERG TABLE ... OPTIMIZE
  → Snowflake merges into fewer, larger Parquet files
  → Query scan time drops dramatically

Partition-targeted compaction:
  ALTER ICEBERG TABLE ... OPTIMIZE WHERE transaction_ts >= DATEADD(DAY,-7,CURRENT_DATE)

Scheduled maintenance:
  ALTER ICEBERG TABLE ... SET AUTO_REFRESH = TRUE
""",
        "files": {
            "SQL — OPTIMIZE / REORG / EXPIRE": ("13_table_maintenance/01_optimize_reorg_expire.sql", "sql"),
        },
        "key_facts": [
            "OPTIMIZE merges small Parquet files — critical after Spark/Flink appends",
            "REORG rewrites files in sort order for better predicate pruning",
            "EXPIRE SNAPSHOTS removes old snapshot metadata to reduce storage cost",
            "Can target specific partitions with WHERE clause to minimize I/O",
        ],
    },
    {
        "id":     "14_schema_evolution",
        "title":  "14. Schema Evolution",
        "status": "GA",
        "icon":   "🔄",
        "summary": (
            "Iceberg supports safe schema evolution: add, rename, drop columns and "
            "change partition specs without rewriting existing Parquet files. "
            "Changes made in Snowflake are immediately visible to all external engines."
        ),
        "arch": """
Snowflake SQL:                      Spark SQL:
ALTER TABLE ... ADD COLUMN ...  ←→  ALTER TABLE ... ADD COLUMNS (...)
ALTER TABLE ... RENAME COLUMN   ←→  ALTER TABLE ... RENAME COLUMN
ALTER TABLE ... DROP COLUMN     ←→  ALTER TABLE ... DROP COLUMN
ALTER ICEBERG TABLE ... SET PARTITION SPEC (new_spec)
  → old files keep old layout, new files use new spec — zero downtime
""",
        "files": {
            "SQL — Schema evolution": ("14_schema_evolution/01_schema_evolution.sql", "sql"),
        },
        "key_facts": [
            "Column adds/drops are metadata-only — no data rewrite",
            "Partition evolution: change spec without rewriting old files",
            "Changes propagate instantly to all engines via Horizon metadata",
            "External engine schema changes (Spark ALTER TABLE) are visible in Snowflake",
        ],
    },
    {
        "id":     "15_competitive_positioning",
        "title":  "15. Competitive Positioning",
        "status": "GA",
        "icon":   "🏆",
        "summary": (
            "Snowflake's Iceberg story vs Databricks Delta (Unity Catalog), AWS Glue/Lake Formation, "
            "Google BigLake, and Microsoft Fabric/OneLake. "
            "Key differentiators: native Snowflake governance, time travel, and true open REST."
        ),
        "arch": """
Platform             | DML    | Time Travel | Policy Enforcement | Open REST | Status
---------------------|--------|-------------|--------------------|-----------|---------
Snowflake + Horizon  | Full   | Native      | RAP + Masking      | Yes       | GA
Databricks + UC      | Full   | Partial     | Unity Catalog only | Yes (new) | GA/caveats
AWS Glue             | Full   | Via IAM     | Lake Formation     | Yes       | GA
Google BigLake       | Read++ | Via IAM     | BigQuery policies  | Yes       | Evolving
MS Fabric OneLake    | Delta  | Via Entra   | Fabric policies    | Partial   | Evolving
""",
        "files": {
            "SQL — Competitive comparison": ("15_competitive_positioning/01_competitive_comparison.sql", "sql"),
        },
        "key_facts": [
            "Databricks: Unity Catalog now supports Iceberg REST but not all engines are native vs federated",
            "AWS Glue: Iceberg REST GA; Snowflake can read AND write Glue-managed tables",
            "Google BigLake: Iceberg REST evolving; metadata latency and write limitations",
            "Microsoft Fabric: primarily Delta Lake; Iceberg REST support is partial",
        ],
    },
    {
        "id":     "16_snowpipe_streaming",
        "title":  "16. Snowpipe Streaming → Iceberg",
        "status": "GA",
        "icon":   "🌊",
        "summary": (
            "Ingest real-time event data directly into Snowflake-managed Iceberg tables "
            "using Snowpipe Streaming (Kafka Connector or SDK). "
            "Streamed data is immediately open Iceberg — readable by external engines."
        ),
        "arch": """
Kafka Topic / Event Stream
    │  Kafka Connector (SNOWPIPE_STREAMING mode) or Ingest SDK
    ▼
Iceberg table in Snowflake
    │  open Iceberg format (Parquet + metadata)
    ▼
Horizon Catalog REST  →  Spark / DuckDB / PyIceberg reads in near-real-time
""",
        "files": {
            "SQL — Streaming table + Kafka config": ("16_snowpipe_streaming/01_streaming_to_iceberg.sql", "sql"),
            "Python — Ingest SDK": ("16_snowpipe_streaming/02_streaming_sdk.py", "python"),
        },
        "key_facts": [
            "Kafka Connector: set snowflake.ingestion.method=SNOWPIPE_STREAMING",
            "snowflake.output.schema.evolution=TRUE enables auto schema evolution on ingest",
            "Latency: seconds-to-minutes for data to appear in Iceberg files",
            "External engines see streamed rows via Horizon REST as soon as files are committed",
        ],
    },
    {
        "id":     "17_dynamic_tables",
        "title":  "17. Dynamic Tables as Iceberg",
        "status": "GA",
        "icon":   "⚡",
        "summary": (
            "CREATE DYNAMIC ICEBERG TABLE incrementally materializes query results "
            "into open Iceberg format. Combines Snowflake's incremental processing "
            "engine with fully open output accessible by any external engine."
        ),
        "arch": """
Source table (raw_transactions)
    │  incremental refresh (TARGET_LAG = '1 hour')
    ▼
DYNAMIC ICEBERG TABLE transactions_daily_agg
    │  open Iceberg format
    ▼
Horizon REST → Spark / DuckDB / Trino reads the aggregated Iceberg table
""",
        "files": {
            "SQL — Dynamic Iceberg Table": ("17_dynamic_tables/01_dynamic_iceberg_table.sql", "sql"),
        },
        "key_facts": [
            "Same DDL as DYNAMIC TABLE but with CATALOG + EXTERNAL_VOLUME or STORAGE_SERIALIZATION_POLICY",
            "TARGET_LAG controls refresh frequency (e.g., '1 hour', '5 minutes')",
            "Chained pipelines: Dynamic Iceberg → Dynamic Iceberg is supported",
            "External engines see fresh aggregated data without managing the pipeline",
        ],
    },
    {
        "id":     "18_partitioning_performance",
        "title":  "18. Partitioning + Performance Tuning",
        "status": "GA",
        "icon":   "🚀",
        "summary": (
            "Iceberg partition transforms (IDENTITY, DAY/MONTH/YEAR, BUCKET, TRUNCATE) "
            "plus sort orders and OPTIMIZE are the primary performance levers. "
            "Proper setup reduces query scan from 100% to <5% of files."
        ),
        "arch": """
Partition transforms:
  IDENTITY(region)         → exact-match pruning
  MONTH(transaction_ts)    → date-range pruning
  BUCKET(16, customer_id)  → hash distribution (high cardinality)
  TRUNCATE(2, currency)    → prefix pruning

Sort order: CLUSTER BY region, transaction_ts
File size: target 128-512 MB per Parquet file (use OPTIMIZE after small-file writes)
""",
        "files": {
            "SQL — Partition transforms + tuning": ("18_partitioning_performance/01_partitioning_transforms.sql", "sql"),
        },
        "key_facts": [
            "PARTITION BY (MONTH(ts), IDENTITY(region)) — most common multi-level pattern",
            "BUCKET(N, col) for high-cardinality join keys (customer_id, order_id)",
            "Partition evolution: ALTER ICEBERG TABLE ... SET PARTITION SPEC — zero downtime",
            "After Spark writes: run OPTIMIZE to merge small files before external reads",
        ],
    },
]

support_rows = [
    {"Capability": "Open Iceberg REST Access",           "Status": "GA",      "Default path": "Horizon REST endpoint",                   "Best for": "Any engine supporting Iceberg REST"},
    {"Capability": "Apache Polaris Integration",          "Status": "GA",      "Default path": "CATALOG_SOURCE=POLARIS or Horizon itself", "Best for": "Open catalog interop story"},
    {"Capability": "Single Endpoint",                     "Status": "GA",      "Default path": "One URI per account",                     "Best for": "Simplifying engine config"},
    {"Capability": "External Engine Read + Write",        "Status": "GA",      "Default path": "Horizon REST + vended credentials",        "Best for": "Open data engineering pipelines"},
    {"Capability": "Existing Security Model",             "Status": "GA",      "Default path": "Snowflake users + roles + key-pair JWT",   "Best for": "Unified governance"},
    {"Capability": "Credential Vending",                  "Status": "GA",      "Default path": "X-Iceberg-Access-Delegation header",       "Best for": "Secure S3 access without static keys"},
    {"Capability": "Governed Multi-Engine Access",        "Status": "GA",      "Default path": "Snowflake RBAC enforced at REST layer",     "Best for": "Compliance across engines"},
    {"Capability": "Policy Enforcement on Iceberg",       "Status": "GA",      "Default path": "RAP + masking evaluated by Horizon",        "Best for": "Row/column-level security for Spark"},
    {"Capability": "Supported External Engines",          "Status": "GA",      "Default path": "Spark, Flink, Trino, DuckDB, Dremio…",      "Best for": "Open lakehouse ecosystem"},
    {"Capability": "Snowflake Storage for Iceberg",       "Status": "Preview", "Default path": "STORAGE_SERIALIZATION_POLICY=COMPATIBLE",  "Best for": "No external volume setup needed"},
    {"Capability": "AWS Glue + Catalog-Linked DBs",       "Status": "GA",      "Default path": "CATALOG_SOURCE=ICEBERG_REST + LINKED_CATALOG", "Best for": "Enterprise AWS Glue integration"},
    {"Capability": "Iceberg Time Travel",                 "Status": "GA",      "Default path": "AT(SNAPSHOT=>) / AT(TIMESTAMP=>)",         "Best for": "Data recovery and historical analysis"},
    {"Capability": "Table Maintenance (OPTIMIZE/REORG)",  "Status": "GA",      "Default path": "ALTER ICEBERG TABLE ... OPTIMIZE",         "Best for": "Post-Spark compaction, performance"},
    {"Capability": "Schema Evolution",                    "Status": "GA",      "Default path": "ALTER TABLE ADD/DROP/RENAME COLUMN",       "Best for": "Evolving schemas without data rewrite"},
    {"Capability": "Competitive Positioning",             "Status": "GA",      "Default path": "Databricks/AWS/GCP/Microsoft comparison",  "Best for": "Customer conversation prep"},
    {"Capability": "Snowpipe Streaming → Iceberg",        "Status": "GA",      "Default path": "Kafka Connector SNOWPIPE_STREAMING mode",  "Best for": "Real-time open Iceberg pipelines"},
    {"Capability": "Dynamic Tables as Iceberg",           "Status": "GA",      "Default path": "CREATE DYNAMIC ICEBERG TABLE",             "Best for": "Incremental pipelines with open output"},
    {"Capability": "Partitioning + Performance Tuning",   "Status": "GA",      "Default path": "PARTITION BY transforms + OPTIMIZE",       "Best for": "Query performance, partition pruning"},
]

engine_rows = [
    {"Engine":      "Apache Spark",   "Iceberg lib": "iceberg-spark-runtime-3.5 + aws-bundle",    "Read": "✅", "Write": "✅", "Credential vending": "✅", "Notes": "Best reference path; full DML via Iceberg REST"},
    {"Engine":      "Apache Flink",   "Iceberg lib": "iceberg-flink-runtime-1.18",                 "Read": "✅", "Write": "✅", "Credential vending": "✅", "Notes": "Streaming insert / CDC to Iceberg"},
    {"Engine":      "Trino",          "Iceberg lib": "Built-in Iceberg connector (≥430)",          "Read": "✅", "Write": "✅", "Credential vending": "✅", "Notes": "catalog.properties file; vended-credentials-enabled=true"},
    {"Engine":      "DuckDB",         "Iceberg lib": "iceberg extension (≥1.1.0)",                 "Read": "✅", "Write": "❌", "Credential vending": "✅", "Notes": "Read-only via REST; excellent for analytics"},
    {"Engine":      "Dremio",         "Iceberg lib": "Native Iceberg REST connector",              "Read": "✅", "Write": "✅", "Credential vending": "✅", "Notes": "ICEBERG_REST type in catalog config"},
    {"Engine":      "Apache Doris",   "Iceberg lib": "Built-in Iceberg catalog (≥2.1)",            "Read": "✅", "Write": "✅", "Credential vending": "✅", "Notes": "CREATE CATALOG ... type='iceberg'"},
    {"Engine":      "PyIceberg",      "Iceberg lib": "pyiceberg[rest] (pure Python)",              "Read": "✅", "Write": "✅", "Credential vending": "✅", "Notes": "No JVM; ideal for notebooks and scripts"},
    {"Engine":      "StarRocks",      "Iceberg lib": "Built-in external catalog (≥3.2)",           "Read": "✅", "Write": "✅", "Credential vending": "✅", "Notes": "CREATE EXTERNAL CATALOG; aws.s3.region required"},
]


def read_asset(rel_path: str) -> str:
    full = ASSETS_ROOT / rel_path
    if full.exists():
        return full.read_text()
    return f"-- File not found: {full}"


def lang_label(ext: str) -> str:
    return {"sql": "sql", "python": "python", "properties": "properties", "json": "json"}.get(ext, "text")


with st.sidebar:
    st.header("Snowflake Iceberg")
    st.caption(f"Horizon endpoint: `{HORIZON_URI}`")
    st.divider()
    st.subheader("Navigate")
    selected_cap = st.radio(
        "Capability",
        [c["title"] for c in CAPABILITIES],
        label_visibility="collapsed",
    )
    st.divider()
    st.subheader("Filters")
    show_arch = st.checkbox("Show architecture diagram", value=True)
    show_key_facts = st.checkbox("Show key facts", value=True)

cap = next(c for c in CAPABILITIES if c["title"] == selected_cap)

overview_tab, code_tab, engines_tab, matrix_tab = st.tabs(
    ["Overview", "Code Assets", "Engine Matrix", "Capability Matrix"]
)

with overview_tab:
    st.title(f"{cap['icon']} {cap['title']}")
    badge_color = {"GA": "green", "Preview": "orange"}.get(cap["status"], "blue")
    st.markdown(f"**Status:** :{badge_color}[{cap['status']}]")
    st.markdown(cap["summary"])

    if show_arch:
        st.subheader("Architecture")
        st.code(cap["arch"], language="text")

    if show_key_facts:
        st.subheader("Key Facts")
        for fact in cap["key_facts"]:
            st.markdown(f"- {fact}")

    c1, c2 = st.columns(2)
    c1.metric("Files in this module", len(cap["files"]))
    c2.metric("Horizon endpoint", "1 per account")

with code_tab:
    st.title(f"{cap['icon']} {cap['title']} — Code Assets")
    st.caption(f"Account: **{ACCOUNT_ID}** · Endpoint: `{HORIZON_URI}`")

    for label, (rel_path, ext) in cap["files"].items():
        with st.expander(f"📄 {label}", expanded=True):
            code = read_asset(rel_path)
            st.code(code, language=lang_label(ext))
            st.caption(f"`code_assets/{rel_path}`")

with engines_tab:
    st.title("External Engine Support Matrix")
    st.caption("All engines connect to the same single Horizon Catalog endpoint.")
    eng_df = pd.DataFrame(engine_rows)
    st.dataframe(eng_df.reset_index(drop=True), use_container_width=True)

    st.subheader("Engine-specific code")
    engine_files = {
        "Apache Spark":   ("09_supported_engines/spark_catalog.py", "python"),
        "Apache Flink":   ("09_supported_engines/flink_catalog.sql", "sql"),
        "Trino":          ("09_supported_engines/trino_catalog.properties", "properties"),
        "DuckDB":         ("09_supported_engines/duckdb_query.py", "python"),
        "Dremio":         ("09_supported_engines/dremio_catalog.json", "json"),
        "Apache Doris":   ("09_supported_engines/doris_catalog.sql", "sql"),
        "PyIceberg":      ("09_supported_engines/pyiceberg_connect.py", "python"),
        "StarRocks":      ("09_supported_engines/starrocks_catalog.sql", "sql"),
    }
    sel_engine = st.selectbox("Engine", list(engine_files.keys()))
    rel, ext = engine_files[sel_engine]
    st.code(read_asset(rel), language=lang_label(ext))
    st.caption(f"`code_assets/{rel}`")

with matrix_tab:
    st.title("Full Capability Matrix")
    df = pd.DataFrame(support_rows)
    st.dataframe(df.reset_index(drop=True), use_container_width=True)

    st.subheader("Demo configuration reference")
    st.code(f"""
# Snowflake account:    {ACCOUNT_ID}
# Horizon endpoint:     {HORIZON_URI}
# External volume:      iceberg_demo_ext_vol
# S3 bucket:            s3://vmedida-iceberg-demo/  (us-east-2)
# IAM role:             arn:aws:iam::913524911227:role/snowflake-iceberg-demo-role
# Glue catalog int:     GLUE_ICEBERG_CATALOG_INT
# Demo database:        horizon_demo_db
# Demo table:           horizon_demo_db.public.transactions
    """, language="text")

    st.subheader("30-second customer talk track")
    st.code(
        "Snowflake's Iceberg strategy is open interoperability without lakehouse complexity. "
        "Horizon Catalog exposes the open Apache Iceberg REST API — the same protocol Apache Polaris implements. "
        "External engines like Spark, Flink, Trino, DuckDB, and PyIceberg connect with a single URI. "
        "Snowflake governs access with existing roles and policies, vends short-lived credentials so engines "
        "never hold static AWS keys, and enforces row-level and column-level policies even when Spark is the engine.",
        language="text",
    )

st.divider()
st.caption(f"Code assets: `{ASSETS_ROOT}`  ·  Notebook: `notebooks/horizon_iceberg_demo.ipynb`")
