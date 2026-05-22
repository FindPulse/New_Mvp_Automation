from __future__ import annotations

import sys
from pathlib import Path
from template_builder_page import render_template_builder_page
import pandas as pd
import streamlit as st

PROJECT_ROOT = Path(__file__).resolve().parents[1]
if str(PROJECT_ROOT) not in sys.path:
    sys.path.insert(0, str(PROJECT_ROOT))

from backend.app.config.settings import get_settings
from backend.app.models.schemas import ColumnMapping
from backend.app.services.io.file_reader import read_tabular_bytes, read_tabular_file
from backend.app.services.workflows.missing_sku_workflow import run_missing_sku_workflow
from connectors.email_connector.microsoft_graph_client import MicrosoftGraphEmailClient
from connectors.woocommerce.category_service import get_brand_categories_for_product_type
from connectors.woocommerce.client import WooCommerceClient

st.set_page_config(page_title="AI Missing SKU Finder", layout="wide")

st.title("AI Missing SKU Finder + CSV Generator")
st.caption("Structured architecture version: Streamlit UI → Workflow → Engines → Connectors")

settings = get_settings()

page = st.sidebar.radio(
    "Navigation",
    [
        "Missing SKU Finder",
        "Template & Rules Builder",
    ]
)

if page == "Template & Rules Builder":
    render_template_builder_page()
    st.stop()

# -----------------------------
# Session State
# -----------------------------
DEFAULT_SESSION_VALUES = {
    "vendor_df": None,
    "vendor_file_name": None,
    "website_df": None,
    "website_source_name": None,
    "outlook_token": None,
    "attachment_emails": None,
    "woo_categories": None,
    "woo_brand_categories": None,
    "woo_product_type": None,
}
for key, value in DEFAULT_SESSION_VALUES.items():
    if key not in st.session_state:
        st.session_state[key] = value


# -----------------------------
# Step 1: Vendor Source
# -----------------------------
st.header("1. Vendor Data Source")
vendor_source = st.radio("Choose vendor file source", ["Upload File", "Outlook"], horizontal=True)

if vendor_source == "Upload File":
    vendor_file = st.file_uploader("Upload Vendor CSV/XLSX", type=["csv", "xlsx", "xls"], key="vendor_upload")
    if vendor_file:
        try:
            st.session_state.vendor_df = read_tabular_file(vendor_file, vendor_file.name)
            st.session_state.vendor_file_name = vendor_file.name
            st.success(f"Vendor file loaded: {vendor_file.name}")
        except Exception as exc:
            st.error(f"Could not read vendor file: {exc}")

elif vendor_source == "Outlook":
    st.info("Outlook connector is modularized under connectors/email_connector/.")
    if not settings.microsoft_client_id:
        st.warning("MICROSOFT_CLIENT_ID is missing. Add it to .env or Streamlit secrets.")
    else:
        graph_client = MicrosoftGraphEmailClient(client_id=settings.microsoft_client_id)
        token = st.session_state.outlook_token or graph_client.acquire_token_silent()
        if token:
            st.session_state.outlook_token = token
            st.success("Outlook connected from saved login.")
        else:
            if st.button("Login with Outlook"):
                flow = graph_client.initiate_device_flow()
                if "user_code" not in flow:
                    st.error("Could not create Microsoft device login flow.")
                else:
                    st.write("Open this link and enter the code:")
                    st.write(flow["verification_uri"])
                    st.code(flow["user_code"])
                    result = graph_client.acquire_token_by_device_flow(flow)
                    if "access_token" in result:
                        st.session_state.outlook_token = result["access_token"]
                        st.success("Outlook login successful.")
                    else:
                        st.error("Outlook login failed.")
                        st.json(result)

        if st.session_state.outlook_token:
            search_text = st.text_input("Search vendor emails", placeholder="katana, rohana, vendor, price list")
            if st.button("Fetch Vendor Emails With Excel/CSV Attachments"):
                try:
                    st.session_state.attachment_emails = graph_client.fetch_recent_attachment_emails(
                        st.session_state.outlook_token,
                        search_text=search_text,
                    )
                except Exception as exc:
                    st.error(f"Could not fetch Outlook emails: {exc}")

            if st.session_state.attachment_emails:
                emails_table = [
                    {
                        "subject": item["subject"],
                        "from_name": item["from_name"],
                        "from_email": item["from_email"],
                        "received": item["received"],
                        "files": item["files"],
                    }
                    for item in st.session_state.attachment_emails
                ]
                st.dataframe(pd.DataFrame(emails_table), use_container_width=True)

                email_options = [
                    f"{i + 1}. {item['subject']} | {item['received']}"
                    for i, item in enumerate(st.session_state.attachment_emails)
                ]
                selected_email_label = st.selectbox("Select email", email_options)
                selected_email = st.session_state.attachment_emails[email_options.index(selected_email_label)]

                attachment_options = [file["file_name"] for file in selected_email["attachments"]]
                selected_file_name = st.selectbox("Select attachment file", attachment_options)
                selected_attachment = next(
                    item for item in selected_email["attachments"] if item["file_name"] == selected_file_name
                )

                if st.button("Load Selected Attachment as Vendor File"):
                    try:
                        content = graph_client.download_attachment(
                            st.session_state.outlook_token,
                            selected_email["message_id"],
                            selected_attachment["attachment_id"],
                        )
                        st.session_state.vendor_df = read_tabular_bytes(selected_file_name, content)
                        st.session_state.vendor_file_name = selected_file_name
                        st.success(f"Vendor attachment loaded: {selected_file_name}")
                    except Exception as exc:
                        st.error(f"Could not load attachment: {exc}")

