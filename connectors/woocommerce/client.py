from __future__ import annotations

from dataclasses import dataclass
from typing import Callable, Iterable, Optional

import pandas as pd
import requests

from backend.app.config.settings import get_settings


@dataclass(frozen=True)
class WooCommerceConfig:
    site_url: str
    consumer_key: str
    consumer_secret: str

    @staticmethod
    def from_settings() -> "WooCommerceConfig":
        settings = get_settings()
        if not settings.woo_site_url or not settings.woo_consumer_key or not settings.woo_consumer_secret:
            raise RuntimeError(
                "WooCommerce config is missing. Set WOO_SITE_URL, WOO_CONSUMER_KEY, WOO_CONSUMER_SECRET."
            )
        return WooCommerceConfig(
            site_url=settings.woo_site_url.rstrip("/"),
            consumer_key=settings.woo_consumer_key,
            consumer_secret=settings.woo_consumer_secret,
        )


class WooCommerceClient:
    """Read-only WooCommerce connector for category and SKU pulls."""

    def __init__(self, config: Optional[WooCommerceConfig] = None) -> None:
        self.config = config or WooCommerceConfig.from_settings()

    def _get(self, path: str, params: Optional[dict] = None, timeout: int = 60) -> requests.Response:
        url = f"{self.config.site_url}{path}"
        return requests.get(
            url,
            auth=(self.config.consumer_key, self.config.consumer_secret),
            params=params,
            timeout=timeout,
        )

    def test_connection(self) -> requests.Response:
        return self._get("/wp-json/wc/v3/products", params={"per_page": 1}, timeout=30)

    def fetch_categories(self) -> pd.DataFrame:
        all_categories: list[dict] = []
        page = 1

        while True:
            response = self._get(
                "/wp-json/wc/v3/products/categories",
                params={"per_page": 100, "page": page, "hide_empty": True},
            )
            response.raise_for_status()
            categories = response.json()
            if not categories:
                break

            for category in categories:
                all_categories.append(
                    {
                        "id": category.get("id"),
                        "name": category.get("name"),
                        "slug": category.get("slug"),
                        "count": category.get("count"),
                        "parent": category.get("parent"),
                    }
                )
            page += 1

        df = pd.DataFrame(all_categories)
        if not df.empty:
            df = df.sort_values(by=["parent", "name"], ascending=[True, True])
        return df

    def fetch_skus_by_brand_categories(
        self,
        selected_brand_rows: Iterable[dict],
        progress_callback: Optional[Callable[[dict], None]] = None,
    ) -> pd.DataFrame:
        all_rows: list[dict] = []
        seen_skus: set[str] = set()
        selected_brand_rows = list(selected_brand_rows)

        total_expected_products = sum(int(brand.get("count") or 0) for brand in selected_brand_rows) or 1
        products_processed = 0
        variations_processed = 0

        def add_sku_row(brand_name: str, source: str, product_id: int, variation_id: int | None, sku: str | None):
            if sku is None:
                return
            sku_text = str(sku).strip()
            if not sku_text:
                return
            sku_key = sku_text.upper()
            if sku_key in seen_skus:
                return
            seen_skus.add(sku_key)
            all_rows.append(
                {
                    "brand": brand_name,
                    "source": source,
                    "product_id": product_id,
                    "variation_id": variation_id,
                    "sku": sku_text,
                }
            )

        def send_progress(stage: str, brand_name: str = "", page: int = 0, done: bool = False):
            if progress_callback:
                progress_callback(
                    {
                        "stage": stage,
                        "brand_name": brand_name,
                        "page": page,
                        "products_processed": products_processed,
                        "total_expected_products": total_expected_products,
                        "variations_processed": variations_processed,
                        "sku_rows_collected": len(all_rows),
                        "progress": 1.0 if done else min(products_processed / total_expected_products, 0.99),
                        "latest_rows": all_rows[-10:],
                    }
                )

        for brand in selected_brand_rows:
            brand_category_id = int(brand["id"])
            brand_name = brand["name"]
            page = 1
            send_progress("Starting brand", brand_name, page)

            while True:
                response = self._get(
                    "/wp-json/wc/v3/products",
                    params={
                        "per_page": 100,
                        "page": page,
                        "category": brand_category_id,
                        "_fields": "id,sku,type",
                    },
                )
                response.raise_for_status()
                products = response.json()
                if not products:
                    break

                for product in products:
                    product_id = product.get("id")
                    product_type = product.get("type")
                    products_processed += 1
                    add_sku_row(brand_name, "product", product_id, None, product.get("sku"))

                    if product_type == "variable":
                        variation_page = 1
                        while True:
                            variation_response = self._get(
                                f"/wp-json/wc/v3/products/{product_id}/variations",
                                params={"per_page": 100, "page": variation_page, "_fields": "id,sku"},
                            )
                            variation_response.raise_for_status()
                            variations = variation_response.json()
                            if not variations:
                                break
                            for variation in variations:
                                variations_processed += 1
                                add_sku_row(
                                    brand_name,
                                    "variation",
                                    product_id,
                                    variation.get("id"),
                                    variation.get("sku"),
                                )
                            send_progress("Reading variation SKUs", brand_name, variation_page)
                            variation_page += 1

                    send_progress("Reading products and SKUs", brand_name, page)
                page += 1

        send_progress("Done", done=True)
        return pd.DataFrame(all_rows, columns=["brand", "source", "product_id", "variation_id", "sku"])
