# Patch Notes - Plug-and-Play Fixed Version

This version fixes the broken core contracts and keeps the MVP flow modular.

## Fixed

1. Added missing shared models in `backend/app/models/schemas.py`:
   - `MappingSuggestion`
   - `FieldValue`
   - `ProductDraft`
   - `VendorNormalizationResult`

2. Added the missing canonical comparison function in:
   - `backend/app/services/engines/comparison/missing_sku_engine.py`

   Main function:
   ```python
   compare_vendor_to_website(...)
   ```

   Backward-compatible wrapper kept:
   ```python
   compare_vendor_vs_platform_skus(...)
   ```

3. Unified SKU normalization in:
   - `backend/app/services/engines/normalization/sku_normalizer.py`

   Clean SKU now:
   - trims
   - uppercases
   - removes hidden characters
   - removes internal spaces

4. Existing vendor product draft builder remains included:
   - `backend/app/services/engines/enrichment/vendor_product_draft_builder.py`

   This supports the next waterfall step:
   - missing on website
   - not found in Supabase library
   - create product draft from vendor sheet

5. Removed unsafe/local files from this ZIP:
   - `.env`
   - `msal_token_cache.bin`
   - `.venv`
   - `__pycache__`
   - `.pytest_cache`

## Verified

Tests passed locally:

```powershell
python -m pytest backend/tests -q
```

Result:

```text
11 passed
```

## Run Commands

From this folder:

```powershell
python -m venv .venv
.\.venv\Scripts\python.exe -m pip install --upgrade pip
.\.venv\Scripts\python.exe -m pip install -r backend\requirements.txt
.\.venv\Scripts\python.exe -m streamlit run frontend\streamlit_app.py
```

Run tests:

```powershell
.\.venv\Scripts\python.exe -m pip install -r backend\requirements-dev.txt
.\.venv\Scripts\python.exe -m pytest backend\tests -q
```