if st.session_state.vendor_df is not None:
    st.subheader("Vendor Preview")
    st.write("Source:", st.session_state.vendor_file_name)
    st.write(f"Rows: {len(st.session_state.vendor_df):,} | Columns: {len(st.session_state.vendor_df.columns):,}")
    st.dataframe(st.session_state.vendor_df.head(50), use_container_width=True)


# -----------------------------
# Step 2: Website Source
# -----------------------------
st.header("2. Website SKU Source")
website_source = st.radio("Choose website SKU source", ["Upload Export File", "WooCommerce"], horizontal=True)

if website_source == "Upload Export File":
    website_file = st.file_uploader("Upload Website SKU Export CSV/XLSX", type=["csv", "xlsx", "xls"], key="website_upload")
    if website_file:
        try:
            st.session_state.website_df = read_tabular_file(website_file, website_file.name)
            st.session_state.website_source_name = website_file.name
            st.success(f"Website export loaded: {website_file.name}")
        except Exception as exc:
            st.error(f"Could not read website export: {exc}")

elif website_source == "WooCommerce":
    st.info("WooCommerce connector is read-only in this MVP foundation.")
    if not settings.woo_site_url:
        st.warning("WooCommerce config is missing. Add WOO_SITE_URL, WOO_CONSUMER_KEY, WOO_CONSUMER_SECRET.")
    else:
        woo_client = WooCommerceClient()
        st.write("Site URL:", settings.woo_site_url)
        col1, col2 = st.columns(2)
        with col1:
            if st.button("Test WooCommerce Connection"):
                try:
                    response = woo_client.test_connection()
                    if response.status_code == 200:
                        st.success("WooCommerce connection successful.")
                        products = response.json()
                        if products:
                            st.json({k: products[0].get(k) for k in ["id", "name", "sku", "type", "status"]})
                    else:
                        st.error(f"WooCommerce failed: {response.status_code}")
                        st.write(response.text)
                except Exception as exc:
                    st.error(f"WooCommerce error: {exc}")
        with col2:
            if st.button("Load WooCommerce Categories"):
                try:
                    st.session_state.woo_categories = woo_client.fetch_categories()
                    st.success("WooCommerce categories loaded.")
                except Exception as exc:
                    st.error(f"Could not load categories: {exc}")

        if st.session_state.woo_categories is not None:
            product_type = st.radio("Product type", ["Tires", "Wheels"], horizontal=True)
            if st.session_state.woo_product_type != product_type:
                st.session_state.woo_product_type = product_type
                st.session_state.woo_brand_categories = None

            if st.button("Load Vendors/Brands for Selected Type"):
                brand_df, product_type_row = get_brand_categories_for_product_type(
                    st.session_state.woo_categories,
                    product_type,
                )
                if product_type_row is None:
                    st.error(f"Could not find {product_type} category.")
                    st.dataframe(st.session_state.woo_categories, use_container_width=True)
                elif brand_df is None or brand_df.empty:
                    st.warning(f"{product_type} category found, but no child brand/vendor categories found.")
                else:
                    st.session_state.woo_brand_categories = brand_df
                    st.success(f"{product_type} brands/vendors loaded.")

            if st.session_state.woo_brand_categories is not None:
                brand_search = st.text_input("Search brand/vendor")
                brand_df = st.session_state.woo_brand_categories.copy()
                if brand_search:
                    brand_df = brand_df[brand_df["name"].str.contains(brand_search, case=False, na=False)]
                st.dataframe(brand_df, use_container_width=True)

                brand_lookup = {
                    f"{row['name']} | Products: {row['count']} | ID: {row['id']}": {
                        "id": int(row["id"]),
                        "name": row["name"],
                        "slug": row["slug"],
                        "count": int(row["count"]),
                        "parent": int(row["parent"]),
                    }
                    for _, row in brand_df.iterrows()
                }
                selected_brand_labels = st.multiselect("Select brands/vendors", list(brand_lookup.keys()))
                if selected_brand_labels and st.button("Pull Selected Brand SKUs"):
                    selected_brand_rows = [brand_lookup[label] for label in selected_brand_labels]
                    progress_bar = st.progress(0)
                    status_placeholder = st.empty()
                    preview_placeholder = st.empty()

                    def update_pull_progress(info: dict):
                        progress_bar.progress(info["progress"])
                        status_placeholder.write(
                            f"**Status:** {info['stage']} | **Brand:** {info['brand_name']} | "
                            f"Products: {info['products_processed']} | Variations: {info['variations_processed']} | "
                            f"SKU rows: {info['sku_rows_collected']}"
                        )
                        if info["latest_rows"]:
                            preview_placeholder.dataframe(pd.DataFrame(info["latest_rows"]))

                    try:
                        woo_df = woo_client.fetch_skus_by_brand_categories(
                            selected_brand_rows,
                            progress_callback=update_pull_progress,
                        )
                        selected_brand_names = [brand["name"] for brand in selected_brand_rows]
                        st.session_state.website_df = woo_df
                        st.session_state.website_source_name = f"WooCommerce - {product_type} - {', '.join(selected_brand_names)}"
                        st.success(f"Pulled {len(woo_df):,} SKU rows from WooCommerce.")
                    except Exception as exc:
                        st.error(f"Could not pull WooCommerce SKUs: {exc}")

