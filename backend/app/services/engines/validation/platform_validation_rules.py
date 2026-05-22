from __future__ import annotations


WHEEL_REQUIRED_FIELDS = ["sku", "brand", "model", "size", "bolt_pattern", "finish", "category"]
TIRE_REQUIRED_FIELDS = ["sku", "brand", "model", "size", "category"]

PLATFORM_REQUIRED_FIELDS = {
    "woocommerce": ["sku", "title", "regular_price", "categories"],
    "magento": ["sku", "name", "price", "attribute_set_code"],
    "shopify": ["Handle", "Title", "Variant SKU"],
}
