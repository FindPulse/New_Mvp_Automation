"""Future ETL worker entrypoint.

For Phase 1, Streamlit/FastAPI call workflows directly.
For Phase 2, move long-running ingestion and normalization jobs here using Celery/RQ/Redis.
"""


def run_etl_job() -> None:
    raise NotImplementedError("ETL worker queue is not wired yet.")