if st.session_state.website_df is not None:
    st.subheader("Website SKU Preview")
    st.write("Source:", st.session_state.website_source_name)
    st.write(f"Rows: {len(st.session_state.website_df):,} | Columns: {len(st.session_state.website_df.columns):,}")
    st.dataframe(st.session_state.website_df.head(50), use_container_width=True)


# -----------------------------
# Step 3: Mapping + Workflow
# -----------------------------
st.header("3. Map Columns and Run Workflow")

vendor_df = st.session_state.vendor_df
website_df = st.session_state.website_df

if vendor_df is not None and website_df is not None:
    col1, col2 = st.columns(2)
    with col1:
        vendor_sku_col = st.selectbox("Vendor SKU Column", vendor_df.columns)
    with col2:
        default_website_idx = list(website_df.columns).index("sku") if "sku" in website_df.columns else 0
        website_sku_col = st.selectbox("Website SKU Column", website_df.columns, index=default_website_idx)

    st.subheader("Optional validation column mapping")
    st.caption("Map these if they exist in the vendor file. If wheel library lookup finds data, it will be used as fallback.")

    def optional_col(label: str) -> str | None:
        options = [""] + list(vendor_df.columns)
        selected = st.selectbox(label, options)
        return selected or None

    map_cols = st.columns(4)
    with map_cols[0]:
        price_col = optional_col("Price")
        brand_col = optional_col("Brand")
    with map_cols[1]:
        model_col = optional_col("Model")
        size_col = optional_col("Size")
    with map_cols[2]:
        bolt_col = optional_col("Bolt Pattern")
        offset_col = optional_col("Offset")
    with map_cols[3]:
        bore_col = optional_col("Bore/Hub")
        finish_col = optional_col("Finish")

    image_col = optional_col("Image URL / Image")
    enable_library = st.checkbox("Check missing SKUs in Supabase wheel library", value=bool(settings.supabase_db_url))

    if st.button("Find Missing SKUs", type="primary"):
        mapping = ColumnMapping(
            vendor_sku=vendor_sku_col,
            website_sku=website_sku_col,
            price=price_col,
            brand=brand_col,
            model=model_col,
            size=size_col,
            bolt_pattern=bolt_col,
            offset=offset_col,
            bore=bore_col,
            finish=finish_col,
            image=image_col,
        )

        with st.spinner("Running missing SKU workflow..."):
            result = run_missing_sku_workflow(
                vendor_df=vendor_df,
                website_df=website_df,
                mapping=mapping,
                enable_wheel_library_lookup=enable_library,
            )

        st.subheader("Comparison Summary")
        m1, m2, m3, m4 = st.columns(4)
        m1.metric("Vendor SKUs", f"{result.summary.vendor_skus:,}")
        m2.metric("Website SKUs", f"{result.summary.website_skus:,}")
        m3.metric("Matched SKUs", f"{result.summary.matched_skus:,}")
        m4.metric("Missing SKUs", f"{result.summary.missing_skus:,}")

        m5, m6, m7, m8 = st.columns(4)
        m5.metric("Found in Library", f"{result.summary.missing_found_in_library:,}")
        m6.metric("Not Found in Library", f"{result.summary.missing_not_found_in_library:,}")
        m7.metric("Ready", f"{result.summary.ready_rows:,}")
        m8.metric("Needs Review", f"{result.summary.needs_review_rows:,}")

        for warning in result.warnings:
            st.warning(warning)

        st.subheader("Business Summary")
        st.write(result.business_summary)

        st.subheader("Missing SKU Results")
        st.dataframe(result.final_missing_df.head(500), use_container_width=True)

        st.subheader("CSV Downloads")
        for file_name, csv_text in result.exports.as_csv_text().items():
            st.download_button(
                label=f"Download {file_name}",
                data=csv_text.encode("utf-8"),
                file_name=file_name,
                mime="text/csv",
            )
else:
    st.info("Load vendor data and website data to start comparison.")
