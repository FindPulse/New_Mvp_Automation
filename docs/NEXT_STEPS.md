# Recommended Next Steps

## Immediate Sprint: stabilize architecture and finish MVP export layer

### Ticket 1 - Team setup

- unzip this repo
- create `.env` from `.env.example`
- install requirements
- run Streamlit
- run tests

Acceptance: every developer can run the same app locally.

### Ticket 2 - Confirm output schema

Define the exact final columns needed for WooCommerce import.

Acceptance: `docs/output_schema.md` exists and is approved.

### Ticket 3 - Validation rules finalization

Confirm which fields are blocking vs warning.

Acceptance: `DEFAULT_WHEEL_RULES` matches business rules.

### Ticket 4 - Test with real vendor + website export

Use a small sample and manually verify missing SKUs.

Acceptance: comparison count matches manual check.

### Ticket 5 - Staging import test

Try `ready_to_upload.csv` in staging WooCommerce import flow.

Acceptance: no format errors in staging.

## Do not do yet

- direct WooCommerce write-back
- Shopify support
- multi-client login
- billing
- full React rebuild
- Celery/Redis jobs

These are Phase 2/3 after CSV output is trusted.
