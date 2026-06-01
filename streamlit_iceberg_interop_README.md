# Streamlit app: Snowflake Iceberg Interop Explorer

## What this app does
This Streamlit app is a customer-facing capability explorer for Snowflake Iceberg interoperability. It is designed to help explain:

- Snowflake-managed Iceberg via Horizon Catalog / Iceberg REST
- External-engine write support for Snowflake-managed Iceberg
- Writable externally managed Iceberg tables
- Snowflake Storage for Iceberg
- Governance and PrivateLink positioning
- Competitive caveats, especially around Databricks / Unity Catalog

## Run locally
```bash
pip install streamlit pandas
streamlit run streamlit_iceberg_interop_app.py
```

## How to adapt it
1. Replace the inline Python lists with a JSON or YAML file.
2. Add icons and diagrams for each access path.
3. Add a scenario selector such as:
   - Existing Snowflake customer wants open interop
   - Customer standardized on Unity Catalog
   - Customer wants lowest-ops storage path
4. Add a customer-safe export button that emits a markdown summary.

## Suggested next enhancement
Connect the app to a small metadata file with columns like:
- capability
- status
- audience_safe_message
- internal_caveat
- recommended_path
- competitor_note
- last_validated_date

That lets you keep the app static while updating messaging quickly.
