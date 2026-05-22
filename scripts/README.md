# Scripts

## upload_wheel_library_to_postgres.py

Loads `Wheel_Library.csv` into `public.wheel_library_raw`.

```bash
export SUPABASE_DB_URL="postgresql://..."
export WHEEL_LIBRARY_CSV="/path/to/Wheel_Library.csv"
python scripts/upload_wheel_library_to_postgres.py
```

Do not commit the large CSV into the repo.
