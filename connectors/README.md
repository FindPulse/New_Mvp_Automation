# Connectors

Connectors are allowed to fetch or send data. They are not allowed to make business decisions.

Good connector responsibilities:

- fetch WooCommerce SKUs
- fetch product categories
- download Outlook attachments
- fetch files from FTP/SFTP
- call vendor APIs

Bad connector responsibilities:

- deciding if a SKU is missing
- deciding Ready vs Needs Review
- applying validation rules
- generating final CSV outputs

Those belong in `backend/app/services/engines/`.
