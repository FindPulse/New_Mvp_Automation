# Engine Contracts

## Normalization Engine

Input: DataFrame and source SKU column.

Output: same DataFrame with `clean_sku`.

Must not:

- fetch files
- call WooCommerce
- create CSV downloads

## Comparison Engine

Input: vendor DataFrame, website DataFrame, SKU column names.

Output:

- vendor_clean
- website_clean
- missing rows
- comparison summary counts

Must not:

- validate product fields
- call wheel library
- generate UI

## Enrichment Engine

Input: missing rows or clean SKU list.

Output: missing rows enriched with library columns and `wheel_library_status`.

Must not:

- decide final Ready vs Needs Review status

## Validation Engine

Input: enriched missing rows and column mapping.

Output:

- `validation_status`
- `issue_reason`
- `validation_warnings`

## Export Engine

Input: final validated DataFrame and summary.

Output:

- `ready_to_upload.csv`
- `needs_review.csv`
- `comparison_summary.csv`
