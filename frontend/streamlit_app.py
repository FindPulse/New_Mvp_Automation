from __future__ import annotations

import sys
from pathlib import Path

from backend.app.services.engines.enrichment.vendor_product_draft_builder import build_vendor_product_drafts
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
# Step 3: Mapping + Direct SKU Comparison
# -----------------------------
st.header("3. Compare Vendor SKUs vs Website SKUs")

vendor_df = st.session_state.vendor_df
website_df = st.session_state.website_df


def clean_sku_for_compare(value):
    """
    Clean SKU only for comparison.
    Raw data remains unchanged.
    """
    import re

    if pd.isna(value):
        return ""

    sku = str(value).strip().upper()

    # Remove common invisible characters
    sku = sku.replace("\u200b", "")
    sku = sku.replace("\xa0", "")

    # Remove non-printable characters
    sku = "".join(ch for ch in sku if ch.isprintable())

    # Remove all spaces inside SKU
    sku = re.sub(r"\s+", "", sku)

    return sku


if vendor_df is not None and website_df is not None:
    st.subheader("Data Preview Before Comparison")

    preview_col1, preview_col2 = st.columns(2)

    with preview_col1:
        st.write("Vendor Data Preview")
        st.dataframe(vendor_df.head(10), use_container_width=True)

    with preview_col2:
        st.write("Website / WooCommerce SKU Preview")
        st.dataframe(website_df.head(10), use_container_width=True)

    st.subheader("Select SKU Columns")

    col1, col2 = st.columns(2)

    with col1:
        vendor_sku_col = st.selectbox(
            "Vendor SKU Column",
            list(vendor_df.columns),
            key="step3_vendor_sku_col",
        )

    with col2:
        website_columns = list(website_df.columns)
        default_website_idx = website_columns.index("sku") if "sku" in website_columns else 0

        website_sku_col = st.selectbox(
            "Website / WooCommerce SKU Column",
            website_columns,
            index=default_website_idx,
            key="step3_website_sku_col",
        )

    st.info(
        "Comparison will be done on cleaned SKU values. "
        "Example: spaces removed, uppercase applied, hidden characters removed."
    )

    if st.button("Find Missing SKUs", type="primary", key="step3_find_missing_skus"):
        try:
            vendor_work = vendor_df.copy()
            website_work = website_df.copy()

            vendor_work["original_vendor_sku"] = vendor_work[vendor_sku_col]
            website_work["original_website_sku"] = website_work[website_sku_col]

            vendor_work["clean_sku"] = vendor_work[vendor_sku_col].apply(clean_sku_for_compare)
            website_work["clean_sku"] = website_work[website_sku_col].apply(clean_sku_for_compare)

            vendor_clean = vendor_work[vendor_work["clean_sku"] != ""].copy()
            website_clean = website_work[website_work["clean_sku"] != ""].copy()

            website_sku_set = set(website_clean["clean_sku"].dropna().tolist())

            vendor_clean["is_on_website"] = vendor_clean["clean_sku"].isin(website_sku_set)

            matched_df = vendor_clean[vendor_clean["is_on_website"] == True].copy()
            missing_df = vendor_clean[vendor_clean["is_on_website"] == False].copy()

            duplicate_vendor_df = vendor_clean[
                vendor_clean["clean_sku"].duplicated(keep=False)
            ].copy()

            duplicate_website_df = website_clean[
                website_clean["clean_sku"].duplicated(keep=False)
            ].copy()

            st.session_state["comparison_missing_df"] = missing_df
            st.session_state["comparison_matched_df"] = matched_df
            st.session_state["comparison_vendor_clean_df"] = vendor_clean
            st.session_state["comparison_website_clean_df"] = website_clean

            st.subheader("Comparison Summary")

            m1, m2, m3, m4 = st.columns(4)
            m1.metric("Vendor Valid SKUs", f"{len(vendor_clean):,}")
            m2.metric("Website Valid SKUs", f"{len(website_clean):,}")
            m3.metric("Matched SKUs", f"{len(matched_df):,}")
            m4.metric("Missing SKUs", f"{len(missing_df):,}")

            m5, m6 = st.columns(2)
            m5.metric("Vendor Duplicate SKUs", f"{vendor_clean['clean_sku'].duplicated().sum():,}")
            m6.metric("Website Duplicate SKUs", f"{website_clean['clean_sku'].duplicated().sum():,}")

            st.subheader("Clean SKU Debug Preview")

            debug_col1, debug_col2 = st.columns(2)

            with debug_col1:
                st.write("Vendor Clean SKU Sample")
                st.dataframe(
                    vendor_clean[[vendor_sku_col, "clean_sku", "is_on_website"]].head(50),
                    use_container_width=True,
                )

            with debug_col2:
                st.write("Website Clean SKU Sample")
                st.dataframe(
                    website_clean[[website_sku_col, "clean_sku"]].head(50),
                    use_container_width=True,
                )

            st.subheader("Missing SKUs")
            st.dataframe(missing_df.head(500), use_container_width=True)

            st.subheader("Matched SKUs")
            st.dataframe(matched_df.head(200), use_container_width=True)

            if not duplicate_vendor_df.empty:
                st.subheader("Vendor Duplicate SKU Rows")
                st.dataframe(duplicate_vendor_df.head(200), use_container_width=True)

            if not duplicate_website_df.empty:
                st.subheader("Website Duplicate SKU Rows")
                st.dataframe(duplicate_website_df.head(200), use_container_width=True)

            missing_csv = missing_df.to_csv(index=False).encode("utf-8")
            matched_csv = matched_df.to_csv(index=False).encode("utf-8")

            st.download_button(
                label="Download Missing SKUs CSV",
                data=missing_csv,
                file_name="missing_skus.csv",
                mime="text/csv",
                key="download_missing_skus_direct",
            )

            st.download_button(
                label="Download Matched SKUs CSV",
                data=matched_csv,
                file_name="matched_skus.csv",
                mime="text/csv",
                key="download_matched_skus_direct",
            )

            st.success("SKU comparison completed successfully.")

        except Exception as exc:
            st.error("Comparison failed.")
            st.write(str(exc))

    # -----------------------------
    # Optional Full Workflow
    # -----------------------------
    st.divider()
    st.subheader("Optional: Run Full Recovery Workflow")

    st.caption(
        "Use this after direct comparison if you want Supabase wheel library lookup, "
        "Ready / Needs Review split, and workflow exports."
    )

    def optional_col(label: str, key: str) -> str | None:
        options = [""] + list(vendor_df.columns)
        selected = st.selectbox(label, options, key=key)
        return selected or None

    with st.expander("Optional validation column mapping", expanded=False):
        map_cols = st.columns(4)

        with map_cols[0]:
            price_col = optional_col("Price", "workflow_price_col")
            brand_col = optional_col("Brand", "workflow_brand_col")

        with map_cols[1]:
            model_col = optional_col("Model", "workflow_model_col")
            size_col = optional_col("Size", "workflow_size_col")

        with map_cols[2]:
            bolt_col = optional_col("Bolt Pattern", "workflow_bolt_col")
            offset_col = optional_col("Offset", "workflow_offset_col")

        with map_cols[3]:
            bore_col = optional_col("Bore / Hub", "workflow_bore_col")
            finish_col = optional_col("Finish", "workflow_finish_col")

        image_col = optional_col("Image URL / Image", "workflow_image_col")

    enable_library = st.checkbox(
        "Check missing SKUs in Supabase wheel library",
        value=bool(settings.supabase_db_url),
        key="workflow_enable_library",
    )

    if st.button("Run Full Workflow + Library Check", key="step3_run_full_workflow"):
        try:
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

            with st.spinner("Running full missing SKU recovery workflow..."):
                result = run_missing_sku_workflow(
                    vendor_df=vendor_df,
                    website_df=website_df,
                    mapping=mapping,
                    enable_wheel_library_lookup=enable_library,
                )
                st.session_state["workflow_final_missing_df"] = result.final_missing_df
                st.session_state["workflow_result"] = result

            st.subheader("Full Workflow Summary")

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

            st.subheader("Missing SKU Results With Library / Validation")
            st.dataframe(result.final_missing_df.head(500), use_container_width=True)

            st.subheader("CSV Downloads")
            for file_name, csv_text in result.exports.as_csv_text().items():
                st.download_button(
                    label=f"Download {file_name}",
                    data=csv_text.encode("utf-8"),
                    file_name=file_name,
                    mime="text/csv",
                    key=f"workflow_download_{file_name}",
                )

            st.success("Full workflow completed successfully.")

        except Exception as exc:
            st.error("Full workflow failed.")
            st.write(str(exc))

