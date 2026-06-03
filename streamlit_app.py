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
        "title":  "2. Horizon Catalog (Polaris-based Implementation)",
        "status": "GA",
        "icon":   "🐻‍❄️",
        "summary": (
            "Apache Polaris is integrated into Snowflake Horizon Catalog — Horizon IS the Polaris-based "
            "implementation. External engines connect TO Horizon using the open Iceberg REST protocol. "
            "Snowflake can also read tables managed by an external Polaris/Open Catalog instance."
        ),
        "arch": """
Horizon Catalog = Polaris-based Iceberg REST endpoint

External engines (Spark/Flink/Trino/DuckDB) → Horizon REST → Snowflake Iceberg tables

Snowflake also reads external Polaris/Open Catalog:
  CATALOG_SOURCE = POLARIS  →  Catalog-Linked DB  →  SQL queries

Key framing: Polaris is the protocol/implementation, Horizon is the customer-facing product.
""",
        "files": {
            "SQL — Catalog Integration": ("02_polaris_integration/01_polaris_catalog_integration.sql", "sql"),
            "Python — PySpark config": ("02_polaris_integration/02_spark_polaris_config.py", "python"),
        },
        "key_facts": [
            "Horizon Catalog IS the Polaris-based open Iceberg REST endpoint — say 'Horizon', not 'Polaris' to customers",
            "Polaris is the open-source implementation; Horizon is the Snowflake product",
            "External engines use standard Iceberg REST — no Polaris-specific client needed",
            "Snowflake can also read from external Polaris/Open Catalog instances via CATALOG_SOURCE = POLARIS",
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
        "title":  "11. Catalog Federation / Catalog-Linked Databases",
        "status": "GA",
        "icon":   "🔌",
        "summary": (
            "Snowflake connects to external Iceberg REST catalogs (AWS Glue, Unity Catalog, "
            "Apache Polaris, Microsoft OneLake) via catalog-linked databases that "
            "auto-discover namespaces and tables. No manual table registration. Full DML from Snowflake SQL."
        ),
        "arch": """
External Catalog (Glue / Unity Catalog / Polaris / OneLake)
    │  Iceberg REST
    ▼
CREATE CATALOG INTEGRATION <name>  (CATALOG_SOURCE = ICEBERG_REST or POLARIS)
    │
    ▼
CREATE DATABASE <db> LINKED_CATALOG = (...) EXTERNAL_VOLUME = ...
    │  auto-discovers: namespaces → schemas, tables → queryable tables
    ▼
SELECT / INSERT / UPDATE / DELETE from external Iceberg tables in Snowflake SQL
ALTER DATABASE <db> REFRESH  ← sync new tables from external catalog
""",
        "files": {
            "SQL — Supported external catalogs": ("27_supported_external_catalogs/01_catalog_integrations.sql", "sql"),
            "SQL — AWS Glue example": ("11_glue_catalog_linked_db/01_glue_catalog_integration.sql", "sql"),
            "SQL — Auto table discovery": ("29_auto_table_discovery/01_auto_discovery_cld.sql", "sql"),
            "SQL — OneLake REST": ("28_onelake_rest_catalog/01_onelake_catalog_integration.sql", "sql"),
        },
        "key_facts": [
            "Supported external catalogs: AWS Glue, Databricks Unity Catalog, Apache Polaris/Open Catalog, Microsoft OneLake",
            "Catalog-linked DBs auto-discover ALL namespaces/tables — no manual CREATE TABLE needed",
            "ALTER DATABASE ... REFRESH syncs new tables added to the external catalog",
            "⚠\ufe0f Private connectivity caveat: catalog-vended credentials NOT supported over PrivateLink (use external volume for data access)",
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
        "title":  "13. Automated Table Maintenance",
        "status": "GA",
        "icon":   "🔧",
        "summary": (
            "For Snowflake-managed Iceberg tables, Snowflake handles maintenance automatically "
            "(compaction, snapshot lifecycle, manifest optimization). "
            "Manual OPTIMIZE is only needed when external engines (Spark, Flink) write to the table "
            "and leave many small files that Snowflake's auto-maintenance does not cover."
        ),
        "arch": """
Snowflake-only writes:   automatic maintenance — nothing to do
Spark/Flink writes:      Spark leaves small files → manual OPTIMIZE needed

Manual OPTIMIZE (only for external-engine writes):
  ALTER ICEBERG TABLE ... OPTIMIZE WHERE ts >= DATEADD(DAY,-7,CURRENT_DATE)

Automatic maintenance (Snowflake-managed tables):
  Compaction, snapshot expiry, manifest optimization — handled by Snowflake

Schedule for mixed workloads (Snowflake + Spark):
  CREATE TASK optimize_task SCHEDULE='0 */4 * * *' AS
    ALTER ICEBERG TABLE ... OPTIMIZE WHERE ts >= DATEADD(HOUR,-6,CURRENT_TIMESTAMP())
""",
        "files": {
            "SQL — OPTIMIZE / REORG / EXPIRE": ("13_table_maintenance/01_optimize_reorg_expire.sql", "sql"),
        },
        "key_facts": [
            "Snowflake auto-manages maintenance for Snowflake-only write workloads — no OPTIMIZE needed",
            "OPTIMIZE only needed when Spark/Flink writes create small files",
            "Schedule via Snowflake Tasks, target recent partitions with WHERE clause",
            "EXPIRE SNAPSHOTS on a separate weekly/monthly task schedule",
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
    {
        "id":     "19_secure_data_sharing",
        "title":  "19. Secure Data Sharing for Iceberg",
        "status": "GA",
        "icon":   "🤝",
        "summary": (
            "Share Snowflake-managed Iceberg tables across accounts. "
            "Multi-tenant row isolation uses SYSTEM$CURRENT_ACCOUNT() in row access policies — "
            "each consumer account sees only their own rows, even via Horizon REST."
        ),
        "arch": """
Provider account                       Consumer account(s)
  ICEBERG TABLE transactions      →    SHARED database (live, read-only)
  + ROW ACCESS POLICY                  Snowflake SQL  ← same governance
    (tenant_col = SYSTEM$CURRENT_ACCOUNT())
                                       Horizon REST   ← policy still enforces
                                       External engine (Spark/DuckDB)
""",
        "files": {
            "SQL — Cross-account share + multi-tenant RAP": ("19_secure_data_sharing/01_iceberg_data_sharing.sql", "sql"),
        },
        "key_facts": [
            "CREATE SHARE + GRANT SELECT ON ICEBERG TABLE — same DDL as regular sharing",
            "SYSTEM$CURRENT_ACCOUNT() in RAP = tenant isolation per account",
            "Consumer queries via Snowflake SQL OR Horizon REST — policies always enforce",
            "Reader accounts for external parties with no Snowflake subscription",
        ],
    },
    {
        "id":     "21_snowpark_on_iceberg",
        "title":  "21. Snowpark on Iceberg",
        "status": "GA",
        "icon":   "🐍",
        "summary": (
            "Use the native Snowflake Python DataFrame API (Snowpark) to read, transform, "
            "and write Iceberg tables. No external engine, no REST token — "
            "the simplest Python path for data engineers already in Snowflake."
        ),
        "arch": """
from snowflake.snowpark.context import get_active_session
session = get_active_session()

df = session.table("horizon_demo_db.public.transactions")  # reads Iceberg
agg = df.group_by("CURRENCY").agg(F.sum("AMOUNT"))
agg.write.mode("append").save_as_table("revenue_by_currency")  # writes Iceberg
""",
        "files": {
            "Python — Snowpark read/write/ML": ("21_snowpark_on_iceberg/01_snowpark_iceberg.py", "python"),
        },
        "key_facts": [
            "session.table('iceberg_tbl') reads Iceberg transparently — no special config",
            "write.save_as_table() appends to Iceberg — produces open Parquet + metadata",
            "Snowpark ML feature engineering works directly on Iceberg DataFrames",
            "Pairs with Horizon REST — Snowpark writes open data; external engines read it",
        ],
    },
    {
        "id":     "22_object_tags_classification",
        "title":  "22. Object Tags + Data Classification",
        "status": "GA",
        "icon":   "🏷️",
        "summary": (
            "Apply governance tags and auto-classify PII columns on Iceberg tables. "
            "Tag-based masking policies enforce automatically on any tagged column — "
            "in Snowflake SQL and through Horizon REST from external engines."
        ),
        "arch": """
CREATE TAG data_sensitivity ALLOWED_VALUES 'PUBLIC','CONFIDENTIAL','RESTRICTED'
ALTER TABLE ... MODIFY COLUMN customer_id SET TAG data_sensitivity = 'RESTRICTED'
CREATE MASKING POLICY mask_restricted ... → applies to ALL RESTRICTED-tagged columns
  ↓
External engine query via Horizon → masked automatically
SYSTEM$CLASSIFY() → auto-detects PII columns and applies tags
""",
        "files": {
            "SQL — Tags, classification, tag-based masking": ("22_object_tags_classification/01_tags_and_classification.sql", "sql"),
        },
        "key_facts": [
            "SYSTEM$CLASSIFY() auto-detects PII (name, email, SSN) and tags columns",
            "Tag-based masking: one policy applies to all RESTRICTED-tagged columns across tables",
            "Tags are inherited by external engines — governance follows data",
            "Access history shows tag access for compliance auditing",
        ],
    },
    {
        "id":     "23_unity_catalog_horizon",
        "title":  "23. Unity Catalog ↔ Horizon Catalog",
        "status": "GA",
        "icon":   "🔄",
        "summary": (
            "Bidirectional integration: Databricks Spark reads Snowflake-managed Iceberg "
            "through Horizon, AND Snowflake reads Databricks Delta tables exposed via "
            "Unity Catalog's Iceberg REST endpoint."
        ),
        "arch": """
Direction A — Databricks reads Snowflake:
  Databricks Spark → Horizon REST endpoint → Snowflake Iceberg tables
  (spark.sql.catalog.snowflake.uri = HORIZON_URI)

Direction B — Snowflake reads Databricks:
  Unity Catalog Iceberg REST endpoint
    → CREATE CATALOG INTEGRATION unity_catalog_int
    → CREATE DATABASE uc_db LINKED_CATALOG = (...)
    → SELECT * FROM uc_db.main.my_delta_table
""",
        "files": {
            "Python — Databricks Spark reading Snowflake": ("23_unity_catalog_horizon/01_databricks_spark_horizon.py", "python"),
            "SQL — Snowflake reading Unity Catalog": ("23_unity_catalog_horizon/02_unity_catalog_integration.sql", "sql"),
        },
        "key_facts": [
            "Databricks uses same Spark Iceberg REST config — no special UC connector needed",
            "Snowflake CATALOG_SOURCE = ICEBERG_REST works for Unity Catalog endpoint",
            "Can JOIN Snowflake Iceberg + Databricks Delta in a single SQL query",
            "Key for 'we have both Databricks and Snowflake' customers",
        ],
    },
    {
        "id":     "24_privatelink_catalog",
        "title":  "24. PrivateLink for Catalog Integrations",
        "status": "GA",
        "icon":   "🔒",
        "summary": (
            "All catalog traffic — Snowflake → Glue, Snowflake ↔ Polaris, "
            "external engines → Horizon — can be routed over AWS/Azure PrivateLink. "
            "No public internet exposure for regulated industries. "
            "⚠\ufe0f Important caveat: catalog-vended credentials are NOT supported over PrivateLink."
        ),
        "arch": """
External Engine → AWS PrivateLink VPC Endpoint → Snowflake Horizon
Snowflake → AWS PrivateLink VPC Endpoint → AWS Glue Iceberg REST
Snowflake → Azure Private Link → Databricks Unity Catalog

⚠\ufe0f  PRIVATE CONNECTIVITY CAVEAT:
  Catalog-VENDED CREDENTIALS are NOT supported when using PrivateLink.
  Credential vending requires Snowflake to make outbound calls to the cloud IAM service,
  which is blocked in PrivateLink-only setups.
  → Solution: configure the external volume separately for data access.
  → The catalog integration handles metadata only over the private link.

Network Policy: restrict Horizon to specific CIDR ranges
""",
        "files": {
            "SQL — PrivateLink catalog integration + network policy": ("24_privatelink_catalog/01_privatelink_setup.sql", "sql"),
        },
        "key_facts": [
            "CATALOG_URI uses private DNS name (VPC endpoint) instead of public URL",
            "Network Rules + External Access Integrations restrict outbound catalog traffic",
            "⚠\ufe0f Catalog-vended credentials NOT supported over PrivateLink — use external volume for data access",
            "Required for HIPAA, FedRAMP, PCI-DSS customers",
        ],
    },
    {
        "id":     "25_iceberg_v3_features",
        "title":  "25. Iceberg v3 Features",
        "status": "GA",
        "icon":   "🆕",
        "summary": (
            "Apache Iceberg v3 introduces nanosecond timestamps, semi-structured VARIANT/JSON columns, "
            "default column values, improved delete vectors, and row lineage. "
            "Snowflake supports Iceberg v3 tables natively."
        ),
        "arch": """
Iceberg v2              →    Iceberg v3
TIMESTAMP_NTZ(6)             TIMESTAMP_NTZ(9)  (nanosecond precision)
No JSON columns              OBJECT, ARRAY, VARIANT columns
No default values            DEFAULT <expr> on column definition
Equality deletes             Position delete vectors (more efficient)
No row lineage               METADATA$FILE_ROW_NUMBER, METADATA$PARTITION_ID
""",
        "files": {
            "SQL — v3 table with VARIANT, nanoseconds, defaults": ("25_iceberg_v3_features/01_iceberg_v3.sql", "sql"),
        },
        "key_facts": [
            "TIMESTAMP_NTZ(9) for nanosecond precision — critical for event/telemetry tables",
            "OBJECT_CONSTRUCT() / ARRAY_CONSTRUCT() stored natively in Iceberg Parquet",
            "DEFAULT values on columns — no need to populate on insert",
            "Engines supporting v3: Spark ≥3.4+Iceberg 1.5, PyIceberg ≥0.7, Trino ≥438",
        ],
    },
    {
        "id":     "26_wif_oidc_auth",
        "title":  "26. WIF / OIDC Authentication for External Engines",
        "status": "GA",
        "icon":   "🔑",
        "summary": (
            "External engines (EMR, Databricks, Dataproc) authenticate to Horizon Catalog "
            "using their native cloud identity (AWS IAM role, Azure Managed Identity, GCP Service Account) — "
            "no static Snowflake tokens, no key rotation. Added with write-support GA release."
        ),
        "arch": """
Static token (old):   EMR → generate JWT → exchange for Snowflake token → pass in config
                      Token expires → restart. Key rotation: manual. Complexity: HIGH.

WIF/OIDC (new):       EMR/Spark → AWS IAM role → OIDC token → Snowflake validates automatically
                      No keys, no rotation, no token management. Complexity: LOW.

Supported identity providers:
  AWS   → IAM role via STS/OIDC
  Azure → Managed Identity or Entra ID service principal
  GCP   → Service Account via GCP OIDC
""",
        "files": {
            "SQL — WIF/OIDC security integration setup": ("26_wif_oidc_auth/01_wif_oidc_setup.sql", "sql"),
        },
        "key_facts": [
            "CREATE SECURITY INTEGRATION TYPE=EXTERNAL_OAUTH maps cloud identity to Snowflake user",
            "Engine uses its existing IAM role — no Snowflake password or JWT needed",
            "Works for AWS EMR, Databricks, GCP Dataproc, Azure ADF",
            "Introduced with external-engine write support GA release",
        ],
    },
    {
        "id":     "27_supported_external_catalogs",
        "title":  "27. Supported External Catalogs",
        "status": "GA",
        "icon":   "📚",
        "summary": (
            "External CATALOGS that Snowflake can federate to (read/write via CLD). "
            "Separate concept from external ENGINES which connect TO Snowflake Horizon. "
            "Supported: AWS Glue, Databricks Unity Catalog, Apache Polaris/Open Catalog, Microsoft OneLake."
        ),
        "arch": """
External CATALOGS (Snowflake reads FROM these via Catalog Federation):
  AWS Glue          → CATALOG_SOURCE=ICEBERG_REST, CATALOG_API_TYPE=AWS_GLUE
  Unity Catalog     → CATALOG_SOURCE=ICEBERG_REST, OAuth (service principal)
  Polaris/Open Cat  → CATALOG_SOURCE=POLARIS, OAuth
  OneLake REST      → CATALOG_SOURCE=ICEBERG_REST, Azure OAuth

External ENGINES (these read FROM Snowflake Horizon):
  Spark / Flink / Trino / DuckDB / PyIceberg / Dremio / Doris / StarRocks

These are two DIFFERENT directions — do not conflate them.
""",
        "files": {
            "SQL — All catalog integrations reference": ("27_supported_external_catalogs/01_catalog_integrations.sql", "sql"),
        },
        "key_facts": [
            "Engines connect TO Horizon; Catalogs are connected FROM Snowflake — opposite directions",
            "AWS Glue: use CATALOG_API_TYPE=AWS_GLUE with SigV4 auth",
            "Unity Catalog: OAuth service principal; storage via UC external locations (not Snowflake vending)",
            "OneLake: Azure OAuth; separate from Fabric JDBC path (which needs a warehouse)",
        ],
    },
    {
        "id":     "28_onelake_rest_catalog",
        "title":  "28. Microsoft OneLake REST Catalog",
        "status": "GA",
        "icon":   "🏢",
        "summary": (
            "Snowflake connects to Microsoft OneLake as an Iceberg REST catalog source via catalog-linked database. "
            "Distinct from the Fabric JDBC path: this uses Iceberg REST, no warehouse needed. "
            "Read OneLake-managed Iceberg tables in Snowflake SQL."
        ),
        "arch": """
Path A (THIS feature): Snowflake reads OneLake via Iceberg REST
  Direction: Snowflake → OneLake  |  Protocol: Iceberg REST  |  Warehouse: NOT needed

Path B (Fabric JDBC): Fabric reads Snowflake via SQL connector
  Direction: Fabric → Snowflake   |  Protocol: JDBC/ODBC     |  Warehouse: REQUIRED
  Docs: docs.snowflake.com/.../tables-iceberg-query-using-microsoft-fabric

⚠️ Private connectivity caveat:
   Catalog-vended credentials NOT supported over PrivateLink.
   Configure external volume separately for data access.
""",
        "files": {
            "SQL — OneLake catalog integration + CLD": ("28_onelake_rest_catalog/01_onelake_catalog_integration.sql", "sql"),
        },
        "key_facts": [
            "OneLake speaks Iceberg REST — connect via CATALOG_SOURCE=ICEBERG_REST",
            "No warehouse needed for metadata/reads — Parquet files accessed directly",
            "Auth: Azure OAuth service principal (Azure app registration)",
            "⚠️ Catalog-vended credentials NOT supported over PrivateLink — use external volume for data",
        ],
    },
    {
        "id":     "29_auto_table_discovery",
        "title":  "29. Automatic Table Discovery + Remote Catalog Sync",
        "status": "GA",
        "icon":   "🔍",
        "summary": (
            "Catalog-linked databases auto-discover ALL namespaces and tables from external catalogs. "
            "No manual table registration. New tables added to the external catalog "
            "appear in Snowflake after ALTER DATABASE ... REFRESH."
        ),
        "arch": """
External catalog adds a new table:
  Glue: CREATE TABLE my_new_table  →  not yet in Snowflake

ALTER DATABASE iceberg_glue_db REFRESH
  →  Snowflake auto-discovers my_new_table
  →  Immediately queryable in Snowflake SQL: SELECT * FROM iceberg_glue_db.public.my_new_table

Behavior:
  New table     → appears after refresh
  Dropped table → disappears after refresh
  Schema change → schema evolution propagated at next refresh
""",
        "files": {
            "SQL — Auto-discovery + CLD sync": ("29_auto_table_discovery/01_auto_discovery_cld.sql", "sql"),
        },
        "key_facts": [
            "ALTER DATABASE ... REFRESH syncs new tables/namespaces from the external catalog",
            "Schema evolution in external catalog propagates to Snowflake automatically at refresh",
            "Scheduled refresh possible via Snowflake Tasks",
            "⚠️ CLDs do not support Snowflake Data Sharing listings — those are separate paths",
        ],
    },
    {
        "id":     "29_bidirectional_write",
        "title":  "29. Bidirectional Write / Concurrent Write Pattern",
        "status": "GA",
        "icon":   "🔄",
        "summary": (
            "Both Snowflake AND external engines (Spark, Flink) write to the same Snowflake-managed "
            "Iceberg table concurrently via Horizon REST. Snowflake handles merge/upsert; "
            "Spark handles high-throughput appends. Both read the latest committed state immediately."
        ),
        "arch": """
Multi-writer architecture:
  Spark/Flink  → Horizon REST (append)  → Iceberg table
  Snowflake    → MERGE / INSERT         → same Iceberg table
  Both readers see latest committed snapshot via OCC

Concurrency model: Optimistic Concurrency Control (OCC) on Iceberg metadata
  Conflict → one writer retries (automatic)
  Best practice: partition by time window OR separate ingestion tables + single-writer merge
""",
        "files": {
            "SQL — Bidirectional write setup + merge + verify": ("29_bidirectional_write/01_bidirectional_write_pattern.sql", "sql"),
        },
        "key_facts": [
            "Snowflake uses OCC on Iceberg metadata — concurrent writes auto-retry on conflict",
            "Best practice: Spark appends raw events, Snowflake handles merge/dedup",
            "OPTIMIZE after Spark appends to compact small files",
            "This is distinct from simple Read+Write — it is a multi-writer production architecture",
        ],
    },
    {
        "id":     "30_auto_refresh_metadata_sync",
        "title":  "30. Auto-Refresh / Metadata Sync for Externally Managed Iceberg",
        "status": "GA",
        "icon":   "🔃",
        "summary": (
            "When Spark/Flink writes new snapshots to an externally managed Iceberg table, "
            "Snowflake must refresh its metadata to see the new data. "
            "AUTO_REFRESH=TRUE polls automatically (default 30s). "
            "Distinct from CLD auto-discovery — this is table-level metadata sync for known tables."
        ),
        "arch": """
Spark writes snapshot → external catalog (Glue) → Snowflake polls → new data visible

AUTO_REFRESH = TRUE  → Snowflake polls catalog on interval (30s default, serverless cost)
Manual REFRESH       → ALTER ICEBERG TABLE ... REFRESH (immediate, on-demand)
Task-triggered       → CREATE TASK ... AS ALTER ICEBERG TABLE ... REFRESH (post-job pattern)

vs CLD auto-discovery (Feature 28):
  CLD           = database-level (new TABLES appear automatically)
  Auto-refresh  = table-level  (new DATA in a known table becomes visible)
""",
        "files": {
            "SQL — Auto-refresh setup + monitoring + Task pattern": ("30_auto_refresh_metadata_sync/01_auto_refresh_externally_managed.sql", "sql"),
        },
        "key_facts": [
            "ALTER ICEBERG TABLE ... SET AUTO_REFRESH = TRUE — no warehouse cost, serverless polling",
            "Default poll interval: 30s — configure REFRESH_INTERVAL_SECONDS on catalog integration",
            "Manual ALTER ... REFRESH for immediate sync after Spark jobs",
            "⚠️ Different from CLD auto-discovery: this is DATA sync, not TABLE discovery",
        ],
    },
    {
        "id":     "31_bcdr_failsafe",
        "title":  "31. BCDR / Fail-Safe / Replication for Snowflake-managed Iceberg",
        "status": "GA",
        "icon":   "🛡️",
        "summary": (
            "Snowflake-managed Iceberg tables get enterprise BCDR automatically: "
            "7-day Fail-safe (non-configurable, ops recovery), "
            "0–90 day Time Travel, and cross-region/cross-cloud Replication. "
            "Key differentiator vs self-managed Iceberg — no equivalent in plain S3/Glue."
        ),
        "arch": """
Snowflake-managed Iceberg:
  Fail-safe   7 days   automatic, Snowflake Support only, non-configurable
  Time Travel 0-90 days  ALTER ICEBERG TABLE ... SET DATA_RETENTION_TIME_IN_DAYS = N
  Replication  cross-region/cloud  CREATE REPLICATION GROUP ... OBJECT_TYPES = DATABASES
  Zero-copy clone  CREATE ICEBERG TABLE t CLONE source AT (TIMESTAMP => ...)

Self-managed Iceberg (Spark + S3 only):
  ❌ No fail-safe  ❌ No built-in replication  ⚠️ Snapshot retention = manual
""",
        "files": {
            "SQL — Fail-safe, Time Travel, Replication, zero-copy clone": ("31_bcdr_failsafe/01_bcdr_failsafe_replication.sql", "sql"),
        },
        "key_facts": [
            "Fail-safe: automatic 7-day protection — no config needed, no SQL access (Snowflake Support only)",
            "Time Travel: 0–90 days on Snowflake-managed Iceberg — CREATE ICEBERG TABLE CLONE for point-in-time recovery",
            "Replication: CREATE REPLICATION GROUP covers Iceberg tables cross-region/cloud",
            "Key differentiator: self-managed Iceberg (Spark/Glue) has none of these built-in",
        ],
    },
]

support_rows = [
    # ── PILLAR 1: Interop Foundations ──────────────────────────────────────
    {"Pillar": "🏗️ Interop Foundations",   "Capability": "Open Iceberg REST Access",          "Status": "GA", "Default path": "Horizon REST endpoint",                    "Best for": "Any engine supporting Iceberg REST"},
    {"Pillar": "🏗️ Interop Foundations",   "Capability": "Horizon Catalog (Polaris-based)",   "Status": "GA", "Default path": "Horizon IS the Polaris implementation",   "Best for": "Open interop — say 'Horizon' not 'Polaris'"},
    {"Pillar": "🏗️ Interop Foundations",   "Capability": "Single Endpoint",                   "Status": "GA", "Default path": "One URI per account",                     "Best for": "Simplifying engine config"},
    # ── PILLAR 2: Access Patterns ──────────────────────────────────────────
    {"Pillar": "⚡ Access Patterns",        "Capability": "External Engine Read via Horizon",  "Status": "GA", "Default path": "Horizon REST + Iceberg catalog config",   "Best for": "Open lakehouse reads from any engine"},
    {"Pillar": "⚡ Access Patterns",        "Capability": "External Engine Write via Horizon", "Status": "GA", "Default path": "Horizon REST write + credential vending", "Best for": "Open lakehouse writes (Spark, Flink)"},
    {"Pillar": "⚡ Access Patterns",        "Capability": "Bidirectional Write Pattern",       "Status": "GA", "Default path": "OCC on Iceberg metadata",                 "Best for": "Spark appends + Snowflake merge on same table"},
    {"Pillar": "⚡ Access Patterns",        "Capability": "Supported External Engines",        "Status": "GA", "Default path": "Spark/Flink/Trino/DuckDB/Dremio/Doris…", "Best for": "Open lakehouse ecosystem"},
    # ── PILLAR 3: Catalog Federation ───────────────────────────────────────
    {"Pillar": "🔌 Catalog Federation",     "Capability": "Catalog Federation / CLD",          "Status": "GA", "Default path": "CREATE DATABASE LINKED_CATALOG",          "Best for": "Federate to Glue/Unity/Polaris/OneLake"},
    {"Pillar": "🔌 Catalog Federation",     "Capability": "Supported External Catalogs",       "Status": "GA", "Default path": "Glue/Unity/Polaris/OneLake REST",         "Best for": "Catalog federation reference guide"},
    {"Pillar": "🔌 Catalog Federation",     "Capability": "OneLake REST Catalog",              "Status": "GA", "Default path": "CATALOG_SOURCE=ICEBERG_REST + Azure OAuth","Best for": "Snowflake ↔ Microsoft Fabric/OneLake"},
    {"Pillar": "🔌 Catalog Federation",     "Capability": "Auto Table Discovery",              "Status": "GA", "Default path": "LINKED_CATALOG + ALTER DATABASE REFRESH", "Best for": "Zero-registration catalog sync"},
    {"Pillar": "🔌 Catalog Federation",     "Capability": "Auto-Refresh / Metadata Sync",      "Status": "GA", "Default path": "AUTO_REFRESH=TRUE on externally managed", "Best for": "New Spark snapshots visible in Snowflake"},
    # ── PILLAR 4: Governance & Security ───────────────────────────────────
    {"Pillar": "🔐 Governance & Security",  "Capability": "Snowflake Security Model",          "Status": "GA", "Default path": "Snowflake users + roles + key-pair JWT",  "Best for": "Unified governance across all engines"},
    {"Pillar": "🔐 Governance & Security",  "Capability": "Credential Vending",                "Status": "GA", "Default path": "X-Iceberg-Access-Delegation header",      "Best for": "Secure S3 access without static keys"},
    {"Pillar": "🔐 Governance & Security",  "Capability": "WIF / OIDC Authentication",         "Status": "GA", "Default path": "EXTERNAL_OAUTH security integration",     "Best for": "Cloud-native auth — no static tokens"},
    {"Pillar": "🔐 Governance & Security",  "Capability": "Policy Enforcement on Iceberg",     "Status": "GA", "Default path": "RAP + masking evaluated by Horizon",      "Best for": "Row/column-level security for Spark"},
    {"Pillar": "🔐 Governance & Security",  "Capability": "Object Tags + Data Classification", "Status": "GA", "Default path": "CREATE TAG + SYSTEM$CLASSIFY()",          "Best for": "PII governance on Iceberg tables"},
    # ── PILLAR 5: Data Operations ──────────────────────────────────────────
    {"Pillar": "🗄️ Data Operations",        "Capability": "Snowflake Storage for Iceberg",     "Status": "GA", "Default path": "STORAGE_SERIALIZATION_POLICY=COMPATIBLE", "Best for": "No external volume setup needed"},
    {"Pillar": "🗄️ Data Operations",        "Capability": "Iceberg Time Travel",               "Status": "GA", "Default path": "AT(SNAPSHOT=>) / AT(TIMESTAMP=>)",        "Best for": "Data recovery and historical analysis"},
    {"Pillar": "🗄️ Data Operations",        "Capability": "Automated Table Maintenance",       "Status": "GA", "Default path": "Auto for Snowflake; OPTIMIZE for Spark",  "Best for": "Table health after mixed engine writes"},
    {"Pillar": "🗄️ Data Operations",        "Capability": "Schema Evolution",                  "Status": "GA", "Default path": "ALTER TABLE ADD/DROP/RENAME COLUMN",      "Best for": "Evolving schemas without data rewrite"},
    {"Pillar": "🗄️ Data Operations",        "Capability": "Partitioning (Iceberg-native)",     "Status": "GA", "Default path": "PARTITION BY transforms",                 "Best for": "Multi-engine partition pruning"},
    {"Pillar": "🗄️ Data Operations",        "Capability": "Iceberg v3 Features",               "Status": "GA", "Default path": "VARIANT, TIMESTAMP_NTZ(9), DEFAULT",      "Best for": "Event/telemetry tables, JSON payloads"},
    # ── PILLAR 6: Ingest & Transform ──────────────────────────────────────
    {"Pillar": "🔁 Ingest & Transform",     "Capability": "Snowpipe Streaming → Iceberg",      "Status": "GA", "Default path": "Kafka Connector SNOWPIPE_STREAMING mode", "Best for": "Real-time open Iceberg pipelines"},
    {"Pillar": "🔁 Ingest & Transform",     "Capability": "Dynamic Tables as Iceberg",         "Status": "GA", "Default path": "CREATE DYNAMIC ICEBERG TABLE",            "Best for": "Incremental pipelines with open output"},
    {"Pillar": "🔁 Ingest & Transform",     "Capability": "Snowpark on Iceberg",               "Status": "GA", "Default path": "session.table() + write.save_as_table()", "Best for": "Python-native Iceberg access in Snowflake"},
    # ── PILLAR 7: Distribution & Enterprise ───────────────────────────────
    {"Pillar": "🌐 Distribution & Enterprise", "Capability": "Secure Data Sharing for Iceberg","Status": "GA", "Default path": "CREATE SHARE + multi-tenant RAP",         "Best for": "Cross-account & multi-tenant Iceberg"},
    {"Pillar": "🌐 Distribution & Enterprise", "Capability": "Unity Catalog ↔ Horizon",        "Status": "GA", "Default path": "Iceberg REST both directions",            "Best for": "Databricks + Snowflake customers"},
    {"Pillar": "🌐 Distribution & Enterprise", "Capability": "PrivateLink for Catalog Integrations","Status": "GA","Default path": "Private DNS + Network Policy",        "Best for": "HIPAA/PCI/FedRAMP environments"},
    {"Pillar": "🌐 Distribution & Enterprise", "Capability": "BCDR / Fail-Safe / Replication", "Status": "GA", "Default path": "Fail-safe 7d + Time Travel + Replication","Best for": "Enterprise-grade Iceberg data protection"},
    # ── APPENDIX ──────────────────────────────────────────────────────────
    {"Pillar": "📎 Appendix",               "Capability": "Competitive Positioning",            "Status": "GA", "Default path": "Databricks/AWS/GCP/Microsoft comparison", "Best for": "Seller talk track — not customer-facing"},
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
    st.markdown("### 7-Pillar Structure (Glean-recommended)")
    pillars = df["Pillar"].unique()
    for pillar in pillars:
        st.markdown(f"**{pillar}**")
        sub = df[df["Pillar"] == pillar][["Capability", "Status", "Default path", "Best for"]].reset_index(drop=True)
        st.dataframe(sub, use_container_width=True)

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
