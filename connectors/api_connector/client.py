"""Generic vendor API connector placeholder.

Use this folder for vendor APIs that are not WooCommerce/Shopify.
"""

from __future__ import annotations


class APIConnectorNotImplemented(Exception):
    pass


def fetch_vendor_feed(*args, **kwargs):
    raise APIConnectorNotImplemented("Generic vendor API connector is planned but not implemented yet.")