else:
    st.info("Load vendor data and website / WooCommerce SKU data first.")

# -----------------------------
# Step 4: Build Product Drafts From Vendor Sheet
# -----------------------------
st.header("4. Build Product Drafts From Vendor Sheet")

vendor_df_for_draft = st.session_state.get("vendor_df")
vendor_sku_col_for_draft = st.session_state.get("step3_vendor_sku_col")

missing_source_df = None
missing_source_label = None

# Prefer full workflow result because it has Supabase library status
if "workflow_final_missing_df" in st.session_state:
    workflow_missing_df = st.session_state["workflow_final_missing_df"].copy()

    if "wheel_library_status" in workflow_missing_df.columns:
        status_text = workflow_missing_df["wheel_library_status"].astype(str).str.upper()

        missing_source_df = workflow_missing_df[
            status_text.str.contains("NOT FOUND", na=False)
        ].copy()

        missing_source_label = "Missing SKUs not found in Supabase wheel library"

    elif "library_sku" in workflow_missing_df.columns:
        missing_source_df = workflow_missing_df[
            workflow_missing_df["library_sku"].isna()
            | (workflow_missing_df["library_sku"].astype(str).str.strip() == "")
        ].copy()

        missing_source_label = "Missing SKUs with no library_sku"

    else:
        missing_source_df = workflow_missing_df.copy()
        missing_source_label = "Workflow missing SKUs"

