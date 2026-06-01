# Snowflake Iceberg Interop Explorer

A comprehensive reference app and code library for every **Snowflake Horizon Catalog + Iceberg interoperability** capability — covering 18 features from open REST access to partitioning, time travel, policy enforcement, and competitive positioning.

Built for Snowflake field teams, SEs, and customers who want runnable code assets alongside a structured explanation of the Iceberg story.

---

## Live App

Deployed on Snowflake (Streamlit in Snowflake):

```
https://app.snowflake.com/SFSENORTHAMERICA/afe_americas/#/streamlit-apps/AFENG_DB.ICEBERG_DEMOS.ICEBERG_INTEROP_EXPLORER
```

## What's Inside

### 18 Capabilities Covered

| # | Capability | Code |
|---|-----------|------|
| 1 | Open Iceberg REST Access | SQL + PyIceberg |
| 2 | Apache Polaris Integration | SQL + PySpark |
| 3 | Single Endpoint | SQL + Python (multi-engine) |
| 4 | External Engine Read + Write | Spark, DuckDB, PyIceberg |
| 5 | Existing Snowflake Security Model | SQL + Python (key-pair JWT) |
| 6 | Credential Vending | SQL + Python (STS credentials) |
| 7 | Governed Multi-Engine Access | SQL + Python (cross-engine query) |
| 8 | Policy Enforcement on Iceberg | SQL (RAP + masking) + Spark test |
| 9 | Supported External Engines | Spark, Flink, Trino, DuckDB, Dremio, Doris, PyIceberg, StarRocks |
| 10 | Snowflake Storage for Iceberg | SQL (no external volume) |
| 11 | AWS Glue + Catalog-Linked DBs | SQL + PyIceberg |
| 12 | Iceberg Time Travel | SQL |
| 13 | Table Maintenance (OPTIMIZE/REORG) | SQL |
| 14 | Schema Evolution | SQL |
| 15 | Competitive Positioning | SQL comparison |
| 16 | Snowpipe Streaming → Iceberg | SQL + Python |
| 17 | Dynamic Tables as Iceberg | SQL |
| 18 | Partitioning + Performance Tuning | SQL |

### Repository Structure

```
.
├── streamlit_app.py              # Main Streamlit app (Snowflake SiS entry point)
├── streamlit_iceberg_interop_app.py  # Local dev copy
├── snowflake.yml                 # Snowflake CLI deployment manifest
├── pyproject.toml                # Python dependencies
├── quickstart.md                 # Self-contained Quickstart lab guide
├── notebooks/
│   └── horizon_iceberg_demo.ipynb  # Importable Snowflake Notebook
└── code_assets/
    ├── 01_horizon_rest_access/
    ├── 02_polaris_integration/
    ├── 03_single_endpoint/
    ├── 04_external_engine_read_write/
    ├── 05_security_model/
    ├── 06_credential_vending/
    ├── 07_governed_multi_engine/
    ├── 08_policy_enforcement/
    ├── 09_supported_engines/
    ├── 10_snowflake_storage/
    ├── 11_glue_catalog_linked_db/
    ├── 12_time_travel/
    ├── 13_table_maintenance/
    ├── 14_schema_evolution/
    ├── 15_competitive_positioning/
    ├── 16_snowpipe_streaming/
    ├── 17_dynamic_tables/
    └── 18_partitioning_performance/
```

---

## Quick Start

### Option A — Deploy as Streamlit in Snowflake (recommended)

```bash
# 1. Clone this repo
git clone https://github.com/YOUR_ORG/snowflake-iceberg-interop-explorer.git
cd snowflake-iceberg-interop-explorer

# 2. Install Snowflake CLI
pip install snowflake-cli

# 3. Configure your Snowflake connection
snow connection add

# 4. Deploy (creates AFENG_DB.ICEBERG_DEMOS.ICEBERG_INTEROP_EXPLORER by default)
snow streamlit deploy --replace

# 5. Grant access to your team
snow sql -q "GRANT USAGE ON STREAMLIT AFENG_DB.ICEBERG_DEMOS.ICEBERG_INTEROP_EXPLORER TO ROLE PUBLIC;"
```

> Edit `snowflake.yml` to change the target database/schema/warehouse before deploying.

### Option B — Run locally

```bash
pip install streamlit pandas
streamlit run streamlit_app.py
```

### Option C — Import the Notebook into Snowflake

1. In Snowsight → **Projects → Notebooks → Import**
2. Upload `notebooks/horizon_iceberg_demo.ipynb`
3. Set warehouse and run all cells

---

## Prerequisites

| Component | Details |
|-----------|---------|
| Snowflake account | Any edition |
| External volume | S3/GCS/Azure with IAM role |
| Warehouse | Any size (XS is fine) |
| Python | 3.9+ for local run |

---

## Horizon Catalog Endpoint

```
https://<account_identifier>.snowflakecomputing.com/polaris/api/catalog
```

Retrieve for your account:
```sql
SELECT SYSTEM$GET_ICEBERG_REST_CATALOG_ENDPOINT();
```

---

## Adapting the Code to Your Account

The code assets use demo account values. Replace these:

| Placeholder | Replace with |
|-------------|-------------|
| `scb47336` | Your Snowflake account identifier |
| `iceberg_demo_ext_vol` | Your external volume name |
| `horizon_demo_db` | Your database name |
| `s3://vmedida-iceberg-demo/` | Your S3 bucket |
| `913524911227` | Your AWS account ID (for Glue) |

---

## Contributing

PRs welcome. Each new capability should:
1. Add a folder under `code_assets/NN_feature_name/`
2. Include at least one `.sql` file and one `.py` file
3. Add an entry to the `CAPABILITIES` list in `streamlit_app.py`

---

## Related Resources

- [Snowflake Iceberg Tables docs](https://docs.snowflake.com/en/user-guide/tables-iceberg)
- [Horizon Catalog REST API](https://docs.snowflake.com/en/user-guide/tables-iceberg-catalog)
- [Apache Iceberg REST Catalog spec](https://github.com/apache/iceberg/blob/main/open-api/rest-catalog-open-api.yaml)
- [Snowflake Quickstarts](https://quickstarts.snowflake.com)

---

*Built by Venkat Medida · Snowflake AFE Americas · June 2026*
