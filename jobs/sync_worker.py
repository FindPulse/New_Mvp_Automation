"""Future WooCommerce/Shopify sync worker entrypoint.

Direct website write-back is not part of the current CSV-based MVP.
"""


def run_sync_job() -> None:
    raise NotImplementedError("Sync worker queue is not wired yet.")