# Fallback: direct comparison missing SKUs
elif "comparison_missing_df" in st.session_state:
    missing_source_df = st.session_state["comparison_missing_df"].copy()
    missing_source_label = "Direct comparison missing SKUs"

if vendor_df_for_draft is None:
    st.info("Load vendor data first.")

elif missing_source_df is None or missing_source_df.empty:
    st.info(
        "No missing SKUs available for vendor-sheet draft building yet. "
        "First run comparison and Supabase library check."
    )

elif not vendor_sku_col_for_draft:
    st.warning(
        "Vendor SKU column is not selected yet. Go back to comparison step and select Vendor SKU Column."
    )

else:
    st.write(f"Source: **{missing_source_label}**")

    col_a, col_b = st.columns(2)
    col_a.metric("Rows to Build From Vendor Sheet", f"{len(missing_source_df):,}")
    col_b.metric("Vendor SKU Column", vendor_sku_col_for_draft)

    st.subheader("SKUs that will be built from vendor sheet")
    st.dataframe(missing_source_df.head(200), use_container_width=True)

    if st.button("Build Product Drafts From Vendor Sheet", key="build_vendor_product_drafts"):
        try:
            with st.spinner("Creating product drafts from vendor sheet..."):
                vendor_drafts_df = build_vendor_product_drafts(
                    missing_df=missing_source_df,
                    vendor_df=vendor_df_for_draft,
                    vendor_sku_col=vendor_sku_col_for_draft,
                )

            st.session_state["vendor_product_drafts_df"] = vendor_drafts_df

            if vendor_drafts_df.empty:
                st.warning("No vendor product drafts were created.")
            else:
                ready_count = (
                    vendor_drafts_df["validation_status"].astype(str).str.upper() == "READY"
                ).sum()

                needs_review_count = (
                    vendor_drafts_df["validation_status"].astype(str).str.upper() == "NEEDS REVIEW"
                ).sum()

                st.subheader("Vendor Product Draft Summary")

                d1, d2, d3 = st.columns(3)
                d1.metric("Draft Rows", f"{len(vendor_drafts_df):,}")
                d2.metric("Ready", f"{ready_count:,}")
                d3.metric("Needs Review", f"{needs_review_count:,}")

                preview_cols = [
                    "sku",
                    "brand",
                    "model",
                    "title",
                    "size",
                    "wheel_diameter",
                    "wheel_width",
                    "bolt_pattern",
                    "offset",
                    "center_bore",
                    "finish",
                    "price",
                    "quantity",
                    "image_url",
                    "draft_source",
                    "confidence_score",
                    "validation_status",
                    "validation_notes",
                ]

                available_preview_cols = [
                    col for col in preview_cols
                    if col in vendor_drafts_df.columns
                ]

                st.subheader("Product Draft Preview")
                st.dataframe(
                    vendor_drafts_df[available_preview_cols].head(500),
                    use_container_width=True,
                )

                with st.expander("Advanced: Field source JSON"):
                    if "field_sources_json" in vendor_drafts_df.columns:
                        st.dataframe(
                            vendor_drafts_df[["sku", "field_sources_json"]].head(50),
                            use_container_width=True,
                        )

                csv_data = vendor_drafts_df.to_csv(index=False).encode("utf-8")

                st.download_button(
                    label="Download Vendor Product Drafts CSV",
                    data=csv_data,
                    file_name="vendor_product_drafts.csv",
                    mime="text/csv",
                    key="download_vendor_product_drafts",
                )

                st.success("Vendor product drafts created successfully.")

        except Exception as exc:
            st.error("Vendor product draft creation failed.")
            st.write(str(exc))