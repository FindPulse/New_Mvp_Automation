"""FTP/SFTP connector placeholder.

Keep all vendor file fetching code here later. The ingestion engine should call this connector,
but this connector should not contain SKU comparison or validation logic.
"""

from __future__ import annotations


class FTPConnectorNotImplemented(Exception):
    pass


def fetch_latest_vendor_files(*args, **kwargs):
    raise FTPConnectorNotImplemented("FTP/SFTP connector is planned but not implemented in this boilerplate.")
