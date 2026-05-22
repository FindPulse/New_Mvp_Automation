# Architecture

## Why this structure was chosen

The current product needs to support both a fast demo and future scaling. The original app worked as a single Streamlit file, but that makes it hard to add WooCommerce, Outlook, Supabase, validation, AI, jobs, and future Shopify support without breaking existing logic.

This boilerplate separates the product into 6 layers:

1. Frontend / Interface
2. API / Application
3. Engines
4. Domain / Models
5. Infrastructure / Connectors
6. Quality / Operations

## Engine boundaries

| Engine | Folder | What it owns |
|---|---|---|
| Normalization | `backend/app/services/engines/normalization/` | SKU cleanup, hidden char removal, normalized comparison keys. |
| Comparison | `backend/app/services/engines/comparison/` | Vendor vs website SKU matching and missing SKU calculation. |
| Enrichment | `backend/app/services/engines/enrichment/` | Wheel library lookup and enrichment fields. |
| Validation | `backend/app/services/engines/validation/` | Ready vs Needs Review and issue reasons. |
| Export | `backend/app/services/engines/export/` | ready_to_upload.csv, needs_review.csv, comparison_summary.csv. |
| Summary | `backend/app/services/engines/summary/` | Business-friendly deterministic summary. |

## Rule

UI and connectors should not contain business logic. They call workflows. Workflows call engines.
