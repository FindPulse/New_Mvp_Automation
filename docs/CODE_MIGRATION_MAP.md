# Current Code Migration Map

This file explains how the original `app.py` was converted into the new structured project.

| Original code area | New location | Status |
|---|---|---|
| `read_file`, `read_file_from_bytes` | `backend/app/services/io/file_reader.py` | Done |
| `clean_sku` | `backend/app/services/engines/normalization/sku_normalizer.py` | Done |
| vendor vs website comparison logic | `backend/app/services/engines/comparison/missing_sku_engine.py` | Done |
| Supabase wheel library lookup | `backend/app/services/engines/enrichment/wheel_library_engine.py` | Done |
| Ready/Needs Review split | `backend/app/services/engines/validation/validation_engine.py` | Added as missing MVP layer |
| CSV downloads | `backend/app/services/engines/export/csv_export_engine.py` | Added as proper 3-file export package |
| business summary | `backend/app/services/engines/summary/summary_engine.py` | Added deterministic summary |
| `get_woo_config`, Woo product/category/SKU functions | `connectors/woocommerce/` | Done |
| Outlook MSAL/email attachment logic | `connectors/email_connector/microsoft_graph_client.py` | Done |
| Streamlit UI | `frontend/streamlit_app.py` | Refactored to call workflow/engines |
| FastAPI backend | `backend/app/main.py`, `backend/app/api/` | Added skeleton |
| tests | `backend/tests/` | Added basic unit tests |
| Docker | `backend/Dockerfile` | Added API container |
| CI | `.github/workflows/ci.yml` | Added quality pipeline |

## Done now

- Current single-file app logic is separated into modules.
- Secrets and local token cache are removed from distributable repo.
- Large wheel library CSV is excluded from repo.
- The MVP now has a proper engine-based workflow.
- Streamlit remains available for demo speed.
- FastAPI skeleton exists for future API development.
- Basic tests exist for normalization, comparison, validation, and workflow.

## Still missing / next tickets

1. Decide final WooCommerce upload CSV column schema.
2. Confirm exact required fields for wheel import.
3. Add staging WooCommerce import test for `ready_to_upload.csv`.
4. Add real auth before exposing FastAPI publicly.
5. Add background jobs only after the workflow is stable.
6. Add OpenAI summary only after deterministic counts are trusted.
7. Add React dashboard only after Streamlit demo is approved.
8. Add Shopify connector later; do not mix into MVP 1.

## Current supported use cases

1. Upload vendor file + upload website export.
2. Upload vendor file + pull website SKUs from WooCommerce.
3. Load vendor file from Outlook attachment.
4. Normalize SKUs and find missing SKUs.
5. Check missing SKUs in Supabase/Postgres wheel library.
6. Split missing rows into Ready / Needs Review.
7. Download `ready_to_upload.csv`, `needs_review.csv`, and `comparison_summary.csv`.
