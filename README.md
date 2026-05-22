# Tire Platform - AI Missing SKU Finder Foundation

This repository is a structured boilerplate converted from the original single-file Streamlit MVP.
It keeps the current working use cases, but moves the code into clear layers so the team can scale without turning the app into a larger monolith.

## Current MVP flow

```text
Vendor file / Outlook attachment
        +
Website export / WooCommerce SKU pull
        ↓
Normalize SKUs
        ↓
Compare vendor SKUs vs website SKUs
        ↓
Find missing SKUs
        ↓
Check missing SKUs in wheel library / Supabase Postgres
        ↓
Validate Ready vs Needs Review
        ↓
Export CSVs + summary
```

## 6-layer architecture

| Layer | Folder | Responsibility |
|---|---|---|
| 1. Frontend / Interface | `frontend/` | Streamlit MVP UI now; React can be added later. |
| 2. API / Application | `backend/app/main.py`, `backend/app/api/`, `backend/app/services/workflows/` | FastAPI skeleton and workflow orchestration. |
| 3. Engines | `backend/app/services/engines/` | Business logic: normalization, comparison, validation, enrichment, export, summary. |
| 4. Domain / Models | `backend/app/models/` | Pydantic models and shared contracts. |
| 5. Infrastructure / Connectors | `connectors/`, `backend/app/db/`, `backend/app/config/` | WooCommerce, Outlook, FTP/API placeholders, Postgres/Supabase, config. |
| 6. Quality / Operations | `backend/tests/`, `.github/workflows/`, `infra/`, `docs/` | Tests, CI, Docker, docs, deployment foundation. |

## What was intentionally removed from the original ZIP

The original ZIP included files that should not be shared in a code repo:

- `venv/`
- `.streamlit/secrets.toml`
- `msal_token_cache.bin`
- large data file `Wheel_Library.csv`

Use `.env.example` and `.streamlit/secrets.example.toml` to configure local environments.

## Quick start - Streamlit MVP

```bash
cd tire-platform
python -m venv .venv
source .venv/bin/activate  # Windows: .venv\Scripts\activate
pip install -r backend/requirements.txt
streamlit run frontend/streamlit_app.py
```

## Quick start - API skeleton

```bash
cd tire-platform
pip install -r backend/requirements.txt
uvicorn backend.app.main:app --reload
```

Open:

```text
http://127.0.0.1:8000/health
http://127.0.0.1:8000/docs
```

## Run tests

```bash
pip install -r backend/requirements-dev.txt
pytest backend/tests
```

## Next development rule

Do not add new features directly to Streamlit. Build logic inside an engine first, then call that engine from Streamlit or FastAPI.
